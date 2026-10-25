// HIDVIA provisional vendor-neutral research RNA transport. NO medical interpretation.
'use strict';
(function(){
 const $=id=>document.getElementById(id);
 let lastReading=null;
 const status=msg=>{const e=$('rnaStatus');if(e)e.textContent=msg};
 function normalize(input,source){
  const d=typeof input==='string'?JSON.parse(input):input;
  if(!d||typeof d!=='object'||Array.isArray(d))throw Error('Expected JSON object');
  if(d.schema!=='hidvia-rna-v1')throw Error('Unsupported RNA format');
  if(!d.markers||typeof d.markers!=='object'||!Object.keys(d.markers).length)throw Error('Missing markers');
  return {...d,source};
 }
 async function upload(payload){
  if(!window.HIDVIA_RNA_API)throw Error('Sign in before sending the reading');
  const result=await window.HIDVIA_RNA_API(payload);
  status('Fictional RNA reading saved (#'+result.id+'); research only.');
 }
 async function take(raw,source){lastReading=normalize(raw,source);status('Reading received. Review and submit only fictional research data.');$('rnaPreview').textContent=JSON.stringify(lastReading,null,2).slice(0,2500);}
 function readFile(f){if(f.size>65536)throw Error('RNA file exceeds 64 KB');return f.text()}
 async function connectBle(){
  if(!navigator.bluetooth)throw Error('Web Bluetooth unavailable here. On Android use the native HIDVIA app; on desktop use Chrome/Edge over HTTPS.');
  const service=$('rnaService').value.trim(),char=$('rnaCharacteristic').value.trim();
  if(!service||!char)throw Error('Enter vendor service and characteristic UUIDs first');
  const dev=await navigator.bluetooth.requestDevice({filters:[{services:[service]}]});
  const svr=await dev.gatt.connect();const characteristic=await(await svr.getPrimaryService(service)).getCharacteristic(char);
  // One characteristic value. Fragmented vendor messages require a custom adapter.
  const parseValue=v=>take(new TextDecoder().decode(v), 'ble').catch(e=>status(e.message));
  if(characteristic.properties.notify){await characteristic.startNotifications();characteristic.addEventListener('characteristicvaluechanged',e=>parseValue(e.target.value));status('BLE notifications connected; awaiting JSON reading');}
  else{parseValue(await characteristic.readValue())}
 }
 async function connectSerial(){
  if(!navigator.serial)throw Error('Web Serial requires supported desktop Chrome/Edge and HTTPS');
  const port=await navigator.serial.requestPort();await port.open({baudRate:9600});
  let buffer=''; const reader=port.readable.getReader();status('USB serial connected; awaiting newline-terminated JSON');
  try{while(true){const {value,done}=await reader.read();if(done)break;buffer+=new TextDecoder().decode(value);if(buffer.length>65536)throw Error('Frame too large');let i;while((i=buffer.indexOf('\n'))>=0){const line=buffer.slice(0,i).trim();buffer=buffer.slice(i+1);if(line)await take(line,'serial')}}}finally{reader.releaseLock();await port.close()}
 }
 function init(){
  if(!$('rnaUpload'))return;
  $('rnaUpload').onclick=()=>upload(lastReading).catch(e=>status(e.message));
  $('rnaFile').onchange=async e=>{try{const file=e.target.files?.[0];if(file)await take(await readFile(file),'file')}catch(ex){status(ex.message)}};
  $('rnaBle').onclick=()=>{
   const service=$('rnaService').value.trim(),ch=$('rnaCharacteristic').value.trim();
   if(window.HidviaNative?.connectRnaBle){window.HidviaNative.connectRnaBle(service,ch);status('Android BLE pairing initiated. Accept system permissions if requested.');}
   else connectBle().catch(e=>status(e.message));
  };
  $('rnaSerial').onclick=()=>connectSerial().catch(e=>status(e.message));
 }
 window.HidviaRnaReceive=(json)=>take(json,'ble').catch(e=>status(e.message));
 document.addEventListener('DOMContentLoaded',init);
})();
