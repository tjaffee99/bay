/** Colours: soft pastel "diorama" look (Latos-style), tuned for SF. */
export type RGB = [number, number, number];
export type RGBA = [number, number, number, number];

export const WATER = '#a7c7d4';
export const LAND: RGBA = [222, 218, 202, 255];
export const LAND_SIDE: RGBA = [196, 186, 165, 255];
export const PARK: RGBA = [196, 214, 166, 255];

// Palettes by construction era. Victorians are famously painted; interwar
// stucco is cream/white; post-war is white/grey; towers read as pale glass.
const VICTORIAN: RGB[] = [
  [244, 228, 203], [238, 215, 207], [214, 228, 213], [213, 224, 234],
  [241, 234, 197], [229, 217, 233], [246, 236, 222]
];
const INTERWAR: RGB[] = [[246, 240, 228], [240, 232, 216], [238, 226, 214], [228, 234, 226], [242, 235, 224], [235, 229, 236]];
const MIDCENTURY: RGB[] = [[238, 237, 232], [230, 230, 224], [240, 236, 228], [233, 236, 238]];
const MODERN: RGB[] = [[234, 236, 237], [226, 230, 232], [242, 240, 236], [230, 228, 222]];
const TOWER: RGB[] = [[206, 217, 226], [214, 221, 228], [200, 211, 220], [222, 225, 228]];

function hash01(i: number): number {
  let x = (i + 1) * 2654435761;
  x = (x ^ (x >>> 15)) >>> 0;
  x = Math.imul(x, 2246822519) >>> 0;
  x = (x ^ (x >>> 13)) >>> 0;
  return (x % 10007) / 10007;
}

export function buildingColor(start: number, height: number, i: number, out: Uint8Array | number[], o = 0) {
  const h = hash01(i);
  let pal: RGB[];
  if (height > 55 && start >= 1955) pal = TOWER;
  else if (start < 1906) pal = VICTORIAN;
  else if (start < 1946) pal = INTERWAR;
  else if (start < 1985) pal = MIDCENTURY;
  else pal = MODERN;
  const c = pal[Math.floor(h * pal.length) % pal.length];
  out[o] = c[0];
  out[o + 1] = c[1];
  out[o + 2] = c[2];
  out[o + 3] = 255;
}

/** year_confidence codes written by the pipeline. */
export const CONFIDENCE = ['exact', 'estimated', 'procedural', 'reconstructed'] as const;
export const CONFIDENCE_COLORS: RGBA[] = [
  [64, 150, 140, 255], // exact – teal
  [232, 146, 60, 255], // estimated – orange
  [150, 110, 190, 255], // procedural – purple
  [214, 176, 52, 255] // reconstructed landmark – gold
];
