/** Colours: soft pastel "diorama" look (Latos-style), tuned for SF. */
export type RGB = [number, number, number];
export type RGBA = [number, number, number, number];

export const WATER = '#a7c7d4';
export const LAND: RGBA = [222, 218, 202, 255];
export const LAND_SIDE: RGBA = [196, 186, 165, 255];
export const PARK: RGBA = [186, 208, 152, 255];
export const GROUND_COLORS: Record<string, RGBA> = {
  park: PARK,
  wood: [150, 184, 122, 255],
  sand: [236, 226, 196, 255]
};

// Facade materials (pipeline/sf_export.py materials()): a few real-world shades each,
// picked per building by a stable hash. Soft, but no longer all off-white.
export const MATERIALS: RGB[][] = [
  // 0 generic
  [[232, 228, 220], [222, 218, 210]],
  // 1 early (gold-rush wood frame, canvas, adobe)
  [[196, 182, 160], [182, 170, 150], [214, 204, 184], [230, 222, 204], [200, 170, 132]],
  // 2 Victorian / Edwardian painted wood
  [
    [238, 226, 198], [212, 226, 212], [204, 219, 232], [232, 212, 222], [242, 230, 178], [226, 210, 188],
    [198, 212, 188], [246, 243, 236], [214, 204, 226], [230, 192, 172], [190, 210, 214], [244, 236, 220]
  ],
  // 3 brick (19th-century commercial, warehouses)
  [[180, 106, 84], [162, 94, 76], [192, 124, 98], [152, 98, 82], [198, 142, 112], [170, 116, 92]],
  // 4 masonry: terra cotta, granite, buff brick (1906-1935 downtown)
  [[238, 228, 206], [228, 216, 190], [214, 208, 196], [242, 234, 216], [222, 202, 172], [204, 198, 190]],
  // 5 stucco (Sunset / Richmond / Marina houses)
  [[248, 244, 236], [242, 226, 210], [240, 234, 204], [222, 234, 222], [224, 230, 240], [240, 222, 224], [234, 226, 212], [246, 238, 222]],
  // 6 mid-century painted concrete / stucco
  [[238, 236, 230], [226, 222, 214], [212, 212, 208], [234, 226, 208], [216, 222, 226]],
  // 7 1960s-80s towers: bronze glass, concrete, brown granite
  [[118, 108, 98], [156, 152, 146], [204, 200, 192], [100, 108, 116], [176, 150, 130]],
  // 8 glass towers (1986+), postmodern granite
  [[152, 178, 194], [124, 152, 170], [198, 206, 210], [178, 198, 202], [212, 202, 188], [198, 174, 164]],
  // 9 contemporary mid-rise panels
  [[216, 218, 220], [174, 176, 180], [104, 106, 112], [240, 238, 232], [188, 164, 134], [206, 190, 174]],
  // 10 civic Beaux-Arts granite
  [[228, 226, 218], [216, 214, 206], [238, 234, 224]],
  // 11 industrial concrete / metal
  [[198, 194, 186], [184, 180, 172], [212, 206, 192], [170, 172, 172], [202, 188, 162]],
  // 12 adobe (sun-dried brick, often limewashed)
  [[226, 206, 172], [210, 182, 144], [236, 224, 200], [198, 170, 132]],
  // 13 tule (Ohlone reed houses)
  [[178, 158, 112], [164, 146, 102], [190, 170, 124]]
];

function hash01(i: number): number {
  let x = (i + 1) * 2654435761;
  x = (x ^ (x >>> 15)) >>> 0;
  x = Math.imul(x, 2246822519) >>> 0;
  x = (x ^ (x >>> 13)) >>> 0;
  return (x % 10007) / 10007;
}

/** Fill colour; alpha carries the roof type for the building shader (255 flat, 254 tile, 253 shingle, 252 as walls). */
export function buildingColor(mat: number, roof: number, i: number, out: Uint8Array | number[], o = 0) {
  const pal = MATERIALS[mat] ?? MATERIALS[0];
  const c = pal[Math.floor(hash01(i) * pal.length) % pal.length];
  out[o] = c[0];
  out[o + 1] = c[1];
  out[o + 2] = c[2];
  out[o + 3] = 255 - Math.min(3, roof);
}

/** year_confidence codes written by the pipeline. */
export const CONFIDENCE = ['exact', 'estimated', 'procedural', 'reconstructed'] as const;
export const CONFIDENCE_COLORS: RGBA[] = [
  [64, 150, 140, 255], // exact – teal
  [232, 146, 60, 255], // estimated – orange
  [150, 110, 190, 255], // procedural – purple
  [214, 176, 52, 255] // reconstructed landmark – gold
];
