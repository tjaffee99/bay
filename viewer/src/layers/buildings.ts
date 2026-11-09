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
};

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
    return fromBinary(file);
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

export function fromBinary(file: ColumnarFile & {dim: number}): BuildingSet {
  const c = file.columns;
  const n = file.header.counts.features;
  const start = c.start_year as Float32Array;
  const end = c.end_year as Float32Array;
  const height = c.height as Float32Array;
  const confidence = c.confidence as Uint8Array;
  const {colors, qualityColors} = colorArrays(n, confidence, c.fid as Uint32Array, c.mat as Uint8Array | undefined, c.roof as Uint8Array | undefined);
  // ring-end markers: stored as u8, deck wants u16
  const vertexValid = Uint16Array.from(c.vertex_valid as Uint8Array);
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
  const data = {
    length: n,
    startIndices: c.start_indices,
    dim: file.dim,
    attributes: {
      getPolygon: {value: c.positions, size: file.dim},
      indices: c.indices,
      ringEndMarkers: vertexValid
    }
  };
  return {
    kind: 'binary',
    count: n,
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

export function buildingsLayer(set: BuildingSet, year: number, quality: boolean, hideReplaced: boolean, id = 'buildings') {
  const colors = quality ? set.qualityColors : set.colors;
  const common = {
    id,
    extruded: true,
    pickable: true,
    material: BUILDING_MATERIAL,
    getElevation: (_: any, {index}: {index: number}) => set.height[index],
    getFillColor: (_: any, {index, target}: {index: number; target: number[]}) => {
      target[0] = colors[index * 4];
      target[1] = colors[index * 4 + 1];
      target[2] = colors[index * 4 + 2];
      target[3] = colors[index * 4 + 3];
      return target as any;
    },
    getYears: (_: any, {index, target}: {index: number; target: number[]}) => {
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
    return new BuildingLayer({
      ...common,
      data: set.data,
      positionFormat: set.data.dim === 3 ? 'XYZ' : 'XY',
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
