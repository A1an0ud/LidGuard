"use strict";

const $ = id => document.getElementById(id);
const preview = $("preview"), ctx = preview.getContext("2d");
const raw = document.createElement("canvas"), rawCtx = raw.getContext("2d", {willReadFrequently:true});
const crop = document.createElement("canvas"), cropCtx = crop.getContext("2d");
const video = $("video");
let mode = "simulation", epoch = 0, stream = null, running = false, piStarted = false;
let roi = null, selecting = false, selectionStart = null, frameReady = false;
let transitioning = false, inferenceBusy = false, cameraGeneration = 0, imageGeneration = 0;
let lastPredictedVideoTime = -1;
let lastStatus = null, lastSignature = "", audioContext = null, lastAlarm = false;
const history = [];

function message(text, error=false) {
  $("message").textContent=text;
  $("message").hidden=!text;
  $("message").classList.toggle("error",error);
}

async function api(path, body) {
  const options={cache:"no-store"};
  if(body!==undefined){options.method="POST";options.headers={"Content-Type":"application/json"};options.body=JSON.stringify(body);}
  const response=await fetch(path,options);
  let data;
  try{data=await response.json();}catch{throw new Error(`Local service returned an unreadable response (${response.status}).`);}
  if(!response.ok)throw new Error(data.error||data.message||`Request failed (${response.status}).`);
  return data;
}

function sourceName(){return mode==="simulation"?"simulation":mode==="upload"?"upload":"camera";}
function connection(ok){$("connection").className=ok?"connected":"disconnected";$("connection").innerHTML="<i></i>"+(ok?"Local service connected":"Local service disconnected");}
function resetCanvas(){raw.width=640;raw.height=480;preview.width=640;preview.height=480;ctx.fillStyle="#11272f";ctx.fillRect(0,0,640,480);frameReady=false;roi=null;$("roiConfirmed").checked=false;$("emptyPreview").hidden=false;}

async function stopCapture(){
  running=false;cameraGeneration++;
  if(stream){stream.getTracks().forEach(t=>t.stop());stream=null;}
  video.srcObject=null;
  if(piStarted){piStarted=false;try{await api("/api/pi-camera",{action:"stop"});}catch{}}
  $("startCamera").hidden=!(mode==="browser"||mode==="pi");
  $("stopCamera").hidden=true;
}

async function changeMode(next){
  if(transitioning)return;
  transitioning=true;
  try{
    imageGeneration++;await stopCapture();mode=next;resetCanvas();message("");lastSignature="";lastAlarm=false;
    for(const b of document.querySelectorAll(".mode")){const active=b.dataset.mode===mode;b.classList.toggle("active",active);b.setAttribute("aria-pressed",active);}
    $("simulationStage").hidden=mode!=="simulation";$("captureStage").hidden=mode==="simulation";
    $("fileLabel").hidden=mode!=="upload";$("classifyImage").hidden=mode!=="upload";$("singleImageNote").hidden=mode!=="upload";
    $("startCamera").hidden=!(mode==="browser"||mode==="pi");$("stopCamera").hidden=true;
    const labels={simulation:["Workflow simulation","SIMULATED INPUT"],upload:["Single-image test","IMAGE CLASSIFICATION"],browser:["Computer camera","MANUAL EYE REGION"],pi:["Raspberry Pi camera","CSI · MANUAL EYE REGION"]};
    $("inputTitle").textContent=labels[mode][0];$("sourceBadge").textContent=labels[mode][1];$("sourceBadge").classList.toggle("amber",mode==="simulation");
    $("captureHint").textContent=mode==="upload"?"Use an RGB crop of one eye. You can refine the selection.":"Start the camera, then drag tightly around one eye.";
    $("emptyTitle").textContent=mode==="upload"?"No image selected":"Camera is off";
    $("emptySubtitle").textContent=mode==="upload"?"Choose a tightly cropped image of one eye.":mode==="pi"?"Picamera2 must be installed on the Raspberry Pi running this app.":"Camera access is requested only when you press Start camera.";
    $("imageFile").value="";
    const status=await api("/api/source",{source:sourceName()});paintStatus(status);connection(true);
    if(mode==="pi")message("This mode captures from the CSI camera on the Raspberry Pi running this app. Hardware operation must be checked on your device.");
  }catch(e){message(e.message,true);connection(false);}finally{transitioning=false;}
}

function drawPreview(){
  if(!frameReady)return;
  if(preview.width!==raw.width||preview.height!==raw.height){preview.width=raw.width;preview.height=raw.height;}
  ctx.drawImage(raw,0,0);
  if(roi){
    const {x,y,w,h}=roi;ctx.fillStyle="rgba(5,22,28,.42)";
    ctx.fillRect(0,0,raw.width,y);ctx.fillRect(0,y+h,raw.width,raw.height-y-h);ctx.fillRect(0,y,x,h);ctx.fillRect(x+w,y,raw.width-x-w,h);
    ctx.strokeStyle="#f2c05b";ctx.lineWidth=Math.max(1.2,raw.width/250);ctx.strokeRect(x,y,w,h);
  }
}

function point(event){const r=preview.getBoundingClientRect();return{x:Math.max(0,Math.min(raw.width,(event.clientX-r.left)*raw.width/r.width)),y:Math.max(0,Math.min(raw.height,(event.clientY-r.top)*raw.height/r.height))};}
preview.addEventListener("pointerdown",e=>{if(!frameReady)return;selectionStart=point(e);selecting=true;roi=null;$("roiConfirmed").checked=false;preview.setPointerCapture(e.pointerId);});
preview.addEventListener("pointermove",e=>{if(!selecting)return;const p=point(e);roi={x:Math.min(selectionStart.x,p.x),y:Math.min(selectionStart.y,p.y),w:Math.abs(p.x-selectionStart.x),h:Math.abs(p.y-selectionStart.y)};drawPreview();});
preview.addEventListener("pointerup",e=>{if(!selecting)return;selecting=false;if(roi&&(roi.w<24||roi.h<14)){roi=null;message("Select a larger region that includes one eye and its eyelids (at least 24 by 14 pixels).");}drawPreview();});
preview.addEventListener("pointercancel",()=>{selecting=false;roi=null;drawPreview();});
$("fullImage").onclick=()=>{if(!frameReady){message("Load an image or start the camera first.");return;}roi={x:0,y:0,w:raw.width,h:raw.height};$("roiConfirmed").checked=false;drawPreview();message("The whole image is selected. Confirm only if it is already a tight crop of one eye.");};

async function predictOnce(){
  if(inferenceBusy||transitioning||!frameReady||!roi||selecting)return;
  inferenceBusy=true;
  const thisEpoch=epoch,thisMode=mode;
  try{
    if(thisMode==="browser"){
      if(!running||video.readyState<2||video.paused||video.ended||video.currentTime===lastPredictedVideoTime)return;
      lastPredictedVideoTime=video.currentTime;
      rawCtx.drawImage(video,0,0,raw.width,raw.height);
    }
    crop.width=Math.max(1,Math.round(roi.w));crop.height=Math.max(1,Math.round(roi.h));
    cropCtx.drawImage(raw,roi.x,roi.y,roi.w,roi.h,0,0,crop.width,crop.height);
    const result=await api("/api/predict",{image:crop.toDataURL("image/png"),source:sourceName(),source_epoch:thisEpoch,roi_confirmed:$("roiConfirmed").checked});
    if(epoch===thisEpoch&&mode===thisMode){paintStatus(result);connection(true);}
  }catch(e){if(epoch===thisEpoch){message(e.message,true);connection(false);}}finally{inferenceBusy=false;}
}

$("imageFile").addEventListener("change",async e=>{
  const file=e.target.files[0];if(!file)return;
  const thisImageGeneration=++imageGeneration;
  if(file.size>5*1024*1024){message("Choose an image smaller than 5 MB.",true);return;}
  try{
    const img=await createImageBitmap(file);
    if(mode!=="upload"||thisImageGeneration!==imageGeneration){img.close();return;}
    const scale=Math.min(1,1280/Math.max(img.width,img.height));
    raw.width=Math.max(1,Math.round(img.width*scale));raw.height=Math.max(1,Math.round(img.height*scale));
    rawCtx.drawImage(img,0,0,raw.width,raw.height);img.close();frameReady=true;roi={x:0,y:0,w:raw.width,h:raw.height};
    $("roiConfirmed").checked=false;$("emptyPreview").hidden=true;drawPreview();
    const s=await api("/api/reset",{});if(mode!=="upload"||thisImageGeneration!==imageGeneration)return;paintStatus(s);
    message("Image loaded. Select one eye, confirm that you can see it clearly, then classify.");
  }catch(e2){message("The image could not be opened. "+e2.message,true);}
});
$("classifyImage").onclick=async()=>{if(!frameReady||!roi){message("Choose an image and select one eye first.");return;}message("");await predictOnce();};

function videoPreview(generation){
  if(!running||generation!==cameraGeneration||mode!=="browser")return;
  if(video.readyState>=2){if(raw.width!==video.videoWidth||raw.height!==video.videoHeight){raw.width=video.videoWidth;raw.height=video.videoHeight;}rawCtx.drawImage(video,0,0);frameReady=true;$("emptyPreview").hidden=true;drawPreview();}
  requestAnimationFrame(()=>videoPreview(generation));
}

async function piFrame(generation){
  if(!running||generation!==cameraGeneration||mode!=="pi")return;
  try{
    const response=await fetch("/api/pi-frame.jpg?t="+Date.now(),{cache:"no-store"});
    if(!response.ok){let detail;try{detail=await response.json();}catch{}throw new Error(detail?.error||"The Raspberry Pi camera did not return an image.");}
    const img=await createImageBitmap(await response.blob());
    if(!running||generation!==cameraGeneration){img.close();return;}
    raw.width=img.width;raw.height=img.height;rawCtx.drawImage(img,0,0);img.close();frameReady=true;$("emptyPreview").hidden=true;drawPreview();
    await predictOnce();
  }catch(e){message(e.message,true);}
  if(running&&generation===cameraGeneration)setTimeout(()=>piFrame(generation),500);
}

$("startCamera").onclick=async()=>{
  $("startCamera").disabled=true;
  const startMode=mode,startGeneration=++cameraGeneration;
  const stillCurrent=()=>mode===startMode&&cameraGeneration===startGeneration;
  try{
    message("");resetCanvas();lastPredictedVideoTime=-1;const s=await api("/api/source",{source:"camera"});if(!stillCurrent())return;paintStatus(s);
    if(startMode==="browser"){
      if(!navigator.mediaDevices?.getUserMedia)throw new Error("Use this app at http://localhost:8765 on the same computer as the camera. Browsers generally require localhost or HTTPS for camera access.");
      const acquired=await navigator.mediaDevices.getUserMedia({video:{width:{ideal:640},height:{ideal:480},facingMode:"user"},audio:false});
      if(!stillCurrent()){acquired.getTracks().forEach(t=>t.stop());return;}
      stream=acquired;video.srcObject=stream;await video.play();if(!stillCurrent()){acquired.getTracks().forEach(t=>t.stop());return;}running=true;videoPreview(startGeneration);
      acquired.getVideoTracks().forEach(track=>track.onended=()=>{if(!stillCurrent())return;running=false;$("roiConfirmed").checked=false;message("Camera disconnected. Observation will become unable to assess.",true);});
    }else if(startMode==="pi"){
      await api("/api/pi-camera",{action:"start"});if(!stillCurrent()){await api("/api/pi-camera",{action:"stop"});return;}piStarted=true;running=true;piFrame(startGeneration);
    }
    $("startCamera").hidden=true;$("stopCamera").hidden=false;message("Drag tightly around one eye. Check the visibility box to enable estimates; keep the eye in that region.");
  }catch(e){if(stillCurrent()){await stopCapture();message(e.name==="NotAllowedError"?"Camera permission was denied. Allow camera access in your browser or use Image test / Simulation.":e.message,true);}}finally{$("startCamera").disabled=false;}
};
$("stopCamera").onclick=async()=>{await stopCapture();$("roiConfirmed").checked=false;message("Camera stopped. The stream will become unable to assess; no further images are being processed.");};
setInterval(()=>{if(running&&mode==="browser")predictOnce();},500);

for(const button of document.querySelectorAll("[data-state]"))button.onclick=async()=>{try{message("");const s=await api("/api/simulation",{state:button.dataset.state,source_epoch:epoch});paintStatus(s);}catch(e){message(e.message,true);}};
for(const button of document.querySelectorAll("[data-mode]"))button.onclick=()=>changeMode(button.dataset.mode);

$("reset").onclick=async()=>{try{const s=await api("/api/reset",{});lastAlarm=false;paintStatus(s);message("Observation reset. Exported events still record previous activity.");}catch(e){message(e.message,true);}};
$("acknowledge").onclick=async()=>{try{paintStatus(await api("/api/ack",{}));}catch(e){message(e.message,true);}};
$("applySettings").onclick=async()=>{const n=Number($("thresholdInput").value);if(!Number.isFinite(n)||n<1||n>60){message("Choose a demo threshold between 1 and 60 seconds.");return;}try{const s=await api("/api/config",{threshold_seconds:n});lastAlarm=false;paintStatus(s);message("Demo threshold updated. This value is not a clinical exposure limit.");}catch(e){message(e.message,true);}};
$("soundEnabled").onchange=async()=>{if($("soundEnabled").checked){try{audioContext=audioContext||new (window.AudioContext||window.webkitAudioContext)();await audioContext.resume();}catch{$("soundEnabled").checked=false;message("Sound could not be enabled in this browser.");}}};
function beep(){if(!$("soundEnabled").checked||!audioContext)return;const oscillator=audioContext.createOscillator(),gain=audioContext.createGain();oscillator.type="sine";oscillator.frequency.value=650;gain.gain.setValueAtTime(.045,audioContext.currentTime);gain.gain.exponentialRampToValueAtTime(.001,audioContext.currentTime+.35);oscillator.connect(gain);gain.connect(audioContext.destination);oscillator.start();oscillator.stop(audioContext.currentTime+.36);}

const qualityLabels={ok:"Basic checks passed",no_observation:"No observation",camera_stream_stale:"Stream interrupted",simulated_input:"Simulated",ambiguous_model_score:"Uncertain estimate",minimum_resolution:"Crop too small",illumination:"Poor lighting",contrast:"Low contrast",not_mostly_clipped:"Clipped image",operator_confirmed_eye_roi:"Eye not confirmed"};
function qualityText(q){if(!q)return"No observation";if(typeof q==="string")return qualityLabels[q]||q.replaceAll("_"," ");if(q.reason){const reason=String(q.reason).split(", ")[0];return qualityLabels[reason]||reason.replaceAll("_"," ");}return q.passed?"Basic checks passed":"Input not assessable";}
function addHistory(s){
  const signature=[s.source,s.source_epoch,s.state,s.alarm,s.acknowledged,s.stale].join("|");if(signature===lastSignature)return;lastSignature=signature;
  const label=s.acknowledged&&s.alarm?"Alert acknowledged; condition remains visible":s.alarm?"Demo review alert active":s.state==="OPEN"?"Open state observed":s.state==="CLOSED"?"Closed state observed":"Unable to assess";
  history.unshift({time:new Date().toLocaleTimeString([], {hour12:false}),text:`${label} · ${s.source==="simulation"?"simulation":s.source==="upload"?"single image":"camera"}`});history.splice(5);
  $("eventList").replaceChildren(...history.map(item=>{const li=document.createElement("li"),time=document.createElement("time"),span=document.createElement("span");time.textContent=item.time;span.textContent=item.text;li.append(time,span);return li;}));
}

function paintStatus(s){
  if(s.source_epoch!==undefined&&s.source_epoch<epoch)return;
  if(s.source_epoch!==undefined)epoch=s.source_epoch;
  lastStatus=s;
  const state=s.state||"UNKNOWN";
  $("stateCard").className="state-card "+state.toLowerCase();
  $("eyeState").textContent=state==="OPEN"?"Open":state==="CLOSED"?"Closed":"Unable to assess";
  $("stateDetail").textContent=s.source==="simulation"?"Operator-selected state. Image classification is not running.":s.source==="upload"?"Single-image estimate. Duration monitoring is inactive.":s.stale?"No recent usable camera observation. Continuity has been reset.":state==="UNKNOWN"?"The current input does not support an estimate.":"Estimated from the manually selected eye region.";
  $("liveTag").textContent=s.source==="simulation"?"SIMULATION":s.source==="upload"?"SNAPSHOT":s.stale?"NO RECENT FRAME":s.sample_age_seconds==null?"NO INPUT":"CAMERA";
  const seconds=Number(s.open_seconds??s.exposure_seconds??0),threshold=Number(s.threshold_seconds??5);
  $("openTime").innerHTML=seconds.toFixed(1)+" <small>s</small>";$("thresholdDisplay").textContent=threshold+" s";
  const percent=Math.min(100,Math.max(0,seconds/threshold*100));$("progressFill").style.width=percent+"%";$("progressFill").style.background=s.alarm?"#bd5142":"#d3a446";$("progressFill").parentElement.setAttribute("aria-valuenow",Math.round(percent));
  $("alarmBanner").hidden=!s.alarm;
  $("alarmText").textContent=(s.acknowledged?"Acknowledged. ":"")+(s.alarm_unresolved?"A previous alert remains unresolved. Continuity was interrupted; review is still required.":"The detected open state reached the demo threshold. This is a request to review the demonstration.");
  $("acknowledge").disabled=Boolean(s.acknowledged);$("acknowledge").textContent=s.acknowledged?"Acknowledged":"Acknowledge this event";
  $("modelScore").textContent=s.source==="simulation"||s.score==null?"—":Number(s.score).toFixed(3);
  $("qualityLabel").textContent=qualityText(s.quality);$("eventCount").textContent=s.events_count??0;
  if(s.alarm&&!s.acknowledged&&!lastAlarm)beep();lastAlarm=Boolean(s.alarm);
  $("simEye").setAttribute("class","sim-eye "+state.toLowerCase());
  $("simCaption").textContent=state==="OPEN"?"Simulated open state":state==="CLOSED"?"Simulated closed state":"No assessable observation";
  for(const b of document.querySelectorAll("[data-state]"))b.classList.toggle("selected",s.source==="simulation"&&b.dataset.state===state);
  addHistory(s);
}

let pollBusy=false;
async function poll(){
  if(pollBusy||transitioning)return;pollBusy=true;
  try{const s=await api("/api/status");paintStatus(s);connection(true);}catch{connection(false);$("eyeState").textContent="Service unavailable";$("stateCard").className="state-card unknown";$("stateDetail").textContent="Monitoring is not active. Keep the Python application running and reconnect.";$("liveTag").textContent="OFFLINE";$("openTime").innerHTML="— <small>s</small>";$("progressFill").style.width="0%";}finally{pollBusy=false;}
}

window.addEventListener("pagehide",()=>{if(stream)stream.getTracks().forEach(t=>t.stop());});
resetCanvas();
changeMode("simulation").then(()=>api("/api/model-info")).then(info=>{$("modelInfo").textContent=JSON.stringify(info,null,2);}).catch(e=>{$("modelInfo").textContent="Model metadata is unavailable: "+e.message;});
setInterval(poll,300);
