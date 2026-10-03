'use strict';
const armNames={left:'左臂',right:'右臂'};
let armOverviewBusy=false;
function showArmOverview(arms){
  for(const arm of arms){
    const card=document.getElementById(`arm-${arm.id}-card`);
    if(!card)continue;
    const s=arm.state,valid=s?.model_ready===true;
    const label=!s?'服务不可用':s.robot_status==='initializing'?'正在初始化':!valid?'未就绪':s.enabled?'已使能':'已连接 · 未使能';
    card.querySelector('.arm-status').textContent=label;
    card.classList.toggle('arm-unavailable',!valid);
    card.classList.toggle('arm-selected',arm.id===selectedArm);
    card.querySelector('.arm-channel').textContent=`${arm.id==='left'?'can0 · 765931':'can1 · 5E5931'} · ${s&&Number.isFinite(s.rx_age_ms)&&s.rx_age_ms<1000?`CAN 回包 ${s.rx_age_ms} ms`:'暂无新鲜电机反馈'}`;
    card.querySelectorAll('[data-joint]').forEach((el,i)=>{el.textContent=valid&&Number.isFinite(s.joints_deg?.[i])?s.joints_deg[i].toFixed(2)+'°':'—';});
    card.querySelector('.arm-grip').textContent=valid&&Number.isFinite(s.gripper_raw)?s.gripper_raw.toFixed(3):'—';
    card.querySelector('.arm-grip-target').textContent=valid&&Number.isFinite(s.gripper_command_raw)?s.gripper_command_raw.toFixed(3):'—';
    card.querySelector('.arm-error').textContent=arm.error||(s?.error_codes?.length?`故障码：${[...new Set(s.error_codes)].join(', ')}`:s?.message||'');
  }
}
function enableDualUI(){
  dualMode=true;
  document.body.classList.add('dual-mode');
  $('dual-overview').hidden=false;$('arm-selector').hidden=false;
  $('arm-cards').innerHTML=['left','right'].map(arm=>`<article id="arm-${arm}-card" class="arm-card"><div class="small-head"><h3>${armNames[arm]} <span class="arm-channel"></span></h3><span class="arm-status pill">等待状态</span></div><dl class="arm-joints">${Array.from({length:6},(_,i)=>`<div><dt>J${i+1}</dt><dd data-joint="${i}">—</dd></div>`).join('')}</dl><div class="arm-grip-line">夹爪反馈 <strong class="arm-grip">—</strong><span>目标 <b class="arm-grip-target">—</b> · SDK 原始值</span></div><p class="arm-error"></p></article>`).join('');
  $('camera-title').textContent='左右手腕 + 全局画面';
  document.querySelector('[data-camera="gemini"] strong').textContent='左臂手腕 · Gemini 305';
  document.querySelector('[data-camera="gemini"] .camera-card-head>div>span').textContent='848 × 480 · CV2C8610015R';
  document.querySelector('[data-camera="gemini_right"]').hidden=false;
  createCameraFeed('gemini_right');
  $('demo-title').textContent='左臂遥操示范记录';
  document.querySelector('.demo-intro').textContent='此录制仍仅保存左臂状态、左腕与全局画面。双臂联合录制尚未开启。';
  $('active-arm').onchange=()=>{
    const requested=$('active-arm').value;
    if(state?.enabled||state?.robot_status==='initializing'||inFlightCommands||$('dialog').open){$('active-arm').value=selectedArm;toast('请先结束当前操作并失能，再切换机械臂。');return;}
    release();selectedArm=requested;state=null;lastOk=0;dirty.clear();gripDirty=false;savedSignature='';eventSignature='';
    for(let i=0;i<6;i++)for(const p of ['joint','cart']){$(`${p}-target-${i}`).value='';$(`${p}-actual-${i}`).textContent='—';}
    $('grip-input').value='';$('grip-value').textContent='—';$('grip-percent').textContent='—';
    for(const id of ['x-value','y-value','z-value'])$(id).textContent='—';
    document.querySelectorAll('.motion-action').forEach(e=>e.disabled=true);$('enable').disabled=true;
    $('active-arm-label').textContent=`正在读取${armNames[selectedArm]}…`;cycle();
  };
}
async function pollArmOverview(){
  if(armOverviewBusy||document.hidden){setTimeout(pollArmOverview,500);return;}
  armOverviewBusy=true;
  try{
    const response=await fetch('/api/arms',{signal:AbortSignal.timeout(1500)});
    if(response.status===404&&!dualMode)return;
    if(!response.ok)throw new Error('双臂状态服务暂不可用');
    const result=await response.json();
    if(!dualMode&&result.arms?.some(a=>a.id==='right'))enableDualUI();
    if(dualMode)showArmOverview(result.arms);
  }catch(error){if(dualMode)showArmOverview(['left','right'].map(id=>({id,state:null,error:error.message})));}
  finally{armOverviewBusy=false;if(dualMode)setTimeout(pollArmOverview,500);}
}
pollArmOverview();
