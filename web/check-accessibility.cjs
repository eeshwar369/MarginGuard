const {chromium} = require('playwright');
const AxeBuilder = require('@axe-core/playwright').default;
const fs = require('node:fs/promises');
async function main(){
 const browser=await chromium.launch({executablePath:process.env.MG_BROWSER_PATH});
 const context=await browser.newContext({viewport:{width:1440,height:1050}});
 const page=await context.newPage();
 await page.goto('http://127.0.0.1:8000');
 const results=[];
 async function check(name){
   const r=await new AxeBuilder({page}).withTags(['wcag2a','wcag2aa','wcag21aa']).analyze();
   results.push({screen:name,violations:r.violations.map(v=>({id:v.id,impact:v.impact,nodes:v.nodes.map(n=>({target:n.target,summary:n.failureSummary}))}))});
 }
 await check('landing');
 await page.getByRole('button',{name:'Explore the live workspace'}).click();
 await page.getByRole('heading',{name:'See the story behind your margin.'}).waitFor();
 await check('overview');
 await page.getByRole('navigation').getByRole('button',{name:'Decision lab',exact:true}).click();
 await page.getByRole('button',{name:'Create decision memo'}).waitFor();
 await check('decision-lab');
 await fs.writeFile('../artifacts/accessibility.json',JSON.stringify(results,null,2));
 for(const r of results) console.log(r.screen,r.violations.map(v=>({id:v.id,count:v.nodes.length,examples:v.nodes.slice(0,3)})));
 await browser.close();
 process.exitCode=results.some(r=>r.violations.length)?1:0;
}
main().catch(e=>{console.error(e);process.exit(1);});
