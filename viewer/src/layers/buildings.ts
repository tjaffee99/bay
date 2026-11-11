/**
 * Buildings: SF footprints from the pipeline's binary file, falling back to the
 * tiny Phase 0 sample GeoJSON when the built data is not present.
 */
import {COORDINATE_SYSTEM} from '@deck.gl/core';
import {SolidPolygonLayer} from '@deck.gl/layers';
import {BuildingLayer} from './building-layer';
import {TimeExtension} from './time-extension';
import type {ColumnarFile} from '../data/columnar';
import {buildingColor, CONFIDENCE, CONFIDENCE_COLORS} from '../palette';

export const BUILDING_MATERIAL = {ambient: 0.56, diffuse: 0.66, shininess: 10, specularColor: [36, 34, 30] as [number, number, number]};

const polygonTime = new TimeExtension({mode: 'polygon'});

export type BuildingSet = {
  kind: 'binary' | 'geojson';
  count: number;
  start: Float32Array;
  end: Float32Array;
  height: Float32Array;
  confidence: Uint8Array;
  colors: Uint8Array;
  qualityColors: Uint8Array;
  file?: ColumnarFile;
  data: any;
  /** lon/lat centroid of each feature (for landmark replacement tests). */
  centroids: Float64Array;
  /** construction-start year of the landmark reconstruction on this footprint (NaN = none):
   *  while landmarks are shown the building ends then (or is hidden if it is the landmark) */
  replaced: Float32Array;
  /** per building [from, to]: years a vanished landmark occupied its site (landmarks occupiedMask) */
  occupied?: Float32Array;
  /** Extra per-feature info for the click popup. */
  info: (i: number) => Record<string, string | number>;
  /** the binary set cut into pieces that are drawn only when in view and in their years */
  chunks?: BuildingChunk[];
};

/**
 * A piece of the building set: the features of one block of the city (16 blocks of equal
 * count, a k-d split of the centroids) and of one era class — gone by the 1906 fire /
 * post-war / the rest. The whole set used to be one buffer, drawn in full on every frame:
 * 16 M vertices through the vertex shader at any zoom and year, most of them outside the
 * view or outside their lifespan (profile, 2026-11).
 */
export type BuildingChunk = {
  /** feature index in the whole set, per chunk feature */
  ids: Uint32Array;
  data: any;
  /** west, south, east, north of the chunk's footprints */
  bbox: [number, number, number, number];
  /** years outside which nothing of the chunk can be on screen */
  from: number;
  to: number;
  key: string;
};

const GONE_BY = 1906.7; // class 0: the pre-fire city and everything else lost by April 1906
const POST_WAR = 1946; // class 2
const BLOCKS = 16;

function chunkBinary(
  n: number,
  dim: number,
  starts: Uint32Array,
  pos: Float32Array,
  ringEnd: Uint8Array,
  indices: Uint32Array,
  centroids: Float64Array,
  start: Float32Array,
  end: Float32Array,
  origin: [number, number]
): BuildingChunk[] {
  // triangles are stored feature by feature: the first triangle index of each feature
  const triStart = new Uint32Array(n + 1);
  let p = 0;
  for (let f = 0; f < n; f++) {
    triStart[f] = p;
    const stop = starts[f + 1];
    while (p < indices.length && indices[p] < stop) p++;
  }
  triStart[n] = p;
  // k-d split into BLOCKS leaves of equal count
  let leaves: Uint32Array[] = [Uint32Array.from({length: n}, (_, i) => i)];
  while (leaves.length < BLOCKS) {
    const next: Uint32Array[] = [];
    for (const ids of leaves) {
      let x0 = Infinity, x1 = -Infinity, y0 = Infinity, y1 = -Infinity;
      for (const f of ids) {
        const x = centroids[f * 2], y = centroids[f * 2 + 1];
        if (x < x0) x0 = x;
        if (x > x1) x1 = x;
        if (y < y0) y0 = y;
        if (y > y1) y1 = y;
      }
      const ax = (x1 - x0) * 0.79 > y1 - y0 ? 0 : 1;
      const sorted = Array.from(ids).sort((a, b) => centroids[a * 2 + ax] - centroids[b * 2 + ax]);
      const half = sorted.length >> 1;
      next.push(Uint32Array.from(sorted.slice(0, half)), Uint32Array.from(sorted.slice(half)));
    }
    leaves = next;
  }
  const out: BuildingChunk[] = [];
  leaves.forEach((leaf, li) => {
    for (let cls = 0; cls < 3; cls++) {
      const ids = leaf.filter(f => (end[f] <= GONE_BY ? 0 : start[f] >= POST_WAR ? 2 : 1) === cls).sort();
      if (!ids.length) continue;
      let nv = 0, nt = 0;
      for (const f of ids) {
        nv += starts[f + 1] - starts[f];
        nt += triStart[f + 1] - triStart[f];
      }
      const cPos = new Float32Array(nv * dim);
      const cEnd = new Uint16Array(nv);
      const cStart = new Uint32Array(ids.length + 1);
      const cIdx = new Uint32Array(nt);
      let v = 0, t = 0;
      let w = Infinity, e = -Infinity, so = Infinity, no = -Infinity, y0 = Infinity, y1 = -Infinity;
      ids.forEach((f, k) => {
        const a = starts[f], b = starts[f + 1];
        cStart[k] = v;
        cPos.set(pos.subarray(a * dim, b * dim), v * dim);
        for (let i = a; i < b; i++) {
          cEnd[v + i - a] = ringEnd[i];
          const x = pos[i * dim], y = pos[i * dim + 1];
          if (x < w) w = x;
          if (x > e) e = x;
          if (y < so) so = y;
          if (y > no) no = y;
        }
        for (let i = triStart[f]; i < triStart[f + 1]; i++) cIdx[t++] = indices[i] - a + v;
        v += b - a;
        if (start[f] < y0) y0 = start[f];
        if (end[f] > y1) y1 = end[f];
      });
      cStart[ids.length] = v;
      out.push({
        ids,
        data: {length: ids.length, startIndices: cStart, dim, attributes: {getPolygon: {value: cPos, size: dim}, indices: cIdx, ringEndMarkers: cEnd}},
        bbox: [origin[0] + w, origin[1] + so, origin[0] + e, origin[1] + no],
        // construction frames go up to 3 years before the start; a building lost in a
        // disaster stays on screen for the days it burns
        from: y0 - 3.1,
        to: y1 + 0.06,
        key: `${li}-${cls}`
      });
    }
  });
  return out;
}

function colorArrays(n: number, conf: Uint8Array, ids?: ArrayLike<number>, mat?: ArrayLike<number>, roof?: ArrayLike<number>) {
  const colors = new Uint8Array(n * 4);
  const qualityColors = new Uint8Array(n * 4);
  for (let i = 0; i < n; i++) {
    buildingColor(mat ? mat[i] : 0, roof ? roof[i] : 0, ids ? ids[i] : i, colors, i * 4);
    qualityColors.set(CONFIDENCE_COLORS[conf[i]] ?? CONFIDENCE_COLORS[1], i * 4);
    qualityColors[i * 4 + 3] = 252; // roofs as walls
  }
  return {colors, qualityColors};
}

export async function loadBuildings(onProgress?: (f: number) => void): Promise<BuildingSet> {
  try {
    const file = await loadInWorker(new URL('data/sf-buildings.bin.gz', document.baseURI).href, onProgress);
    return fromBinary(file, true);
  } catch (err) {
    console.warn('SF building data not found, using Phase 0 sample', err);
    return fromSample();
  }
}

/** A few long-lived decode workers for the region's building tiles. */
const pool: {w: Worker; busy: number}[] = [];
const pending = new Map<number, {resolve: (v: any) => void; reject: (e: any) => void}>();
let nextId = 1;
export function loadTileInWorker(url: string): Promise<ColumnarFile & {dim: number}> {
  if (!pool.length) {
    for (let i = 0; i < 3; i++) {
      const w = new Worker(new URL('../data/buildings-worker.ts', import.meta.url), {type: 'module'});
      const slot = {w, busy: 0};
      w.onmessage = e => {
        const p = pending.get(e.data.id);
        if (!p) return;
        pending.delete(e.data.id);
        slot.busy--;
        if (e.data.error) p.reject(new Error(e.data.error));
        else p.resolve(e.data);
      };
      pool.push(slot);
    }
  }
  const slot = pool.reduce((a, b) => (b.busy < a.busy ? b : a));
  const id = nextId++;
  slot.busy++;
  return new Promise((resolve, reject) => {
    pending.set(id, {resolve, reject});
    slot.w.postMessage({url, id});
  });
}

/** Decode + triangulate off the main thread (see data/buildings-worker.ts). */
function loadInWorker(url: string, onProgress?: (f: number) => void): Promise<ColumnarFile & {dim: number}> {
  return new Promise((resolve, reject) => {
    const w = new Worker(new URL('../data/buildings-worker.ts', import.meta.url), {type: 'module'});
    w.onmessage = e => {
      if (e.data.progress !== undefined) return onProgress?.(e.data.progress);
      w.terminate();
      if (e.data.error) reject(new Error(e.data.error));
      else resolve(e.data);
    };
    w.onerror = e => {
      w.terminate();
      reject(e);
    };
    w.postMessage({url});
  });
}

/** `chunked`: cut the set into view / era chunks (the San Francisco file; region tiles are small and stay whole). */
export function fromBinary(file: ColumnarFile & {dim: number}, chunked = false): BuildingSet {
  const c = file.columns;
  const n = file.header.counts.features;
  const start = c.start_year as Float32Array;
  const end = c.end_year as Float32Array;
  const height = c.height as Float32Array;
  const confidence = c.confidence as Uint8Array;
  const {colors, qualityColors} = colorArrays(n, confidence, c.fid as Uint32Array, c.mat as Uint8Array | undefined, c.roof as Uint8Array | undefined);
  const meta = file.header.meta;
  const uses: string[] = meta.use_categories ?? [];
  const [ox, oy] = file.header.origin;
  const pos = c.positions as Float32Array;
  const starts = c.start_indices as Uint32Array;
  const ringEnd = c.vertex_valid as Uint8Array;
  const centroids = new Float64Array(n * 2);
  for (let f = 0; f < n; f++) {
    let sx = 0;
    let sy = 0;
    let k = 0;
    for (let v = starts[f]; v < starts[f + 1]; v++) {
      sx += pos[v * file.dim];
      sy += pos[v * file.dim + 1];
      k++;
      if (ringEnd[v] === 0) break; // outer ring only
    }
    centroids[f * 2] = ox + sx / Math.max(k, 1);
    centroids[f * 2 + 1] = oy + sy / Math.max(k, 1);
  }
  const data = chunked
    ? null // drawn chunk by chunk (chunkBinary)
    : {
        length: n,
        startIndices: c.start_indices,
        dim: file.dim,
        attributes: {
          getPolygon: {value: c.positions, size: file.dim},
          indices: c.indices,
          // ring-end markers: stored as u8, deck wants u16
          ringEndMarkers: Uint16Array.from(c.vertex_valid as Uint8Array)
        }
      };
  const chunks = chunked ? chunkBinary(n, file.dim, starts, pos, ringEnd, c.indices as Uint32Array, centroids, start, end, [ox, oy]) : undefined;
  // (the whole-set buffers are not kept: the chunks hold the geometry now)
  if (chunked) for (const k of ['positions', 'indices', 'vertex_valid', 'start_indices']) delete (c as any)[k];
  return {
    kind: 'binary',
    count: n,
    chunks,
    start,
    end,
    height,
    confidence,
    colors,
    qualityColors,
    file,
    data,
    centroids,
    replaced: new Float32Array(n).fill(NaN),
    info: i => {
      const out: Record<string, string | number> = {};
      const raw = (c.raw_year as Int16Array)?.[i];
      out['Built'] = fmtYear(start[i]);
      if (end[i] < 9000) out['Removed'] = fmtYear(end[i]);
      out['Year source'] = CONFIDENCE[confidence[i]] ?? '?';
      if (raw && raw !== Math.round(start[i])) out['Assessor year'] = raw > 0 ? raw : 'missing';
      out['Height'] = `${height[i].toFixed(1)} m`;
      const st = (c.stories as Uint8Array)?.[i];
      if (st) out['Stories'] = st;
      const u = (c.use as Uint8Array)?.[i];
      if (u !== undefined && uses[u]) out['Use'] = uses[u];
      return out;
    }
  };
}

async function fromSample(): Promise<BuildingSet> {
  const gj = await (await fetch('data/sample-buildings.geojson')).json();
  const feats = gj.features as any[];
  const n = feats.length;
  const start = new Float32Array(feats.map(f => f.properties.start_year));
  const end = new Float32Array(feats.map(f => f.properties.end_year));
  const height = new Float32Array(feats.map(f => f.properties.height_m));
  const confidence = new Uint8Array(feats.map(f => Math.max(0, CONFIDENCE.indexOf(f.properties.year_confidence))));
  const {colors, qualityColors} = colorArrays(n, confidence);
  return {
    kind: 'geojson',
    count: n,
    start,
    end,
    height,
    confidence,
    colors,
    qualityColors,
    data: feats,
    centroids: new Float64Array(feats.flatMap(f => f.geometry.coordinates[0][0])),
    replaced: new Float32Array(n).fill(NaN),
    info: i => ({Built: fmtYear(start[i]), Removed: end[i] < 9000 ? fmtYear(end[i]) : '—', Height: `${height[i]} m`, Source: 'sample'})
  };
}

function fmtYear(y: number) {
  return Math.floor(y).toString();
}

/** Chunks of the set that can be on screen: inside the view box (west, south, east, north) and in their years. */
export function visibleChunks(set: BuildingSet, year: number, view: [number, number, number, number] | null): boolean[] {
  return (set.chunks ?? []).map(
    c => !!view && year >= c.from && year < c.to && c.bbox[2] > view[0] && c.bbox[0] < view[2] && c.bbox[3] > view[1] && c.bbox[1] < view[3]
  );
}

/**
 * The building layers: one per chunk of the binary set (kept in the layer list, and their
 * buffers on the GPU, whether drawn or not), or the single GeoJSON sample layer. `view` =
 * the map's bounds (null: nothing of the set is in view).
 */
export function buildingsLayers(
  set: BuildingSet,
  year: number,
  quality: boolean,
  hideReplaced: boolean,
  view: [number, number, number, number] | null,
  id = 'buildings'
) {
  if (set.kind !== 'binary' || !set.chunks) return [buildingsLayer(set, year, quality, hideReplaced, id, !!view)];
  const vis = visibleChunks(set, year, view);
  return set.chunks.map((c, k) => buildingsLayer(set, year, quality, hideReplaced, `${id}-${c.key}`, vis[k], c));
}

/** The whole-set feature index of a picked object of a building layer. */
export function pickedBuilding(set: BuildingSet, layerId: string, index: number): number {
  const c = set.chunks?.find(ch => layerId.endsWith(`-${ch.key}`));
  return c ? c.ids[index] : index;
}

export function buildingsLayer(set: BuildingSet, year: number, quality: boolean, hideReplaced: boolean, id = 'buildings', visible = true, chunk?: BuildingChunk) {
  // accessors get the index within the layer's data: a chunk maps it to the whole set
  const at = chunk ? (i: number) => chunk.ids[i] : (i: number) => i;
  const colors = quality ? set.qualityColors : set.colors;
  const common = {
    id,
    visible,
    extruded: true,
    pickable: true,
    material: BUILDING_MATERIAL,
    getElevation: (_: any, {index}: {index: number}) => set.height[at(index)],
    getFillColor: (_: any, {index: local, target}: {index: number; target: number[]}) => {
      const index = at(local);
      target[0] = colors[index * 4];
      target[1] = colors[index * 4 + 1];
      target[2] = colors[index * 4 + 2];
      target[3] = colors[index * 4 + 3];
      return target as any;
    },
    getYears: (_: any, {index: local, target}: {index: number; target: number[]}) => {
      const index = at(local);
      const lm = hideReplaced ? set.replaced[index] : NaN;
      const end = Number.isNaN(lm) ? set.end[index] : Math.min(set.end[index], lm);
      // under a standing landmark: a footprint that stands today is the landmark itself
      // (hidden in every year — the roll dated Macy's at Stanford 1900 and it stood there
      // as a block for 55 years before the model); vanished buildings stand until the
      // landmark's construction starts
      let hidden = end <= set.start[index] + 0.1 || (!Number.isNaN(lm) && set.end[index] >= 9000);
      let start = set.start[index];
      let stop = end;
      // inside a landmark that is gone today (a ballpark, an exposition): not while it stood
      const occ = hideReplaced ? set.occupied : undefined;
      if (occ && !hidden && !Number.isNaN(occ[index * 2])) {
        const from = occ[index * 2];
        const to = occ[index * 2 + 1];
        // (a building older than the landmark that outlived it was not on the site: the
        // outline is generous — left alone)
        if (start < from) {
          if (stop <= to) stop = Math.min(stop, from);
        } else if (start < to) start = to;
        hidden = stop <= start + 0.1;
      }
      target[0] = hidden ? 1e5 : start;
      target[1] = hidden ? 1e5 : stop;
      return target as any;
    },
    currentYear: year,
    growYears: 2,
    shrinkYears: 0.6,
    // Buildings destroyed in a year get a scorched tint as they sink.
    endTint: [0.42, 0.3, 0.24, 0.65],
    updateTriggers: {getFillColor: quality, getYears: [hideReplaced, set.replaced, set.occupied]},
    extensions: [polygonTime]
  };
  if (set.kind === 'binary') {
    const origin = set.file!.header.origin;
    const data = chunk ? chunk.data : set.data;
    return new BuildingLayer({
      ...common,
      data,
      positionFormat: data.dim === 3 ? 'XYZ' : 'XY',
      _normalize: false,
      coordinateSystem: COORDINATE_SYSTEM.LNGLAT_OFFSETS,
      coordinateOrigin: [origin[0], origin[1], 0]
    } as any);
  }
  return new SolidPolygonLayer({
    ...common,
    data: set.data,
    getPolygon: (f: any) => f.geometry.coordinates
  } as any);
}
