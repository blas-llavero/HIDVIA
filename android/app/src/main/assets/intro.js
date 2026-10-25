/* HIDVIA intro video. Research concept; never medical advice. */
(()=>{
'use strict';
const src=location.protocol==='file:'?'intro.mp4':'/intro.mp4', key='hidvia_intro_shown_v1';
const text={en:['Watch video','Welcome to HIDVIA','Close','Enable sound'],ca:['Veure el vídeo','Benvingut a HIDVIA','Tancar','Activar el so'],es:['Ver el vídeo','Bienvenido a HIDVIA','Cerrar','Activar sonido'],fr:['Voir la vidéo','Bienvenue sur HIDVIA','Fermer','Activer le son'],de:['Video ansehen','Willkommen bei HIDVIA','Schließen','Ton aktivieren'],it:['Guarda il video','Benvenuto su HIDVIA','Chiudi','Attiva audio'],pt:['Ver vídeo','Bem-vindo ao HIDVIA','Fechar','Ativar som'],ar:['مشاهدة الفيديو','مرحبًا بك في HIDVIA','إغلاق','تشغيل الصوت'],zh:['观看视频','欢迎使用 HIDVIA','关闭','打开声音'],hi:['वीडियो देखें','HIDVIA में आपका स्वागत है','बंद करें','ध्वनि चालू करें']};
let modal,video,button,previous;
const tr=n=>(text[String(window.currentLang||document.documentElement.lang||'en').split('-')[0]]||text.en)[n];
const close=()=>{if(!modal||modal.hidden)return;video.pause();modal.hidden=true;document.body.style.overflow='';if(previous)previous.focus();};
function open(auto){
 previous=auto?null:document.activeElement;modal.hidden=false;document.body.style.overflow='hidden';video.currentTime=0;video.muted=!!auto;video.play().catch(()=>{});
 try{sessionStorage.setItem(key,'yes')}catch(_){}
 modal.querySelector('#hi-close').focus();
}
function start(){
const css=document.createElement('style');css.textContent=`
#hi-watch{position:fixed;bottom:calc(94px + env(safe-area-inset-bottom,0px));right:15px;z-index:80;padding:11px 15px;border-radius:24px;background:#126f80;color:#fff;border:2px solid #fff;font:700 13px system-ui;box-shadow:0 4px 18px #1239;cursor:pointer}
#hi-modal{position:fixed;inset:0;z-index:100000;background:#071b26ee;display:grid;place-items:center;padding:12px;box-sizing:border-box}
#hi-modal[hidden]{display:none}
#hi-inner{display:flex;flex-direction:column;max-height:98%;width:min(100%,460px);border-radius:16px;overflow:hidden;background:#123544;color:white;font:14px system-ui}
#hi-bar{display:flex;align-items:center;justify-content:space-between;padding:10px 12px;gap:8px}
#hi-bar button{font:600 13px system-ui;background:#2d6571;color:#fff;border:1px solid #88adb5;border-radius:9px;padding:8px;cursor:pointer}
#hi-video{width:100%;max-height:72vh;aspect-ratio:9/16;object-fit:contain;background:#06131c}
#hi-note{font:12px/1.4 system-ui;margin:9px 12px 13px;color:#c0e6eb}`;document.head.append(css);
button=document.createElement('button');button.type='button';button.id='hi-watch';button.setAttribute('aria-haspopup','dialog');button.textContent='▶ '+tr(0);document.body.append(button);
modal=document.createElement('div');modal.id='hi-modal';modal.hidden=true;
modal.innerHTML='<section id="hi-inner" role="dialog" aria-modal="true" aria-label="HIDVIA introductory video"><div id="hi-bar"><b id="hi-title"></b><div><button id="hi-sound" type="button"></button> <button id="hi-close" type="button"></button></div></div><video id="hi-video" playsinline controls preload="metadata"></video><p id="hi-note">Research illustration. RNA sensor concept only. No validated disease prediction. Not for medical decisions.</p></section>';
document.body.append(modal);video=modal.querySelector('video');video.src=src;
const refresh=()=>{button.textContent='▶ '+tr(0);modal.querySelector('#hi-title').textContent=tr(1);modal.querySelector('#hi-close').textContent=tr(2);modal.querySelector('#hi-sound').textContent='🔊 '+tr(3);};
refresh();window.addEventListener('hidvia-language',refresh);
button.onclick=()=>open(false);modal.querySelector('#hi-close').onclick=close;modal.querySelector('#hi-sound').onclick=()=>{video.muted=false;video.play().catch(()=>{});};modal.onclick=e=>{if(e.target===modal)close();};
document.addEventListener('keydown',e=>{if(e.key==='Escape')close();});video.onended=close;
try{if(sessionStorage.getItem(key)!=='yes')open(true)}catch(_){open(true)}
}
function init(){
if(location.protocol==='file:'){const probe=document.createElement('video');probe.preload='metadata';probe.src=src;probe.addEventListener('loadedmetadata',start,{once:true});probe.load();}
else fetch('/api/intro-status',{cache:'no-store'}).then(r=>r.json()).then(x=>{if(x.available)start();}).catch(()=>{});
}
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',init);else init();
})();