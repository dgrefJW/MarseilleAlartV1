const LAT=43.2965,LON=5.3698;
const liveWeather=`https://api.open-meteo.com/v1/forecast?latitude=${LAT}&longitude=${LON}&current=temperature_2m,relative_humidity_2m,apparent_temperature,wind_speed_10m,weather_code&hourly=precipitation_probability,wind_gusts_10m,weather_code&forecast_days=2&timezone=Europe%2FParis`;
const cacheWeather='weather.json', cacheEvents='events.json';
const $=id=>document.getElementById(id);
const codeText={0:['☀️','Ciel dégagé'],1:['🌤️','Peu nuageux'],2:['⛅','Partiellement nuageux'],3:['☁️','Couvert'],45:['🌫️','Brouillard'],48:['🌫️','Brouillard givrant'],51:['🌦️','Bruine'],53:['🌦️','Bruine'],55:['🌧️','Bruine forte'],61:['🌧️','Pluie faible'],63:['🌧️','Pluie'],65:['🌧️','Forte pluie'],71:['🌨️','Neige'],73:['🌨️','Neige'],75:['❄️','Forte neige'],80:['🌦️','Averses'],81:['🌦️','Averses'],82:['⛈️','Fortes averses'],95:['⛈️','Orage'],96:['⛈️','Orage avec grêle'],99:['⛈️','Orage avec grêle']};

async function getJson(url){const r=await fetch(url,{cache:'no-store'});if(!r.ok)throw Error('HTTP '+r.status);return r.json()}

function renderWeather(j){
  const c=j.current||j;
  const [icon,label]=codeText[c.weather_code]||['🌤️','Météo'];
  $('temp').textContent=Math.round(c.temperature_2m)+'°';
  $('feels').textContent=Math.round(c.apparent_temperature)+'°';
  $('wind').textContent=Math.round(c.wind_speed_10m)+' km/h';
  $('humidity').textContent=c.relative_humidity_2m+'%';
  $('weatherText').textContent=label;$('weatherIcon').textContent=icon;
  renderWeatherAlerts(j);
  if(j.updatedAt)$('weatherSource').textContent='Mise à jour '+new Date(j.updatedAt).toLocaleString('fr-FR',{dateStyle:'short',timeStyle:'short'});
}
function renderWeatherAlerts(j){
  const h=j.hourly||{}; const gusts=h.wind_gusts_10m||[]; const rains=h.precipitation_probability||[];
  const maxGust=Math.max(0,...gusts.slice(0,24)), maxRain=Math.max(0,...rains.slice(0,24));
  const cards=[];
  if(maxGust>=70)cards.push(['urgent','💨 Rafales fortes','Jusqu’à '+Math.round(maxGust)+' km/h prévues dans les prochaines 24 h.']);
  if(maxRain>=70)cards.push(['info','🌧️ Pluie probable','Probabilité maximale : '+Math.round(maxRain)+' % dans les prochaines 24 h.']);
  if((j.alerts||[]).length) (j.alerts||[]).forEach(a=>cards.push([a.level||'urgent',a.title||'Alerte météo',a.message||'']));
  if(!cards.length)cards.push(['','🟢 Aucun signal météo majeur','Aucun seuil simple d’alerte détecté dans les prochaines 24 h.']);
  $('alerts').innerHTML=cards.map(x=>`<div class="card ${x[0]}"><span class="tag">MÉTÉO</span><h3>${esc(x[1])}</h3><p>${esc(x[2])}</p></div>`).join('');
}

function normalizeEvents(payload){
  const arr=Array.isArray(payload)?payload:(payload.events||payload.data||payload.results||[]);
  return arr.map(e=>({
    title:e.title?.fr||e.title||e.name||e.nom||'Événement',
    date:e.date||e.startDate||e.start||e.timing?.begin||e.date_debut||'',
    end:e.endDate||e.end||e.timing?.end||e.date_fin||'',
    place:e.location?.name||e.location?.city||e.city||e.commune||e.lieu||'Marseille',
    url:e.url||e.link||e.website||'',
    category:e.category||e.type||e.type_detail||'Événement',
    source:e.source||'France Evasion / DATAtourisme'
  })).slice(0,40);
}
function eventPriority(e){
  const s=(e.title+' '+e.category).toLowerCase();
  if(/manifest|rassemble|match|football|concert|festival|foire|marathon|course|vélodrome|velodrome/.test(s))return 'important';
  return 'info';
}
async function loadEvents(){
  try{
    const data=await getJson(cacheEvents);
    const arr=normalizeEvents(data);
    $('eventCount').textContent=arr.length+' à venir';
    $('events').innerHTML=arr.length?arr.map(e=>`<article class="card ${eventPriority(e)}"><span class="tag">${esc(e.category)}</span><h3>${esc(e.title)}</h3><p>📍 ${esc(e.place)}${e.date?' · 📅 '+esc(e.date):''}</p>${e.url?`<p><a href="${esc(e.url)}" target="_blank" rel="noopener">Voir la source →</a></p>`:''}</article>`).join(''):`<div class="card"><h3>Aucun événement en cache</h3><p>La veille automatique n’a pas encore publié de résultat.</p></div>`;
    if(data.updatedAt && $('eventsSource')) $('eventsSource').textContent='Veille : '+new Date(data.updatedAt).toLocaleString('fr-FR',{dateStyle:'short',timeStyle:'short'});
  }catch(e){
    $('eventCount').textContent='Indisponible';
    $('events').innerHTML='<div class="card"><h3>Événements temporairement indisponibles</h3><p>La prochaine mise à jour automatique réessaiera la source.</p></div>';
  }
}
async function refreshWeather(){
  try{const j=await getJson(liveWeather);renderWeather(j)}
  catch(e){try{renderWeather(await getJson(cacheWeather))}catch(_){$('weatherText').textContent='Météo indisponible'}}
}
async function notifications(){
  if(!('Notification'in window)){alert('Les notifications ne sont pas prises en charge ici.');return}
  const p=await Notification.requestPermission();
  if(p==='granted')new Notification('Marseille Alert',{body:'Les notifications locales sont activées pendant l’utilisation de l’app.'});
}
function esc(s){return String(s??'').replace(/[&<>\"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]))}
$('refresh').onclick=()=>{refreshWeather();loadEvents()};
$('notifyBtn').onclick=notifications;
refreshWeather();loadEvents();
if('serviceWorker'in navigator)navigator.serviceWorker.register('sw.js');
