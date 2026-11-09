/**
 * Street trees: real positions from DataSF's Street Tree List, instanced
 * low-poly meshes (broadleaf / conifer / palm) that grow in over ~6 years
 * from their planting year (recorded, or estimated from trunk diameter).
 */
import {COORDINATE_SYSTEM} from '@deck.gl/core';
import type {Layer} from '@deck.gl/core';
import {loadColumnar} from '../data/columnar';
import {MeshBuilder, circle} from '../landmarks/kit';
import {elevationAt} from './elevation';
import {DecoLayer, rankByte} from './deco-layer';
import {broadleafLow, coniferLow, palmLow, treeLod} from './decoration-meshes';

export type TreeSet = {
  id: string;
  origin: [number, number];
  growYears: number;
  forms: {data: any; count: number}[];
};

// Unit meshes; each instance is scaled by [crown radius, crown radius, height].
function broadleaf() {
  const b = new MeshBuilder();
  b.color('#7A5C40').box(0, 0, 0, 0.16, 0.16, 0.4);
  b.color('#FFFFFF');
  b.loft([circle(0, 0, 0.55, 7), circle(0, 0, 1, 7), circle(0, 0, 0.85, 7)], [0.3, 0.55, 0.85], {top: false, bottom: true});
  b.pyramid(circle(0, 0, 0.85, 7), 0.85, [0, 0, 1]);
  return b.build();
}
function conifer() {
  const b = new MeshBuilder();
  b.color('#6B4E36').box(0, 0, 0, 0.14, 0.14, 0.2);
  b.color('#FFFFFF');
  b.frustum(0, 0, 0.8, 0.45, 0.15, 0.55, 7, false);
  b.pyramid(circle(0, 0, 0.62, 7), 0.5, [0, 0, 1]);
  return b.build();
}
function palm() {
  const b = new MeshBuilder();
  b.color('#8C7556').frustum(0, 0, 0.09, 0.06, 0, 0.88, 5, false);
  b.color('#FFFFFF');
  for (let i = 0; i < 6; i++) {
    const a = (i / 6) * Math.PI * 2;
    b.tri([0, 0, 0.92], [Math.cos(a - 0.25), Math.sin(a - 0.25), 0.8], [Math.cos(a + 0.25), Math.sin(a + 0.25), 0.8]);
  }
  return b.build();
}
const MESHES = [broadleaf(), conifer(), palm()];
const MESHES_LOW = [broadleafLow(), coniferLow(), palmLow()];
const GREENS: [number, number, number][][] = [
  [
    [122, 158, 92],
    [104, 144, 84],
    [138, 166, 98],
    [96, 134, 80]
  ],
  [
    [74, 112, 72],
    [64, 102, 68]
  ],
  [[118, 150, 86]]
];

export async function loadTrees(url = 'data/sf-trees.bin.gz', id = 'street', growYears = 6): Promise<TreeSet> {
  const f = await loadColumnar(url);
  return {id, origin: f.header.origin, growYears, forms: decodeTrees(f)};
}

/** Per-form instance buffers (broadleaf / conifer / palm) of a tree file or tile. */
export function decodeTrees(f: {columns: any; header: any}): {data: any; count: number}[] {
  const c = f.columns;
  const n = f.header.counts.features;
  const scale = f.header.meta.position_scale ?? 1e-7;
  const q = c.position_q as Int32Array;
  const form = c.form as Uint8Array;
  const forms = [0, 1, 2].map(k => {
    let m = 0;
    for (let i = 0; i < n; i++) if (form[i] === k) m++;
    const pos = new Float32Array(m * 3);
    const scl = new Float32Array(m * 3);
    const years = new Float32Array(m * 2);
    const ang = new Float32Array(m);
    const col = new Uint8Array(m * 4);
    let j = 0;
    for (let i = 0; i < n; i++) {
      if (form[i] !== k) continue;
      pos[j * 3] = q[i * 2] * scale;
      pos[j * 3 + 1] = q[i * 2 + 1] * scale;
      pos[j * 3 + 2] = elevationAt(f.header.origin[0] + pos[j * 3], f.header.origin[1] + pos[j * 3 + 1]) - 0.3;
      const cr = Math.max(4, (c.crown as Float32Array)[i] * 2.0);
      scl[j * 3] = cr;
      scl[j * 3 + 1] = cr;
      scl[j * 3 + 2] = (c.height as Float32Array)[i] * 1.45;
      years[j * 2] = (c.start_year as Float32Array)[i];
      years[j * 2 + 1] = 9999;
      ang[j] = ((((i * 2654435761) >>> 0) % 360) * Math.PI) / 180;
      const g = GREENS[k][(i * 2654435761) % GREENS[k].length >>> 0] ?? GREENS[k][0];
      col.set(g, j * 4);
      col[j * 4 + 3] = rankByte(f.header.origin[0] + pos[j * 3], f.header.origin[1] + pos[j * 3 + 1]);
      j++;
    }
    return {
      count: m,
      data: {
        length: m,
        attributes: {
          getPosition: {value: pos, size: 3},
          getScale: {value: scl, size: 3},
          getAngle: {value: ang, size: 1},
          getYears: {value: years, size: 2},
          getColor: {value: col, size: 4, normalized: true}
        }
      }
    };
  });
  return forms;
}

export function treesLayer(trees: TreeSet, year: number, zoom = 16, zoomIn = 11.6): Layer[] {
  const lod = treeLod(zoom);
  return trees.forms.map(
    (f, k) =>
      new DecoLayer({
        id: `trees-${trees.id}-${k}`,
        data: f.data,
        mesh: (lod.low ? MESHES_LOW : MESHES)[k],
        keep: lod.keep,
        zoomIn,
        coordinateSystem: COORDINATE_SYSTEM.LNGLAT_OFFSETS,
        coordinateOrigin: [trees.origin[0], trees.origin[1], 0],
        material: {ambient: 0.55, diffuse: 0.55, shininess: 4, specularColor: [20, 24, 18]},
        year,
        growYears: trees.growYears,
        shrinkYears: 0.5
      }) as any
  );
}
