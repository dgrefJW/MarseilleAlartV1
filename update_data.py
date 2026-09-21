import json, urllib.request, datetime, os, re

OUT="MarseilleAlertBuild/data"
os.makedirs(OUT, exist_ok=True)
now=datetime.datetime.now(datetime.timezone.utc).isoformat()

def get(url):
    req=urllib.request.Request(url, headers={"User-Agent":"MarseilleAlert/2.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode("utf-8"))

# Public event feed documented on data.gouv.fr.
events_url="https://france-evasion-regions.com/api/open/evenements.json?departement=13"
try:
    raw=get(events_url)
    arr=raw if isinstance(raw,list) else raw.get("events",raw.get("data",raw.get("results",[])))
    # Keep Marseille / Bouches-du-Rhône items; the frontend performs a stricter Marseille filter.
    events={"updatedAt":now,"source":"France Evasion / DATAtourisme","events":arr[:500],"error":None}
except Exception as e:
    events={"updatedAt":now,"source":"France Evasion / DATAtourisme","events":[],"error":str(e)}

with open(f"{OUT}/events.json","w",encoding="utf-8") as f:
    json.dump(events,f,ensure_ascii=False,indent=2)

weather_url=("https://api.open-meteo.com/v1/forecast?latitude=43.2965&longitude=5.3698"
             "&current=temperature_2m,relative_humidity_2m,apparent_temperature,wind_speed_10m,weather_code"
             "&hourly=precipitation_probability,wind_gusts_10m,weather_code&forecast_days=2&timezone=Europe%2FParis")
try:
    w=get(weather_url); w["updatedAt"]=now; w["source"]="Open-Meteo"
    alerts=[]
    gust=max((w.get("hourly",{}).get("wind_gusts_10m") or [])[:24],default=0)
    rain=max((w.get("hourly",{}).get("precipitation_probability") or [])[:24],default=0)
    if gust>=70: alerts.append({"level":"urgent","title":"Rafales fortes","message":f"Jusqu’à {round(gust)} km/h prévues dans les prochaines 24 h."})
    if rain>=70: alerts.append({"level":"info","title":"Pluie probable","message":f"Probabilité maximale de précipitations : {round(rain)} %."})
    w["alerts"]=alerts
except Exception as e:
    w={"updatedAt":now,"source":"Open-Meteo","error":str(e)}

with open(f"{OUT}/weather.json","w",encoding="utf-8") as f:
    json.dump(w,f,ensure_ascii=False,indent=2)
