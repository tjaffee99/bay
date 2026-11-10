#!/usr/bin/env node
// Offline preview of landmark reconstructions: no browser, no WebGL.
//
// Bundles the landmark modules for Node (esbuild), builds the meshes of the chosen
// landmarks the way landmarks/index.ts does (local metres around each anchor, turned
// into lon / lat offsets with the same constants; bridges from sea level), and draws
// them with a small software z-buffer rasteriser: flat shading with the mesh colours,
// perspective or orthographic camera, optional reference polylines (an OSM centreline,
// a surveyed axis) on top so misalignment shows. Writes a PNG (zlib only).
// There is no terrain offline: every landmark stands at z = 0 (in the viewer the
// non-bridge ones stand on the ground at their anchor).
//
// usage (from viewer/):
//   node scripts/landmark_preview.mjs --match '^bay_bridge' --view top --out /tmp/plan.png
//   node scripts/landmark_preview.mjs --ids bay_bridge_west_span --view 130,12 --out /tmp/west.png
//
//   --ids a,b,c         landmark ids (exact)            --match <regex>   ids by pattern
//   --year 1950         only landmarks standing then (built[1] <= year < end)
//   --list              print ids, dates, triangle counts and exit
//   --view top          plan view, north up (orthographic)
//   --view az,el[,dist] camera seen FROM compass azimuth az (deg), el deg above the horizon;
//                       dist in metres = perspective, omitted = orthographic
//   --target lon,lat[,z]  look-at point (default: centre of the meshes' bounding box)
//   --span m            metres across the picture (default: fit)
//   --size WxH          default 1800x1000        --ss n   supersampling (default 2)
//   --ref file[:color[:width]]  reference lines, repeatable. JSON: GeoJSON (Line / Polygon
//                       features), or [[lon,lat(,z)],…], or [[[lon,lat],…],…], or
//                       {name: polyline(s)}. Drawn over the model unless --refdepth.
//   --ground z          draw a flat plane at height z under the model (default: none)
//   --bg #rrggbb        background (default water blue-grey)
//   --out file.png
import {build} from 'esbuild';
import {deflateSync} from 'node:zlib';
import {readFileSync, writeFileSync, mkdirSync, mkdtempSync, rmSync} from 'node:fs';
import {dirname, join, resolve} from 'node:path';
import {fileURLToPath, pathToFileURL} from 'node:url';
import {tmpdir} from 'node:os';

const HERE = dirname(fileURLToPath(import.meta.url));
const LM_DIR = resolve(HERE, '../src/landmarks');
const ORIGIN = [-122.42, 37.78]; // landmarks/index.ts
const M_PER_DEG_LAT = 110_574;
const kxAt = lat => 111_320 * Math.cos((lat * Math.PI) / 180);

const die = msg => {
  console.error(`landmark_preview: ${msg}`);
  process.exit(1);
};

// ---------------------------------------------------------------- arguments
function parseArgs(argv) {
  const a = {ref: [], size: [1800, 1000], ss: 2, view: 'top', bg: '#AFC3CC'};
  for (let i = 0; i < argv.length; i++) {
    const k = argv[i];
    const v = () => argv[++i];
    if (k === '--ids') a.ids = v().split(',');
    else if (k === '--match') a.match = new RegExp(v());
    else if (k === '--year') a.year = Number(v());
    else if (k === '--list') a.list = true;
    else if (k === '--view') a.view = v();
    else if (k === '--target') a.target = v().split(',').map(Number);
    else if (k === '--span') a.span = Number(v());
    else if (k === '--size') a.size = v().split('x').map(Number);
    else if (k === '--ss') a.ss = Number(v());
    else if (k === '--ref') a.ref.push(v());
    else if (k === '--refdepth') a.refdepth = true;
    else if (k === '--ground') a.ground = Number(v());
    else if (k === '--bg') a.bg = v();
    else if (k === '--out') a.out = v();
    else die(`unknown option ${k} (see the header of this script)`);
  }
  return a;
}

// ---------------------------------------------------------------- landmarks
/** Bundle every landmark module index.ts registers (same order), without index.ts itself
 *  (it pulls in deck.gl); the terrain lookup is stubbed (no elevation grids offline). */
async function loadLandmarks() {
  const index = readFileSync(join(LM_DIR, 'index.ts'), 'utf8');
  const skip = new Set(['./kit', './merged-layer', './types']);
  const imports = [...index.matchAll(/^import\s+\{([^}]+)\}\s+from\s+'(\.\/[^']+)';/gm)].filter(m => !skip.has(m[2]) && !/^type\s/.test(m[1].trim()));
  const list = index.match(/export const LANDMARKS[^=]*=\s*\[([\s\S]*?)\];/);
  if (!list) throw new Error('LANDMARKS array not found in landmarks/index.ts');
  const entry =
    imports.map(m => `import {${m[1]}} from '${m[2]}';`).join('\n') +
    `\nimport {MeshBuilder} from './kit';\nexport {MeshBuilder};\nexport const LANDMARKS = [${list[1]}];\n`;
  const stub = {
    name: 'stub-elevation',
    setup(b) {
      b.onResolve({filter: /layers\/elevation$/}, () => ({path: 'elevation-stub', namespace: 'stub'}));
      b.onLoad({filter: /.*/, namespace: 'stub'}, () => ({contents: 'export const elevationAt = () => 0; export const hasElevation = () => false;', loader: 'js'}));
    }
  };
  const out = await build({
    stdin: {contents: entry, resolveDir: LM_DIR, sourcefile: 'preview-entry.ts', loader: 'ts'},
    bundle: true,
    format: 'esm',
    platform: 'node',
    write: false,
    logLevel: 'silent',
    plugins: [stub]
  });
  const dir = mkdtempSync(join(tmpdir(), 'lm-preview-'));
  const file = join(dir, 'landmarks.mjs');
  writeFileSync(file, out.outputFiles[0].text);
  try {
    return await import(pathToFileURL(file).href);
  } finally {
    rmSync(dir, {recursive: true, force: true});
  }
}

// ---------------------------------------------------------------- references
function readRef(spec) {
  const [file, color = '#E0218A', width = '2'] = spec.split(':');
  const j = JSON.parse(readFileSync(file, 'utf8'));
  const lines = [];
  const isPt = p => Array.isArray(p) && typeof p[0] === 'number';
  const add = v => {
    if (!Array.isArray(v) || !v.length) return;
    if (isPt(v[0])) lines.push(v);
    else for (const w of v) add(w);
  };
  if (j && j.type === 'FeatureCollection') for (const f of j.features) add(f.geometry.coordinates);
  else if (j && j.type === 'Feature') add(j.geometry.coordinates);
  else if (Array.isArray(j)) add(j);
  else for (const k of Object.keys(j)) add(j[k]);
  return {lines, color: hex(color), width: Number(width)};
}
const hex = c => {
  const h = c.replace('#', '');
  return [parseInt(h.slice(0, 2), 16), parseInt(h.slice(2, 4), 16), parseInt(h.slice(4, 6), 16)];
};

// ---------------------------------------------------------------- PNG
function crc32(buf) {
  let c;
  let crc = 0xffffffff;
  for (let n = 0; n < buf.length; n++) {
    c = (crc ^ buf[n]) & 0xff;
    for (let k = 0; k < 8; k++) c = c & 1 ? 0xedb88320 ^ (c >>> 1) : c >>> 1;
    crc = (crc >>> 8) ^ c;
  }
  return (crc ^ 0xffffffff) >>> 0;
}
function png(w, h, rgb) {
  const raw = Buffer.alloc((w * 3 + 1) * h);
  for (let y = 0; y < h; y++) {
    raw[y * (w * 3 + 1)] = 0;
    rgb.copy(raw, y * (w * 3 + 1) + 1, y * w * 3, (y + 1) * w * 3);
  }
  const chunk = (type, data) => {
    const len = Buffer.alloc(4);
    len.writeUInt32BE(data.length);
    const td = Buffer.concat([Buffer.from(type), data]);
    const crc = Buffer.alloc(4);
    crc.writeUInt32BE(crc32(td));
    return Buffer.concat([len, td, crc]);
  };
  const ihdr = Buffer.alloc(13);
  ihdr.writeUInt32BE(w, 0);
  ihdr.writeUInt32BE(h, 4);
  ihdr[8] = 8;
  ihdr[9] = 2; // RGB
  return Buffer.concat([Buffer.from([137, 80, 78, 71, 13, 10, 26, 10]), chunk('IHDR', ihdr), chunk('IDAT', deflateSync(raw, {level: 6})), chunk('IEND', Buffer.alloc(0))]);
}

// ---------------------------------------------------------------- main
const args = parseArgs(process.argv.slice(2));
const mod = await loadLandmarks();
let lms = mod.LANDMARKS;
if (args.ids) lms = lms.filter(l => args.ids.includes(l.id));
if (args.match) lms = lms.filter(l => args.match.test(l.id));
if (args.year !== undefined) lms = lms.filter(l => l.built[1] <= args.year && args.year < l.end);
if (!lms.length) die('no landmark selected (use --ids / --match / --year; --match . --list prints them all)');

// meshes -> one triangle soup in metres around a common centre, exactly through the
// lon / lat offsets index.ts stores (anchor offset + local / kx, local / M_PER_DEG_LAT)
const tris = []; // per landmark: {pos: Float64Array (lon, lat, z), col}
let total = 0;
for (const lm of lms) {
  const b = new mod.MeshBuilder();
  lm.build(b);
  const m = b.build();
  const pos = m.positions.value;
  const n = pos.length / 3;
  const kx = kxAt(lm.anchor[1]);
  const ax = lm.anchor[0] - ORIGIN[0];
  const ay = lm.anchor[1] - ORIGIN[1];
  const ll = new Float64Array(n * 3);
  for (let v = 0; v < n; v++) {
    ll[v * 3] = ORIGIN[0] + ax + pos[v * 3] / kx;
    ll[v * 3 + 1] = ORIGIN[1] + ay + pos[v * 3 + 1] / M_PER_DEG_LAT;
    ll[v * 3 + 2] = pos[v * 3 + 2];
  }
  tris.push({lm, ll, col: m.colors.value, n});
  total += n / 3;
  if (args.list) console.log(`${lm.id.padEnd(44)} ${String(lm.built[0]).padEnd(8)} ${String(lm.built[1]).padEnd(8)} ${String(lm.end).padEnd(8)} ${n / 3} triangles`);
}
console.log(`${lms.length} landmark(s), ${total} triangles`);
if (args.list) process.exit(0);
if (!args.out) die('--out file.png is required');

// common metric frame
let lon0 = 0;
let lat0 = 0;
{
  let x0 = Infinity, x1 = -Infinity, y0 = Infinity, y1 = -Infinity;
  for (const t of tris)
    for (let v = 0; v < t.n; v++) {
      x0 = Math.min(x0, t.ll[v * 3]);
      x1 = Math.max(x1, t.ll[v * 3]);
      y0 = Math.min(y0, t.ll[v * 3 + 1]);
      y1 = Math.max(y1, t.ll[v * 3 + 1]);
    }
  lon0 = (x0 + x1) / 2;
  lat0 = (y0 + y1) / 2;
}
const KX = kxAt(lat0);
const toM = (lon, lat, z = 0) => [(lon - lon0) * KX, (lat - lat0) * M_PER_DEG_LAT, z];
const P = new Float64Array(total * 9);
const C = new Float32Array(total * 9);
{
  let o = 0;
  for (const t of tris) {
    for (let v = 0; v < t.n; v++) {
      const p = toM(t.ll[v * 3], t.ll[v * 3 + 1], t.ll[v * 3 + 2]);
      P[o * 3] = p[0];
      P[o * 3 + 1] = p[1];
      P[o * 3 + 2] = p[2];
      C[o * 3] = t.col[v * 3];
      C[o * 3 + 1] = t.col[v * 3 + 1];
      C[o * 3 + 2] = t.col[v * 3 + 2];
      o++;
    }
  }
}
const refs = args.ref.map(readRef);

// camera: right-handed basis (r = right, u = up, f = forward into the scene)
const [W, H] = args.size;
const SS = Math.max(1, args.ss | 0);
const w = W * SS;
const h = H * SS;
let r, u, f;
let dist = 0;
if (args.view === 'top') {
  r = [1, 0, 0];
  u = [0, 1, 0];
  f = [0, 0, -1];
} else {
  const [az, el, d] = args.view.split(',').map(Number);
  dist = d || 0;
  const a = (az * Math.PI) / 180;
  const e = (el * Math.PI) / 180;
  // camera sits at compass azimuth az from the target, el above the horizon
  const toCam = [Math.sin(a) * Math.cos(e), Math.cos(a) * Math.cos(e), Math.sin(e)];
  f = toCam.map(c => -c);
  r = [Math.cos(a), -Math.sin(a), 0].map(c => -c); // right of the viewing direction
  u = [r[1] * f[2] - r[2] * f[1], r[2] * f[0] - r[0] * f[2], r[0] * f[1] - r[1] * f[0]]; // r x f
}
const dot = (a, b) => a[0] * b[0] + a[1] * b[1] + a[2] * b[2];
// bounding box in view space for target / span
const view = (x, y, z) => [x * r[0] + y * r[1] + z * r[2], x * u[0] + y * u[1] + z * u[2], x * f[0] + y * f[1] + z * f[2]];
let tgt;
if (args.target) tgt = toM(args.target[0], args.target[1], args.target[2] ?? 0);
let bx0 = Infinity, bx1 = -Infinity, by0 = Infinity, by1 = -Infinity;
for (let i = 0; i < total * 3; i++) {
  const v = view(P[i * 3], P[i * 3 + 1], P[i * 3 + 2]);
  bx0 = Math.min(bx0, v[0]);
  bx1 = Math.max(bx1, v[0]);
  by0 = Math.min(by0, v[1]);
  by1 = Math.max(by1, v[1]);
}
const tv = tgt ? view(...tgt) : [(bx0 + bx1) / 2, (by0 + by1) / 2, 0];
const span = args.span ?? Math.max(bx1 - bx0, ((by1 - by0) * W) / H) * 1.06;
const scale = w / span; // pixels per metre at the target depth
const camDepth = tv[2] - dist; // view-space depth of the camera (perspective)
function project(x, y, z) {
  const v = view(x, y, z);
  let k = scale;
  if (dist > 0) {
    const dz = v[2] - camDepth;
    if (dz < 1) return null;
    k = (scale * dist) / dz;
  }
  return [w / 2 + (v[0] - tv[0]) * k, h / 2 - (v[1] - tv[1]) * k, v[2]];
}

const bg = hex(args.bg);
const img = new Float32Array(w * h * 3);
const zb = new Float32Array(w * h).fill(Infinity);
for (let i = 0; i < w * h; i++) {
  img[i * 3] = bg[0];
  img[i * 3 + 1] = bg[1];
  img[i * 3 + 2] = bg[2];
}
// light from the south-west, high (like the viewer's sun); two-sided Lambert + ambient
const L = (() => {
  const v = [-0.45, -0.55, 0.7];
  const n = Math.hypot(...v);
  return v.map(c => c / n);
})();

function fillTri(a, b, c, col) {
  const minX = Math.max(0, Math.floor(Math.min(a[0], b[0], c[0])));
  const maxX = Math.min(w - 1, Math.ceil(Math.max(a[0], b[0], c[0])));
  const minY = Math.max(0, Math.floor(Math.min(a[1], b[1], c[1])));
  const maxY = Math.min(h - 1, Math.ceil(Math.max(a[1], b[1], c[1])));
  if (minX > maxX || minY > maxY) return;
  const area = (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0]);
  if (Math.abs(area) < 1e-9) return;
  const inv = 1 / area;
  for (let y = minY; y <= maxY; y++) {
    const py = y + 0.5;
    for (let x = minX; x <= maxX; x++) {
      const px = x + 0.5;
      const w0 = ((b[0] - px) * (c[1] - py) - (b[1] - py) * (c[0] - px)) * inv;
      const w1 = ((c[0] - px) * (a[1] - py) - (c[1] - py) * (a[0] - px)) * inv;
      const w2 = 1 - w0 - w1;
      if (w0 < 0 || w1 < 0 || w2 < 0) continue;
      const z = w0 * a[2] + w1 * b[2] + w2 * c[2];
      const i = y * w + x;
      if (z < zb[i]) {
        zb[i] = z;
        img[i * 3] = col[0];
        img[i * 3 + 1] = col[1];
        img[i * 3 + 2] = col[2];
      }
    }
  }
}

if (args.ground !== undefined) {
  const g = 20000;
  const q = [
    [-g, -g],
    [g, -g],
    [g, g],
    [-g, g]
  ].map(([x, y]) => project(x, y, args.ground));
  if (q.every(Boolean)) {
    fillTri(q[0], q[1], q[2], [150, 170, 178]);
    fillTri(q[0], q[2], q[3], [150, 170, 178]);
  }
}
for (let t = 0; t < total; t++) {
  const o = t * 9;
  const A = [P[o], P[o + 1], P[o + 2]];
  const B = [P[o + 3], P[o + 4], P[o + 5]];
  const Cc = [P[o + 6], P[o + 7], P[o + 8]];
  const a = project(...A);
  const b = project(...B);
  const c = project(...Cc);
  if (!a || !b || !c) continue;
  const e1 = [B[0] - A[0], B[1] - A[1], B[2] - A[2]];
  const e2 = [Cc[0] - A[0], Cc[1] - A[1], Cc[2] - A[2]];
  const n = [e1[1] * e2[2] - e1[2] * e2[1], e1[2] * e2[0] - e1[0] * e2[2], e1[0] * e2[1] - e1[1] * e2[0]];
  const nl = Math.hypot(...n) || 1;
  let nn = n.map(v => v / nl);
  if (dot(nn, f) > 0) nn = nn.map(v => -v); // face the camera (winding is arbitrary)
  const sh = 0.42 + 0.58 * Math.max(0, dot(nn, L));
  fillTri(a, b, c, [C[o] * 255 * sh, C[o + 1] * 255 * sh, C[o + 2] * 255 * sh]);
}

// reference lines
function drawLine(p, q, col, width) {
  const steps = Math.ceil(Math.hypot(q[0] - p[0], q[1] - p[1]));
  const rad = (width * SS) / 2;
  for (let s = 0; s <= steps; s++) {
    const t = steps ? s / steps : 0;
    const x = p[0] + (q[0] - p[0]) * t;
    const y = p[1] + (q[1] - p[1]) * t;
    const z = p[2] + (q[2] - p[2]) * t;
    for (let dy = -Math.ceil(rad); dy <= Math.ceil(rad); dy++)
      for (let dx = -Math.ceil(rad); dx <= Math.ceil(rad); dx++) {
        if (dx * dx + dy * dy > rad * rad + 0.5) continue;
        const X = Math.round(x + dx);
        const Y = Math.round(y + dy);
        if (X < 0 || Y < 0 || X >= w || Y >= h) continue;
        const i = Y * w + X;
        if (args.refdepth && z > zb[i] + 0.5) continue;
        img[i * 3] = col[0];
        img[i * 3 + 1] = col[1];
        img[i * 3 + 2] = col[2];
      }
  }
}
for (const ref of refs)
  for (const line of ref.lines)
    for (let i = 0; i < line.length - 1; i++) {
      const p = project(...toM(line[i][0], line[i][1], line[i][2] ?? 0));
      const q = project(...toM(line[i + 1][0], line[i + 1][1], line[i + 1][2] ?? 0));
      if (p && q) drawLine(p, q, ref.color, ref.width);
    }

// scale bar (plan / orthographic views), bottom left: 100 m, 500 m or 1 km
if (!dist) {
  const len = span > 4000 ? 1000 : span > 1200 ? 500 : 100;
  const y = h - 30 * SS;
  const x0 = 30 * SS;
  for (let x = x0; x < x0 + len * scale; x++)
    for (let dy = 0; dy < 4 * SS; dy++) {
      const i = (y + dy) * w + Math.round(x);
      img[i * 3] = img[i * 3 + 1] = img[i * 3 + 2] = 20;
    }
  console.log(`scale bar: ${len} m; ${(span / W).toFixed(2)} m per pixel`);
}

// downsample + encode
const out = Buffer.alloc(W * H * 3);
for (let y = 0; y < H; y++)
  for (let x = 0; x < W; x++) {
    let rS = 0, gS = 0, bS = 0;
    for (let dy = 0; dy < SS; dy++)
      for (let dx = 0; dx < SS; dx++) {
        const i = ((y * SS + dy) * w + x * SS + dx) * 3;
        rS += img[i];
        gS += img[i + 1];
        bS += img[i + 2];
      }
    const k = 1 / (SS * SS);
    const o = (y * W + x) * 3;
    out[o] = Math.max(0, Math.min(255, Math.round(rS * k)));
    out[o + 1] = Math.max(0, Math.min(255, Math.round(gS * k)));
    out[o + 2] = Math.max(0, Math.min(255, Math.round(bS * k)));
  }
mkdirSync(dirname(resolve(args.out)), {recursive: true});
writeFileSync(args.out, png(W, H, out));
console.log(`wrote ${args.out} (${W}x${H})`);
