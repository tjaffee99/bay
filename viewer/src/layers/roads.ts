/**
 * Roads, rail and transit routes (pipeline/roads.py) draped on the terrain,
 * each with its lifespan; columns under elevated viaducts; and procedural
 * traffic — cars on the roads with an era-dependent density (none before
 * ~1903, a few in the 1910s, full after the 1960s) and streetcars / cable cars
 * running on the lines that existed that year.
 */
import {COORDINATE_SYSTEM, Layer, project32, phongMaterial} from '@deck.gl/core';
import type {LayerContext, UpdateParameters, DefaultProps} from '@deck.gl/core';
import {Geometry, Model} from '@luma.gl/engine';
import type {ShaderModule} from '@luma.gl/shadertools';
import {PathLayer} from '@deck.gl/layers';
import {TileLayer} from '@deck.gl/geo-layers';
import {loadColumnar} from '../data/columnar';
import {TimeExtension} from './time-extension';
import {MeshBuilder} from '../landmarks/kit';
import {DecoLayer} from './deco-layer';
import {elevationAt} from './elevation';
import {LandmarkMeshLayer, type MergedLandmarks} from '../landmarks/merged-layer';

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
  columns?: {data: any};
  decks?: MergedLandmarks;
  /** cumulative metres along each path (per vertex) for traffic */
  cum?: Float32Array;
  /** lon/lat bounds (absolute) of the set — for culling chunks out of view */
  bbox?: [number, number, number, number];
};

/** Whole sets (traffic) and what is drawn: the region's 124k roads are split into
 *  map squares so that only the squares in view go through the GPU. */
const sets: PathSet[] = [];
// suburban streets at city scale: thin and translucent, a texture rather than lines
const FAINT_STREET: [number, number, number, number] = [150, 146, 138, 150];
const drawSets: PathSet[] = [];
const fade = new TimeExtension({mode: 'fade'});

const DEG = 111320;

async function loadSet(id: string, url: string) {
  const set = decodeSet(id, await loadColumnar(url));
  sets.push(set);
  if (id === 'roads-region' || id === 'freeways') for (const ch of splitSet(set, 8, 8)) drawSets.push(addDecks(withColumns(ch)));
  else drawSets.push(addDecks(withColumns(set)));
}

function decodeSet(id: string, f: any): PathSet {
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
  // Ground-level paths were sampled bilinearly from the elevation grid, but the
  // terrain is drawn as flat triangles between 30–60 m vertices, which can bulge
  // above that on hills and cut roads into dashes: lift them a little.
  for (let p = 0; p < n; p++) {
    if (set.elevated[p] !== 0 || set.kind[p] === K.FERRY) continue;
    for (let v = starts[p]; v < starts[p + 1]; v++) pos[v * 3 + 2] += 0.9;
  }
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
  return set;
}

// ------------------------------------------------------------------ suburban streets
// Residential streets, lanes and alleys outside SF (roads.py local_streets): z12 tiles
// loaded on demand from zoom 12.5, like the region buildings.
let localIndex: Set<string> | null = null;
let localLow: Set<string> | null = null;
let localZ = 12;
let localLowZ = 10;
export async function loadLocalStreetIndex() {
  try {
    const r = await fetch('data/region-streets/index.json');
    if (!r.ok || !(r.headers.get('content-type') ?? '').includes('json')) return;
    const j = await r.json();
    localZ = j.z;
    localIndex = new Set((j.tiles as {x: number; y: number}[]).map(t => `${t.x}/${t.y}`));
    if (j.low) {
      localLowZ = j.low.z;
      localLow = new Set((j.low.tiles as {x: number; y: number}[]).map(t => `${t.x}/${t.y}`));
    }
  } catch (e) {
    console.warn('region streets index', e);
  }
}

function streetTiles(
  id: string,
  z: number,
  have: Set<string>,
  zoomOffset: number,
  year: number,
  low: boolean,
  show = true,
  loadFrom: number | null = null,
  loadTo: number | null = null
) {
  return new TileLayer<PathSet | null>({
    id,
    minZoom: z,
    maxZoom: z,
    tileSize: 256,
    zoomOffset,
    // kept in the scene at every zoom and loading a little beyond where it is drawn (see
    // region-buildings.ts): no reload, no blink when the view crosses the switch zoom
    visibleMinZoom: loadFrom,
    visibleMaxZoom: loadTo,
    maxCacheSize: 400,
    extent: [-123.68, 36.78, -121.16, 38.91],
    getTileData: async ({index: t}: any) => {
      if (!have.has(`${t.x}/${t.y}`)) return null;
      return decodeSet(`${id}-${t.x}-${t.y}`, await loadColumnar(`data/region-streets/${z}/${t.x}/${t.y}.bin.gz`));
    },
    renderSubLayers: (props: any) => {
      const s = props.data as PathSet | null;
      return s && show ? pathLayer(s, year, `${props.id}-p`, low) : null;
    },
    updateTriggers: {renderSubLayers: [year, show]}
  } as any) as any;
}

/** Residential streets, drawn like San Francisco's: every street from zoom 11, the
 *  simplified grid further out. */
export function localStreetLayers(year: number, zoom: number): Layer[] {
  if (!localIndex) return [];
  const out = [streetTiles('region-streets', localZ, localIndex, 1, year, false, zoom >= 11, 10.7, null)];
  if (localLow) out.push(streetTiles('region-streets-low', localLowZ, localLow, 1, year, false, zoom < 11, null, 11.8));
  return out;
}

/** Bents under elevated paths: a wall-like pier across the roadway every ~60 m,
 *  as tall as the deck is above the ground there (terrain lookup). */
function withColumns(set: PathSet) {
  const {n, starts, pos, origin} = set;
  const kx = DEG * Math.cos((origin[1] * Math.PI) / 180);
  const cols: number[] = [];
  const scl: number[] = [];
  const ang: number[] = [];
  const cyears: number[] = [];
  for (let p = 0; p < n; p++) {
    if (set.elevated[p] !== 2) continue;
    const step = set.width[p] > 8 ? 3 : 4;
    for (let v = starts[p] + 1; v < starts[p + 1] - 1; v += step) {
      const lon = pos[v * 3] + origin[0];
      const lat = pos[v * 3 + 1] + origin[1];
      const g = elevationAt(lon, lat);
      const h = pos[v * 3 + 2] - g;
      if (h < 4.5) continue;
      const dx = (pos[(v + 1) * 3] - pos[(v - 1) * 3]) * kx;
      const dy = (pos[(v + 1) * 3 + 1] - pos[(v - 1) * 3 + 1]) * DEG;
      cols.push(pos[v * 3], pos[v * 3 + 1], g - 0.5);
      scl.push(1.8, Math.max(2.5, set.width[p] * 0.55), h - 1.2);
      ang.push(Math.atan2(dy, dx));
      cyears.push(set.years[p * 2], set.years[p * 2 + 1]);
    }
  }
  if (cols.length) {
    const m = cols.length / 3;
    set.columns = {
      data: {
        length: m,
        attributes: {
          getPosition: {value: new Float32Array(cols), size: 3},
          getScale: {value: new Float32Array(scl), size: 3},
          getAngle: {value: new Float32Array(ang), size: 1},
          getYears: {value: new Float32Array(cyears), size: 2}
        }
      }
    };
  }
  return set;
}

/** Concrete deck slabs (with parapets) under every elevated stretch of a set (chunk). */
function addDecks(set: PathSet) {
  const {n, starts, pos, origin} = set;
  const kx = DEG * Math.cos((origin[1] * Math.PI) / 180);
  const out = {origin, pos: [] as number[], col: [] as number[], times: [] as number[]};
  const SIDE = [0.74, 0.73, 0.7];
  const UNDER = [0.55, 0.55, 0.54];
  const TOP = [0.5, 0.5, 0.5];
  for (let p = 0; p < n; p++) {
    if (set.elevated[p] !== 2) continue;
    const w = set.width[p] / 2 + 0.6;
    const y0 = set.years[p * 2];
    const y1 = set.years[p * 2 + 1];
    const a = starts[p];
    const b = starts[p + 1];
    // per-vertex left offset (averaged normals) and height above ground
    const L: [number, number][] = [];
    const H: number[] = [];
    const G: number[] = [];
    for (let v = a; v < b; v++) {
      const v0 = Math.max(a, v - 1);
      const v1 = Math.min(b - 1, v + 1);
      const dx = (pos[v1 * 3] - pos[v0 * 3]) * kx;
      const dy = (pos[v1 * 3 + 1] - pos[v0 * 3 + 1]) * DEG;
      const len = Math.hypot(dx, dy) || 1;
      L.push([(-dy / len) * w / kx, (dx / len) * w / DEG]);
      const g = elevationAt(pos[v * 3] + origin[0], pos[v * 3 + 1] + origin[1]);
      G.push(g);
      H.push(pos[v * 3 + 2] - g);
    }
    const tri = (q: number[][], c: number[], base: number) => {
      for (const v of q) {
        out.pos.push(v[0], v[1], v[2]);
        out.col.push(c[0], c[1], c[2]);
        out.times.push(y0, y0, y1, base);
      }
    };
    for (let k = 0; k < b - a - 1; k++) {
      if (H[k] < 3 || H[k + 1] < 3) continue;
      const i0 = (a + k) * 3;
      const i1 = (a + k + 1) * 3;
      const top0 = pos[i0 + 2] - 0.15;
      const top1 = pos[i1 + 2] - 0.15;
      const P = (i: number, side: number, kk: number, z: number) => [pos[i] + side * L[kk][0], pos[i + 1] + side * L[kk][1], z];
      const lt0 = P(i0, 1, k, top0), rt0 = P(i0, -1, k, top0), lt1 = P(i1, 1, k + 1, top1), rt1 = P(i1, -1, k + 1, top1);
      const lb0 = P(i0, 1, k, top0 - 1.7), rb0 = P(i0, -1, k, top0 - 1.7), lb1 = P(i1, 1, k + 1, top1 - 1.7), rb1 = P(i1, -1, k + 1, top1 - 1.7);
      const lp0 = P(i0, 1, k, top0 + 1.0), rp0 = P(i0, -1, k, top0 + 1.0), lp1 = P(i1, 1, k + 1, top1 + 1.0), rp1 = P(i1, -1, k + 1, top1 + 1.0);
      const base = Math.min(G[k], G[k + 1]);
      tri([lt0, rt0, rt1], TOP, base);
      tri([lt0, rt1, lt1], TOP, base);
      tri([lb0, rb1, rb0], UNDER, base);
      tri([lb0, lb1, rb1], UNDER, base);
      // outer faces: slab edge + parapet
      tri([lb0, lb1, lp1], SIDE, base);
      tri([lb0, lp1, lp0], SIDE, base);
      tri([rb0, rp1, rb1], SIDE, base);
      tri([rb0, rp0, rp1], SIDE, base);
    }
  }
  if (out.pos.length) {
    const nv = out.pos.length / 3;
    set.decks = {
      origin,
      positions: new Float32Array(out.pos),
      colors: new Float32Array(out.col),
      times: new Float32Array(out.times),
      pickingColors: new Float32Array(nv * 3)
    };
  }
  return set;
}

/** Split a set into a grid of chunks by each path's bbox centre (bbox per chunk). */
function splitSet(set: PathSet, nx: number, ny: number): PathSet[] {
  const {n, starts, pos, origin} = set;
  const bb = new Float64Array(n * 4);
  let [x0, y0, x1, y1] = [Infinity, Infinity, -Infinity, -Infinity];
  for (let p = 0; p < n; p++) {
    let a = Infinity, b = Infinity, c = -Infinity, d = -Infinity;
    for (let v = starts[p]; v < starts[p + 1]; v++) {
      const x = pos[v * 3] + origin[0];
      const y = pos[v * 3 + 1] + origin[1];
      if (x < a) a = x;
      if (y < b) b = y;
      if (x > c) c = x;
      if (y > d) d = y;
    }
    bb.set([a, b, c, d], p * 4);
    x0 = Math.min(x0, a);
    y0 = Math.min(y0, b);
    x1 = Math.max(x1, c);
    y1 = Math.max(y1, d);
  }
  const cellOf = (p: number) => {
    const cx = (bb[p * 4] + bb[p * 4 + 2]) / 2;
    const cy = (bb[p * 4 + 1] + bb[p * 4 + 3]) / 2;
    const i = Math.min(nx - 1, Math.floor(((cx - x0) / (x1 - x0 || 1)) * nx));
    const j = Math.min(ny - 1, Math.floor(((cy - y0) / (y1 - y0 || 1)) * ny));
    return j * nx + i;
  };
  const members: number[][] = Array.from({length: nx * ny}, () => []);
  for (let p = 0; p < n; p++) members[cellOf(p)].push(p);
  const out: PathSet[] = [];
  members.forEach((paths, cell) => {
    if (!paths.length) return;
    const m = paths.length;
    let nv = 0;
    for (const p of paths) nv += starts[p + 1] - starts[p];
    const cs = new Uint32Array(m + 1);
    const cp = new Float32Array(nv * 3);
    const kind = new Uint8Array(m);
    const width = new Uint8Array(m);
    const years = new Float32Array(m * 2);
    const elevated = new Uint8Array(m);
    const box: [number, number, number, number] = [Infinity, Infinity, -Infinity, -Infinity];
    let o = 0;
    paths.forEach((p, k) => {
      cs[k] = o;
      cp.set(pos.subarray(starts[p] * 3, starts[p + 1] * 3), o * 3);
      o += starts[p + 1] - starts[p];
      kind[k] = set.kind[p];
      width[k] = set.width[p];
      years[k * 2] = set.years[p * 2];
      years[k * 2 + 1] = set.years[p * 2 + 1];
      elevated[k] = set.elevated[p];
      box[0] = Math.min(box[0], bb[p * 4]);
      box[1] = Math.min(box[1], bb[p * 4 + 1]);
      box[2] = Math.max(box[2], bb[p * 4 + 2]);
      box[3] = Math.max(box[3], bb[p * 4 + 3]);
    });
    cs[m] = o;
    out.push({
      id: `${set.id}-${cell}`,
      origin,
      n: m,
      starts: cs,
      pos: cp,
      kind,
      width,
      years,
      elevated,
      bbox: box,
      data: {length: m, startIndices: cs, attributes: {getPath: {value: cp, size: 3}}}
    });
  });
  return out;
}


export async function loadRoads() {
  await Promise.all([
    loadSet('roads-region', 'data/roads-region.bin.gz').catch(e => console.warn('roads-region', e)),
    loadSet('roads-sf', 'data/roads-sf.bin.gz').catch(e => console.warn('roads-sf', e)),
    loadSet('routes', 'data/routes.bin.gz').catch(e => console.warn('routes', e)),
    loadSet('freeways', 'data/freeways.bin.gz').catch(e => console.warn('freeways', e)),
    // BART / Muni tracks (pipeline/transit.py): real per-track geometry, aerial decks + bents
    loadSet('transit', 'data/transit.bin.gz').catch(e => console.warn('transit', e))
  ]);
  setupTraffic();
}

function columnMesh() {
  const b = new MeshBuilder();
  b.color('#BEB9AE').box(0, 0, 0, 1, 1, 1);
  return b.build();
}
const COLUMN = columnMesh();

/** bounds: the map's [west, south, east, north] — chunks outside it (with a margin) are skipped. */
export function roadLayers(year: number, zoom: number, bounds?: [number, number, number, number]): Layer[] {
  const out: Layer[] = [];
  let view = bounds;
  if (view) {
    const mx = (view[2] - view[0]) * 0.5;
    const my = (view[3] - view[1]) * 0.5;
    view = [view[0] - mx, view[1] - my, view[2] + mx, view[3] + my];
  }
  for (const s of drawSets) {
    if (view && s.bbox && (s.bbox[2] < view[0] || s.bbox[0] > view[2] || s.bbox[3] < view[1] || s.bbox[1] > view[3])) continue;
    out.push(pathLayer(s, year, `paths-${s.id}`));
    if (s.decks)
      out.push(
        new LandmarkMeshLayer({
          id: `decks-${s.id}`,
          data: [],
          merged: s.decks,
          coordinateSystem: COORDINATE_SYSTEM.LNGLAT_OFFSETS,
          coordinateOrigin: [s.origin[0], s.origin[1], 0],
          year,
          quality: false,
          material: {ambient: 0.62, diffuse: 0.55, shininess: 6, specularColor: [24, 24, 24]},
          pickable: false
        }) as any
      );
    if (s.columns) {
      out.push(
        new DecoLayer({
          id: `columns-${s.id}`,
          data: s.columns.data,
          mesh: COLUMN,
          zoomIn: 0, // bents stand with their decks at every zoom (never thinned: keep 1)
          coordinateSystem: COORDINATE_SYSTEM.LNGLAT_OFFSETS,
          coordinateOrigin: [s.origin[0], s.origin[1], 0],
          material: {ambient: 0.6, diffuse: 0.5, shininess: 4, specularColor: [20, 20, 20]},
          year,
          growYears: 1.5,
          shrinkYears: 0.5
        }) as any
      );
    }
  }
  return out;
}

function pathLayer(s: PathSet, year: number, id: string, faint = false): Layer {
  return new PathLayer({
    id,
    data: s.data,
    positionFormat: 'XYZ',
    _pathType: 'open',
    coordinateSystem: COORDINATE_SYSTEM.LNGLAT_OFFSETS,
    coordinateOrigin: [s.origin[0], s.origin[1], 0],
    getWidth: (_: any, {index}: any) => s.width[index] * (s.kind[index] === K.FERRY ? 0.6 : s.id === 'transit' && s.elevated[index] === 4 ? 0.5 : 1),
    getColor: (_: any, {index}: any) =>
      s.id === 'transit' ? trackColor(s.kind[index], s.elevated[index]) : faint ? FAINT_STREET : (COLORS[s.kind[index]] ?? COLORS[0]),
    widthUnits: 'meters',
    widthMinPixels: s.id === 'routes' ? 1.5 : faint ? 0.5 : 0.8,
    shadowEnabled: false,
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
    // pull roads toward the camera in the depth test so they win over the terrain
    parameters: {depthBias: -4, depthBiasSlopeScale: -2} as any
  } as any) as any;
}

/** Track beds as seen from the air: ballast / concrete for BART, rails set in the
 *  street for Muni; tunnels as a faint line (not visible in reality, but they show
 *  where the subway runs). */
function trackColor(kind: number, elevated: number): [number, number, number, number] {
  if (elevated === 4) return kind === K.BART ? [70, 92, 140, 70] : [140, 70, 60, 60];
  if (kind === K.BART) return elevated === 2 ? [128, 124, 118, 255] : [140, 133, 123, 255];
  if (kind === K.CABLE) return [78, 76, 74, 255];
  return [86, 84, 82, 255];
}

// ------------------------------------------------------------------ traffic
//
// Vehicles are animated entirely on the GPU: each one is assigned a straight
// "leg" of its road (≤ ~220 m between two path vertices, lane-offset to the
// right) once at load; the vertex shader moves it along the leg from a time
// uniform and hides it by year / era density. A frame of traffic therefore costs
// one redraw — no layer rebuild, no attribute upload.

type Fleet = {
  n: number;
  a: Float32Array; // leg start (lng/lat offsets from ORIGIN, z metres)
  b: Float32Array; // leg end
  motion: Float32Array; // speed m/s, phase 0..1, leg length m, heading rad
  rank: Float32Array; // density rank 0..1, size scale
  years: Float32Array; // [start, end) of the road
  colorIdx: Uint8Array;
  fixedColor?: Uint8Array; // trams: one colour per line
};
let fleets: {car?: Fleet; tram?: Fleet} = {};
let origin: [number, number] = [0, 0];

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

const PALETTES: [number, number, number][][] = [
  // before 1940: black and dark
  [
    [30, 30, 32],
    [40, 38, 36],
    [60, 52, 44],
    [34, 46, 40]
  ],
  // 1940–1975
  [
    [200, 70, 60],
    [90, 130, 170],
    [230, 220, 190],
    [120, 160, 120],
    [60, 60, 70],
    [210, 180, 90]
  ],
  // after 1975
  [
    [240, 240, 238],
    [200, 202, 205],
    [40, 42, 46],
    [150, 30, 30],
    [40, 70, 130],
    [120, 120, 125]
  ]
];
const eraOf = (year: number) => (year < 1940 ? 0 : year < 1975 ? 1 : 2);

function rand(seed: number) {
  let s = seed >>> 0;
  return () => {
    s = (Math.imul(s, 1664525) + 1013904223) >>> 0;
    return s / 4294967296;
  };
}

/** A straight leg of path p around vertex v: extend while the direction stays within ~18°. */
function legOf(s: PathSet, p: number, v: number, maxLen: number): [number, number] {
  const st = s.starts[p];
  const en = s.starts[p + 1] - 1;
  const kx = DEG * Math.cos((s.origin[1] * Math.PI) / 180);
  const dir = (i: number): [number, number] => {
    const dx = (s.pos[(i + 1) * 3] - s.pos[i * 3]) * kx;
    const dy = (s.pos[(i + 1) * 3 + 1] - s.pos[i * 3 + 1]) * DEG;
    const l = Math.hypot(dx, dy) || 1;
    return [dx / l, dy / l];
  };
  let i = Math.min(Math.max(v, st), en - 1);
  const d0 = dir(i);
  let lo = i;
  let hi = i + 1;
  const cum = s.cum!;
  while (hi < en && cum[hi + 1] - cum[lo] < maxLen) {
    const d = dir(hi);
    if (d[0] * d0[0] + d[1] * d0[1] < 0.95) break;
    hi++;
  }
  while (lo > st && cum[hi] - cum[lo - 1] < maxLen) {
    const d = dir(lo - 1);
    if (d[0] * d0[0] + d[1] * d0[1] < 0.95) break;
    lo--;
  }
  return [lo, hi];
}

function buildFleet(items: {s: PathSet; p: number; v: number; speed: number; dir: number; lane: number; rank: number; maxLen: number; color?: [number, number, number]}[]): Fleet {
  const n = items.length;
  const f: Fleet = {
    n,
    a: new Float32Array(n * 3),
    b: new Float32Array(n * 3),
    motion: new Float32Array(n * 4),
    rank: new Float32Array(n * 2),
    years: new Float32Array(n * 2),
    colorIdx: new Uint8Array(n)
  };
  if (items.some(it => it.color)) f.fixedColor = new Uint8Array(n * 4);
  let k = 0;
  for (const it of items) {
    const {s, p} = it;
    const [lo, hi] = legOf(s, p, it.v, it.maxLen);
    let i0 = lo;
    let i1 = hi;
    if (it.dir < 0) [i0, i1] = [i1, i0];
    const kx = DEG * Math.cos((s.origin[1] * Math.PI) / 180);
    const dx = (s.pos[i1 * 3] - s.pos[i0 * 3]) * kx;
    const dy = (s.pos[i1 * 3 + 1] - s.pos[i0 * 3 + 1]) * DEG;
    const L = Math.hypot(dx, dy);
    if (L < 15) continue;
    // keep right: offset to the right of the direction of travel
    const ox = ((dy / L) * it.lane) / kx;
    const oy = ((-dx / L) * it.lane) / DEG;
    f.a.set([s.pos[i0 * 3] + ox, s.pos[i0 * 3 + 1] + oy, s.pos[i0 * 3 + 2] + 0.15], k * 3);
    f.b.set([s.pos[i1 * 3] + ox, s.pos[i1 * 3 + 1] + oy, s.pos[i1 * 3 + 2] + 0.15], k * 3);
    f.motion.set([it.speed, (k * 0.754877666) % 1, L, Math.atan2(dx, dy)], k * 4);
    f.rank.set([it.rank, 1], k * 2);
    f.years.set([s.years[p * 2], s.years[p * 2 + 1]], k * 2);
    f.colorIdx[k] = (k * 2654435761) % 251;
    if (it.color && f.fixedColor) f.fixedColor.set([...it.color, 255], k * 4);
    k++;
  }
  f.n = k;
  return f;
}

function setupTraffic() {
  const r = rand(1906);
  const weightOf = (s: PathSet, p: number) => {
    const k = s.kind[p];
    const len = s.cum![s.starts[p + 1] - 1] || 0;
    if (k === K.FREEWAY) return len * 6;
    if (k === K.HIGHWAY) return len * 4;
    if (k === K.MAJOR) return len * 2.2;
    if (k === K.STREET) return len * (s.id === 'roads-sf' ? 1 : 0.15);
    return 0;
  };
  const cars: Parameters<typeof buildFleet>[0] = [];
  for (const s of sets) {
    if (s.id === 'routes' || s.id === 'transit') continue;
    origin = s.origin;
    const w = new Float64Array(s.n);
    let tot = 0;
    for (let p = 0; p < s.n; p++) w[p] = tot += weightOf(s, p);
    const count = s.id === 'roads-sf' ? 7000 : 5000;
    for (let i = 0; i < count; i++) {
      const x = r() * tot;
      let lo = 0;
      let hi = s.n - 1;
      while (lo < hi) {
        const mid = (lo + hi) >> 1;
        if (w[mid] < x) lo = mid + 1;
        else hi = mid;
      }
      const fast = s.kind[lo] === K.FREEWAY || s.kind[lo] === K.HIGHWAY;
      const v = s.starts[lo] + Math.floor(r() * (s.starts[lo + 1] - s.starts[lo]));
      cars.push({s, p: lo, v, speed: (fast ? 26 : 10) * (0.7 + 0.6 * r()), dir: r() < 0.5 ? 1 : -1, lane: fast ? 2 + r() * 5 : 1.8 + r() * 1.2, rank: r(), maxLen: fast ? 400 : 220});
    }
  }
  const trams: Parameters<typeof buildFleet>[0] = [];
  for (const s of sets) {
    if (s.id !== 'routes') continue;
    origin = s.origin;
    for (let p = 0; p < s.n; p++) {
      const k = s.kind[p];
      if (k !== K.CABLE && k !== K.STREETCAR && k !== K.KEY && k !== K.LIGHTRAIL) continue;
      const len = s.cum![s.starts[p + 1] - 1] || 0;
      const n = Math.max(1, Math.round(len / 500));
      for (let i = 0; i < n; i++) {
        const v = s.starts[p] + Math.floor(((i + 0.5) / n) * (s.starts[p + 1] - s.starts[p]));
        const color: [number, number, number] = k === K.CABLE ? [150, 60, 40] : k === K.KEY ? [230, 140, 50] : [200, 170, 90];
        trams.push({s, p, v, speed: k === K.CABLE ? 4.2 : 7, dir: i % 2 ? 1 : -1, lane: 1.3, rank: 0, maxLen: 300, color});
      }
    }
  }
  fleets = {car: buildFleet(cars), tram: buildFleet(trams)};
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

// per-fleet, per-era binary data (stable objects: deck only re-uploads when the era changes)
const dataCache = new Map<string, any>();
function fleetData(kind: 'car' | 'tram', f: Fleet, era: number) {
  const key = `${kind}-${kind === 'tram' ? 0 : era}`;
  let d = dataCache.get(key);
  if (d) return d;
  let col = f.fixedColor;
  if (!col) {
    const pal = PALETTES[era];
    col = new Uint8Array(f.n * 4);
    for (let i = 0; i < f.n; i++) {
      const c = pal[f.colorIdx[i] % pal.length];
      col.set([c[0], c[1], c[2], 255], i * 4);
    }
  }
  d = {
    length: f.n,
    attributes: {
      getA: {value: f.a, size: 3},
      getB: {value: f.b, size: 3},
      getMotion: {value: f.motion, size: 4},
      getRank: {value: f.rank, size: 2},
      getYears: {value: f.years, size: 2},
      getColor: {value: col, size: 4, normalized: true}
    }
  };
  dataCache.set(key, d);
  return d;
}

let liveTraffic: Layer[] = [];

export function trafficLayers(year: number, zoom: number): Layer[] {
  const out: Layer[] = [];
  const visible = zoom >= 12.5;
  for (const kind of ['car', 'tram'] as const) {
    const f = fleets[kind];
    if (!f || !f.n) continue;
    out.push(
      new TrafficLayer({
        id: `traffic-${kind}`,
        data: fleetData(kind, f, eraOf(year)),
        mesh: kind === 'car' ? CAR : TRAM,
        coordinateSystem: COORDINATE_SYSTEM.LNGLAT_OFFSETS,
        coordinateOrigin: [origin[0], origin[1], 0],
        year,
        density: kind === 'car' ? carDensity(year) : 1,
        sizeScale: kind === 'car' ? 2.1 : 1.3,
        shadowEnabled: false,
        visible
      } as any)
    );
  }
  liveTraffic = out;
  return out;
}

/** Ask deck to redraw the traffic (call from an animation loop). */
export function tickTraffic() {
  for (const l of liveTraffic) if (l.props.visible) l.setNeedsRedraw();
}

export function hasTraffic() {
  return !!fleets.car?.n;
}

// ------------------------------------------------------------------ GPU layer

type TrafficUniforms = {time: number; year: number; density: number; sizeScale: number};
const trafficModule: ShaderModule<TrafficUniforms> = {
  name: 'traffic',
  vs: `layout(std140) uniform trafficUniforms {
  float time;
  float year;
  float density;
  float sizeScale;
} traffic;
`,
  uniformTypes: {time: 'f32', year: 'f32', density: 'f32', sizeScale: 'f32'}
};

const trafficVs = `#version 300 es
#define SHADER_NAME traffic-vs
in vec3 positions;
in vec3 colors;
in vec3 instanceA;
in vec3 instanceB;
in vec4 instanceMotion;
in vec2 instanceRank;
in vec2 instanceYears;
in vec4 instanceColors;
out vec3 vColor;
out vec3 vCommon;
out vec3 vCamera;
void main(void) {
  bool vis = traffic.year >= instanceYears.x && traffic.year < instanceYears.y && instanceRank.x < traffic.density;
  float L = max(instanceMotion.z, 1.0);
  float u = fract(instanceMotion.y + traffic.time * instanceMotion.x / L);
  vec3 p = mix(instanceA, instanceB, u);
  // appear / disappear at the ends of the leg
  float s = smoothstep(0.0, 0.05, u) * (1.0 - smoothstep(0.95, 1.0, u));
  float h = instanceMotion.w;
  float c = cos(h);
  float sn = sin(h);
  vec3 m = positions * traffic.sizeScale * instanceRank.y * s;
  vec3 r = vec3(m.x * c + m.y * sn, -m.x * sn + m.y * c, m.z);
  vec4 commonPos;
  gl_Position = project_position_to_clipspace(p, vec3(0.0), project_size(r), commonPos);
  if (!vis) gl_Position = vec4(0.0);
  vCommon = commonPos.xyz;
  vCamera = project.cameraPosition;
  vColor = colors * instanceColors.rgb;
}
`;

const trafficFs = `#version 300 es
#define SHADER_NAME traffic-fs
precision highp float;
in vec3 vColor;
in vec3 vCommon;
in vec3 vCamera;
out vec4 fragColor;
void main(void) {
  vec3 n = normalize(cross(dFdx(vCommon), dFdy(vCommon)));
  // screen-space derivatives give a normal that always faces the camera (as in deck's SimpleMeshLayer)
  fragColor = vec4(lighting_getLightColor(vColor, vCamera, vCommon, n), 1.0);
}
`;

type TrafficLayerProps = {data: any; mesh: any; year: number; density: number; sizeScale: number; material: any};

const trafficDefaults: DefaultProps<TrafficLayerProps> = {
  mesh: {type: 'object', value: null as any, compare: true},
  year: 2026,
  density: 1,
  sizeScale: 1,
  material: {ambient: 0.55, diffuse: 0.6, shininess: 24, specularColor: [60, 60, 60]}
};

class TrafficLayer extends Layer<TrafficLayerProps> {
  static layerName = 'TrafficLayer';
  static defaultProps = trafficDefaults;
  state!: {model?: Model};

  getShaders() {
    return super.getShaders({vs: trafficVs, fs: trafficFs, modules: [project32, phongMaterial, trafficModule]});
  }

  initializeState(_: LayerContext) {
    this.getAttributeManager()!.addInstanced({
      instanceA: {size: 3, accessor: 'getA'},
      instanceB: {size: 3, accessor: 'getB'},
      instanceMotion: {size: 4, accessor: 'getMotion'},
      instanceRank: {size: 2, accessor: 'getRank'},
      instanceYears: {size: 2, accessor: 'getYears'},
      instanceColors: {size: 4, type: 'unorm8', accessor: 'getColor', defaultValue: [255, 255, 255, 255]}
    });
    this.setState({});
  }

  updateState(params: UpdateParameters<this>) {
    super.updateState(params);
    if (params.props.mesh !== params.oldProps.mesh || params.changeFlags.extensionsChanged) {
      this.state.model?.destroy();
      this.setState({model: this._getModel()});
      this.getAttributeManager()!.invalidateAll();
    }
  }

  finalizeState(context: LayerContext) {
    super.finalizeState(context);
    this.state.model?.destroy();
  }

  _getModel() {
    const m = this.props.mesh;
    return new Model(this.context.device, {
      ...this.getShaders(),
      id: this.props.id,
      bufferLayout: this.getAttributeManager()!.getBufferLayouts(),
      geometry: new Geometry({
        topology: 'triangle-list',
        attributes: {positions: m.positions, colors: m.colors}
      }),
      isInstanced: true
    });
  }

  draw() {
    const {model} = this.state;
    if (!model) return;
    const {year, density, sizeScale} = this.props;
    model.shaderInputs.setProps({traffic: {time: (performance.now() / 1000) % 2000, year, density, sizeScale}});
    model.draw(this.context.renderPass);
  }
}
