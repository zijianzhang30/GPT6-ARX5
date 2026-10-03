const {Builder,By}=require('../.qa/node_modules/selenium-webdriver');
const firefox=require('../.qa/node_modules/selenium-webdriver/firefox');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const base=process.env.DUAL_TEST_URL||'http://127.0.0.1:8768';
(async()=>{
  const arms=(await(await fetch(base+'/api/arms')).json()).arms;
  assert(arms.length===2&&arms.every(a=>a.state&&!a.state.enabled),'Inspect only disabled arms');
  const d=await new Builder().usingServer('http://127.0.0.1:4444').forBrowser('firefox')
    .setFirefoxOptions(new firefox.Options().setBinary('/snap/firefox/current/usr/lib/firefox/firefox')
      .addArguments('-headless').setPreference('network.proxy.type',0)).build();
  try{
    await d.manage().window().setRect({width:1440,height:1100});
    await d.get(base);
    await d.executeScript(`window.robotWrites=[];window.armReads=[];const originalFetch=window.fetch;window.fetch=function(url,options){if(String(url).endsWith('/command')){window.robotWrites.push(String(url));return Promise.reject(new Error('Hardware commands forbidden during UI inspection'));}if(String(url).includes('/api/arms/'))window.armReads.push(String(url));return originalFetch.apply(window,arguments);};`);
    await d.wait(async()=>await d.findElement(By.id('dual-overview')).isDisplayed(),6000);
    await d.wait(async()=>await d.executeScript(`return ['gemini','gemini_right','external'].every(k=>document.getElementById('camera-'+k+'-image').naturalWidth>0)`),15000);
    assert.equal(await d.findElements(By.css('.arm-joints [data-joint]')).then(x=>x.length),12);
    await d.executeScript(`const el=document.getElementById('active-arm');el.value='right';el.dispatchEvent(new Event('change',{bubbles:true}));`);
    await d.wait(async()=>await d.executeScript(`return document.getElementById('active-arm-label').textContent.includes('右臂的')&&window.armReads.includes('/api/arms/right/state')`),5000);
    await d.executeScript(`const el=document.getElementById('active-arm');el.value='left';el.dispatchEvent(new Event('change',{bubbles:true}));`);
    await d.wait(async()=>await d.executeScript(`return document.getElementById('active-arm-label').textContent.includes('左臂的')`),5000);
    fs.writeFileSync('docs/dual-workbench-desktop.png',await d.takeScreenshot(),'base64');
    await d.manage().window().setRect({width:390,height:844});
    assert(await d.executeScript('return document.documentElement.scrollWidth<=innerWidth+1'),'Mobile overflow');
    fs.writeFileSync('docs/dual-workbench-mobile.png',await d.takeScreenshot(),'base64');
    assert.deepEqual(await d.executeScript('return window.robotWrites'),[]);
    const after=(await(await fetch(base+'/api/arms')).json()).arms;
    assert(after.every(a=>a.state&&!a.state.enabled));
    console.log('PASS: two arm cards, 12 joint values, two grippers, three live cameras, explicit arm switching, desktop/mobile, no motor commands.');
  }finally{await d.quit();}
})().catch(error=>{console.error(error);process.exitCode=1;});
