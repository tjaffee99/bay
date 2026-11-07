/**
 * Street trees: real positions from DataSF's Street Tree List, instanced
 * low-poly meshes (broadleaf / conifer / palm) that grow in over ~6 years
 * from their planting year (recorded, or estimated from trunk diameter).
 */
import {COORDINATE_SYSTEM} from '@deck.gl/core';
import type {Layer} from '@deck.gl/core';
import {SimpleMeshLayer} from '@deck.gl/mesh-layers';
import {loadColumnar} from '../data/columnar';
import {MeshBuilder, circle} from '../landmarks/kit';
import {TimeExtension} from './time-extension';

export type TreeSet = {
  origin: [number, number];
  forms: {data: any; count: number}[];
};

const treeTime = new TimeExtension({mode: 'mesh'});

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

export async function loadTrees(): Promise<TreeSet | null> {
  const f = await loadColumnar('data/sf-trees.bin.gz');
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
    const col = new Uint8Array(m * 3);
    let j = 0;
    for (let i = 0; i < n; i++) {
      if (form[i] !== k) continue;
      pos[j * 3] = q[i * 2] * scale;
      pos[j * 3 + 1] = q[i * 2 + 1] * scale;
      const cr = (c.crown as Float32Array)[i];
      scl[j * 3] = cr;
      scl[j * 3 + 1] = cr;
      scl[j * 3 + 2] = (c.height as Float32Array)[i];
      years[j * 2] = (c.start_year as Float32Array)[i];
      years[j * 2 + 1] = 9999;
      const g = GREENS[k][(i * 2654435761) % GREENS[k].length >>> 0] ?? GREENS[k][0];
      col.set(g, j * 3);
      j++;
    }
    return {
      count: m,
      data: {
        length: m,
        attributes: {
          getPosition: {value: pos, size: 3},
          getScale: {value: scl, size: 3},
          getYears: {value: years, size: 2},
          getColor: {value: col, size: 3, normalized: true}
        }
      }
    };
  });
  return {origin: f.header.origin, forms};
}

export function treesLayer(trees: TreeSet, year: number): Layer[] {
  return trees.forms.map(
    (f, k) =>
      new SimpleMeshLayer({
        id: `trees-${k}`,
        data: f.data,
        mesh: MESHES[k],
        coordinateSystem: COORDINATE_SYSTEM.LNGLAT_OFFSETS,
        coordinateOrigin: [trees.origin[0], trees.origin[1], 0],
        material: {ambient: 0.55, diffuse: 0.55, shininess: 4, specularColor: [20, 24, 18]},
        pickable: false,
        extensions: [treeTime],
        currentYear: year,
        growYears: 6,
        shrinkYears: 0.5
      } as any)
  );
}
