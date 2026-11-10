/**
 * Terrain tile loading and decoding (no WebGL here: this module also runs in a worker,
 * terrain-worker.ts, so that the dozens of tiles a flight brings in — each with thousands
 * of trees — are not decoded on the main thread between two frames).
 */
import {loadColumnar} from '../data/columnar';
import {DECO_COLORS} from './decoration-meshes';
import {DECO_ORIGIN, rankByte, type DecoBatch} from './deco-common';
import {extentFade, extentReady} from './extent';

export const N = 65;
export const TILE_ZOOM_DETAIL = 14;

export type TerrainMesh = {
  n: number;
  positions: Float32Array;
  normals: Float32Array;
  uv: Float32Array;
  covers: Float32Array;
  cover4: Float32Array;
  years: Float32Array;
  skirt: Float32Array;
  /** 0 outside the map's extent … 1 inside (extent.ts) */
  fade: Float32Array;
  indices: Uint32Array;
  origin: [number, number];
  /** z13 lattice cells per vertex step, and the tile's lattice origin (farm patterns) */
  latScale: number;
  latBase: [number, number];
};


const R = 6378137;
function tileLon(x: number, z: number) {
  return (x / 2 ** z) * 360 - 180;
}
function tileLat(y: number, z: number) {
  const n = Math.PI - (2 * Math.PI * y) / 2 ** z;
  return (180 / Math.PI) * Math.atan(Math.sinh(n));
}
void R;

const indexCache = new Map<number, Uint32Array>();
/** Triangle indices of an n×n vertex grid with its four skirts (shared by all tiles of that size). */
export function gridIndices(n: number) {
  let idx = indexCache.get(n);
  if (idx) return idx;
  const quads = (n - 1) * (n - 1) + 4 * (n - 1);
  idx = new Uint32Array(quads * 6);
  let k = 0;
  const q = (a: number, b: number, c: number, d: number) => {
    idx![k++] = a;
    idx![k++] = b;
    idx![k++] = d;
    idx![k++] = b;
    idx![k++] = c;
    idx![k++] = d;
  };
  for (let i = 0; i < n - 1; i++) for (let j = 0; j < n - 1; j++) q(i * n + j, i * n + j + 1, (i + 1) * n + j + 1, (i + 1) * n + j);
  // skirts: 4 edges, skirt vertices start at n*n in edge order (top, right, bottom, left)
  const base = n * n;
  const edge = (e: number, t: number) => base + e * n + t;
  const top = (t: number) => t;
  const right = (t: number) => t * n + (n - 1);
  const bottom = (t: number) => (n - 1) * n + t;
  const left = (t: number) => t * n;
  const edges = [top, right, bottom, left];
  for (let e = 0; e < 4; e++) for (let t = 0; t < n - 1; t++) q(edges[e](t), edges[e](t + 1), edge(e, t + 1), edge(e, t));
  indexCache.set(n, idx);
  return idx;
}

export type TileContent = {mesh: TerrainMesh; deco: DecoBatch[]} | null;

function decodeYear(v: number) {
  return v === 0 ? 0 : v / 10 + 1000;
}

async function fetchTile(z: number, x: number, y: number) {
  try {
    return await loadColumnar(`tiles/terrain/${z}/${x}/${y}.bin.gz`);
  } catch {
    return null;
  }
}

// open water: the pipeline skips tiles that are deep water throughout (terrain_tiles.py
// write_tiles); they are drawn as flat water here, with the map-edge fade, instead of
// leaving the parchment background showing through as squares
let oceanCols: Record<string, any> | null = null;
function oceanTile() {
  oceanCols ??= {
    elev: new Int16Array(N * N).fill(-100),
    cover: new Uint8Array(N * N * 5),
    year: new Uint16Array(N * N * 4)
  };
  return {columns: oceanCols} as any;
}

/** Load a tile; z14 outside the San Francisco detail grid falls back to a quadrant of its z13 parent. */
export async function loadTerrainTile(z: number, x: number, y: number): Promise<TileContent> {
  await extentReady;
  let f = await fetchTile(z, x, y);
  let sub = {r0: 0, c0: 0, step: 1, n: N, srcZ: z, srcX: x, srcY: y};
  if (!f && z === TILE_ZOOM_DETAIL) {
    f = (await fetchTile(z - 1, x >> 1, y >> 1)) ?? oceanTile();
    sub = {
      r0: (y & 1) * 32,
      c0: (x & 1) * 32,
      step: 1,
      n: 33,
      srcZ: z - 1,
      srcX: x >> 1,
      srcY: y >> 1
    };
  }
  const c = (f ?? oceanTile()).columns;
  const elev = c.elev as Int16Array;
  const cov = c.cover as Uint8Array;
  const yrs = c.year as Uint16Array;
  const n = sub.n;
  const west = tileLon(x, z);
  const east = tileLon(x + 1, z);
  const north = tileLat(y, z);
  const nv = n * n + 4 * n;
  const positions = new Float32Array(nv * 3);
  const covers = new Float32Array(nv * 4);
  const cover4 = new Float32Array(nv);
  const years = new Float32Array(nv * 4);
  const skirt = new Float32Array(nv);
  const fade = new Float32Array(nv);
  const normals = new Float32Array(nv * 3);
  const uv = new Float32Array(nv * 2);
  const latAt = (i: number) => tileLat(y + i / (n - 1), z) - north;
  const lats = Array.from({length: n}, (_, i) => latAt(i));
  // grid spacing in metres (same for a sub-window: it keeps its parent's spacing)
  const dxm = ((east - west) / (n - 1)) * 111320 * Math.cos((north * Math.PI) / 180);
  const dym = Math.abs(lats[1] - lats[0]) * 110574;
  const h = (r: number, c: number) => Math.max(elev[Math.min(N - 1, Math.max(0, r)) * N + Math.min(N - 1, Math.max(0, c))] / 10, 0);
  const setV = (v: number, i: number, j: number) => {
    const src = (sub.r0 + i) * N + (sub.c0 + j);
    const r = sub.r0 + i;
    const cc = sub.c0 + j;
    const rUp = Math.max(0, r - 1);
    const rDn = Math.min(N - 1, r + 1);
    const cL = Math.max(0, cc - 1);
    const cR = Math.min(N - 1, cc + 1);
    const gx = (h(r, cR) - h(r, cL)) / (dxm * (cR - cL) || 1);
    const gy = (h(rUp, cc) - h(rDn, cc)) / (dym * (rDn - rUp) || 1); // rows run south
    const len = Math.hypot(gx, gy, 1);
    normals[v * 3] = -gx / len;
    normals[v * 3 + 1] = -gy / len;
    normals[v * 3 + 2] = 1 / len;
    // texel centre of this vertex in the tile's cover texture (n × n)
    uv[v * 2] = (j + 0.5) / n;
    uv[v * 2 + 1] = (i + 0.5) / n;
    positions[v * 3] = ((east - west) * j) / (n - 1);
    positions[v * 3 + 1] = lats[i];
    fade[v] = extentFade(west + ((east - west) * j) / (n - 1), north + lats[i]);
    positions[v * 3 + 2] = elev[src] / 10;
    for (let k = 0; k < 4; k++) covers[v * 4 + k] = cov[src * 5 + k];
    cover4[v] = cov[src * 5 + 4];
    for (let k = 0; k < 4; k++) years[v * 4 + k] = decodeYear(yrs[src * 4 + k]);
  };
  for (let i = 0; i < n; i++) for (let j = 0; j < n; j++) setV(i * n + j, i, j);
  const edges: [number, number][][] = [
    Array.from({length: n}, (_, t) => [0, t]),
    Array.from({length: n}, (_, t) => [t, n - 1]),
    Array.from({length: n}, (_, t) => [n - 1, t]),
    Array.from({length: n}, (_, t) => [t, 0])
  ];
  edges.forEach((edge, e) =>
    edge.forEach(([i, j], t) => {
      const v = n * n + e * n + t;
      setV(v, i, j);
      skirt[v] = 1;
    })
  );
  const mesh: TerrainMesh = {
    n,
    normals,
    uv,
    positions,
    covers,
    cover4,
    years,
    skirt,
    fade,
    indices: gridIndices(n),
    origin: [west, north],
    latScale: 2 ** (13 - sub.srcZ),
    latBase: [(sub.srcX * 64 + sub.c0) * 2 ** (13 - sub.srcZ), (sub.srcY * 64 + sub.r0) * 2 ** (13 - sub.srcZ)]
  };

  // decorations
  const deco: DecoBatch[] = [];
  const dpos = c.deco_pos as Uint16Array | undefined;
  if (dpos && dpos.length) {
    const kinds = c.deco_kind as Uint8Array;
    const sizes = c.deco_size as Uint8Array;
    const dy = c.deco_years as Uint16Array;
    const groups = new Map<number, number[]>();
    const dense = kinds.length * (sub.srcZ === 14 ? 4 : 1) > 6000;
    for (let i = 0; i < kinds.length; i++) {
      let gx = (dpos[i * 2] / 65535) * (N - 1);
      let gy = (dpos[i * 2 + 1] / 65535) * (N - 1);
      if (sub.n !== N) {
        gx -= sub.c0;
        gy -= sub.r0;
        if (gx < 0 || gy < 0 || gx > n - 1 || gy > n - 1) continue;
      }
      // thinning by the tree's rank (rankByte of its own position: a z13 tile and its z14
      // children keep the same trees): dense natural forest keeps 40 % (density per
      // z13-tile area); a z13 tile is only drawn below zoom 12.5, where the deco shader
      // keeps at most 40 % of what can be thinned, so the rest isn't even loaded
      const rk = rankByte(west + ((east - west) * gx) / (n - 1), tileLat(y + gy / (n - 1), z)) / 255;
      if (rk > 0.4 && ((kinds[i] <= 1 && dense) || (z === 13 && kinds[i] !== 4 && kinds[i] !== 6))) continue;
      // nothing stands in the faded margin of the map
      if (extentFade(west + ((east - west) * (sub.n !== N ? gx : gx)) / (n - 1), tileLat(y + gy / (n - 1), z)) < 0.4) continue;
      const arr = groups.get(kinds[i]) ?? [];
      arr.push(i);
      groups.set(kinds[i], arr);
    }
    const elevAt = (gx: number, gy: number) => {
      const j0 = Math.min(Math.floor(gx), N - 2);
      const i0 = Math.min(Math.floor(gy), N - 2);
      const fx = gx - j0;
      const fy = gy - i0;
      const e = (i: number, j: number) => Math.max(elev[i * N + j] / 10, 0.9);
      return (e(i0, j0) * (1 - fx) + e(i0, j0 + 1) * fx) * (1 - fy) + (e(i0 + 1, j0) * (1 - fx) + e(i0 + 1, j0 + 1) * fx) * fy;
    };
    for (const [kind, ids] of groups) {
      const m = ids.length;
      const pos = new Float32Array(m * 3);
      const scl = new Float32Array(m * 3);
      const ang = new Float32Array(m);
      const yr = new Float32Array(m * 2);
      const col = new Uint8Array(m * 4);
      const pal = DECO_COLORS[kind] ?? DECO_COLORS[0];
      ids.forEach((i, k) => {
        const gx = (dpos[i * 2] / 65535) * (N - 1);
        const gy = (dpos[i * 2 + 1] / 65535) * (N - 1);
        const lx = sub.n !== N ? gx - sub.c0 : gx;
        const ly = sub.n !== N ? gy - sub.r0 : gy;
        // relative to the shared decoration origin (all tiles are drawn together)
        pos[k * 3] = west + ((east - west) * lx) / (n - 1) - DECO_ORIGIN[0];
        pos[k * 3 + 1] = tileLat(y + ly / (n - 1), z) - DECO_ORIGIN[1];
        ang[k] = ((((i * 2654435761) >>> 0) % 360) * Math.PI) / 180;
        pos[k * 3 + 2] = elevAt(gx, gy) - 0.3;
        const s = sizes[i];
        // stylised: crowns ~2x and trunks ~1.5x real size so trees read at city scale (Civ-like)
        const building = kind === 4 || kind === 6;
        const crown = building ? s : Math.max(4.5, s * 0.62);
        scl[k * 3] = crown;
        scl[k * 3 + 1] = crown;
        scl[k * 3 + 2] = building ? s : s * 1.45;
        yr[k * 2] = dy[i * 2] ? decodeYear(dy[i * 2]) : -10000;
        yr[k * 2 + 1] = dy[i * 2 + 1] ? decodeYear(dy[i * 2 + 1]) : 10000;
        col.set(pal[((i * 2654435761) % pal.length) >>> 0] ?? pal[0], k * 4);
        col[k * 4 + 3] = rankByte(west + ((east - west) * lx) / (n - 1), tileLat(y + ly / (n - 1), z));
      });
      deco.push({
        kind,
        count: m,
        pos,
        scale: scl,
        angle: ang,
        years: yr,
        color: col
      });
    }
  }
  return {mesh, deco};
}

