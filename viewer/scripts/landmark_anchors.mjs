// Lists every landmark model's id, kind, anchor and horizontal reach (metres) as JSON, for the
// pipeline stage that stands landmarks on the fine terrain grid (pipeline/landmark_ground.py).
// usage: node scripts/landmark_anchors.mjs [out.json]   (default ../data/interim/landmark_anchors.json)
// The landmark modules are bundled for Node with the WebGL libraries stubbed out: the mesh
// builders need none of them.
import {build} from 'esbuild';
import {mkdtempSync, writeFileSync, mkdirSync} from 'node:fs';
import {tmpdir} from 'node:os';
import path from 'node:path';
import {fileURLToPath, pathToFileURL} from 'node:url';

const here = path.dirname(fileURLToPath(import.meta.url));
const out = process.argv[2] || path.join(here, '../../data/interim/landmark_anchors.json');
const tmp = mkdtempSync(path.join(tmpdir(), 'lm-'));
const stub = path.join(tmp, 'stub.cjs');
// any import from a package resolves to a class that can be extended / called / read
// (the bundler's interop reads named imports through the prototype chain of the module object)
writeFileSync(stub, 'const any = new Proxy({}, {get: (t, k) => (typeof k === "symbol" || k === "__esModule" ? undefined : class Stub {})});\nmodule.exports = Object.create(any);\n');
const entry = path.join(tmp, 'entry.ts');
writeFileSync(
  entry,
  `import {LANDMARKS} from ${JSON.stringify(path.join(here, '../src/landmarks/index.ts'))};
import {MeshBuilder} from ${JSON.stringify(path.join(here, '../src/landmarks/kit.ts'))};
export const rows = LANDMARKS.map(lm => {
  let reach = 0;
  let top = 0;
  try {
    const b = new MeshBuilder();
    lm.build(b);
    const pos = b.build().positions.value;
    for (let i = 0; i < pos.length; i += 3) {
      reach = Math.max(reach, Math.hypot(pos[i], pos[i + 1]));
      top = Math.max(top, pos[i + 2]);
    }
  } catch (e) {
    reach = -1;
  }
  return {id: lm.id, name: lm.name, kind: lm.kind, lon: lm.anchor[0], lat: lm.anchor[1], reach_m: Math.round(reach), height_m: Math.round(top * 10) / 10, built: lm.built, end: lm.end};
});
`
);
const bundle = path.join(tmp, 'bundle.mjs');
await build({
  entryPoints: [entry],
  bundle: true,
  format: 'esm',
  platform: 'node',
  outfile: bundle,
  logLevel: 'error',
  plugins: [
    {
      name: 'stub-packages',
      setup(b) {
        // (math.gl's earcut is pure geometry and the mesh kit needs it: bundled for real)
        b.onResolve({filter: /^[^./]/}, a => (path.isAbsolute(a.path) || a.path.startsWith('@math.gl/') || a.importer.includes('node_modules') ? null : {path: stub}));
      }
    }
  ]
});
globalThis.window = globalThis.window || {};
const {rows} = await import(pathToFileURL(bundle).href);
mkdirSync(path.dirname(out), {recursive: true});
writeFileSync(out, JSON.stringify(rows));
console.log(`${rows.length} landmarks -> ${out}; build errors: ${rows.filter(r => r.reach_m < 0).length}`);
