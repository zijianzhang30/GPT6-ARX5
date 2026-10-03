const {Builder,By}=require('../.qa/node_modules/selenium-webdriver');
const firefox=require('../.qa/node_modules/selenium-webdriver/firefox');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const base=process.env.RECORDING_TEST_URL||'http://127.0.0.1:8768';
(async()=>{
  const before=await (await fetch(base+'/api/state')).json();
  assert.equal(before.enabled,false,'Only inspect an idle workbench.');
  const current=await (await fetch(base+'/api/recording/status')).json();
  assert(!['recording','saving'].includes(current.episode?.status),'Do not interrupt an existing recording.');
  const d=await new Builder().usingServer('http://127.0.0.1:4444').forBrowser('firefox')
    .setFirefoxOptions(new firefox.Options().setBinary('/snap/firefox/current/usr/lib/firefox/firefox')
      .addArguments('-headless').setPreference('network.proxy.type',0)).build();
  try{
    await d.manage().window().setRect({width:1440,height:1100});
    await d.get(base);
    await d.executeScript(`window.testRobotWrites=[];const originalFetch=window.fetch;window.fetch=function(url,options){if(url==='/api/command'){window.testRobotWrites.push(options.body);return Promise.reject(new Error('Robot commands are forbidden in recording UI test'));}return originalFetch.apply(window,arguments);};`);
    await d.wait(async()=>await d.findElement(By.id('demo-start')).isEnabled(),5000);
    console.log('Recording controls ready');
    await d.wait(async()=>await d.executeScript('return document.getElementById("camera-gemini-image").naturalWidth===848&&document.getElementById("camera-external-image").naturalWidth===640'),12000);
    const name=d.findElement(By.id('demo-name'));await name.clear();await name.sendKeys('连接验证 静止采集');
    await d.findElement(By.id('demo-start')).click();
    console.log('Start clicked');
    await d.wait(async()=>(await d.findElement(By.id('demo-status')).getText()).includes('录制中'),5000);
    await d.wait(async()=>{const s=await(await fetch(base+'/api/recording/status')).json();return s.episode.counts.gemini>=3&&s.episode.counts.external>=3&&s.episode.counts.states>=6;},7000);
    await d.findElement(By.id('demo-note')).sendKeys('只验证记录 没有运动');
    await d.findElement(By.id('demo-note-add')).click();
    await d.wait(async()=>await d.findElement(By.id('demo-stop')).isEnabled(),3000);
    await d.executeScript('document.getElementById("demo-result").value="partial"');
    await d.findElement(By.id('demo-stop')).click();
    await d.wait(async()=>await d.findElement(By.id('demo-analysis')).isDisplayed(),7000);
    const record=(await(await fetch(base+'/api/recording/status')).json()).episode;
    assert.equal(record.status,'saved');assert.equal(record.result,'partial');
    assert.equal(record.counts.commands,0);assert.equal(record.counts.capture_errors,0);
    assert.equal(record.markers[0].note,'只验证记录 没有运动');
    assert.deepEqual(await d.executeScript('return window.testRobotWrites'),[]);
    assert.equal((await(await fetch(base+'/api/state')).json()).enabled,false);
    await d.executeScript('document.getElementById("camera-title").scrollIntoView({block:"start"})');
    fs.writeFileSync('docs/recording-workbench.png',await d.takeScreenshot(),'base64');
    await d.manage().window().setRect({width:390,height:844});
    assert(await d.executeScript('return document.documentElement.scrollWidth<=window.innerWidth+1'),'Mobile overflow');
    await d.executeScript('document.getElementById("demo-title").scrollIntoView({block:"center"})');
    fs.writeFileSync('docs/recording-mobile.png',await d.takeScreenshot(),'base64');
    console.log(JSON.stringify({pass:true,episode:record.id,counts:record.counts,duration_s:record.duration_s,robot_commands:0}));
  }catch(error){
    console.error(await d.executeScript('return {status:document.getElementById("demo-status").textContent,detail:document.getElementById("demo-detail").textContent,toast:document.getElementById("toast").textContent,writes:window.testRobotWrites}'));
    throw error;
  }finally{await d.quit();}
})().catch(e=>{console.error(e);process.exitCode=1});
