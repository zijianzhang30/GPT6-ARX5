'use strict';
const $ = id => document.getElementById(id);
const token = document.querySelector('meta[name="control-token"]').content;
const client = crypto.randomUUID();
let state = null, selected = 0, keys = new Set(), held = null, busy = false, lastOk = 0;
let dirty = new Set(), gripDirty = false, toastTimer, dragging = null;
let dualMode = false, selectedArm = 'left', inFlightCommands = 0;
function controlPath(endpoint, arm=selectedArm) { return dualMode ? `/api/arms/${arm}/${endpoint}` : `/api/${endpoint}`; }
const camera = {yaw: -1.05, pitch: .52, zoom: 1};
const canvas = $('scene'), ctx = canvas.getContext('2d');
const cameraFeeds = new Map();
function createCameraFeed(key) {
  const card=document.querySelector(`[data-camera="${key}"]`),img=$(`camera-${key}-image`),message=$(`camera-${key}-message`),statusEl=$(`camera-${key}-status`),detail=$(`camera-${key}-detail`),button=document.querySelector(`[data-camera-toggle="${key}"]`);
  const feed={key,card,img,message,statusEl,detail,button,wanted:true,running:false,generation:0,abort:null,timer:null,url:null,count:0,countAt:0,previousId:null};
  function stopFeed(label='已暂停',manual=true){if(manual)feed.wanted=false;feed.running=false;feed.generation++;clearTimeout(feed.timer);feed.abort?.abort();feed.abort=null;if(feed.url)URL.revokeObjectURL(feed.url);feed.url=null;feed.img.hidden=true;feed.img.removeAttribute('src');feed.message.hidden=false;feed.message.textContent=label;feed.statusEl.textContent=label;feed.button.textContent='继续';feed.card.classList.remove('is-live','has-error');feed.card.classList.add('is-paused');}
  async function next(generation){if(!feed.running||generation!==feed.generation)return;feed.abort=new AbortController();const timeout=setTimeout(()=>feed.abort.abort(),7000);try{const response=await fetch(`/api/cameras/${key}/frame.jpg?t=${Date.now()}`,{cache:'no-store',signal:feed.abort.signal});if(!response.ok){let reason=`相机返回 ${response.status}`;try{reason=(await response.json()).error||reason;}catch{}throw new Error(reason);}const blob=await response.blob();if(!feed.running||generation!==feed.generation)return;const id=response.headers.get('X-Frame-Id');if(id!==feed.previousId){feed.previousId=id;const url=URL.createObjectURL(blob);feed.img.src=url;if(feed.url)URL.revokeObjectURL(feed.url);feed.url=url;feed.count++;}feed.img.hidden=false;feed.message.hidden=true;feed.statusEl.textContent='实时';feed.card.classList.add('is-live');feed.card.classList.remove('has-error','is-paused');const now=performance.now();if(now-feed.countAt>=1000){const fps=(feed.count*1000/(now-feed.countAt)).toFixed(1),device=response.headers.get('X-Camera-Device')||'V4L2';feed.detail.textContent=`${device} · ${feed.img.naturalWidth||'—'} × ${feed.img.naturalHeight||'—'} · ${fps} FPS`;feed.count=0;feed.countAt=now;}}catch(error){if(!feed.running||generation!==feed.generation)return;feed.img.hidden=true;feed.message.hidden=false;feed.message.textContent=error.name==='AbortError'?'取流超时，正在重试…':error.message;feed.statusEl.textContent='重试中';feed.card.classList.remove('is-live','is-paused');feed.card.classList.add('has-error');}finally{clearTimeout(timeout);feed.abort=null;if(feed.running&&generation===feed.generation)feed.timer=setTimeout(()=>next(generation),100);}}
  function startFeed(){if(document.hidden){feed.wanted=true;stopFeed('页面隐藏时已释放相机',false);return;}feed.wanted=true;feed.running=true;feed.generation++;feed.count=0;feed.countAt=performance.now();feed.button.textContent='暂停';feed.statusEl.textContent='连接中';feed.message.textContent='正在读取相机彩色接口…';feed.card.classList.remove('is-paused','has-error');next(feed.generation);}
  feed.start=startFeed;feed.stop=stopFeed;feed.button.onclick=()=>feed.running?stopFeed():startFeed();cameraFeeds.set(key,feed);startFeed();
}
for(const key of ['gemini','external'])createCameraFeed(key);
document.addEventListener('visibilitychange',()=>{for(const feed of cameraFeeds.values()){if(document.hidden&&feed.running)feed.stop('页面隐藏时已释放相机',false);else if(!document.hidden&&feed.wanted&&!feed.running)feed.start();}});
window.addEventListener('pagehide',()=>{for(const feed of cameraFeeds.values())feed.stop('页面已关闭',true);});
function toast(text) { $('toast').textContent = text; $('toast').hidden = false; clearTimeout(toastTimer); toastTimer = setTimeout(() => $('toast').hidden = true, 4200); }
async function api(data) {
  const arm=selectedArm; inFlightCommands++;
  try {
    const response = await fetch(controlPath('command',arm), {method:'POST', headers:{'Content-Type':'application/json','X-Control-Token':token}, body:JSON.stringify({...data, client}), signal:AbortSignal.timeout(1600)});
    const value = await response.json();
    if (!response.ok) throw new Error(value.error || '操作失败');
    if(arm===selectedArm){render(value);lastOk=Date.now();} return value;
  } catch (e) { toast(e.message); return null; }
  finally { inFlightCommands--; }
}
function release() { keys.clear(); held = null; document.querySelectorAll('.held').forEach(e=>e.classList.remove('held')); }
async function stop() { release(); await api({action:'stop'}); }
function showDialog(html) { release(); if(state?.enabled)stop(); $('dialog-content').innerHTML = html; $('dialog').showModal(); }
function editable() { return ['INPUT','TEXTAREA','SELECT'].includes(document.activeElement?.tagName) || $('dialog').open; }
function drawRows(prefix, labels, units) {
  $(prefix+'-rows').innerHTML = labels.map((label,i)=>`<div class="axis-row" data-row="${prefix}-${i}"><div class="axis-meta"><b>${label}</b><output id="${prefix}-actual-${i}">—</output><small id="${prefix}-bounds-${i}">${units[i]}</small></div><button class="jog motion-action" data-axis="${i}" data-sign="-1" aria-label="${label} 减小">−</button><input id="${prefix}-target-${i}" type="number" step="${prefix==='joint'?'.1':'1'}" aria-label="${label} 目标 ${units[i]}"><button class="jog motion-action" data-axis="${i}" data-sign="1" aria-label="${label} 增大">+</button></div>`).join('');
  for(let i=0;i<6;i++) $(prefix+'-target-'+i).addEventListener('input',()=>dirty.add(prefix+'-'+i));
}
drawRows('joint',['J1 · 基座','J2 · 肩部','J3 · 肘部','J4 · 腕部','J5 · 腕部','J6 · 腕部'],Array(6).fill('°'));
drawRows('cart',['X','Y','Z','Roll · 滚转','Pitch · 俯仰','Yaw · 偏航'],['mm','mm','mm','°','°','°']);
document.querySelectorAll('.axis-meta').forEach(el=>el.onclick=()=>{selected=Number(el.parentElement.dataset.row.split('-')[1]);});
for (const button of document.querySelectorAll('.jog')) {
  button.addEventListener('pointerdown', event=>{
    if(!state?.enabled || button.disabled) return;
    event.preventDefault(); release(); button.setPointerCapture(event.pointerId);
    held = button.dataset.grip ? {grip:Number(button.dataset.grip)} : {axis:Number(button.dataset.axis),sign:Number(button.dataset.sign)};
    if(held.axis!==undefined) selected=held.axis;
    button.classList.add('held');
  });
  for (const name of ['pointerup','pointercancel','lostpointercapture']) button.addEventListener(name,release);
}
$('connect').onclick=()=>{showDialog(`<h2>连接真实机械臂</h2><p>厂商 SDK 会使能电机并执行初始化，其中包含回零行为。连接后模型显示实测关节状态。</p><p>请确认机械臂工作区空旷，手远离关节和夹爪。初始化过程中网页暂停无法中断厂商构造函数；需要能够使用设备电源/急停。</p><button id="confirm-connect" class="primary">连接并初始化机械臂</button>`);$('confirm-connect').onclick=async()=>{$('dialog').close();await api({action:'connect',acknowledge_initialization:true});};};
$('disconnect').onclick=()=>api({action:'disconnect'});
$('enable').onclick=()=>state?.enabled?stop():api({action:'enable'});
$('stop').onclick=stop;
$('reset').onclick=async()=>{dirty.clear();gripDirty=false;await api({action:'reset'});};
$('speed').oninput=()=>{$('speed-value').textContent=$('speed').value+'%';};
$('speed').onchange=()=>api({action:'settings',speed:Number($('speed').value)/100});
$('frame').onchange=()=>{release();api({action:'settings',frame:$('frame').value});};
async function changeMode(mode){release();dirty.clear();selected=0;await api({action:'settings',mode});}
$('joint-tab').onclick=()=>changeMode('joint'); $('cart-tab').onclick=()=>changeMode('cartesian');
function getTargets(prefix){return Array.from({length:6},(_,i)=>{const el=$(prefix+'-target-'+i);if(el.value.trim()==='')throw new Error('目标不能为空');return Number(el.value);});}
$('apply-joints').onclick=async()=>{try {const r=await api({action:'target',joints_deg:getTargets('joint')});if(r)dirty.clear();}catch(e){toast(e.message);}};
$('apply-pose').onclick=async()=>{try {const r=await api({action:'target',pose:getTargets('cart')});if(r)dirty.clear();}catch(e){toast(e.message);}};
$('gripper').oninput=()=>{gripDirty=true;$('grip-input').value=$('gripper').value;};
$('grip-input').oninput=()=>{gripDirty=true;$('gripper').value=$('grip-input').value;};
$('apply-grip').onclick=async()=>{if($('grip-input').value==='')return toast('请输入夹爪开口');const r=await api({action:'target',[state.simulation?'gripper_mm':'gripper_raw']:Number($('grip-input').value)});if(r)gripDirty=false;};
$('keyboard').onchange=release;
$('help').onclick=()=>showDialog(`<h2>让每一次按键都有把握。</h2><p>先启用控制，再勾选「启用键盘点动」。按住持续移动，松开停止。输入数字时不会触发移动。</p><table><tr><td><kbd>Space</kbd> / <kbd>Esc</kbd></td><td>暂停并取消待执行动作</td></tr><tr><td><kbd>1</kbd>–<kbd>6</kbd></td><td>选择当前模式的控制轴</td></tr><tr><td><kbd>↑</kbd> / <kbd>↓</kbd></td><td>选中轴增加 / 减少</td></tr><tr><td><kbd>W S</kbd> / <kbd>A D</kbd> / <kbd>R F</kbd></td><td>末端模式：X / Y / Z</td></tr><tr><td><kbd>I K</kbd> / <kbd>J L</kbd> / <kbd>U O</kbd></td><td>末端模式：Rx / Ry / Rz</td></tr><tr><td><kbd>[</kbd> / <kbd>]</kbd></td><td>夹爪闭合 / 张开</td></tr></table><p>切出窗口自动暂停。不同坐标系下旋转效果不同；姿态输入使用基座坐标系的 Roll / Pitch / Yaw。</p>`);
$('hardware-info').onclick=()=>showDialog(`<h2>实机连接与反馈</h2><p>CAN 接口：${state?.channel||'can0'}。点击「连接机械臂」会调用厂商 SDK 初始化。带夹爪从臂使用 type=0。</p><p>六关节模型由 SDK 实际关节反馈驱动；目标单独显示。夹爪使用 SDK 原始位置值，毫米开口尚未标定。</p><p>控制失联会请求 SDK 保护模式。保护模式可能不保持姿态，不是物理急停。初始化由厂商库内部完成。</p>`);
$('close-dialog').onclick=()=>$('dialog').close();
$('dialog').addEventListener('click',e=>{if(e.target===$('dialog'))$('dialog').close();});
$('save-pose').onclick=()=>{showDialog(`<h2>保存当前的位置</h2><p>记录六关节角度和夹爪开口，位置保留在本次服务会话中。可导出 JSON 备份。</p><form id="save-form"><label for="pose-name">位置名称</label><input id="pose-name" maxlength="40" placeholder="例如：观察位置" autofocus><button class="primary" type="submit">保存位置</button></form>`);$('save-form').onsubmit=async e=>{e.preventDefault();const r=await api({action:'save_pose',name:$('pose-name').value});if(r)$('dialog').close();};};
$('export').onclick=()=>{const data={model:'R5',mode:'simulation',units:{joints:'degrees',gripper:'mm_simulated'},poses:state?.poses||[]};const a=document.createElement('a');a.href=URL.createObjectURL(new Blob([JSON.stringify(data,null,2)],{type:'application/json'}));a.download='r5-positions.json';a.click();setTimeout(()=>URL.revokeObjectURL(a.href),1000);};
window.addEventListener('keydown', e=>{
  if((e.code==='Escape'||(e.code==='Space'&&!editable()))&&!$('dialog').open){e.preventDefault();stop();return;}
  if(e.key==='?'&&!editable()){e.preventDefault();$('help').click();return;}
  if(editable()||!$('keyboard').checked||!state?.enabled)return;
  if(/^Digit[1-6]$/.test(e.code)){selected=Number(e.code.slice(-1))-1;e.preventDefault();return;}
  const valid=['ArrowUp','ArrowDown','KeyW','KeyS','KeyA','KeyD','KeyR','KeyF','KeyI','KeyK','KeyJ','KeyL','KeyU','KeyO','BracketLeft','BracketRight'];
  if(valid.includes(e.code)){e.preventDefault();keys.add(e.code);}
});
window.addEventListener('keyup',e=>keys.delete(e.code));
window.addEventListener('blur',()=>{release();if(state?.enabled&&state.owner===client)stop();});
document.addEventListener('visibilitychange',()=>{if(document.hidden){release();if(state?.enabled&&state.owner===client)stop();}});
document.addEventListener('focusin',e=>{if(['INPUT','SELECT','TEXTAREA'].includes(e.target.tagName))release();});
function commandVector(){const jog=[0,0,0,0,0,0];let gripper=0;
  if(held){if(held.grip)gripper=held.grip;else jog[held.axis]=held.sign;}
  if(!editable()&&$('keyboard').checked){
    if(keys.has('ArrowUp'))jog[selected]+=1;if(keys.has('ArrowDown'))jog[selected]-=1;
    if(state?.mode==='cartesian')for(const [i,a,b] of [[0,'KeyW','KeyS'],[1,'KeyA','KeyD'],[2,'KeyR','KeyF'],[3,'KeyI','KeyK'],[4,'KeyJ','KeyL'],[5,'KeyU','KeyO']]){if(keys.has(a))jog[i]+=1;if(keys.has(b))jog[i]-=1;}
    if(keys.has('BracketLeft'))gripper-=1;if(keys.has('BracketRight'))gripper+=1;
  }
  return {jog:jog.map(x=>Math.max(-1,Math.min(1,x))),gripper:Math.max(-1,Math.min(1,gripper))};
}
let savedSignature='',eventSignature='';
function render(s){state=s;
  if(dualMode){$('active-arm-label').textContent=`${selectedArm==='left'?'左臂':'右臂'}的关节、夹爪和末端控制`;$('active-arm').disabled=!!s.enabled||s.robot_status==='initializing'||inFlightCommands>0;}
  const live=!s.simulation;
  $('mode-badge').textContent=live?'实机模式':'离线模拟';
  $('connect').hidden=!live;
  $('connect').disabled=live&&s.worker_running;
  $('connect').textContent=s.robot_status==='initializing'?'初始化中…':dualMode?`连接${selectedArm==='left'?'左臂':'右臂'}`:'连接机械臂';
  $('disconnect').hidden=!live||!s.worker_running||s.robot_status==='initializing';
  $('reset').hidden=live;$('save-pose').hidden=live;$('export').hidden=live;
  $('enable').disabled=live&&!s.model_ready;
  $('backend-label').textContent=live?'实机后端 · '+(s.channel||'can0'):'离线模拟 · 不发送 CAN';
  $('grip-unit').textContent=live?'SDK 原始反馈':'mm · 模拟';
  $('grip-input-unit').textContent=live?'SDK':'mm';
  $('grip-description').textContent=live?'目标 0–5 为 SDK 原始单位；不是毫米。图中夹爪宽度为估计显示。':'0–80 mm 为模拟开口。';
  for(const id of ['gripper','grip-input']){$(id).max=live?5:80;$(id).step=live?.02:1;}
  if(live&&!s.model_ready){
    $('connection').textContent='● '+({disconnected:'机械臂未连接',initializing:'SDK 初始化中',waiting:'等待反馈',fault:'反馈故障',disconnecting:'正在断开'}[s.robot_status]||s.robot_status);
    $('notice').textContent=s.message;$('motion-state').textContent='等待真实反馈';$('grip-percent').textContent='—';
    if(!gripDirty){$('grip-input').value='';$('gripper').value=0;}
    for(const id of ['x-value','y-value','z-value','grip-value'])$(id).textContent='—';
    for(let i=0;i<6;i++){ $('joint-actual-'+i).textContent='—';$('cart-actual-'+i).textContent='—';$('joint-bounds-'+i).textContent='等待当前机械臂反馈'; }
    document.querySelectorAll('.motion-action').forEach(e=>e.disabled=true);
    return;
  }

  $('enable').textContent=s.enabled?'控制已启用 · 点击暂停':dualMode?`启用${selectedArm==='left'?'左臂':'右臂'}`:'启用控制';
  $('motion-state').textContent=s.enabled?(s.moving?'移动中':'已启用 · 就绪'):'已暂停';
  $('connection').textContent=live?`● CAN RX ${s.rx_count} · ${s.rx_age_ms} ms`:'● 本地服务已连接';$('notice').textContent=s.message;
  $('speed-value').textContent=Math.round(s.speed*100)+'%';
  if(document.activeElement!==$('speed'))$('speed').value=s.speed*100;
  $('frame').value=s.frame;
  const joint=s.mode==='joint';$('joint-panel').hidden=!joint;$('cart-panel').hidden=joint;
  for(const [id,on] of [['joint-tab',joint],['cart-tab',!joint]]){$(id).classList.toggle('active',on);$(id).setAttribute('aria-selected',String(on));}
  $('mode-hint').textContent=joint?'按住 − / + 移动；直接输入角度后点击「执行目标」。':'平移 + 旋转，全部六维。选好坐标系后按住按钮点动。';
  for(let i=0;i<6;i++){
    $('joint-actual-'+i).textContent=s.joints_deg[i].toFixed(1)+'°';
    $('joint-bounds-'+i).textContent=s.lower_deg[i].toFixed(1)+'° 至 '+s.upper_deg[i].toFixed(1)+'°'+(live?` · v ${s.velocity_deg[i].toFixed(1)}°/s · I ${s.currents[i].toFixed(2)}${s.command_deg?.[i]!=null?` · 下发 ${s.command_deg[i].toFixed(1)}° · 误差 ${s.tracking_error_deg[i].toFixed(1)}°${Math.abs(s.tracking_error_deg[i])>=2.9?' ⚠ 跟随滞后':''}`:''}`:'');
    $('cart-actual-'+i).textContent=s.pose[i].toFixed(1)+(i<3?' mm':'°');
    for(const p of ['joint','cart']){
      const el=$(p+'-target-'+i);if(!dirty.has(p+'-'+i)&&document.activeElement!==el)el.value=(p==='joint'?s.target_deg[i]:s.target_pose[i]).toFixed(1);
      document.querySelector(`[data-row="${p}-${i}"]`).classList.toggle('selected',selected===i);
    }
    $('joint-target-'+i).min=s.lower_deg[i];$('joint-target-'+i).max=s.upper_deg[i];
  }
  for(const [i,id] of ['x-value','y-value','z-value'].entries())$(id).textContent=s.pose[i].toFixed(1);
  $('grip-value').textContent=live?s.gripper_raw.toFixed(3):s.gripper_mm.toFixed(1);$('grip-percent').textContent=live?'反馈 '+s.gripper_raw.toFixed(3):Math.round(s.gripper_mm/80*100)+'%';
  if(!gripDirty){const g=live?(s.gripper_target_raw??s.gripper_raw):s.gripper_target_mm;$('gripper').value=g;$('grip-input').value=g.toFixed(live?3:1);}
  for(const el of document.querySelectorAll('.motion-action'))el.disabled=!s.enabled;
  $('reset').disabled=s.enabled;
  $('singularity').textContent=s.near_singular?'接近奇异位姿 · 建议关节控制':'工作范围：SDK 关节限位';
  const signature=JSON.stringify(s.poses)+s.enabled;
  if(signature!==savedSignature){savedSignature=signature;const list=$('saved-list');list.replaceChildren();if(!s.poses.length){const p=document.createElement('p');p.className='muted';p.textContent='把调好的位置存下来，之后一键调用。';list.append(p);}
    s.poses.forEach((pose,i)=>{const row=document.createElement('div');row.className='saved-item';const name=document.createElement('span');name.textContent=pose.name;const go=document.createElement('button');go.textContent='调用';go.disabled=!s.enabled;go.onclick=()=>api({action:'target',joints_deg:pose.joints_deg,gripper_mm:pose.gripper_mm});const del=document.createElement('button');del.textContent='删除';del.onclick=()=>api({action:'delete_pose',index:i});row.append(name,go,del);list.append(row);});}
  const es=JSON.stringify(s.events);if(es!==eventSignature){eventSignature=es;const list=$('events');list.replaceChildren();for(const item of [...s.events].reverse()){const div=document.createElement('div'),time=document.createElement('time');time.textContent=item.time;div.append(time,document.createTextNode(item.message));list.append(div);}}
}
async function cycle(){if(busy||document.hidden)return;busy=true;const arm=selectedArm;try{if(state?.enabled&&state.owner===client){await api({action:'heartbeat',...commandVector()});}else{const r=await fetch(controlPath('state',arm),{signal:AbortSignal.timeout(1500)});if(!r.ok)throw new Error();const value=await r.json();if(arm===selectedArm){render(value);lastOk=Date.now();}}}catch(e){release();$('connection').textContent='● 服务连接断开';$('notice').textContent='本地服务连接中断。请确认启动终端仍在运行。';$('enable').disabled=true;document.querySelectorAll('.motion-action').forEach(e=>e.disabled=true);}finally{busy=false;}}
setInterval(cycle,80);cycle();setInterval(()=>{if(lastOk&&Date.now()-lastOk>1000){release();$('connection').textContent='● 服务连接断开';document.querySelectorAll('.motion-action').forEach(e=>e.disabled=true);}},250);
// Project the actual URDF kinematic chain. This is a technical schematic, not a mesh or collision model.
function project(p,w,h){const cy=Math.cos(camera.yaw),sy=Math.sin(camera.yaw),cp=Math.cos(camera.pitch),sp=Math.sin(camera.pitch);const v=[p[0]-.08,p[1],p[2]-.22];const u=cy*v[0]-sy*v[1],depth=sy*v[0]+cy*v[1];const scale=Math.min(w,h)*1.32*camera.zoom;return [w*.5+u*scale,h*.53-(cp*v[2]-sp*depth)*scale,sp*v[2]+cp*depth];}
function line(a,b,color,width=1,dash=[]){ctx.beginPath();ctx.setLineDash(dash);ctx.moveTo(a[0],a[1]);ctx.lineTo(b[0],b[1]);ctx.strokeStyle=color;ctx.lineWidth=width;ctx.lineCap='round';ctx.stroke();ctx.setLineDash([]);}
function paint(){const bounds=canvas.getBoundingClientRect(),dpr=window.devicePixelRatio||1,w=bounds.width,h=bounds.height;if(canvas.width!==Math.round(w*dpr)||canvas.height!==Math.round(h*dpr)){canvas.width=w*dpr;canvas.height=h*dpr;}ctx.setTransform(dpr,0,0,dpr,0,0);ctx.clearRect(0,0,w,h);
 const pp=p=>project(p,w,h);for(let i=-8;i<=8;i++){const d=i*.1;line(pp([-.8,d,0]),pp([.8,d,0]),'#dce3e4',.7);line(pp([d,-.8,0]),pp([d,.8,0]),'#dce3e4',.7);}
 const origin=pp([0,0,.001]);for(const [v,color,label]of [[[.16,0,0],'#c47768','X'],[[0,.16,0],'#56927c','Y'],[[0,0,.16],'#698fb9','Z']]){const p=pp(v);line(origin,p,color,1.5);ctx.fillStyle=color;ctx.font='10px monospace';ctx.fillText(label,p[0]+5,p[1]);}
 if(state&&state.frames.length===6){const pts=state.points.map(pp);const segments=pts.slice(1).map((p,i)=>({a:pts[i],b:p,i})).sort((a,b)=>(a.a[2]+a.b[2])-(b.a[2]+b.b[2]));
  const corners=[[-.055,-.055,0],[.055,-.055,0],[.055,.055,0],[-.055,.055,0]].map(pp);ctx.beginPath();corners.forEach((p,i)=>i?ctx.lineTo(p[0],p[1]):ctx.moveTo(p[0],p[1]));ctx.closePath();ctx.fillStyle='#637478';ctx.fill();
  for(const seg of segments){const thickness=Math.max(5,15-seg.i)*camera.zoom;line(seg.a,seg.b,'#b7c9c7',thickness+4);line(seg.a,seg.b,seg.i%2?'#3d7067':'#73958f',thickness);}
  for(let i=1;i<pts.length;i++){const p=pts[i];ctx.beginPath();ctx.arc(p[0],p[1],(i===selected+1?9:7)*camera.zoom,0,Math.PI*2);ctx.fillStyle=i===selected+1?'#167668':'#e8f2ee';ctx.fill();ctx.strokeStyle='#446f64';ctx.lineWidth=2;ctx.stroke();ctx.fillStyle='#4b655d';ctx.font='10px monospace';ctx.fillText('J'+i,p[0]+12,p[1]-9);}
  const f=state.frames[5];const world=(x,y,z)=>[0,1,2].map(i=>f[i][3]+f[i][0]*x+f[i][1]*y+f[i][2]*z);const half=state.simulation?state.gripper_mm/2000:Math.max(0,Math.min(5,state.gripper_raw))/5*.04;
  line(pp(world(.015,-.05,0)),pp(world(.015,.05,0)),'#303e43',9*camera.zoom);
  for(const sign of [-1,1]){line(pp(world(.015,sign*half,0)),pp(world(.075,sign*half,0)),'#46565b',7*camera.zoom);line(pp(world(.075,sign*half,0)),pp(world(.075,sign*Math.max(0,half-.008),0)),'#182a2a',7*camera.zoom);}
  const tip=pp(state.points[6]);ctx.beginPath();ctx.arc(tip[0],tip[1],3,0,Math.PI*2);ctx.fillStyle='#d69d49';ctx.fill();
 }requestAnimationFrame(paint);}
canvas.addEventListener('pointerdown',e=>{dragging={x:e.clientX,y:e.clientY};canvas.setPointerCapture(e.pointerId);});canvas.addEventListener('pointermove',e=>{if(!dragging)return;camera.yaw+=(e.clientX-dragging.x)*.008;camera.pitch=Math.max(-1.4,Math.min(1.5,camera.pitch+(e.clientY-dragging.y)*.008));dragging={x:e.clientX,y:e.clientY};});canvas.addEventListener('pointerup',()=>dragging=null);canvas.addEventListener('pointercancel',()=>dragging=null);canvas.addEventListener('wheel',e=>{e.preventDefault();camera.zoom=Math.max(.5,Math.min(2.5,camera.zoom*Math.exp(-e.deltaY*.001)));},{passive:false});
for(const b of document.querySelectorAll('[data-view]'))b.onclick=()=>{const v=b.dataset.view;camera.yaw=v==='front'?0:-1.05;camera.pitch=v==='top'?Math.PI/2-.01:v==='front'?0:.52;camera.zoom=1;document.querySelectorAll('[data-view]').forEach(x=>x.classList.toggle('active',x===b));};
requestAnimationFrame(paint);

// Recording runs independently of the control heartbeat and never calls api().
const demoPhases={approach:'靠近',grasp:'夹取',lift:'抬起',release:'放下 / 松开',note:'备注'};
const demoResults={unspecified:'未标注',success:'成功抓起',failed:'未成功',partial:'部分完成'};
let demoBusy=false,demoEpisode=null,demoHistorySignature='';
async function demoRequest(path, data){
  const options={signal:AbortSignal.timeout(7000)};
  if(data!==undefined)Object.assign(options,{method:'POST',headers:{'Content-Type':'application/json','X-Control-Token':token},body:JSON.stringify(data)});
  const response=await fetch(path,options),value=await response.json();
  if(!response.ok)throw new Error(value.error||'录制服务不可用');
  return value;
}
function demoRender(episode){
  demoEpisode=episode;
  const active=episode?.status==='recording',saving=episode?.status==='saving';
  $('demo-start').disabled=demoBusy||active||saving;
  $('demo-stop').disabled=demoBusy||!active;
  $('demo-name').disabled=active||saving;
  $('demo-result').disabled=saving;
  document.querySelectorAll('[data-demo-phase],#demo-note-add').forEach(el=>el.disabled=demoBusy||!active);
  $('demo-status').classList.toggle('is-recording',active);
  $('demo-status').textContent=active?'● 录制中':saving?'保存中…':episode?.status==='error'?'录制异常 · 已停止':'准备就绪';
  if(episode){
    const c=episode.counts,seconds=episode.duration_s.toFixed(1);
    $('demo-detail').textContent=`${episode.name} · ${seconds} 秒 · 状态 ${c.states} 条 · 腕部 ${c.gemini} 帧 · 第三人称 ${c.external} 帧 · ${(episode.bytes/1048576).toFixed(1)} MB`+(episode.error?` · ${episode.error}`:'')+(c.capture_errors?` · 采集异常 ${c.capture_errors} 次`:'');
    if(!active&&!saving)$('demo-detail').textContent+=' · 文件已保留在本机';
  }
}
function demoAnalyze(episode){
  const area=$('demo-analysis');area.hidden=false;area.replaceChildren();
  const heading=document.createElement('h3');heading.textContent=episode.name;area.append(heading);
  const intro=document.createElement('p');intro.textContent=`${episode.simulation?'模拟数据':'实机数据'} · ${episode.duration_s.toFixed(1)} 秒 · 人工结果：${demoResults[episode.result]||episode.result} · 有效状态 ${episode.counts.valid_states}/${episode.counts.states} · 操作 ${episode.counts.commands} 条（拒绝或结果未知 ${episode.counts.rejected_commands} 条）`;area.append(intro);
  const table=document.createElement('table'),header=table.insertRow();
  for(const label of ['关节','最小角度','最大角度','活动范围']){const cell=document.createElement('th');cell.textContent=label;header.append(cell);}
  episode.joint_ranges_deg.forEach((range,index)=>{const row=table.insertRow();for(const value of [`J${index+1}`,range[0].toFixed(2)+'°',range[1].toFixed(2)+'°',(range[1]-range[0]).toFixed(2)+'°'])row.insertCell().textContent=value;});area.append(table);
  const grip=document.createElement('p');grip.textContent=episode.gripper_range_raw?`夹爪原始反馈范围：${episode.gripper_range_raw.map(v=>v.toFixed(3)).join(' — ')}（非毫米）`:'无实机夹爪反馈';area.append(grip);
  const markers=document.createElement('p');markers.textContent=episode.markers.length?episode.markers.map(m=>`${(m.t_ns/1e9).toFixed(1)}s ${demoPhases[m.phase]||m.phase}${m.note?'：'+m.note:''}`).join(' → '):'本次未添加动作阶段标记。';area.append(markers);
  const quality=document.createElement('p');quality.className='fine';quality.textContent=`腕部 ${episode.counts.gemini} 帧，第三人称 ${episode.counts.external} 帧；采集异常 ${episode.counts.capture_errors} 次。${episode.error||''} 此统计用于检查示范，不代表模型已训练，也不自动判断是否抓牢。`;area.append(quality);
}
async function demoHistory(){
  const episodes=await demoRequest('/api/recordings');
  const signature=JSON.stringify(episodes.map(e=>[e.id,e.status,e.counts.states]));
  if(signature===demoHistorySignature)return;demoHistorySignature=signature;
  const list=$('demo-list');list.replaceChildren();
  if(!episodes.length){list.textContent='暂无示范。';return;}
  for(const episode of episodes){
    const row=document.createElement('div');row.className='demo-saved';
    const label=document.createElement('span');label.textContent=`${episode.name} · ${new Date(episode.started_at).toLocaleString()} · ${episode.duration_s.toFixed(1)} 秒 · ${demoResults[episode.result]||episode.result}${episode.simulation?' · 模拟':''}${episode.status==='error'||episode.status==='interrupted'?' · 数据不完整':''}`;
    const analysis=document.createElement('button');analysis.textContent='查看分析';analysis.onclick=async()=>{try{demoAnalyze(await demoRequest(`/api/recordings/${episode.id}`));}catch(error){toast(error.message);}};
    row.append(label,analysis);
    if(!['recording','saving'].includes(episode.status)){const download=document.createElement('a');download.href=`/api/recordings/${episode.id}/download`;download.textContent='下载数据';download.setAttribute('download',episode.id+'.tar');row.append(download);}
    list.append(row);
  }
}
async function demoAction(action,data){
  if(demoBusy)return;demoBusy=true;demoRender(demoEpisode);
  try{
    const episode=await demoRequest('/api/recording/'+action,data);demoRender(episode);
    if(action==='start'){$('demo-result').value='unspecified';toast('录制已开始，可以遥操示范。');}
    if(action==='marker'){toast('已记录阶段 / 备注');$('demo-note').value='';}
    if(action==='stop'){$('demo-history').open=true;await demoHistory();demoAnalyze(episode);toast(episode.status==='saving'?'正在保存…':'示范已保存到本机');}
  }catch(error){toast(error.message);}finally{demoBusy=false;demoRender(demoEpisode);}
}
$('demo-start').onclick=()=>demoAction('start',{name:$('demo-name').value.trim()});
$('demo-stop').onclick=()=>demoAction('stop',{result:$('demo-result').value});
for(const button of document.querySelectorAll('[data-demo-phase]'))button.onclick=()=>demoAction('marker',{phase:button.dataset.demoPhase,note:$('demo-note').value});
$('demo-note-add').onclick=()=>demoAction('marker',{phase:'note',note:$('demo-note').value});
async function demoPoll(){
  try{
    const value=await demoRequest('/api/recording/status');$('demo-upgrade').hidden=true;
    if(!demoBusy)demoRender(value.episode);
    await demoHistory();
  }catch(error){
    $('demo-status').textContent='录制服务未连接';$('demo-start').disabled=true;$('demo-stop').disabled=true;
    document.querySelectorAll('[data-demo-phase],#demo-note-add').forEach(el=>el.disabled=true);
    if(location.port==='8765'){$('demo-upgrade').hidden=false;$('demo-detail').textContent='请使用录制工作台完成示范；它复用当前机械臂连接。';}
    else $('demo-detail').textContent='录制状态暂时未知，请检查服务。不要把断线视为已停止录制。';
  }finally{setTimeout(demoPoll,1000);}
}
demoPoll();
