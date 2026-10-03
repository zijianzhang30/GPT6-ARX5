const {Builder,By}=require('../.qa/node_modules/selenium-webdriver');
const firefox=require('../.qa/node_modules/selenium-webdriver/firefox');
const assert=require('node:assert/strict');
(async()=>{
const d=await new Builder().usingServer('http://127.0.0.1:4444').forBrowser('firefox')
.setFirefoxOptions(new firefox.Options().setBinary('/snap/firefox/current/usr/lib/firefox/firefox').addArguments('-headless').setPreference('network.proxy.type',0)).build();
try {
 await d.get('http://127.0.0.1:8765');
 await d.wait(async()=>await d.executeScript('return document.getElementById("camera-gemini-image").naturalWidth===848'),10000);
 await d.wait(async()=>await d.executeScript('return document.getElementById("camera-external-image").naturalWidth===640'),10000);
 const gemini=d.findElement(By.id('camera-gemini-image')),external=d.findElement(By.id('camera-external-image'));
 const geminiSrc=await gemini.getAttribute('src'),externalSrc=await external.getAttribute('src');
 await d.wait(async()=>(await gemini.getAttribute('src'))!==geminiSrc&&(await external.getAttribute('src'))!==externalSrc,4000);
 const buttons=await d.findElements(By.css('[data-camera-toggle]'));
 await buttons[0].click();
 assert.equal(await d.findElement(By.id('camera-gemini-status')).getText(),'已暂停');
 assert.equal(await gemini.isDisplayed(),false);
 assert.equal(await external.isDisplayed(),true);
 await buttons[0].click();
 await d.wait(async()=>await gemini.isDisplayed(),7000);
 console.log('PASS two embedded live views refresh and pause independently without arm commands.');
} catch(e) {
 console.error('CAMERA STATE',await d.executeScript('return ["gemini","external"].map(k=>({key:k,width:document.getElementById(`camera-${k}-image`).naturalWidth,status:document.getElementById(`camera-${k}-status`).textContent,message:document.getElementById(`camera-${k}-message`).textContent}))'));
 throw e;
} finally {await d.quit();}
})().catch(e=>{console.error(e);process.exitCode=1});
