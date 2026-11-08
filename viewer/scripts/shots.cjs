// Headless screenshots of the viewer at given years / camera positions.
// usage: node scripts/shots.cjs <url> <outdir> <spec.json>
//   spec: [{"name":"1906","hash":"year=1906&c=-122.41,37.79&z=14&p=60&b=-20","w":1400,"h":850}]
const {chromium} = require('playwright');
const fs = require('fs');
const path = require('path');

(async () => {
  const [url, outdir, specFile] = process.argv.slice(2);
  const specs = JSON.parse(fs.readFileSync(specFile, 'utf8'));
  fs.mkdirSync(outdir, {recursive: true});
  const browser = await chromium.launch({args: ['--enable-unsafe-swiftshader', '--use-angle=swiftshader', '--ignore-gpu-blocklist']});
  for (const s of specs) {
    const page = await browser.newPage({viewport: {width: s.w || 1400, height: s.h || 850}, deviceScaleFactor: s.dpr || 1});
    page.on('console', m => { if (m.type() === 'error' || m.type() === 'warning') console.log(`[${s.name}] ${m.type()}: ${m.text().slice(0, 300)}`); });
    page.on('pageerror', e => console.log(`[${s.name}] pageerror: ${e.message}`));
    await page.goto(`${url}#${s.hash}`, {waitUntil: 'load'});
    await page.waitForFunction(() => window.__ready === true, null, {timeout: 900000});
    if (s.year !== undefined) await page.evaluate(y => window.__setYear(y), s.year);
    for (const sel of s.click || []) await page.click(sel);
    if (s.mouse) await page.mouse.click(s.mouse[0], s.mouse[1]);
    await page.waitForTimeout(s.wait || 2500);
    const t0 = Date.now();
    await page.screenshot({path: path.join(outdir, `${s.name}.png`), timeout: 900000});
    console.log(`${s.name}: ok (${Date.now() - t0} ms)`);
    await page.close();
  }
  await browser.close();
})();
