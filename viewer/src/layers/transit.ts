/**
 * BART and Muni trains (pipeline/transit.py): service lines with their real
 * centrelines, stops and opening years; trains are procedural (constant headway,
 * trapezoid speed profile between stops, real car sizes / train lengths) and run
 * entirely on the GPU.
 *
 * Every car is one instance. Its line's vertices (lon/lat offset, z, cumulative m,
 * opening year, tunnel flag, half track spacing) and stop knots (distance, arrive s,
 * depart s) live in a float texture; the vertex shader turns the clock into the
 * train's position (binary search over the knots, then over the vertices), so the
 * animation never touches the CPU. Each direction keeps right on its own track;
 * where the tracks spread round an island platform the train follows them.
 * Cars on stretches not yet open in the chosen year are hidden, and so are cars
 * running underground.
 *
 * Stations: BART stations above ground get a platform and canopy (dimensions:
 * 700 ft platforms); names are labels (labels.ts).
 */
import {COORDINATE_SYSTEM, Layer, project32, phongMaterial} from '@deck.gl/core';
import type {DefaultProps, LayerContext, UpdateParameters} from '@deck.gl/core';
import {Geometry, Model} from '@luma.gl/engine';
import type {Texture} from '@luma.gl/core';
import type {ShaderModule} from '@luma.gl/shadertools';
import {MeshBuilder} from '../landmarks/kit';
import {LandmarkMeshLayer, type MergedLandmarks} from '../landmarks/merged-layer';

type Vehicle = {car: [number, number, number]; gap: number; vmax: number; acc: number; dwell: number};
type Line = {
  id: string;
  name: string;
  system: 'bart' | 'muni';
  veh: string;
  cars: number;
  headway: number;
  color: string;
  gap: [number, number] | null;
  lon: number[];
  lat: number[];
  z: number[];
  cum: number[];
  year: number[];
  tunnel: number[];
  half: number[];
  knots: [number, number, number][];
};
export type Station = {
  code: string;
  name: string;
  system: 'bart' | 'muni';
  lon: number;
  lat: number;
  z: number;
  ground: number;
  heading: number;
  kind: 'underground' | 'elevated' | 'surface';
  start: number;
  end: number;
  line: string;
  veh: string;
};

const TEX_W = 2048;
const DEG = 111320;

let origin: [number, number] = [-122.44, 37.76];
let texData: Float32Array | null = null;
let texH = 0;
let instances: {n: number; attrs: Record<string, {value: Float32Array; size: number}>; rand: Float32Array; train: Int32Array; veh: string[]; lineColor: Uint8Array} | null = null;
let stationMesh: MergedLandmarks | null = null;
export let stations: Station[] = [];

export async function loadTransit() {
  try {
    const [lr, sr] = await Promise.all([fetch('data/transit-lines.json'), fetch('data/transit-stations.json')]);
    if (!lr.ok) return;
    const meta = (await lr.json()) as {origin: [number, number]; vehicles: Record<string, Vehicle>; lines: Line[]};
    stations = sr.ok ? await sr.json() : [];
    origin = meta.origin;
    build(meta.lines, meta.vehicles);
    stationMesh = buildStations(meta.lines);
  } catch (e) {
    console.warn('transit', e);
  }
}

export function hasTransit() {
  return !!instances?.n;
}

function hex(c: string): [number, number, number] {
  const v = parseInt(c, 16);
  return [(v >> 16) & 255, (v >> 8) & 255, v & 255];
}

function build(lines: Line[], vehicles: Record<string, Vehicle>) {
  // texture: per vertex 2 texels [x, y, z, cum] [year, tunnel, half, 0]; per knot 1 texel
  let texels = 0;
  for (const l of lines) texels += l.lon.length * 2 + l.knots.length;
  texH = Math.ceil(texels / TEX_W);
  const tex = new Float32Array(TEX_W * texH * 4);
  let t = 0;
  const lineInfo: {v0: number; vc: number; k0: number; kc: number}[] = [];
  for (const l of lines) {
    const v0 = t;
    for (let i = 0; i < l.lon.length; i++) {
      tex.set([l.lon[i], l.lat[i], l.z[i], l.cum[i]], t * 4);
      tex.set([l.year[i], l.tunnel[i], l.half[i], 0], (t + 1) * 4);
      t += 2;
    }
    const k0 = t;
    for (const k of l.knots) {
      tex.set([k[0], k[1], k[2], 0], t * 4);
      t += 1;
    }
    lineInfo.push({v0, vc: l.lon.length, k0, kc: l.knots.length});
  }
  texData = tex;

  const line: number[] = [];
  const trip: number[] = [];
  const car: number[] = [];
  const motion: number[] = [];
  const gap: number[] = [];
  const rand: number[] = [];
  const train: number[] = [];
  const veh: string[] = [];
  const lineColor: number[] = [];
  let seed = 7;
  const rnd = () => ((seed = (seed * 16807) % 2147483647) / 2147483647);
  let trainNo = 0;
  lines.forEach((l, li) => {
    const v = vehicles[l.veh];
    const info = lineInfo[li];
    const T = l.knots[l.knots.length - 1][2];
    const layover = l.system === 'bart' ? 240 : 120;
    const N = Math.max(1, Math.ceil((T + layover) / l.headway));
    const period = N * l.headway;
    const col = hex(l.color);
    for (let dir = 0; dir < 2; dir++) {
      for (let i = 0; i < N; i++) {
        const r = rnd();
        const phase = i * l.headway + (dir ? l.headway * 0.47 : 0) + r * 40;
        for (let c = 0; c < l.cars; c++) {
          line.push(info.v0, info.vc, info.k0, info.kc);
          trip.push(T, period, phase, dir);
          car.push(c * (v.car[0] + v.gap) + v.car[0] / 2, v.car[0], v.car[1], v.car[2]);
          motion.push(v.vmax, v.acc, 0, r);
          gap.push(...(l.gap ?? [0, 0]));
          rand.push(r);
          train.push(trainNo);
          veh.push(l.veh);
          lineColor.push(col[0], col[1], col[2], 255);
        }
        trainNo++;
      }
    }
  });
  const n = rand.length;
  instances = {
    n,
    attrs: {
      getLine: {value: new Float32Array(line), size: 4},
      getTrip: {value: new Float32Array(trip), size: 4},
      getCar: {value: new Float32Array(car), size: 4},
      getMotion: {value: new Float32Array(motion), size: 4},
      getGap: {value: new Float32Array(gap), size: 2}
    },
    rand: new Float32Array(rand),
    train: new Int32Array(train),
    veh,
    lineColor: new Uint8Array(lineColor)
  };
}

// ------------------------------------------------------------------ liveries by era
// Approximate liveries (procedural): BART's brushed-aluminium A/B/C cars (1972-2024)
// and the white/blue Fleet of the Future (from 2018); Muni's Boeing LRVs (1980-2002),
// Breda LRV2/3 (1996-2025) and Siemens S200 (2017-); PCC streetcars in their
// heritage liveries; maroon-and-cream cable cars.
const PCC = [
  [234, 190, 64],
  [46, 110, 72],
  [190, 60, 50],
  [70, 110, 170],
  [230, 150, 60],
  [214, 206, 186],
  [120, 40, 40],
  [96, 150, 120]
];
function livery(veh: string, r: number, year: number, train: number): [number[], number[]] {
  const f = (a: number, b: number) => Math.min(1, Math.max(0, (year - a) / (b - a)));
  switch (veh) {
    case 'bart':
      return r < f(2018.0, 2024.7) ? [[230, 232, 235], [38, 96, 172]] : [[192, 196, 200], [56, 62, 74]];
    case 'ebart':
    case 'cable_liner':
      return [[234, 236, 238], [38, 96, 172]];
    case 'lrv':
      if (r < f(2017, 2025.5)) return [[200, 203, 207], [196, 32, 46]];
      if (r < f(1996, 2002.5)) return [[184, 188, 192], [172, 36, 42]];
      return [[236, 232, 222], [214, 98, 42]];
    case 'pcc':
      return [PCC[train % PCC.length], [232, 224, 196]];
    default:
      return [[124, 34, 30], [228, 216, 184]];
  }
}

const colorCache = new Map<string, {body: Uint8Array; band: Uint8Array}>();
function colors(year: number) {
  const key = `${Math.round(year * 4) / 4}`;
  let c = colorCache.get(key);
  if (c) return c;
  const inst = instances!;
  const body = new Uint8Array(inst.n * 4);
  const band = new Uint8Array(inst.n * 4);
  for (let i = 0; i < inst.n; i++) {
    const [b, s] = livery(inst.veh[i], inst.rand[i], year, inst.train[i]);
    body.set([b[0], b[1], b[2], 255], i * 4);
    band.set([s[0], s[1], s[2], 255], i * 4);
  }
  c = {body, band};
  if (colorCache.size > 40) colorCache.clear();
  colorCache.set(key, c);
  return c;
}

const dataCache = new Map<string, any>();
function trainData(year: number) {
  const inst = instances!;
  const c = colors(year);
  const key = `${Math.round(year * 4) / 4}`;
  let d = dataCache.get(key);
  if (d) return d;
  d = {
    length: inst.n,
    attributes: {
      ...inst.attrs,
      getBody: {value: c.body, size: 4, normalized: true},
      getBand: {value: c.band, size: 4, normalized: true},
      getLineColor: {value: inst.lineColor, size: 4, normalized: true}
    }
  };
  if (dataCache.size > 40) dataCache.clear();
  dataCache.set(key, d);
  return d;
}

// ------------------------------------------------------------------ meshes
/** A unit railcar along +y: dark running gear, body, window band, roof (colour codes). */
function carMesh() {
  const b = new MeshBuilder();
  b.color([0, 0, 0]).box(0, 0, 0.0, 0.84, 0.9, 0.16);
  b.color([255, 0, 0]).box(0, 0, 0.14, 1, 1, 0.44);
  b.color([0, 255, 0]).box(0, 0, 0.58, 1, 0.98, 0.26);
  b.color([255, 0, 0]).box(0, 0, 0.84, 1, 1, 0.06);
  b.color([0, 0, 255]).box(0, 0, 0.9, 0.9, 0.96, 0.1);
  return b.build();
}
const CAR = carMesh();

/** Platforms and canopies of the BART stations above ground (one merged mesh). */
function buildStations(lines: Line[]): MergedLandmarks | null {
  const byId = new Map(lines.map(l => [l.id, l]));
  const pos: number[] = [];
  const col: number[] = [];
  const times: number[] = [];
  for (const s of stations) {
    if (s.system !== 'bart' || s.kind === 'underground') continue;
    const l = byId.get(s.line);
    if (!l) continue;
    // track spacing at the station (island platform between the tracks)
    let best = 0;
    let bd = Infinity;
    for (let i = 0; i < l.lon.length; i++) {
      const d = (l.lon[i] + origin[0] - s.lon) ** 2 + (l.lat[i] + origin[1] - s.lat) ** 2;
      if (d < bd) {
        bd = d;
        best = i;
      }
    }
    const half = l.half[best];
    const zt = l.z[best];
    const len = s.veh === 'bart' ? 213 : s.veh === 'ebart' ? 110 : 40;
    const b = new MeshBuilder();
    b.frame(0, 0, 0, s.heading, () => {
      const island = half > 3.4;
      const pw = island ? 2 * half - 3.5 : 4.5;
      const deck = s.kind === 'elevated' ? -0.2 : -0.9;
      if (island) {
        b.color('#B9B4AA').box(0, 0, deck, pw, len, 1.1 - deck);
        b.color('#E8D27A').box(-pw / 2 + 0.35, 0, 1.1, 0.3, len, 0.02);
        b.color('#E8D27A').box(pw / 2 - 0.35, 0, 1.1, 0.3, len, 0.02);
      } else {
        for (const side of [-1, 1]) b.color('#B9B4AA').box(side * (half + 1.7 + pw / 2), 0, deck, pw, len, 1.1 - deck);
      }
      // canopy over the middle two thirds of the platform, on a row of columns
      const cw = 2 * half + (island ? 4 : 12);
      const cl = len * 0.66;
      for (let y = -cl / 2 + 8; y <= cl / 2 - 8; y += 16) b.color('#8E918F').box(0, y, 1.1, 0.5, 0.5, 4.2);
      b.color('#D6D8D6').box(0, 0, 5.3, cw, cl, 0.45);
      b.color('#C3C6C4').gable(0, 0, cw, cl, 5.75, 0.8, true);
    });
    const m = b.build();
    const p = m.positions.value;
    const kx = DEG * Math.cos((s.lat * Math.PI) / 180);
    const ax = s.lon - origin[0];
    const ay = s.lat - origin[1];
    for (let v = 0; v < p.length / 3; v++) {
      pos.push(ax + p[v * 3] / kx, ay + p[v * 3 + 1] / DEG, zt + p[v * 3 + 2]);
      times.push(s.start - 1.5, s.start, s.end, s.ground);
    }
    for (const c of m.colors.value) col.push(c);
  }
  if (!pos.length) return null;
  return {
    origin,
    positions: new Float32Array(pos),
    colors: new Float32Array(col),
    times: new Float32Array(times),
    pickingColors: new Float32Array(pos.length)
  };
}

// ------------------------------------------------------------------ layers
let live: Layer[] = [];

export function transitLayers(year: number, zoom: number): Layer[] {
  const out: Layer[] = [];
  if (stationMesh && zoom >= 12)
    out.push(
      new LandmarkMeshLayer({
        id: 'transit-stations',
        data: [],
        merged: stationMesh,
        coordinateSystem: COORDINATE_SYSTEM.LNGLAT_OFFSETS,
        coordinateOrigin: [origin[0], origin[1], 0],
        year,
        quality: false,
        material: {ambient: 0.6, diffuse: 0.55, shininess: 6, specularColor: [30, 30, 30]},
        pickable: false
      }) as any
    );
  live = [];
  if (!instances?.n || !texData || year < 1972) {
    return out;
  }
  const visible = zoom >= 11.5;
  // trains in tunnels are not drawn at all (the shader hides them); no x-ray pass
  for (const ghost of [false]) {
    const l = new TrainLayer({
      id: ghost ? 'trains-xray' : 'trains',
      data: trainData(year),
      mesh: CAR,
      texData,
      texH,
      coordinateSystem: COORDINATE_SYSTEM.LNGLAT_OFFSETS,
      coordinateOrigin: [origin[0], origin[1], 0],
      year,
      ghost,
      kx: DEG * Math.cos((origin[1] * Math.PI) / 180),
      ky: DEG,
      shadowEnabled: false,
      visible: visible && (!ghost || zoom >= 12.5),
      parameters: (ghost ? {depthCompare: 'always', depthWriteEnabled: false} : {}) as any
    } as any) as any;
    out.push(l);
    live.push(l);
  }
  return out;
}

/** Ask deck to redraw the trains (from the animation loop). */
export function tickTransit() {
  for (const l of live) if (l.props.visible) l.setNeedsRedraw();
}

// ------------------------------------------------------------------ clock + CPU mirror
// ?tclock=<seconds> freezes the trains (screenshots / checks)
const FIXED_CLOCK = Number(new URLSearchParams(location.search).get('tclock') ?? NaN);
export function trainClock() {
  return Number.isFinite(FIXED_CLOCK) ? FIXED_CLOCK : (performance.now() / 1000) % 100000;
}

function runS(u: number, D: number, v: number, a: number) {
  let dAcc = (v * v) / (2 * a);
  let ta: number;
  let T: number;
  if (D < 2 * dAcc) {
    v = Math.sqrt(a * D);
    ta = v / a;
    T = 2 * ta;
    dAcc = D / 2;
  } else {
    ta = v / a;
    T = 2 * ta + (D - 2 * dAcc) / v;
  }
  u = Math.min(Math.max(u, 0), T);
  if (u < ta) return 0.5 * a * u * u;
  if (u > T - ta) return D - 0.5 * a * (T - u) * (T - u);
  return dAcc + v * (u - ta);
}

/** Head-car positions of the trains running at `time` (same maths as the shader): for checks. */
export function trainPositions(time = trainClock(), year = 2026) {
  if (!instances || !texData) return [];
  const t = texData;
  const at = (i: number) => [t[i * 4], t[i * 4 + 1], t[i * 4 + 2], t[i * 4 + 3]];
  const A = instances.attrs;
  const out: {train: number; lon: number; lat: number; tunnel: boolean; s: number}[] = [];
  for (let i = 0; i < instances.n; i++) {
    if (A.getCar.value[i * 4] > A.getCar.value[i * 4 + 1]) continue; // head cars only
    const [v0, vc, k0, kc] = A.getLine.value.slice(i * 4, i * 4 + 4);
    const [T, period, phase, dir] = A.getTrip.value.slice(i * 4, i * 4 + 4);
    const [vmax, acc] = A.getMotion.value.slice(i * 4, i * 4 + 2);
    const tau = (((time + phase) % period) + period) % period;
    if (tau > T) continue;
    const tt = dir > 0.5 ? T - tau : tau;
    let k = 0;
    while (k < kc - 1 && at(k0 + k + 1)[1] <= tt) k++;
    const K0 = at(k0 + k);
    let s = K0[0];
    if (k < kc - 1 && tt > K0[2]) s = K0[0] + runS(tt - K0[2], at(k0 + k + 1)[0] - K0[0], vmax, acc);
    let a = 0;
    while (a < vc - 2 && at(v0 + (a + 1) * 2)[3] <= s) a++;
    const P0 = at(v0 + a * 2);
    const P1 = at(v0 + (a + 1) * 2);
    const E = at(v0 + a * 2 + 1);
    if (year < E[0]) continue;
    const f = Math.min(1, Math.max(0, (s - P0[3]) / Math.max(P1[3] - P0[3], 0.01)));
    out.push({train: instances.train[i], lon: origin[0] + P0[0] + (P1[0] - P0[0]) * f, lat: origin[1] + P0[1] + (P1[1] - P0[1]) * f, tunnel: E[1] > 0.5, s});
  }
  return out;
}
(window as any).__trainPositions = trainPositions;

// ------------------------------------------------------------------ GPU layer
type TrainUniforms = {time: number; year: number; ghost: number; kx: number; ky: number; texW: number};
const TRAIN_UNIFORMS = `layout(std140) uniform trainsUniforms {
  float time;
  float year;
  float ghost;
  float kx;
  float ky;
  float texW;
} trains;
`;
const trainModule: ShaderModule<TrainUniforms> = {
  name: 'trains',
  vs: TRAIN_UNIFORMS,
  fs: TRAIN_UNIFORMS,
  uniformTypes: {time: 'f32', year: 'f32', ghost: 'f32', kx: 'f32', ky: 'f32', texW: 'f32'}
};

const vs = `#version 300 es
#define SHADER_NAME train-vs
in vec3 positions;
in vec3 colors;
in vec4 instLine;
in vec4 instTrip;
in vec4 instCar;
in vec4 instMotion;
in vec2 instGap;
in vec4 instBody;
in vec4 instBand;
in vec4 instLineColor;
uniform sampler2D lineTex;
out vec3 vColor;
out vec3 vCommon;
out vec3 vCamera;

vec4 tx(float i) {
  int k = int(i + 0.5);
  int w = int(trains.texW);
  return texelFetch(lineTex, ivec2(k - (k / w) * w, k / w), 0);
}

// distance covered after u seconds of a run of D metres (accelerate, cruise, brake)
float runS(float u, float D, float v, float a) {
  float dAcc = v * v / (2.0 * a);
  float ta;
  float T;
  if (D < 2.0 * dAcc) {
    v = sqrt(a * D);
    ta = v / a;
    T = 2.0 * ta;
    dAcc = D * 0.5;
  } else {
    ta = v / a;
    T = 2.0 * ta + (D - 2.0 * dAcc) / v;
  }
  u = clamp(u, 0.0, T);
  if (u < ta) return 0.5 * a * u * u;
  if (u > T - ta) return D - 0.5 * a * (T - u) * (T - u);
  return dAcc + v * (u - ta);
}

void main(void) {
  float T = instTrip.x;
  float tau = mod(trains.time + instTrip.z, instTrip.y);
  bool rev = instTrip.w > 0.5;
  bool vis = tau <= T && !(trains.year >= instGap.x && trains.year < instGap.y);
  float tt = rev ? T - tau : tau;
  // where along the line the head of the train is: knots by arrival time
  float k0 = instLine.z;
  int kc = int(instLine.w + 0.5);
  int lo = 0;
  int hi = kc - 1;
  for (int it = 0; it < 9; it++) {
    if (lo >= hi) break;
    int mid = (lo + hi + 1) / 2;
    if (tx(k0 + float(mid)).y <= tt) lo = mid; else hi = mid - 1;
  }
  vec4 K0 = tx(k0 + float(lo));
  float s = K0.x;
  if (lo < kc - 1 && tt > K0.z) {
    vec4 K1 = tx(k0 + float(lo + 1));
    s = K0.x + runS(tt - K0.z, K1.x - K0.x, instMotion.x, instMotion.y);
  }
  float dir = rev ? -1.0 : 1.0;
  float sc = s - dir * instCar.x;
  // the vertex segment holding the car's centre
  float v0 = instLine.x;
  int vc = int(instLine.y + 0.5);
  float L = tx(v0 + float(vc - 1) * 2.0).w;
  vis = vis && sc >= 0.0 && sc <= L;
  sc = clamp(sc, 0.0, L);
  int a = 0;
  int b = vc - 2;
  for (int it = 0; it < 14; it++) {
    if (a >= b) break;
    int mid = (a + b + 1) / 2;
    if (tx(v0 + float(mid) * 2.0).w <= sc) a = mid; else b = mid - 1;
  }
  vec4 P0 = tx(v0 + float(a) * 2.0);
  vec4 P1 = tx(v0 + float(a + 1) * 2.0);
  vec4 E0 = tx(v0 + float(a) * 2.0 + 1.0);
  vec4 E1 = tx(v0 + float(a + 1) * 2.0 + 1.0);
  float f = clamp((sc - P0.w) / max(P1.w - P0.w, 0.01), 0.0, 1.0);
  vec3 p = mix(P0.xyz, P1.xyz, f);
  float halfSep = mix(E0.z, E1.z, f);
  bool tunnel = max(E0.y, E1.y) > 0.5;
  vis = vis && trains.year >= max(E0.x, E1.x);
  vis = vis && (trains.ghost > 0.5 ? tunnel : !tunnel);
  // heading in metres, keep right
  vec2 dm = vec2((P1.x - P0.x) * trains.kx, (P1.y - P0.y) * trains.ky) * dir;
  float len = max(length(dm), 0.001);
  vec2 fw = dm / len;
  vec2 right = vec2(fw.y, -fw.x);
  float slope = (P1.z - P0.z) * dir / len;
  p.xy += right * halfSep / vec2(trains.kx, trains.ky);
  vec3 m = positions * vec3(instCar.z, instCar.y, instCar.w);
  m.z += m.y * slope;
  vec3 r = vec3(m.x * right + m.y * fw, m.z);
  vec4 commonPos;
  gl_Position = project_position_to_clipspace(p, vec3(0.0), project_size(r), commonPos);
  geometry.position = commonPos;
  DECKGL_FILTER_GL_POSITION(gl_Position, geometry);
  if (!vis) gl_Position = vec4(0.0);
  vCommon = commonPos.xyz;
  vCamera = project.cameraPosition;
  vec3 c = colors.r * instBody.rgb + colors.g * instBand.rgb + colors.b * vec3(0.66, 0.67, 0.68);
  if (colors.r + colors.g + colors.b < 0.01) c = vec3(0.16, 0.16, 0.17);
  vColor = trains.ghost > 0.5 ? mix(instLineColor.rgb, vec3(1.0), 0.15) : c;
}
`;

const fs = `#version 300 es
#define SHADER_NAME train-fs
precision highp float;
in vec3 vColor;
in vec3 vCommon;
in vec3 vCamera;
out vec4 fragColor;
void main(void) {
  vec3 n = normalize(cross(dFdx(vCommon), dFdy(vCommon)));
  fragColor = vec4(lighting_getLightColor(vColor, vCamera, vCommon, n), trains.ghost > 0.5 ? 0.55 : 1.0);
  DECKGL_FILTER_COLOR(fragColor, geometry);
}
`;

type Props = {data: any; mesh: any; texData: Float32Array; texH: number; year: number; ghost: boolean; kx: number; ky: number; material: any};

const defaults: DefaultProps<Props> = {
  mesh: {type: 'object', value: null as any, compare: true},
  texData: {type: 'object', value: null as any, compare: true},
  texH: 1,
  year: 2026,
  ghost: false,
  kx: 88000,
  ky: DEG,
  material: {ambient: 0.6, diffuse: 0.6, shininess: 30, specularColor: [70, 70, 70]}
};

class TrainLayer extends Layer<Props> {
  static layerName = 'TrainLayer';
  static defaultProps = defaults;
  state!: {model?: Model; texture?: Texture};

  getShaders() {
    return super.getShaders({vs, fs, modules: [project32, phongMaterial, trainModule]});
  }

  initializeState(_: LayerContext) {
    this.getAttributeManager()!.addInstanced({
      instLine: {size: 4, accessor: 'getLine'},
      instTrip: {size: 4, accessor: 'getTrip'},
      instCar: {size: 4, accessor: 'getCar'},
      instMotion: {size: 4, accessor: 'getMotion'},
      instGap: {size: 2, accessor: 'getGap'},
      instBody: {size: 4, type: 'unorm8', accessor: 'getBody', defaultValue: [200, 200, 200, 255]},
      instBand: {size: 4, type: 'unorm8', accessor: 'getBand', defaultValue: [60, 60, 60, 255]},
      instLineColor: {size: 4, type: 'unorm8', accessor: 'getLineColor', defaultValue: [255, 255, 255, 255]}
    });
    this.setState({});
  }

  updateState(params: UpdateParameters<this>) {
    super.updateState(params);
    const {props, oldProps} = params;
    if (props.mesh !== oldProps.mesh || params.changeFlags.extensionsChanged) {
      this.state.model?.destroy();
      this.setState({model: this._getModel()});
      this.getAttributeManager()!.invalidateAll();
    }
    if (props.texData !== oldProps.texData) {
      this.state.texture?.destroy();
      const texture = this.context.device.createTexture({
        width: TEX_W,
        height: props.texH,
        format: 'rgba32float',
        sampler: {minFilter: 'nearest', magFilter: 'nearest'}
      });
      texture.writeData(props.texData);
      this.setState({texture});
    }
  }

  finalizeState(context: LayerContext) {
    super.finalizeState(context);
    this.state.model?.destroy();
    this.state.texture?.destroy();
  }

  _getModel() {
    const m = this.props.mesh;
    return new Model(this.context.device, {
      ...this.getShaders(),
      id: this.props.id,
      bufferLayout: this.getAttributeManager()!.getBufferLayouts(),
      geometry: new Geometry({topology: 'triangle-list', attributes: {positions: m.positions, colors: m.colors}}),
      isInstanced: true
    });
  }

  draw() {
    const {model, texture} = this.state;
    if (!model || !texture) return;
    const {year, ghost, kx, ky} = this.props;
    model.setBindings({lineTex: texture});
    model.shaderInputs.setProps({
      trains: {time: trainClock(), year, ghost: ghost ? 1 : 0, kx, ky, texW: TEX_W}
    });
    model.draw(this.context.renderPass);
  }
}
