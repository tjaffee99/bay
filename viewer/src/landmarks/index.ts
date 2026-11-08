/**
 * Landmark reconstructions: registry, mesh building, layers, picking info and
 * suppression of the generic footprint extrusions they replace.
 */
import type {Layer, PickingInfo} from '@deck.gl/core';
import {SimpleMeshLayer} from '@deck.gl/mesh-layers';
import {TimeExtension} from '../layers/time-extension';
import {BUILDING_MATERIAL} from '../layers/buildings';
import {MeshBuilder, localToLngLat, type V2} from './kit';
import {elevationAt} from '../layers/elevation';
import type {Landmark} from './types';
import {goldenGateBridge} from './golden-gate-bridge';
import {transamerica, salesforceTower, transitCenter} from './downtown';
import {legionOfHonor, paintedLadies, kavanaughHouse} from './neighborhoods';
import {STADIUMS} from './stadiums';
import {CITY_LANDMARKS} from './city';
import {BATCH3} from './batch3';
import {TRANSBAY} from './transbay';

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
  ...TRANSBAY
];

export type LandmarkSet = {
  items: {lm: Landmark; mesh: any; vertices: number}[];
  /** replaced-footprint polygons in lon/lat, with the landmark index */
  replaced: {poly: V2[]; bbox: [number, number, number, number]; idx: number}[];
};

const meshTime = new TimeExtension({mode: 'mesh-z'});

export async function loadLandmarks(): Promise<LandmarkSet> {
  const items = LANDMARKS.map(lm => {
    const b = new MeshBuilder();
    lm.build(b);
    return {lm, mesh: b.build(), vertices: b.vertexCount};
  });
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
  return {items, replaced};
}

export function landmarkLayers(set: LandmarkSet, year: number, quality: boolean): Layer[] {
  return set.items
    .filter(({lm}) => year >= lm.built[0] - 0.01 && year < lm.end + 1)
    .map(
      ({lm, mesh}) =>
        new SimpleMeshLayer({
          id: `landmark-${lm.id}`,
          data: [lm],
          mesh,
          // bridges are modelled from sea level; everything else stands on the terrain
          getPosition: (d: Landmark) => [d.anchor[0], d.anchor[1], d.kind === 'bridge' ? 0 : elevationAt(d.anchor[0], d.anchor[1]) - 0.5],
          getColor: quality ? [214, 176, 52] : [255, 255, 255],
          getOrientation: [0, 0, 0],
          material: BUILDING_MATERIAL,
          pickable: true,
          // time
          extensions: [meshTime],
          getYears: (d: Landmark) => [d.built[0], d.end],
          currentYear: year,
          growYears: Math.max(0.5, lm.built[1] - lm.built[0]),
          shrinkYears: 0.8,
          endTint: [0.42, 0.3, 0.24, 0.5],
          updateTriggers: {getColor: quality}
        } as any)
    );
}

export function landmarkInfo(set: LandmarkSet, info: PickingInfo) {
  const id = info.layer?.id.replace(/^landmark-/, '');
  const item = set.items.find(i => i.lm.id === id);
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
