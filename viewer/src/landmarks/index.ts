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
  ...BATCH4
];

export type LandmarkSet = {
  items: {lm: Landmark; vertices: number}[];
  merged: MergedLandmarks;
  /** replaced-footprint polygons in lon/lat, with the landmark index */
  replaced: {poly: V2[]; bbox: [number, number, number, number]; idx: number}[];
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
  LANDMARKS.forEach((lm, idx) => {
    // Only standing landmarks replace today's footprints: a demolished
    // stadium's site holds later buildings that must stay visible.
    if (lm.end < 9000) return;
    for (const poly of lm.replaces ?? []) {
      const ll = poly.map(p => localToLngLat(lm.anchor, p));
      const xs = ll.map(p => p[0]);
      const ys = ll.map(p => p[1]);
      replaced.push({poly: ll, bbox: [Math.min(...xs), Math.min(...ys), Math.max(...xs), Math.max(...ys)], idx});
    }
  });
  return {items, merged, replaced};
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
export function replacedMask(set: LandmarkSet, centroids: Float64Array, n: number): Uint8Array {
  const mask = new Uint8Array(n);
  for (const r of set.replaced) {
    const [x0, y0, x1, y1] = r.bbox;
    for (let i = 0; i < n; i++) {
      const x = centroids[i * 2];
      const y = centroids[i * 2 + 1];
      if (x < x0 || x > x1 || y < y0 || y > y1) continue;
      if (pointInPolygon(x, y, r.poly)) mask[i] = 1;
    }
  }
  return mask;
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
