/**
 * Landmark reconstructions: registry, mesh building, layers, picking info and
 * suppression of the generic footprint extrusions they replace.
 */
import type {Layer, PickingInfo} from '@deck.gl/core';
import {BUILDING_MATERIAL} from '../layers/buildings';
import {MeshBuilder, localToLngLat, type V2} from './kit';
import {LandmarkMeshLayer, LANDMARK_COORDS, type MergedLandmarks} from './merged-layer';
import {elevationAt} from '../layers/elevation';
import type {Landmark} from './types';
import {goldenGateBridge} from './golden-gate-bridge';
import {transamerica, salesforceTower, transitCenter} from './downtown';
import {legionOfHonor, paintedLadies, kavanaughHouse} from './neighborhoods';
import {STADIUMS} from './stadiums';
import {CITY_LANDMARKS} from './city';
import {BATCH3} from './batch3';
import {TRANSBAY} from './transbay';
import {BATCH4} from './batch4';
import {EASTBAY} from './eastbay';
import {SOUTHBAY} from './southbay';
import {PORTS} from './ports';

export const LANDMARKS: Landmark[] = [
  goldenGateBridge,
  transamerica,
  salesforceTower,
  transitCenter,
  legionOfHonor,
  paintedLadies,
  kavanaughHouse,
  ...STADIUMS,
  ...CITY_LANDMARKS,
  ...BATCH3,
  ...TRANSBAY,
  ...BATCH4,
  ...EASTBAY,
  ...SOUTHBAY,
  ...PORTS
];

export type LandmarkSet = {
  items: {lm: Landmark; vertices: number}[];
  merged: MergedLandmarks;
  /** replaced-footprint polygons in lon/lat, with the landmark index */
  replaced: {poly: V2[]; bbox: [number, number, number, number]; idx: number}[];
  /** outlines of landmarks that are gone (stadiums, expositions): nothing else stands
   *  inside them while they stood */
  occupied: {poly: V2[]; bbox: [number, number, number, number]; idx: number}[];
};

const ORIGIN: [number, number] = [-122.42, 37.78];
const M_PER_DEG_LAT = 110_574;

/** Build every landmark mesh and merge them into one buffer. Call after elevation loads. */
export async function loadLandmarks(): Promise<LandmarkSet> {
  const meshes = LANDMARKS.map(lm => {
    const b = new MeshBuilder();
    lm.build(b);
    return b.build();
  });
  const total = meshes.reduce((a, m) => a + m.positions.value.length / 3, 0);
  const merged: MergedLandmarks = {
    origin: ORIGIN,
    positions: new Float32Array(total * 3),
    colors: new Float32Array(total * 3),
    times: new Float32Array(total * 4),
    pickingColors: new Float32Array(total * 3),
    builds: new Float32Array(total)
  };
  let o = 0;
  LANDMARKS.forEach((lm, idx) => {
    const m = meshes[idx];
    const pos = m.positions.value;
    const n = pos.length / 3;
    // bridges are modelled from sea level; everything else stands on the terrain
    const base = lm.kind === 'bridge' ? 0 : elevationAt(lm.anchor[0], lm.anchor[1]) - 0.5;
    const kx = 111_320 * Math.cos((lm.anchor[1] * Math.PI) / 180);
    const ax = lm.anchor[0] - ORIGIN[0];
    const ay = lm.anchor[1] - ORIGIN[1];
    const pc = [(idx + 1) % 256, Math.floor((idx + 1) / 256) % 256, Math.floor((idx + 1) / 65536) % 256];
    for (let v = 0; v < n; v++) {
      const k = o + v;
      merged.positions[k * 3] = ax + pos[v * 3] / kx;
      merged.positions[k * 3 + 1] = ay + pos[v * 3 + 1] / M_PER_DEG_LAT;
      merged.positions[k * 3 + 2] = base + pos[v * 3 + 2];
      merged.times[k * 4] = lm.built[0];
      merged.times[k * 4 + 1] = lm.built[1];
      merged.times[k * 4 + 2] = lm.end;
      merged.times[k * 4 + 3] = base;
      merged.builds![k] = lm.kind === 'bridge' ? 1 : 0;
      merged.pickingColors[k * 3] = pc[0];
      merged.pickingColors[k * 3 + 1] = pc[1];
      merged.pickingColors[k * 3 + 2] = pc[2];
    }
    merged.colors.set(m.colors.value, o * 3);
    o += n;
  });
  const items = LANDMARKS.map((lm, i) => ({lm, vertices: meshes[i].positions.value.length / 3}));
  const replaced: LandmarkSet['replaced'] = [];
  const occupied: LandmarkSet['occupied'] = [];
  LANDMARKS.forEach((lm, idx) => {
    // Only standing landmarks replace today's footprints: a demolished
    // stadium's site holds later buildings that must stay visible — but not while
    // the stadium stood (occupied)
    for (const poly of lm.replaces ?? []) {
      const ll = poly.map(p => localToLngLat(lm.anchor, p));
      const xs = ll.map(p => p[0]);
      const ys = ll.map(p => p[1]);
      (lm.end < 9000 ? occupied : replaced).push({poly: ll, bbox: [Math.min(...xs), Math.min(...ys), Math.max(...xs), Math.max(...ys)], idx});
    }
  });
  return {items, merged, replaced, occupied};
}

export function landmarkLayers(set: LandmarkSet, year: number, quality: boolean): Layer[] {
  return [
    new LandmarkMeshLayer({
      id: 'landmarks',
      data: LANDMARKS,
      merged: set.merged,
      ...LANDMARK_COORDS,
      coordinateOrigin: [ORIGIN[0], ORIGIN[1], 0],
      year,
      quality,
      material: BUILDING_MATERIAL,
      pickable: true
    }) as any
  ];
}

export function landmarkInfo(set: LandmarkSet, info: PickingInfo) {
  const item = set.items[info.index];
  if (!item) return null;
  const {lm} = item;
  const rows: Record<string, string | number> = {...lm.facts};
  rows['Model'] = 'reconstructed from cited dimensions & photos';
  rows['Sources'] = lm.sources.map(s => s.replace(/^https?:\/\/(www\.)?/, '').split('/')[0]).join(', ');
  return {title: lm.name, rows};
}

/** Mark buildings whose centroid lies inside a landmark's replaced footprint. */
/** Per building: the construction-start year of the landmark standing on it (NaN if none)
 *  — of the first model of the site's run of landmark models (chainStart). Vanished
 *  buildings on the site stand until then; a footprint that stands today inside the
 *  outline IS the landmark and is hidden in every year, whatever year the roll gives it
 *  (buildings.ts getYears). */
export function replacedMask(set: LandmarkSet, centroids: Float64Array, n: number, heights?: Float32Array): Float32Array {
  const mask = new Float32Array(n).fill(NaN);
  // tall slivers hugging a tower are parts of the same building (OSM maps towers as
  // several building:parts; a 27 m² piece of Salesforce Tower's crown sits just outside
  // the outline and stood alone as a 326 m needle): within ~12 m of the outline they go too
  const TOL_X = 0.00015;
  const TOL_Y = 0.00011;
  for (const r of set.replaced) {
    const from = chainStart(r.idx, r.poly);
    const [x0, y0, x1, y1] = r.bbox;
    for (let i = 0; i < n; i++) {
      const x = centroids[i * 2];
      const y = centroids[i * 2 + 1];
      if (x < x0 - TOL_X || x > x1 + TOL_X || y < y0 - TOL_Y || y > y1 + TOL_Y) continue;
      const tall = heights !== undefined && heights[i] > 60;
      const hit = pointInPolygon(x, y, r.poly) || (tall && distToPolygonDeg(x, y, r.poly) < 1);
      if (hit) mask[i] = Number.isNaN(mask[i]) ? from : Math.min(mask[i], from);
    }
  }
  return mask;
}

/** Per building [from, to] (NaN, NaN if none): the years a landmark that is gone today
 *  occupied its site (Seals Stadium 1931–59, Ewing Field 1914–38, Recreation Park): the
 *  generated houses on those lots stood inside the ballpark. A building there ends when
 *  the landmark's construction starts, or starts when it is gone. */
export function occupiedMask(set: LandmarkSet, centroids: Float64Array, n: number): Float32Array {
  const mask = new Float32Array(n * 2).fill(NaN);
  for (const r of set.occupied) {
    const lm = LANDMARKS[r.idx];
    const [x0, y0, x1, y1] = r.bbox;
    for (let i = 0; i < n; i++) {
      const x = centroids[i * 2];
      const y = centroids[i * 2 + 1];
      if (x < x0 || x > x1 || y < y0 || y > y1 || !pointInPolygon(x, y, r.poly)) continue;
      mask[i * 2] = Number.isNaN(mask[i * 2]) ? lm.built[0] : Math.min(mask[i * 2], lm.built[0]);
      mask[i * 2 + 1] = Number.isNaN(mask[i * 2 + 1]) ? lm.end : Math.max(mask[i * 2 + 1], lm.end);
    }
  }
  return mask;
}

/** Construction start of the first model in the unbroken run of landmark models on a site
 *  that ends with the standing landmark `idx` (Memorial Stadium 1923 → 2012, Hangar One
 *  clad → re-skinned, Call Building → Central Tower, the Cliff Houses): the generated
 *  buildings on the site give way to the first of them, not only to the last. An earlier
 *  model belongs to the site when its anchor lies in the replaced outline (or within
 *  ~90 m of the landmark's anchor) and it ended no more than 5 years before the next. */
const chainCache = new Map<number, number>();
function chainStart(idx: number, poly: V2[]): number {
  const hit = chainCache.get(idx);
  if (hit !== undefined) return hit;
  const lm = LANDMARKS[idx];
  let t = lm.built[0];
  const near = LANDMARKS.filter((o, j) => {
    if (j === idx || o.end >= 9000) return false;
    const dx = (o.anchor[0] - lm.anchor[0]) * 88_000;
    const dy = (o.anchor[1] - lm.anchor[1]) * 111_000;
    return Math.hypot(dx, dy) < 90 || pointInPolygon(o.anchor[0], o.anchor[1], poly);
  }).sort((a, b) => b.end - a.end);
  for (const o of near) {
    if (o.end >= t - 5 && o.built[0] < t) t = o.built[0];
  }
  chainCache.set(idx, t);
  return t;
}

/** Distance from a point to a polygon's edges, in units of the ~12 m tolerance. */
function distToPolygonDeg(x: number, y: number, poly: V2[]) {
  let best = Infinity;
  for (let i = 0, j = poly.length - 1; i < poly.length; j = i++) {
    const ax = (x - poly[j][0]) / 0.00015;
    const ay = (y - poly[j][1]) / 0.00011;
    const bx = (poly[i][0] - poly[j][0]) / 0.00015;
    const by = (poly[i][1] - poly[j][1]) / 0.00011;
    const t = Math.max(0, Math.min(1, (ax * bx + ay * by) / (bx * bx + by * by || 1)));
    best = Math.min(best, Math.hypot(ax - t * bx, ay - t * by));
  }
  return best;
}

function pointInPolygon(x: number, y: number, poly: V2[]) {
  let inside = false;
  for (let i = 0, j = poly.length - 1; i < poly.length; j = i++) {
    const [xi, yi] = poly[i];
    const [xj, yj] = poly[j];
    if (yi > y !== yj > y && x < ((xj - xi) * (y - yi)) / (yj - yi) + xi) inside = !inside;
  }
  return inside;
}
