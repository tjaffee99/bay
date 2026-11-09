/**
 * Low-poly decoration meshes (unit size; instances scale them by
 * [crown radius, crown radius, height]) and their colour palettes.
 * Kinds — keep in sync with pipeline/terrain_tiles.py:
 *   0 broadleaf, 1 conifer, 2 palm, 3 orchard tree, 4 farmstead, 5 shrub,
 *   6 farmyard (barn + tank house beside a real, still standing farmhouse)
 */
import {MeshBuilder, circle} from '../landmarks/kit';

function broadleaf() {
  const b = new MeshBuilder();
  b.color('#7A5C40').box(0, 0, 0, 0.16, 0.16, 0.42);
  b.color('#FFFFFF');
  b.loft([circle(0, 0, 0.6, 7), circle(0, 0, 1, 7), circle(0, 0, 0.82, 7)], [0.32, 0.58, 0.86], {top: false, bottom: true});
  b.pyramid(circle(0, 0, 0.82, 7), 0.86, [0, 0, 1]);
  return b.build();
}
function conifer() {
  const b = new MeshBuilder();
  b.color('#6B4E36').box(0, 0, 0, 0.12, 0.12, 0.18);
  b.color('#FFFFFF');
  b.frustum(0, 0, 0.85, 0.5, 0.12, 0.5, 7, false);
  b.pyramid(circle(0, 0, 0.66, 7), 0.45, [0, 0, 1]);
  return b.build();
}
function palm() {
  const b = new MeshBuilder();
  b.color('#8C7556').frustum(0, 0, 0.09, 0.06, 0, 0.86, 5, false);
  b.color('#FFFFFF');
  for (let i = 0; i < 6; i++) {
    const a = (i / 6) * Math.PI * 2;
    b.tri([0, 0, 0.92], [Math.cos(a - 0.25), Math.sin(a - 0.25), 0.78], [Math.cos(a + 0.25), Math.sin(a + 0.25), 0.78]);
  }
  return b.build();
}
function orchardTree() {
  const b = new MeshBuilder();
  b.color('#7A5C40').box(0, 0, 0, 0.18, 0.18, 0.35);
  b.color('#FFFFFF').dome(0, 0, 1, 0.3, 0.7, 7, 2);
  return b.build();
}
/** Farmstead: house with gable roof + barn, unit ≈ 1 m scaled by size (~8 m). */
function farmstead() {
  const b = new MeshBuilder();
  b.color('#F2EBDD').box(-0.55, 0, 0, 0.9, 0.7, 0.55);
  b.color('#8E5A44').gable(-0.55, 0, 1.0, 0.8, 0.55, 0.35, false);
  b.color('#B0473A').box(0.75, 0.2, 0, 1.0, 1.5, 0.7);
  b.color('#6E3B30').gable(0.75, 0.2, 1.1, 1.6, 0.7, 0.45, true);
  b.color('#D9D2C0').cylinder(0.25, 1.2, 0.18, 0, 1.2, 6);
  return b.build();
}
/** Farmyard: the farmstead without its house (the house is a real building footprint). */
function farmyard() {
  const b = new MeshBuilder();
  b.color('#B0473A').box(0.75, 0.2, 0, 1.0, 1.5, 0.7);
  b.color('#6E3B30').gable(0.75, 0.2, 1.1, 1.6, 0.7, 0.45, true);
  b.color('#D9D2C0').cylinder(-0.3, -0.9, 0.18, 0, 1.2, 6);
  return b.build();
}
function shrub() {
  const b = new MeshBuilder();
  b.color('#FFFFFF').dome(0, 0, 1, 0, 0.9, 6, 2);
  return b.build();
}

export const DECO_MESHES = [broadleaf(), conifer(), palm(), orchardTree(), farmstead(), shrub(), farmyard()];

// ------------------------------------------------------------------ level of detail
// Zoomed out, a tree is a few pixels wide: these 4–10-triangle stand-ins (vs 30–50)
// keep the same silhouette and size. Shared with the street trees (trees.ts).

/** Crown as a bipyramid (squashed diamond) between z0 and z1 with radius r at zm. */
function diamond(b: MeshBuilder, sides: number, r: number, z0: number, zm: number, z1: number) {
  const ring = circle(0, 0, r, sides);
  b.pyramid(ring, zm, [0, 0, z1]);
  // bottom half, wound the other way
  b.pyramid([...ring].reverse(), zm, [0, 0, z0]);
  return b;
}
export function broadleafLow() {
  return diamond(new MeshBuilder().color('#FFFFFF'), 5, 0.95, 0.25, 0.6, 1).build();
}
export function coniferLow() {
  const b = new MeshBuilder().color('#FFFFFF');
  b.pyramid(circle(0, 0, 0.8, 4), 0.1, [0, 0, 1]);
  return b.build();
}
export function palmLow() {
  const b = new MeshBuilder();
  b.color('#8C7556').frustum(0, 0, 0.1, 0.07, 0, 0.86, 3, false);
  b.color('#FFFFFF');
  for (let i = 0; i < 3; i++) {
    const a = (i / 3) * Math.PI * 2;
    b.tri([0, 0, 0.92], [Math.cos(a - 0.4), Math.sin(a - 0.4), 0.78], [Math.cos(a + 0.4), Math.sin(a + 0.4), 0.78]);
  }
  return b.build();
}
function orchardLow() {
  return diamond(new MeshBuilder().color('#FFFFFF'), 4, 1, 0.2, 0.5, 0.95).build();
}
function shrubLow() {
  const b = new MeshBuilder().color('#FFFFFF');
  b.pyramid(circle(0, 0, 1, 4), 0, [0, 0, 0.8]);
  return b.build();
}
export const DECO_MESHES_LOW = [broadleafLow(), coniferLow(), palmLow(), orchardLow(), farmstead(), shrubLow(), farmyard()];

/** Level of detail for all tree-like instances at a map zoom: low-poly below 15, thinned below 14. */
export function treeLod(zoom: number): {low: boolean; keep: number} {
  // keep = share of trees left when zoomed out; the shader (deco-layer.ts) thins
  // continuously from zoom 14.3 down to 12.5
  return {low: zoom < 15, keep: 0.4};
}

export const DECO_COLORS: [number, number, number][][] = [
  [
    [118, 156, 88],
    [100, 142, 80],
    [134, 164, 94],
    [92, 132, 78],
    [128, 150, 84]
  ],
  [
    [70, 108, 70],
    [60, 98, 66],
    [80, 116, 74]
  ],
  [[118, 150, 86]],
  [
    [122, 160, 84],
    [140, 168, 92]
  ],
  [[255, 255, 255]],
  [
    [128, 136, 86],
    [112, 124, 80]
  ],
  [[255, 255, 255]]
];
