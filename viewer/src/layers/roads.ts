/**
 * Roads, rail and transit routes (pipeline/roads.py) draped on the terrain,
 * each with its lifespan; columns under elevated viaducts; and procedural
 * traffic — cars on the roads with an era-dependent density (none before
 * ~1903, a few in the 1910s, full after the 1960s) and streetcars / cable cars
 * running on the lines that existed that year.
 */
import {COORDINATE_SYSTEM} from '@deck.gl/core';
import type {Layer} from '@deck.gl/core';
import {PathLayer} from '@deck.gl/layers';
import {SimpleMeshLayer} from '@deck.gl/mesh-layers';
import {loadColumnar} from '../data/columnar';
import {TimeExtension} from './time-extension';
import {MeshBuilder} from '../landmarks/kit';

// kinds — keep in sync with pipeline/roads.py
const K = {STREET: 0, MAJOR: 1, FREEWAY: 2, HIGHWAY: 3, CABLE: 4, STREETCAR: 5, RAIL: 6, KEY: 7, BART: 8, FERRY: 9, LIGHTRAIL: 10};
const COLORS: Record<number, [number, number, number, number]> = {
  [K.STREET]: [176, 170, 158, 255],
  [K.MAJOR]: [160, 154, 144, 255],
  [K.FREEWAY]: [138, 134, 128, 255],
  [K.HIGHWAY]: [150, 145, 136, 255],
  [K.CABLE]: [112, 74, 52, 255],
  [K.STREETCAR]: [104, 86, 70, 255],
  [K.RAIL]: [96, 84, 74, 255],
  [K.KEY]: [150, 92, 50, 255],
  [K.BART]: [96, 110, 132, 255],
  [K.FERRY]: [250, 252, 255, 150],
  [K.LIGHTRAIL]: [100, 90, 80, 255]
};

type PathSet = {
  id: string;
  origin: [number, number];
  data: any;
  n: number;
  starts: Uint32Array;
  pos: Float32Array;
  kind: Uint8Array;
  width: Uint8Array;
  years: Float32Array;
  elevated: Uint8Array;
  columns?: {data: any; scale: Float32Array; years: Float32Array};
  /** cumulative metres along each path (per vertex) for traffic */
  cum?: Float32Array;
};

const sets: PathSet[] = [];
const fade = new TimeExtension({mode: 'fade'});
const meshTime = new TimeExtension({mode: 'mesh-z'});

const DEG = 111320;

async function loadSet(id: string, url: string) {
  const f = await loadColumnar(url);
  const c = f.columns;
  const n = f.header.counts.paths;
  const starts = c.start_indices as Uint32Array;
  const pos = c.positions as Float32Array;
  const [ox, oy] = f.header.origin;
  const set: PathSet = {
    id,
    origin: [ox, oy],
    n,
    starts,
    pos,
    kind: c.kind as Uint8Array,
    width: c.width as Uint8Array,
    years: c.years as Float32Array,
    elevated: c.elevated as Uint8Array,
    data: {length: n, startIndices: starts, attributes: {getPath: {value: pos, size: 3}}}
  };
  // cumulative distances for traffic
  const cum = new Float32Array(pos.length / 3);
  const kx = DEG * Math.cos((oy * Math.PI) / 180);
  for (let p = 0; p < n; p++) {
    let acc = 0;
    for (let v = starts[p]; v < starts[p + 1]; v++) {
      if (v > starts[p]) {
        const dx = (pos[v * 3] - pos[(v - 1) * 3]) * kx;
        const dy = (pos[v * 3 + 1] - pos[(v - 1) * 3 + 1]) * DEG;
        acc += Math.hypot(dx, dy);
      }
      cum[v] = acc;
    }
  }
  set.cum = cum;
  // columns under elevated (viaduct) paths, every ~50 m
  const cols: number[] = [];
  const cyears: number[] = [];
  for (let p = 0; p < n; p++) {
    if (set.elevated[p] !== 2) continue;
    for (let v = starts[p]; v < starts[p + 1]; v += 2) {
      cols.push(pos[v * 3], pos[v * 3 + 1], pos[v * 3 + 2]);
      cyears.push(set.years[p * 2], set.years[p * 2 + 1]);
    }
  }
  if (cols.length) {
    const m = cols.length / 3;
    const cp = new Float32Array(cols);
    const scale = new Float32Array(m * 3);
    for (let i = 0; i < m; i++) {
      scale[i * 3] = 2.2;
      scale[i * 3 + 1] = 2.2;
      scale[i * 3 + 2] = 14;
      cp[i * 3 + 2] -= 14;
    }
    set.columns = {data: {length: m, attributes: {getPosition: {value: cp, size: 3}, getYears: {value: new Float32Array(cyears), size: 2}}}, scale, years: new Float32Array(cyears)};
  }
  sets.push(set);
}

export async function loadRoads() {
  await Promise.all([
    loadSet('roads-region', 'data/roads-region.bin.gz').catch(e => console.warn('roads-region', e)),
    loadSet('roads-sf', 'data/roads-sf.bin.gz').catch(e => console.warn('roads-sf', e)),
    loadSet('routes', 'data/routes.bin.gz').catch(e => console.warn('routes', e))
  ]);
  setupTraffic();
}

function columnMesh() {
  const b = new MeshBuilder();
  b.color('#BEB9AE').box(0, 0, 0, 1, 1, 1);
  return b.build();
}
const COLUMN = columnMesh();

export function roadLayers(year: number, zoom: number): Layer[] {
  const out: Layer[] = [];
  for (const s of sets) {
    if (s.id === 'roads-region' && zoom > 15.5) continue;
    out.push(
      new PathLayer({
        id: `paths-${s.id}`,
        data: s.data,
        positionFormat: 'XYZ',
        _pathType: 'open',
        coordinateSystem: COORDINATE_SYSTEM.LNGLAT_OFFSETS,
        coordinateOrigin: [s.origin[0], s.origin[1], 0],
        getWidth: (_: any, {index}: any) => s.width[index] * (s.kind[index] === K.FERRY ? 0.6 : 1),
        getColor: (_: any, {index}: any) => COLORS[s.kind[index]] ?? COLORS[0],
        widthUnits: 'meters',
        widthMinPixels: s.id === 'routes' ? 1.5 : 0.8,
        billboard: false,
        jointRounded: true,
        capRounded: false,
        pickable: false,
        extensions: [fade],
        getYears: (_: any, {index, target}: any) => {
          target[0] = s.years[index * 2];
          target[1] = s.years[index * 2 + 1];
          return target;
        },
        currentYear: year,
        growYears: 1.5,
        shrinkYears: 0.5,
        parameters: {depthBias: -1} as any
      } as any) as any
    );
    if (s.columns) {
      const cs = s.columns;
      out.push(
        new SimpleMeshLayer({
          id: `columns-${s.id}`,
          data: cs.data,
          mesh: COLUMN,
          coordinateSystem: COORDINATE_SYSTEM.LNGLAT_OFFSETS,
          coordinateOrigin: [s.origin[0], s.origin[1], 0],
          getScale: (_: any, {index, target}: any) => {
            target[0] = cs.scale[index * 3];
            target[1] = cs.scale[index * 3 + 1];
            target[2] = cs.scale[index * 3 + 2];
            return target;
          },
          getColor: [255, 255, 255, 255],
          material: {ambient: 0.6, diffuse: 0.5, shininess: 4, specularColor: [20, 20, 20]},
          extensions: [meshTime],
          currentYear: year,
          growYears: 1.5,
          shrinkYears: 0.5
        } as any) as any
      );
    }
  }
  return out;
}

// ------------------------------------------------------------------ traffic

type Vehicle = {set: PathSet; path: number; offset: number; speed: number; dir: number; lane: number; color: [number, number, number]; kind: 'car' | 'tram'};
let vehicles: Vehicle[] = [];

function carMesh() {
  const b = new MeshBuilder();
  b.color('#FFFFFF').box(0, 0, 0.35, 1.9, 4.4, 0.75);
  b.color('#DDE3E8').box(0, -0.2, 1.1, 1.7, 2.2, 0.55);
  b.color('#2B2B2B').box(0, 1.35, 0, 1.95, 0.7, 0.4).box(0, -1.35, 0, 1.95, 0.7, 0.4);
  return b.build();
}
function tramMesh() {
  const b = new MeshBuilder();
  b.color('#FFFFFF').box(0, 0, 0.4, 2.6, 13, 2.6);
  b.color('#E8E2D6').box(0, 0, 3.0, 2.4, 12.6, 0.3);
  return b.build();
}
const CAR = carMesh();
const TRAM = tramMesh();

const PALETTE_EARLY: [number, number, number][] = [
  [30, 30, 32],
  [40, 38, 36],
  [60, 52, 44],
  [34, 46, 40]
];
const PALETTE_MID: [number, number, number][] = [
  [200, 70, 60],
  [90, 130, 170],
  [230, 220, 190],
  [120, 160, 120],
  [60, 60, 70],
  [210, 180, 90]
];
const PALETTE_LATE: [number, number, number][] = [
  [240, 240, 238],
  [200, 202, 205],
  [40, 42, 46],
  [150, 30, 30],
  [40, 70, 130],
  [120, 120, 125]
];

function rand(seed: number) {
  let s = seed >>> 0;
  return () => {
    s = (Math.imul(s, 1664525) + 1013904223) >>> 0;
    return s / 4294967296;
  };
}

function setupTraffic() {
  const r = rand(1906);
  vehicles = [];
  const weightOf = (s: PathSet, p: number) => {
    const k = s.kind[p];
    const len = s.cum![s.starts[p + 1] - 1] || 0;
    if (k === K.FREEWAY) return len * 6;
    if (k === K.HIGHWAY) return len * 4;
    if (k === K.MAJOR) return len * 2.2;
    if (k === K.STREET) return len * (s.id === 'roads-sf' ? 1 : 0.15);
    return 0;
  };
  for (const s of sets) {
    if (s.id === 'routes') continue;
    const w: number[] = [];
    let tot = 0;
    for (let p = 0; p < s.n; p++) {
      tot += weightOf(s, p);
      w.push(tot);
    }
    const count = s.id === 'roads-sf' ? 5000 : 4000;
    for (let i = 0; i < count; i++) {
      const x = r() * tot;
      let lo = 0;
      let hi = w.length - 1;
      while (lo < hi) {
        const mid = (lo + hi) >> 1;
        if (w[mid] < x) lo = mid + 1;
        else hi = mid;
      }
      const fast = s.kind[lo] === K.FREEWAY || s.kind[lo] === K.HIGHWAY;
      vehicles.push({
        set: s,
        path: lo,
        offset: r() * 1e5,
        speed: (fast ? 24 : 10) * (0.7 + 0.6 * r()),
        dir: r() < 0.5 ? 1 : -1,
        lane: 1.6 + r() * 1.4,
        color: [0, 0, 0],
        kind: 'car'
      });
    }
  }
  // trams on rail routes, a few per km
  for (const s of sets) {
    if (s.id !== 'routes') continue;
    for (let p = 0; p < s.n; p++) {
      const k = s.kind[p];
      if (k !== K.CABLE && k !== K.STREETCAR && k !== K.KEY && k !== K.LIGHTRAIL) continue;
      const len = s.cum![s.starts[p + 1] - 1] || 0;
      const n = Math.max(1, Math.round(len / 700));
      for (let i = 0; i < n; i++) {
        vehicles.push({set: s, path: p, offset: r() * 1e5, speed: k === K.CABLE ? 4 : 7, dir: r() < 0.5 ? 1 : -1, lane: 1.2, color: k === K.CABLE ? [150, 60, 40] : k === K.KEY ? [230, 140, 50] : [200, 170, 90], kind: 'tram'});
      }
    }
  }
  for (const [i, v] of vehicles.entries()) v.color = (v.kind === 'tram' ? v.color : [i % 997, 0, 0]) as any;
}

/** Era factor: share of the car pool on the road in a given year. */
function carDensity(year: number) {
  const pts: [number, number][] = [
    [1902, 0],
    [1910, 0.04],
    [1920, 0.15],
    [1930, 0.32],
    [1945, 0.4],
    [1960, 0.72],
    [1975, 0.9],
    [2000, 1]
  ];
  if (year <= pts[0][0]) return 0;
  for (let i = 0; i < pts.length - 1; i++) {
    if (year < pts[i + 1][0]) {
      const t = (year - pts[i][0]) / (pts[i + 1][0] - pts[i][0]);
      return pts[i][1] + (pts[i + 1][1] - pts[i][1]) * t;
    }
  }
  return 1;
}

function carColor(i: number, year: number): [number, number, number] {
  const pal = year < 1940 ? PALETTE_EARLY : year < 1975 ? PALETTE_MID : PALETTE_LATE;
  return pal[(i * 2654435761) % pal.length >>> 0] ?? pal[0];
}

/** Vehicle positions at wall-clock time t (seconds) for the given year. */
export function trafficLayers(year: number, zoom: number, t: number): Layer[] {
  if (zoom < 12.5 || !vehicles.length) return [];
  const dens = carDensity(year);
  const groups: Record<'car' | 'tram', {pos: number[]; ang: number[]; col: number[]}> = {car: {pos: [], ang: [], col: []}, tram: {pos: [], ang: [], col: []}};
  let carIdx = 0;
  for (const v of vehicles) {
    const s = v.set;
    const p = v.path;
    if (year < s.years[p * 2] || year >= s.years[p * 2 + 1]) continue;
    if (v.kind === 'car') {
      carIdx++;
      if ((carIdx * 0.6180339887) % 1 > dens) continue;
    }
    const st = s.starts[p];
    const en = s.starts[p + 1] - 1;
    const L = s.cum![en];
    if (L < 20) continue;
    let d = (v.offset + t * v.speed) % (2 * L);
    if (v.dir < 0) d = 2 * L - d;
    const forward = d < L;
    const along = forward ? d : 2 * L - d;
    // binary search segment
    let lo = st;
    let hi = en;
    while (lo < hi - 1) {
      const mid = (lo + hi) >> 1;
      if (s.cum![mid] <= along) lo = mid;
      else hi = mid;
    }
    const seg = Math.max(s.cum![hi] - s.cum![lo], 1e-3);
    const f = (along - s.cum![lo]) / seg;
    const x0 = s.pos[lo * 3];
    const y0 = s.pos[lo * 3 + 1];
    const x1 = s.pos[hi * 3];
    const y1 = s.pos[hi * 3 + 1];
    const z = s.pos[lo * 3 + 2] + (s.pos[hi * 3 + 2] - s.pos[lo * 3 + 2]) * f;
    const kx = DEG * Math.cos((s.origin[1] * Math.PI) / 180);
    let dx = (x1 - x0) * kx;
    let dy = (y1 - y0) * DEG;
    if (!forward) {
      dx = -dx;
      dy = -dy;
    }
    const len = Math.hypot(dx, dy) || 1;
    // keep right: offset to the right of travel direction
    const ox = ((dy / len) * v.lane) / kx;
    const oy = ((-dx / len) * v.lane) / DEG;
    const g = groups[v.kind];
    g.pos.push(x0 + (x1 - x0) * f + ox + s.origin[0], y0 + (y1 - y0) * f + oy + s.origin[1], z + 0.2);
    g.ang.push((Math.atan2(dx, dy) * 180) / Math.PI);
    const c = v.kind === 'tram' ? v.color : carColor(carIdx, year);
    g.col.push(c[0], c[1], c[2], 255);
  }
  const out: Layer[] = [];
  for (const kind of ['car', 'tram'] as const) {
    const g = groups[kind];
    const n = g.ang.length;
    if (!n) continue;
    const pos = new Float64Array(g.pos);
    const col = new Uint8Array(g.col);
    const ang = g.ang;
    const k = kind === 'car' ? 1.7 : 1.15;
    out.push(
      new SimpleMeshLayer({
        id: `traffic-${kind}`,
        data: {length: n, attributes: {getPosition: {value: pos, size: 3}, getColor: {value: col, size: 4, normalized: true}}},
        mesh: kind === 'car' ? CAR : TRAM,
        getScale: [k, k, k],
        getOrientation: (_: any, {index, target}: any) => {
          target[0] = 0;
          target[1] = -ang[index];
          target[2] = 0;
          return target;
        },
        material: {ambient: 0.55, diffuse: 0.6, shininess: 24, specularColor: [60, 60, 60]},
        pickable: false,
        updateTriggers: {getOrientation: t}
      } as any) as any
    );
  }
  return out;
}

export function hasTraffic() {
  return vehicles.length > 0;
}
