const {Builder,By,until}=require('../.qa/node_modules/selenium-webdriver');
const firefox=require('../.qa/node_modules/selenium-webdriver/firefox');
const assert=require('node:assert/strict');const fs=require('node:fs');
(async()=>{const d=await new Builder().usingServer('http://127.0.0.1:4444').forBrowser('firefox').setFirefoxOptions(new firefox.Options().setBinary('/snap/firefox/current/usr/lib/firefox/firefox').addArguments('-headless').setPreference('network.proxy.type',0)).build();try{
await d.manage().window().setRect({width:1440,height:1000});await d.get('http://127.0.0.1:8765');
await d.wait(until.elementTextContains(d.findElement(By.id('connection')),'未连接'),4000);
assert.equal(await d.findElement(By.id('x-value')).getText(),'—');assert(!await d.findElement(By.id('enable')).isEnabled());
await d.findElement(By.id('connect')).click();await d.wait(until.elementIsVisible(d.findElement(By.id('confirm-connect'))),2000);
assert((await d.findElement(By.id('dialog-content')).getText()).includes('回零'));
await d.findElement(By.id('close-dialog')).click();
fs.writeFileSync('docs/live-workbench.png',await d.takeScreenshot(),'base64');
console.log('PASS live UI: no invented pose; disconnected actions disabled; explicit initialization dialog. No hardware command sent.');
}finally{await d.quit();}})().catch(e=>{console.error(e);process.exitCode=1});
