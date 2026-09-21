import json, urllib.request, urllib.parse, datetime as dt, re
from html.parser import HTMLParser

OUT='.'
SOURCES=[
('Ville de Marseille – Que faire cette semaine','https://www.marseille.fr/decouvrir-marseille/actualites/que-faire-cette-semaine'),
('Ville de Marseille – Fêtes de quartiers','https://www.marseille.fr/mairie/les-fetes-de-quartiers-a-marseille/'),
('Mairie 15/16 – Agenda','https://mairie15-16.marseille.fr/agenda/'),
('MyProvence – Agenda Marseille','https://www.myprovence.fr/agenda/evenements-manifestations/marseille'),
]
MONTHS={'janvier':1,'février':2,'fevrier':2,'mars':3,'avril':4,'mai':5,'juin':6,'juillet':7,'août':8,'aout':8,'septembre':9,'octobre':10,'novembre':11,'décembre':12,'decembre':12}
DATE_RE=re.compile(r'\b(?:lundi|mardi|mercredi|jeudi|vendredi|samedi|dimanche)?\s*(\d{1,2})\s+(janvier|février|fevrier|mars|avril|mai|juin|juillet|août|aout|septembre|octobre|novembre|décembre|decembre)\s*(\d{4})?\b',re.I)
ISO_RE=re.compile(r'\b(20\d{2})-(\d{2})-(\d{2})\b')
ZIP_RE=re.compile(r'\b1300[1-6]\b')

def fetch(url):
    req=urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0 MarseilleAlert/3.0'})
    with urllib.request.urlopen(req,timeout=30) as r:
        return r.read().decode(r.headers.get_content_charset() or 'utf-8','replace')

def clean(s): return re.sub(r'\s+',' ',s or '').strip()
def date_of(s):
    s=clean(s); m=ISO_RE.search(s)
    if m: return f'{m.group(1)}-{m.group(2)}-{m.group(3)}'
    m=DATE_RE.search(s)
    if not m: return None
    y=int(m.group(3) or dt.date.today().year); return f'{y:04d}-{MONTHS[m.group(2).lower()]:02d}-{int(m.group(1)):02d}'
def category(s):
    s=s.lower()
    for keys,name in [(['manifestation','rassemblement','grève','greve','mobilisation'],'Manifestation'),(['football','rugby','match','sport','marathon','course'],'Sport'),(['concert','musique','dj '],'Concert'),(['festival'],'Festival'),(['foire','salon'],'Foire / salon'),(['marché','marche','brocante'],'Marché'),(['exposition','expo'],'Exposition'),(['théâtre','theatre','spectacle','comédie musicale'],'Spectacle'),(['fête','fete','quartier'],'Fête / vie locale')]:
        if any(k in s for k in keys): return name
    return 'Événement'
def priority(s):
    s=s.lower()
    if any(k in s for k in ['manifestation','rassemblement','grève','greve','fermeture','circulation','la voie est libre']): return 'urgent'
    if any(k in s for k in ['match','football','foire','festival','concert','marathon','course','fête','fete']): return 'important'
    return 'info'

class P(HTMLParser):
    def __init__(self,base): super().__init__(); self.base=base; self.links=[]; self.jsonld=[]; self.cur=None; self.script=False; self.buf=[]
    def handle_starttag(self,t,a):
        a=dict(a)
        if t=='a' and a.get('href'):
            self.cur={'href':urllib.parse.urljoin(self.base,a['href']),'text':''}; self.links.append(self.cur)
        if t=='script' and a.get('type')=='application/ld+json': self.script=True; self.buf=[]
    def handle_data(self,d):
        if self.script: self.buf.append(d)
        if self.cur: self.cur['text']=clean(self.cur['text']+' '+d)
    def handle_endtag(self,t):
        if t=='script' and self.script:
            try: self.jsonld.append(json.loads(''.join(self.buf)))
            except: pass
            self.script=False
        if t=='a': self.cur=None

def jsonld_events(objs,source):
    out=[]
    def walk(x):
        if isinstance(x,list):
            for y in x: walk(y)
        elif isinstance(x,dict):
            if '@graph' in x: walk(x['@graph'])
            typ=x.get('@type'); typ=typ if isinstance(typ,list) else [typ]
            if any(str(t).lower()=='event' for t in typ):
                title=clean(x.get('name'))
                if title:
                    loc=x.get('location'); place=''
                    if isinstance(loc,dict):
                        place=clean(loc.get('name','')); a=loc.get('address')
                        if isinstance(a,dict): place=clean(' – '.join(filter(None,[place,a.get('streetAddress'),a.get('postalCode'),a.get('addressLocality')])))
                    out.append({'title':title,'date':date_of(x.get('startDate','')),'place':place,'category':category(title+' '+place),'priority':priority(title+' '+place),'url':x.get('url'),'source':source})
    for o in objs: walk(o)
    return out

def scrape(name,url):
    html=fetch(url); p=P(url); p.feed(html); out=jsonld_events(p.jsonld,name)
    for a in p.links:
        title=clean(a['text']); blob=(title+' '+a['href']).lower()
        if len(title)>=5 and any(k in blob for k in ['evenement','événement','agenda','fete','fête','festival','concert','sport','marche','marché','manifest','foire','spectacle','exposition','salon','quartier']):
            out.append({'title':title,'date':date_of(title),'place':'','category':category(title),'priority':priority(title),'url':a['href'],'source':name})
    return out

def normalize(items):
    today=dt.date.today(); seen=set(); out=[]
    for e in items:
        title=clean(e.get('title')); place=clean(e.get('place')); blob=(title+' '+place+' '+str(e.get('url',''))).lower(); d=e.get('date')
        if not title or not ('marseille' in blob or ZIP_RE.search(blob)): continue
        if d:
            try:
                if dt.date.fromisoformat(d)<today-dt.timedelta(days=1): continue
            except: pass
        key=(title.lower(),d or '',place.lower())
        if key in seen: continue
        seen.add(key); e['id']='evt-'+str(abs(hash('|'.join(map(str,key))))); out.append(e)
    return sorted(out,key=lambda x:(x.get('date') or '9999-99-99',x['title'].lower()))[:300]

now=dt.datetime.now(dt.timezone.utc).isoformat(); all_events=[]; errors=[]
for name,url in SOURCES:
    try: all_events += scrape(name,url)
    except Exception as e: errors.append(f'{name}: {e}')
with open('events.json','w',encoding='utf-8') as f: json.dump({'updatedAt':now,'source':'Ville de Marseille + Mairies de secteur + MyProvence','events':normalize(all_events),'errors':errors},f,ensure_ascii=False,indent=2)

weather_url=('https://api.open-meteo.com/v1/forecast?latitude=43.2965&longitude=5.3698&current=temperature_2m,relative_humidity_2m,apparent_temperature,wind_speed_10m,weather_code&hourly=precipitation_probability,wind_gusts_10m,weather_code&forecast_days=2&timezone=Europe%2FParis')
try:
    w=json.loads(fetch(weather_url)); w['updatedAt']=now; w['source']='Open-Meteo'; alerts=[]
    gust=max((w.get('hourly',{}).get('wind_gusts_10m') or [])[:24],default=0); rain=max((w.get('hourly',{}).get('precipitation_probability') or [])[:24],default=0)
    if gust>=70: alerts.append({'level':'urgent','title':'Rafales fortes','message':f'Jusqu’à {round(gust)} km/h prévues dans les prochaines 24 h.'})
    if rain>=70: alerts.append({'level':'info','title':'Pluie probable','message':f'Probabilité maximale de précipitations : {round(rain)} %.'})
    w['alerts']=alerts
except Exception as e: w={'updatedAt':now,'source':'Open-Meteo','error':str(e),'alerts':[]}
with open('weather.json','w',encoding='utf-8') as f: json.dump(w,f,ensure_ascii=False,indent=2)
print(f'Evenements: {len(json.load(open("events.json",encoding="utf-8"))["events"])} | erreurs sources: {len(errors)}')
