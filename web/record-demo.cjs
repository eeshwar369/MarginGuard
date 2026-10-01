const { chromium } = require('playwright');
const fs = require('node:fs/promises');
const path = require('node:path');
const { performance } = require('node:perf_hooks');
const root = path.resolve('..');
async function main() {
  const segments = JSON.parse(await fs.readFile(path.join(root,'artifacts/audio/durations.json'),'utf8'));
  const browser = await chromium.launch({executablePath:process.env.MG_BROWSER_PATH});
  const context = await browser.newContext({viewport:{width:1440,height:960},recordVideo:{dir:path.join(root,'artifacts/video'),size:{width:1440,height:960}},reducedMotion:'reduce'});
  const page = await context.newPage();
  const started = performance.now();
  const timings = [];
  await page.goto(process.env.MG_TEST_URL || 'http://127.0.0.1:8000');
  async function segment(id,action) {
    const s = segments.find(x=>x.id===id);
    await page.evaluate(caption=>{
      let node=document.querySelector('#demo-caption');
      if(!node){node=document.createElement('div');node.id='demo-caption';document.body.appendChild(node);}
      node.textContent=caption;
      Object.assign(node.style,{position:'fixed',bottom:'0',left:'0',width:'100%',padding:'18px 28px',background:'#142b23',color:'#edf4e6',font:'500 17px "DM Sans", sans-serif',zIndex:'99999',borderTop:'1px solid #54724c',textAlign:'center',boxShadow:'0 -6px 20px #19352722'});
    },s.caption);
    const begin=performance.now();timings.push({...s,start_ms:Math.round(begin-started)});
    if(action)await action();
    await page.waitForTimeout(Math.max(800,s.duration*1000+900-(performance.now()-begin)));
  }
  const nav=name=>page.getByRole('navigation').getByRole('button',{name,exact:true}).click();
  await segment('intro');
  await page.getByRole('button',{name:'Explore the live workspace'}).click();
  await page.getByRole('heading',{name:'See the story behind your margin.'}).waitFor();
  await segment('overview');
  await page.getByRole('button',{name:/Discounts increased/}).click();
  await page.locator('.evidence-table tbody tr').first().waitFor();
  await segment('evidence',async()=>{await page.waitForTimeout(7000);await page.locator('.modal .trace summary').click();await page.locator('.modal .trace').scrollIntoViewIfNeeded();});
  await page.getByRole('button',{name:'Close dialog'}).click();await nav('Investigations');
  await page.getByLabel('Business question').fill('Did discounts decrease?');
  const aiToggle=page.getByRole('checkbox',{name:'Use AI to choose analyses'});
  if(await aiToggle.isVisible())await aiToggle.uncheck();
  await page.getByRole('button',{name:'Run investigation'}).click();
  await page.getByText('Hypothesis: discount decreased · contradicted').waitFor();
  await segment('investigation',async()=>{await page.waitForTimeout(8000);await page.locator('.investigation-result .trace summary').click();await page.locator('.investigation-result').scrollIntoViewIfNeeded();});
  await nav('Decision lab');await page.getByRole('heading',{name:'Reduce shipping cost',exact:true}).waitFor();
  await segment('decision',async()=>{await page.waitForTimeout(8000);await page.getByLabel('Maximum extra return cost per order').fill('20');await page.getByRole('heading',{name:'Keep current policy',exact:true}).waitFor();await page.waitForTimeout(5000);await page.getByLabel('Maximum extra return cost per order').fill('4');});
  await page.getByRole('button',{name:'Create decision memo'}).click();
  await page.getByRole('button',{name:'Review and approve'}).click();
  await segment('approval',async()=>{await page.waitForTimeout(9000);await page.getByRole('checkbox').check();await page.getByRole('button',{name:'Approve decision',exact:true}).click();await page.getByText(/Approved by Demo reviewer/).waitFor();});
  await nav('Overview');await page.getByRole('button',{name:/Discounts increased/}).click();
  const line=await page.locator('.evidence-table tbody tr').first().locator('td strong').first().textContent();
  await page.getByRole('button',{name:/Found an incorrect cost/}).click();
  await page.getByLabel('Order line ID',{exact:true}).fill(line);await page.getByLabel('Product cost (₹)',{exact:true}).fill('950');await page.getByLabel('Shipping cost (₹)',{exact:true}).fill('68');await page.getByLabel('Reason for correction').fill('Updated supplier invoice after reconciliation');
  await segment('correction',async()=>{await page.waitForTimeout(6000);await page.getByRole('button',{name:'Create corrected version'}).click();await page.getByRole('dialog').waitFor({state:'hidden'});await nav('Decision memos');await page.getByText('stale',{exact:true}).waitFor();});
  await nav('Data sources');await page.getByRole('button',{name:'Load quality challenge'}).click();await page.getByRole('button',{name:'Acknowledge quarantine'}).waitFor();
  await page.locator('.quality-card').scrollIntoViewIfNeeded();
  await segment('quality',async()=>{await page.waitForTimeout(11000);await page.getByRole('button',{name:'Acknowledge quarantine'}).click();await page.getByText('Quarantine acknowledged. Issue history remains available.').waitFor();});
  await nav('Overview');await segment('closing');
  await context.close();
  const source=await page.video().path();
  await fs.writeFile(path.join(root,'artifacts/video/timings.json'),JSON.stringify({source,segments:timings},null,2));
  await browser.close();console.log('Browser recording complete:',source);
}
main().catch(e=>{console.error(e);process.exit(1);});
