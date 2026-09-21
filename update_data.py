import json, urllib.request, urllib.parse, datetime as dt, re
from bs4 import BeautifulSoup

SOURCES = [
    ("Ville de Marseille – Que faire cette semaine", "https://www.marseille.fr/decouvrir-marseille/actualites/que-faire-cette-semaine"),
    ("Ville de Marseille – Fêtes de quartiers", "https://www.marseille.fr/mairie/les-fetes-de-quartiers-a-marseille/"),
    ("Mairie 15/16 – Agenda", "https://mairie15-16.marseille.fr/agenda/"),
    ("MyProvence – Agenda Marseille", "https://www.myprovence.fr/agenda/evenements-manifestations/marseille"),
]

MONTHS = {
    "janvier":1,"février":2,"fevrier":2,"mars":3,"avril":4,"mai":5,"juin":6,
    "juillet":7,"août":8,"aout":8,"septembre":9,"octobre":10,
    "novembre":11,"décembre":12,"decembre":12
}
DATE_RE = re.compile(
    r"\b(?:lundi|mardi|mercredi|jeudi|vendredi|samedi|dimanche)?\s*"
    r"(\d{1,2})\s+(" + "|".join(MONTHS.keys()) + r")\s*(20\d{2})?\b", re.I
)
ISO_RE = re.compile(r"\b(20\d{2})-(\d{2})-(\d{2})\b")
ZIP_RE = re.compile(r"\b1300[1-6]\b")

GENERIC = {
    "nos belles adresses","marseille","agenda","voir plus","en savoir plus",
    "aller au contenu principal",
    "suivante","page suivante","sport","théâtre","sports & loisirs",
    "transports en commun","10e arrondissement","11e arrondissement",
    "12e arrondissement","13e arrondissement","14e arrondissement",
    "15e arrondissement","16e arrondissement"
}

def fetch(url):
    req = urllib.request.Request(
        url,
        headers={"User-Agent":"Mozilla/5.0 (compatible; MarseilleAlert/4.0)"}
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode(r.headers.get_content_charset() or "utf-8", "replace")

def clean(s):
    return re.sub(r"\s+", " ", s or "").strip()

def date_of(s):
    s = clean(s)
    m = ISO_RE.search(s)
    if m:
        return f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
    m = DATE_RE.search(s)
    if not m:
        return None
    y = int(m.group(3) or dt.date.today().year)
    return f"{y:04d}-{MONTHS[m.group(2).lower()]:02d}-{int(m.group(1)):02d}"

def category(s):
    s = s.lower()
    groups = [
        (["manifestation","rassemblement","grève","greve","mobilisation"], "Manifestation"),
        (["football","rugby","match","sport","marathon","course"], "Sport"),
        (["concert","musique","dj "], "Concert"),
        (["festival"], "Festival"),
        (["foire","salon"], "Foire / salon"),
        (["marché","marche","brocante","vide-grenier"], "Marché"),
        (["exposition","expo"], "Exposition"),
        (["théâtre","theatre","spectacle","comédie musicale"], "Spectacle"),
        (["fête","fete","quartier"], "Fête / vie locale"),
    ]
    for keys, name in groups:
        if any(k in s for k in keys):
            return name
    return "Événement"

def priority(s):
    s = s.lower()
    if any(k in s for k in [
        "manifestation","rassemblement","grève","greve","fermeture",
        "circulation","la voie est libre"
    ]):
        return "urgent"
    if any(k in s for k in [
        "match","football","foire","festival","concert","marathon",
        "course","fête","fete","feu d'artifice"
    ]):
        return "important"
    return "info"

def meaningful_title(title):
    t = clean(title).strip(" -–—:|")
    return len(t) >= 5 and t.lower() not in GENERIC and not re.fullmatch(
        r"\d+(?:e|er) arrondissement", t, re.I
    )

def jsonld_events(soup, source):
    out = []
    for tag in soup.find_all("script", attrs={"type":"application/ld+json"}):
        try:
            obj = json.loads(tag.string or tag.get_text())
        except Exception:
            continue

        def walk(x):
            if isinstance(x, list):
                for y in x:
                    walk(y)
            elif isinstance(x, dict):
                if "@graph" in x:
                    walk(x["@graph"])
                typ = x.get("@type", [])
                typ = typ if isinstance(typ, list) else [typ]
                if any(str(t).lower() == "event" for t in typ):
                    title = clean(x.get("name"))
                    if not meaningful_title(title):
                        return
                    loc = x.get("location")
                    place = ""
                    if isinstance(loc, dict):
                        place = clean(loc.get("name",""))
                        a = loc.get("address")
                        if isinstance(a, dict):
                            place = clean(" – ".join(filter(None, [
                                place, a.get("streetAddress"),
                                a.get("postalCode"), a.get("addressLocality")
                            ])))
                    blob = title + " " + place
                    out.append({
                        "title": title,
                        "date": date_of(x.get("startDate","")),
                        "place": place,
                        "category": category(blob),
                        "priority": priority(blob),
                        "url": x.get("url"),
                        "source": source
                    })
        walk(obj)
    return out

def best_container(anchor):
    node = anchor
    for _ in range(7):
        node = node.parent
        if not node:
            break
        text = clean(node.get_text(" ", strip=True))
        if DATE_RE.search(text) or ISO_RE.search(text):
            if len(text) <= 1800:
                return node, text
    return anchor.parent, clean(anchor.parent.get_text(" ", strip=True)) if anchor.parent else ""

def extract_title(anchor, container):
    title = clean(anchor.get_text(" ", strip=True))
    if meaningful_title(title):
        return title
    if container:
        for h in container.find_all(["h1","h2","h3","h4","h5"], limit=8):
            t = clean(h.get_text(" ", strip=True))
            if meaningful_title(t):
                return t
        text = clean(container.get_text(" ", strip=True))
        d = DATE_RE.search(text)
        if d:
            candidate = clean(text[:d.start()]).strip(" -–—:|")
            if meaningful_title(candidate):
                return candidate[-180:]
    return title

def scrape(name, url):
    html = fetch(url)
    soup = BeautifulSoup(html, "html.parser")
    out = jsonld_events(soup, name)

    for a in soup.find_all("a", href=True):
        href = urllib.parse.urljoin(url, a.get("href"))
        if href.startswith(("mailto:","tel:","#","javascript:")):
            continue

        title = clean(a.get_text(" ", strip=True))

        if name.startswith("MyProvence"):
            candidate_link = "/agenda/" in href and href.rstrip("/") != url.rstrip("/")
        else:
            candidate_link = meaningful_title(title)

        if not candidate_link:
            continue

        container, context = best_container(a)
        d = date_of(context)
        if not d:
            continue

        title = extract_title(a, container)
        if not meaningful_title(title):
            continue

        place = ""
        z = ZIP_RE.search(context)
        if z:
            place = z.group(0)

        blob = title + " " + context
        out.append({
            "title": title,
            "date": d,
            "place": place,
            "category": category(blob),
            "priority": priority(blob),
            "url": href,
            "source": name
        })

    return out

def normalize(items):
    today = dt.date.today()
    seen = set()
    out = []

    for e in items:
        title = clean(e.get("title"))
        place = clean(e.get("place"))
        d = e.get("date")
        url = str(e.get("url") or "")

        if not meaningful_title(title):
            continue

        blob = (title + " " + place + " " + url).lower()
        if not ("marseille" in blob or ZIP_RE.search(blob)
                or "marseille.fr" in url.lower()
                or "myprovence.fr" in url.lower()):
            continue

        if d:
            try:
                if dt.date.fromisoformat(d) < today - dt.timedelta(days=1):
                    continue
            except Exception:
                pass

        key = (title.lower(), d or "", place.lower())
        if key in seen:
            continue

        seen.add(key)
        e["id"] = "evt-" + str(abs(hash("|".join(key))))
        out.append(e)

    return sorted(
        out,
        key=lambda x: (x.get("date") or "9999-99-99", x["title"].lower())
    )[:300]

now = dt.datetime.now(dt.timezone.utc).isoformat()
all_events = []
errors = []

for name, url in SOURCES:
    try:
        all_events += scrape(name, url)
    except Exception as e:
        errors.append(f"{name}: {type(e).__name__}: {e}")

events = normalize(all_events)

with open("events.json","w",encoding="utf-8") as f:
    json.dump({
        "updatedAt": now,
        "source": "Ville de Marseille + Mairies de secteur + MyProvence",
        "events": events,
        "errors": errors
    }, f, ensure_ascii=False, indent=2)

weather_url = (
    "https://api.open-meteo.com/v1/forecast?"
    "latitude=43.2965&longitude=5.3698&"
    "current=temperature_2m,relative_humidity_2m,apparent_temperature,wind_speed_10m,weather_code&"
    "hourly=precipitation_probability,wind_gusts_10m,weather_code&"
    "forecast_days=2&timezone=Europe%2FParis"
)

try:
    w = json.loads(fetch(weather_url))
    w["updatedAt"] = now
    w["source"] = "Open-Meteo"
    alerts = []

    gust = max(
        (w.get("hourly",{}).get("wind_gusts_10m") or [])[:24],
        default=0
    )
    rain = max(
        (w.get("hourly",{}).get("precipitation_probability") or [])[:24],
        default=0
    )

    if gust >= 70:
        alerts.append({
            "level":"urgent",
            "title":"Rafales fortes",
            "message":f"Jusqu’à {round(gust)} km/h prévues dans les prochaines 24 h."
        })

    if rain >= 70:
        alerts.append({
            "level":"info",
            "title":"Pluie probable",
            "message":f"Probabilité maximale de précipitations : {round(rain)} %."
        })

    w["alerts"] = alerts

except Exception as e:
    w = {
        "updatedAt":now,
        "source":"Open-Meteo",
        "error":str(e),
        "alerts":[]
    }

with open("weather.json","w",encoding="utf-8") as f:
    json.dump(w,f,ensure_ascii=False,indent=2)

print(f"Evenements: {len(events)} | erreurs sources: {len(errors)}")
