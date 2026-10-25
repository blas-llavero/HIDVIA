'use strict';
const $=id=>document.getElementById(id);
let token=sessionStorage.getItem('hidvia_token')||'';
let currentUser=null, checkins=[], appointments=[], results=[], visits=[], notifications=[];
let offline=location.protocol==='file:' || !token;
let lastPhoto=null;
const STORE='hidvia_local_records_v2';
const savedLocal=()=>JSON.parse(localStorage.getItem(STORE)||'[]');
const storedCalibration=()=>JSON.parse(localStorage.getItem('hidvia_baseline')||'null');
const apiBase=()=>location.protocol==='file:'?(localStorage.getItem('hidvia_server')||''):location.origin;
const fmt=date=>{try{return new Intl.DateTimeFormat(window.currentLang,{dateStyle:'medium',timeStyle:'short'}).format(new Date(date))}catch{return date||'—'}};
const htmlSafe=x=>String(x??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const toast=message=>{const el=$('toast');el.textContent=message;el.classList.remove('hidden');setTimeout(()=>el.classList.add('hidden'),3600)};
function request(url,method='GET',body){
 const base=apiBase(); if(!base) return Promise.reject(new Error('No clinic server configured'));
 const opts={method,headers:{'Authorization':`Bearer ${token}`,'Content-Type':'application/json'},cache:'no-store'};
 if(body!==undefined)opts.body=JSON.stringify(body);
 return fetch(base+url,opts).then(async r=>{const data=await r.json();if(!r.ok)throw Error(data.error||'Request failed');return data});
}
function deviceScore(vals,recent,baseline){
 const n=k=>Math.max(0,Math.min(10,Number(vals[k])||0));
 let score=n('pain')*2.1+n('swelling')*2.6+n('fatigue')+n('itch')*.9+n('stress')*.45+Math.max(0,7.5-(Number(vals.sleep)||7))*2.3+(vals.drainage?12:0);
 if(recent){score+=Math.max(0,n('pain')-Number(recent.pain))*2.4;score+=Math.max(0,n('swelling')-Number(recent.swelling))*2.4}
 if(baseline){score+=Math.max(0,n('pain')-Number(baseline.pain))*1.4;score+=Math.max(0,n('swelling')-Number(baseline.swelling))*1.6}
 score=Math.max(0,Math.min(100,Math.round(score)));return {score,level:score>=65?'high':score>=40?'elevated':'low',method:'illustrative_heuristic_v1'};
}
function go(tab){document.querySelectorAll('.screen').forEach(e=>e.classList.toggle('active',e.id==='screen-'+tab));document.querySelectorAll('.tabs button').forEach(e=>e.classList.toggle('active',e.dataset.tab===tab));window.scrollTo({top:0,behavior:'instant'});}
function makeRange(key,baseline=false){const labels={pain:'pain',itch:'itch',swelling:'swelling',fatigue:'fatigue',stress:'stress'};const langKey=baseline?{pain:'baselinePain',swelling:'baselineSwelling',fatigue:'baselineFatigue'}[key]:labels[key];return `<div class="range-wrap form-field ${baseline?'':'full'}"><div class="range-caption"><label for="${baseline?'base-':''}${key}" data-i18n="${langKey}">${t(langKey)}</label><output id="${baseline?'base-':''}${key}-value">${baseline?'2':'0'}</output></div><input type="range" id="${baseline?'base-':''}${key}" min="0" max="10" value="${baseline?'2':'0'}" step="1" aria-label="${t(langKey)}"><div class="ends"><span>0</span><span>10</span></div></div>`}
function buildRanges(){
 $('symptomRanges').innerHTML=['pain','itch','swelling','fatigue','stress'].map(k=>makeRange(k)).join('');
 $('baselineRanges').innerHTML=['pain','swelling','fatigue'].map(k=>makeRange(k,true)).join('');
 document.querySelectorAll('input[type=range]').forEach(input=>input.addEventListener('input',()=>$(input.id+'-value').textContent=input.value));
 const base=storedCalibration();if(base)for(const key of ['pain','swelling','fatigue']){$('base-'+key).value=base[key];$('base-'+key+'-value').textContent=base[key]}
}
function reviewItem(row){const level=row.level||'low';let photo=row.photo_id&&token&&!offline?`<a href="${htmlSafe(apiBase()+'/api/photos/'+row.photo_id)}" class="small" target="_blank">Photo available in authenticated clinical view</a>`:'';
 return `<div class="review"><div class="review-title"><strong class="small">${htmlSafe(fmt(row.created_at))}</strong><span class="chip ${level}">${t(level)} · ${Number(row.score)||0}/100</span></div><p>${t('pain')}: ${row.pain} · ${t('swelling')}: ${row.swelling} · ${t('fatigue')}: ${row.fatigue}</p>${row.notes?`<p>${htmlSafe(row.notes)}</p>`:''}${photo}</div>`;
}
function buildHome(){
 const row=checkins[0];document.querySelectorAll('[data-i18n=riskHelp]').forEach(e=>{e.textContent=(row?.method||'').startsWith('research_logistic')?'Experimental seven-day ML score. Not clinically validated.':t('riskHelp')});$('scoreNumber').textContent=row?row.score:'—';$('scoreLevel').className='chip '+(row?.level||'low');$('scoreLevel').textContent=row?t(row.level):t('noData');$('lastDate').textContent=row?fmt(row.created_at):'—';$('scoreRing').style.background=row?`conic-gradient(${row.level==='high'?'#b75048':row.level==='elevated'?'#d09841':'#0e8390'} ${row.score}%,#def0ee ${row.score}% 100%)`:'conic-gradient(#e0efed 0 100%)';
 const upcoming=appointments.map(a=>({...a,parsed:new Date(a.when_at)})).filter(a=>a.parsed.getTime()>Date.now()-864e5).sort((a,b)=>a.parsed-b.parsed)[0];$('nextAppointment').textContent=upcoming?.title||'—';$('nextAppointmentTime').textContent=upcoming?fmt(upcoming.when_at):t('noResults');
 $('notifBadge').textContent=notifications.filter(n=>!n.seen).length;
 $('notificationList').innerHTML=notifications.slice(0,5).map(n=>`<div class="item"><span class="chip">${htmlSafe(n.kind)}</span><p>${htmlSafe(n.message)}</p><span class="muted tiny">${fmt(n.created_at)}</span></div>`).join('')||`<p class="empty">${t('noResults')}</p>`;
 $('shortHistory').innerHTML=checkins.slice(0,3).map(reviewItem).join('')||`<p class="empty">${t('noData')}</p>`;
}
function buildTimeline(){
 $('longHistory').innerHTML=checkins.map(reviewItem).join('')||`<p class="empty">${t('noData')}</p>`;
 const recent=checkins.slice(0,8).reverse();$('trendBars').innerHTML=recent.map(row=>`<div class="bar" style="height:${Math.max(7,Number(row.score)||0)}%" title="${htmlSafe(fmt(row.created_at))}: ${row.score}/100"><span>${new Date(row.created_at).getDate()}</span></div>`).join('')||`<p class="empty">${t('noData')}</p>`;
 $('resultsList').innerHTML=results.map(r=>`<div class="item"><strong>${htmlSafe(fmt(r.created_at))}</strong><p>${htmlSafe(r.summary)}</p></div>`).join('')||`<p class="empty">${t('noResults')}</p>`;
 $('visitsList').innerHTML=visits.map(r=>`<div class="item"><strong>${htmlSafe(fmt(r.created_at))}</strong><p>${htmlSafe(r.summary)}</p></div>`).join('')||`<p class="empty">${t('noResults')}</p>`;
}
async function refresh(){
 if(token){try{
  const [ch,a,n,r,v]=await Promise.all([request('/api/checkins'),request('/api/appointments'),request('/api/notifications'),request('/api/results'),request('/api/visits')]);
  checkins=ch;appointments=a;notifications=n;results=r;visits=v;offline=false;
  $('connectionStatus').textContent=t('online');
  // Native local notification bridge works if Android permission granted.
  for(const notice of n.filter(x=>!x.seen)){
   const seenKey='hidvia_notified_'+notice.id;
   if(!sessionStorage.getItem(seenKey)){
    if(window.HidviaNative?.notifyLocal)window.HidviaNative.notifyLocal('HIDVIA',notice.message);
    sessionStorage.setItem(seenKey,'1');
   }
  }
  const base=await request('/api/calibration').catch(()=>({calibrated:false}));
  $('calibStatus').textContent=base.calibrated===false?t('notCalibrated'):base.pain!==undefined?t('calibrated'):t('notCalibrated');
 }catch(e){offline=true;checkins=savedLocal();$('connectionStatus').textContent=t('offline');console.warn('Offline fallback',e)}}else{offline=true;checkins=savedLocal();$('connectionStatus').textContent=t('offline')}
 if(offline)$('calibStatus').textContent=storedCalibration()?t('calibrated'):t('notCalibrated');
 buildHome();buildTimeline();
}
async function signIn(event){event.preventDefault();$('loginError').textContent='';try{const r=await request('/api/login','POST',{email:$('loginEmail').value,password:$('loginPassword').value});if(r.user.role!=='patient'){throw Error('Use patient credentials for the mobile app')}token=r.token;currentUser=r.user;sessionStorage.setItem('hidvia_token',token);$('loginScreen').classList.add('hidden');$('patientMain').classList.remove('hidden');$('bottomTabs').classList.remove('hidden');await refresh();}catch(e){$('loginError').textContent=e.message}}
async function saveCheckin(event){event.preventDefault();const d={};for(const k of ['pain','itch','swelling','fatigue','stress'])d[k]=Number($(k).value);d.sleep=Number($('sleep').value);d.area=$('area').value;d.notes=$('notes').value;d.drainage=$('drainage').checked;
 if($('includeSensors').checked&&window.HidviaNative?.getSensors){try{d.sensors=JSON.parse(window.HidviaNative.getSensors())}catch{}}
 const btn=$('submitCheckin');btn.disabled=true;try{
  let outcome;
  if(token&&!offline){if(lastPhoto)d.image_data=lastPhoto;outcome=await request('/api/checkins','POST',d);}
  else{const base=storedCalibration();outcome=deviceScore(d,savedLocal(),base);const local={...d,...outcome,id:'local-'+Date.now(),created_at:new Date().toISOString(),photo_id:null};const records=savedLocal();records.unshift(local);localStorage.setItem(STORE,JSON.stringify(records.slice(0,90)));}
  $('checkinOutcome').classList.remove('hidden');$('outcomeText').textContent=`${t('signal')}: ${outcome.score}/100 · ${t(outcome.level)}. ${!offline&&outcome.alert_sent?t('clinicalAlert'):t('noClinicalAlert')}`;
  toast(t('submitted'));$('checkinForm').reset();lastPhoto=null;$('photoPreview').classList.add('hidden');document.querySelectorAll('#symptomRanges input[type=range]').forEach(i=>$(i.id+'-value').textContent=i.value);await refresh();
 }catch(e){toast(t('error')+': '+e.message)}finally{btn.disabled=false}}
async function saveCalibration(e){e.preventDefault();const d={pain:Number($('base-pain').value),swelling:Number($('base-swelling').value),fatigue:Number($('base-fatigue').value)};
 try{if(token&&!offline)await request('/api/calibration','POST',d);localStorage.setItem('hidvia_baseline',JSON.stringify(d));$('calibStatus').textContent=t('calibrated');toast(t('saved'))}catch(e){toast(t('error')+': '+e.message)}}
function setClinicServer(){const url=$('serverUrl').value.trim().replace(/\/$/,'');if(url&&!/^https?:\/\//i.test(url)){toast('Use http:// or https://');return}localStorage.setItem('hidvia_server',url);sessionStorage.removeItem('hidvia_token');token='';toast(t('saved'));if(window.HidviaNative?.openClinic&&url){window.HidviaNative.openClinic(url+'/patient');return}if(url&&location.protocol==='file:'){$('loginScreen').classList.remove('hidden');$('patientMain').classList.add('hidden');$('bottomTabs').classList.add('hidden');}else if(url&&location.origin!==url)location.href=url+'/patient';else refresh();}
function setLoginScreen(){const needsLogin=!!apiBase()&&!token;
 $('loginScreen').classList.toggle('hidden',!needsLogin);$('patientMain').classList.toggle('hidden',needsLogin);$('bottomTabs').classList.toggle('hidden',needsLogin);
}
function init(){buildRanges();initLanguagePicker('languageSelect');applyLanguage();$('serverUrl').value=localStorage.getItem('hidvia_server')||((location.protocol==='http:'||location.protocol==='https:')?location.origin:'');
 document.querySelectorAll('[data-tab]').forEach(e=>e.onclick=()=>go(e.dataset.tab));$('startButton').onclick=()=>go('checkin');$('allHistory').onclick=()=>go('timeline');$('checkinForm').onsubmit=saveCheckin;$('loginForm').onsubmit=signIn;$('offlineAccess').onclick=()=>{localStorage.removeItem('hidvia_server');token='';sessionStorage.removeItem('hidvia_token');setLoginScreen();refresh();};$('calibrationForm').onsubmit=saveCalibration;$('saveServer').onclick=setClinicServer;
 $('signOut').onclick=async()=>{try{if(token)await request('/api/logout','POST')}catch{}token='';sessionStorage.removeItem('hidvia_token');setLoginScreen();toast(t('signOut'))};
 $('requestSensorPermissions').onclick=()=>{if(window.HidviaNative?.requestActivitySensorPermissions)window.HidviaNative.requestActivitySensorPermissions();else toast(t('unsupported'))};
 $('readSensors').onclick=()=>{try{$('sensorsOutput').textContent=window.HidviaNative?.getSensors?.()||JSON.stringify({available:false,message:t('unsupported')},null,2)}catch(e){$('sensorsOutput').textContent=e.message}};
 $('photoInput').onchange=async e=>{const file=e.target.files?.[0];if(!file)return;if(file.size>4_000_000){toast('Maximum image size 4 MB');e.target.value='';return}if(!['image/jpeg','image/png','image/webp'].includes(file.type)){toast('JPEG, PNG or WebP only');return}const reader=new FileReader();reader.onload=()=>{lastPhoto=reader.result;$('photoPreview').src=lastPhoto;$('photoPreview').classList.remove('hidden')};reader.readAsDataURL(file)};
 window.addEventListener('hidvia-language',()=>{buildRanges();buildHome();buildTimeline();$('connectionStatus').textContent=offline?t('offline'):t('online')});
 setLoginScreen();refresh();
 if('serviceWorker'in navigator&&location.protocol.startsWith('http'))navigator.serviceWorker.register('/sw.js').catch(()=>{});
 setInterval(()=>{if(token&&document.visibilityState==='visible')refresh()},30000);
}
document.addEventListener('DOMContentLoaded',init);

window.HIDVIA_RNA_API=async data=>{if(!token||offline)throw Error("Connect to a clinician server and sign in first");return request("/api/rna","POST",data)};
