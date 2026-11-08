/**
 * Third batch of reconstructions (data/research/landmarks_batch3.md).
 *
 * Footprints are the OpenStreetMap outlines (via Overture 2026-10-21.0) of the
 * standing buildings, in a frame aligned with the building (`b.frame(0, 0, 0,
 * bearing)`: local +y at `bearing`, +x at `bearing + 90°`), anchored on the
 * OSM centroid; heights from Wikipedia / OSM; massing, setbacks and colours from
 * the reference photos in data/raw/reference_photos/<id>/. Demolished buildings
 * and exposition structures are placed from documented street positions; every
 * estimate is named in the model's facts ("Model: …").
 */
import {MeshBuilder, circle, lngLatToLocal, rect, rotRect, roundedRect, type V2, type V3} from './kit';
import type {Landmark} from './types';

const WIKI = 'https://en.wikipedia.org/wiki/';
const OSM_NOTE = 'footprint from OpenStreetMap (© OSM contributors, ODbL)';

// ------------------------------------------------------------------ helpers

/** Scale a ring about its centroid (setbacks that keep the footprint's shape). */
function scaleRing(ring: V2[], sx: number, sy = sx, dx = 0, dy = 0): V2[] {
  const cx = ring.reduce((s, p) => s + p[0], 0) / ring.length;
  const cy = ring.reduce((s, p) => s + p[1], 0) / ring.length;
  return ring.map(([x, y]) => [cx + (x - cx) * sx + dx, cy + (y - cy) * sy + dy] as V2);
}

/** An OSM part whose outline is given in its own centroid frame (same bearing as the parent). */
function part(b: MeshBuilder, anchor: V2, partAnchor: V2, bearing: number, fn: () => void) {
  const p = lngLatToLocal(anchor, partAnchor);
  b.frame(p[0], p[1], 0, bearing, fn);
}

/** Thin cornice band around a ring. */
function cornice(b: MeshBuilder, ring: V2[], z: number, h: number, color: string, grow = 1.02) {
  b.color(color).prism(scaleRing(ring, grow), z, z + h);
}

/** Vertical facade piers / bay strips along a straight wall from p to q (outward normal side). */
function piers(b: MeshBuilder, p: V2, q: V2, z0: number, z1: number, every: number, depth: number, width: number, color: string) {
  const dx = q[0] - p[0];
  const dy = q[1] - p[1];
  const L = Math.hypot(dx, dy);
  const brg = (Math.atan2(dx, dy) * 180) / Math.PI;
  b.color(color);
  for (let t = every / 2; t < L; t += every) {
    b.frame(p[0] + (dx * t) / L, p[1] + (dy * t) / L, 0, brg, () => b.box(depth / 2, 0, z0, depth, width, z1 - z0));
  }
}

/** Keep the part of a convex-or-not ring where (p − a)·n ≥ d (Sutherland–Hodgman, one plane). */
function clipHalfPlane(ring: V2[], a: V2, n: V2, d: number): V2[] {
  const f = (p: V2) => (p[0] - a[0]) * n[0] + (p[1] - a[1]) * n[1] - d;
  const out: V2[] = [];
  for (let i = 0; i < ring.length; i++) {
    const p = ring[i];
    const q = ring[(i + 1) % ring.length];
    const fp = f(p);
    const fq = f(q);
    if (fp >= 0) out.push(p);
    if (fp >= 0 !== fq >= 0) {
      const t = fp / (fp - fq);
      out.push([p[0] + (q[0] - p[0]) * t, p[1] + (q[1] - p[1]) * t]);
    }
  }
  return out;
}

// =========================================================== Palace Hotel (1875 and 1909)
// Block bounded by Market St (NW), New Montgomery St (NE), Jessie St (SE) and
// Annie St (SW); OSM outline 79 × 102 m. Frame 135°: +y SE along New Montgomery,
// +x SW along Market; the Market/New Montgomery corner is at (−39.5, −52.9).
const PALACE: V2 = [-122.40193, 37.787958];
const palace1875: Landmark = {
  id: 'palace_hotel_1875',
  name: 'Palace Hotel (1875)',
  kind: 'building',
  built: [1873.0, 1875.75],
  end: 1906.3,
  anchor: PALACE,
  build: b => {
    b.frame(0, 0, 0, 135, () => {
      const outer = rect(0, -1.75, 79, 102.3);
      const court = rect(0, -1.75, 26, 44); // Grand Court (carriage court) under a glass roof
      b.color('#ECE6D6').prism(outer, 0, 35, {holes: [court]});
      b.color('#9A9A96').cap(outer, 36.6, [court]).prism(outer, 35, 36.6, {top: false, holes: [court]});
      b.color('#B9CDD6').cap(court, 30); // glass roof over the Grand Court
      // the famous tiers of bay windows on every street front
      for (const [p, q] of [
        [[-39.5, -52.9], [39.6, -52.9]],
        [[39.6, -52.9], [39.6, 49.4]],
        [[39.6, 49.4], [-39.5, 49.4]],
        [[-39.5, 49.4], [-39.5, -52.9]]
      ] as [V2, V2][])
        piers(b, p, q, 4.5, 33, 5.2, 0.9, 2.6, '#F3EFE4');
    });
  },
  facts: {
    Opened: 'Oct 2, 1875 (William Ralston) — the largest hotel in the American West',
    Size: '120 ft (37 m), 755 rooms, a bay window to every parlour; skylit Grand Court (carriage entrance) ringed by seven tiers of balconies',
    Fate: 'survived the earthquake of Apr 18, 1906 but burned that afternoon; demolished',
    Model: 'block outline from today’s OSM footprint (same block, rebuilt on the same site); Grand Court size and bay-window rhythm estimated (no period photo downloaded)'
  },
  sources: [WIKI + 'Palace_Hotel,_San_Francisco']
};
const palace1909: Landmark = {
  id: 'palace_hotel_1909',
  name: 'Palace Hotel',
  kind: 'building',
  built: [1907.0, 1909.97],
  end: 9999,
  anchor: PALACE,
  build: b => {
    b.frame(0, 0, 0, 135, () => {
      const outer = rect(0, -1.75, 79, 102.3);
      const wells = [rect(-20, 30, 14, 26), rect(20, 30, 14, 26), rect(-20, -34, 14, 22), rect(20, -34, 14, 22)];
      b.color('#D9C7A6').prism(outer, 0, 32, {holes: wells});
      cornice(b, outer, 32, 1.2, '#E8DCC3', 1.01);
      b.color('#C9B994').prism(scaleRing(outer, 0.97), 33.2, 35);
      // Garden Court: glass-roofed centre of the block
      b.color('#B9CDD6').box(0, -2, 10, 34, 26, 1.5);
      // rooftop "THE PALACE" sign at the Market / New Montgomery corner
      b.color('#5B5E62').box(-33, -46, 35, 1, 1, 6).box(-30, -48, 35, 1, 1, 6);
      b.color('#F2F0EA').frame(-31.5, -47, 0, 45, () => b.box(0, 0, 38, 0.6, 11, 4));
    });
  },
  replaces: [rotRect(0, -1.75, 82, 106, 135)],
  facts: {
    Reopened: 'Dec 19, 1909 (Trowbridge & Livingston), rebuilt on the 1875 site',
    Height: '9 storeys, 35 m',
    'Garden Court': 'glass-roofed dining room in the former carriage court',
    Model: OSM_NOTE + '; light wells and sign position from photos (estimated)'
  },
  sources: [WIKI + 'Palace_Hotel,_San_Francisco']
};

// =========================================================== Call Building (1898) → Central Tower (1938)
// 3rd & Market; OSM footprint 24.3 × 22.2 m (frame 135°).
const CALL: V2 = [-122.403585, 37.787188];
const callBuilding: Landmark = {
  id: 'call_building_1898',
  name: 'Call Building (Claus Spreckels Building)',
  kind: 'tower',
  built: [1895.3, 1898.0],
  end: 1938.0,
  anchor: CALL,
  build: b => {
    b.frame(0, 0, 0, 135, () => {
      b.color('#BDB3A1').box(0, 0, 0, 24.3, 22.2, 62);
      b.color('#D2C9B8').box(0, 0, 62, 25.3, 23.2, 2);
      // Baroque dome stage: square attic with corner turrets, drum, dome and lantern
      b.color('#BDB3A1').box(0, 0, 64, 20, 18, 6);
      for (const [x, y] of [
        [-9, -8],
        [9, -8],
        [9, 8],
        [-9, 8]
      ])
        b.color('#BDB3A1').cylinder(x, y, 2.2, 64, 76, 8).color('#5E6266').dome(x, y, 2.4, 76, 3, 8, 2);
      b.color('#BDB3A1').cylinder(0, 0, 9, 70, 76, 16);
      b.color('#5E6266').dome(0, 0, 9.5, 76, 11, 16, 4);
      b.color('#BDB3A1').cylinder(0, 0, 2.6, 86, 92, 8);
      b.color('#5E6266').dome(0, 0, 2.8, 92, 3, 8, 2).cylinder(0, 0, 0.3, 94.5, 96, 4);
    });
  },
  facts: {
    Built: 'completed 1898 (Reid & Reid) for Claus Spreckels’ San Francisco Call — the tallest building west of Chicago',
    Height: '315 ft (96 m), 15 storeys; Baroque dome (architects’ offices) with four corner cupolas',
    '1906': 'burned out but did not collapse; restored',
    '1938': 'dome and cupolas removed, re-clad and raised to 21 floors as the Central Tower',
    Model: 'shaft from today’s OSM footprint; dome and cupola proportions estimated (no period photo downloaded)'
  },
  sources: [WIKI + 'Central_Tower_(San_Francisco)']
};
const centralTower: Landmark = {
  id: 'central_tower_1938',
  name: 'Central Tower',
  kind: 'tower',
  built: [1937.2, 1938.2],
  end: 9999,
  anchor: CALL,
  build: b => {
    b.frame(0, 0, 0, 135, () => {
      const cream = '#E2DACB';
      b.color(cream).box(0, 0, 0, 24.3, 22.2, 74);
      b.color('#D7CEBD').box(0, 0, 74, 21, 19, 7).box(0, 0, 81, 17, 15, 6);
      b.color(cream).box(0, 0, 87, 12, 10, 4);
      // vertical piers on the Market St (NW, −y) and 3rd St (SW, +x) fronts
      piers(b, [-12.15, -11.1], [12.15, -11.1], 6, 74, 3.1, 0.4, 0.8, '#EEE8DC');
    });
  },
  replaces: [rect(0, 0, 30, 30)],
  facts: {Remodelled: '1937–38 (Albert Roller): dome removed, Art Moderne re-cladding, 15 → 21 floors', Height: '298 ft (91 m)', Model: OSM_NOTE + '; setbacks from photo'},
  sources: [WIKI + 'Central_Tower_(San_Francisco)']
};

// =========================================================== Mills Building (1892) + Mills Tower (1931)
const MILLS: V2 = [-122.401883, 37.79136];
const millsBuilding: Landmark = {
  id: 'mills_building',
  name: 'Mills Building',
  kind: 'building',
  built: [1890.5, 1892.0],
  end: 9999,
  anchor: MILLS,
  build: b => {
    b.frame(0, 0, 0, 171, () => {
      const ring: V2[] = [
        [-44.6, -20.3],
        [18.5, -20.4],
        [18.5, -25.3],
        [41.2, -25.3],
        [41.2, 22.7],
        [-44.7, 22.8]
      ];
      const court = rect(-8, 1, 30, 18);
      b.color('#E4DCCB').prism(ring, 0, 44, {holes: [court]});
      cornice(b, ring, 44, 1.5, '#D3C9B6', 1.01);
      b.color('#CFC5B1').prism(scaleRing(ring, 0.97), 45.5, 47);
      // Romanesque arched entrance bay on Montgomery St (+x side here faces west)
      b.color('#8A7F70').box(40.6, 0, 0, 1.4, 9, 12);
    });
  },
  replaces: [rect(1.7, 1.2, 88, 50)],
  facts: {
    Completed: '1892 (Burnham & Root) — survived the 1906 earthquake, gutted by the fire, restored 1908',
    Height: '10 storeys, 46.9 m',
    Model: OSM_NOTE + '; light-court size estimated'
  },
  sources: [WIKI + 'Mills_Building_and_Tower']
};
const millsTower: Landmark = {
  id: 'mills_tower_1931',
  name: 'Mills Tower',
  kind: 'tower',
  built: [1930.2, 1931.5],
  end: 9999,
  anchor: [-122.401303, 37.791421],
  build: b => {
    b.frame(0, 0, 0, 171, () => {
      b.color('#E4DCCB').box(0, 0, 0, 13.6, 43.1, 88);
      b.color('#D3C9B6').box(0, 0, 88, 14.2, 43.7, 1.5).box(0, 0, 89.5, 12, 41, 2.5);
    });
  },
  replaces: [rect(0, 0, 16, 45)],
  facts: {Built: '1931 (Lewis P. Hobart), 22 floors, matching the 1892 building', Height: '92 m', Model: OSM_NOTE},
  sources: [WIKI + 'Mills_Building_and_Tower']
};

// =========================================================== Montgomery Block (1853–1959)
// SE corner of Montgomery & Washington, Montgomery frontage from Washington to
// Merchant St (≈ 37 m between the DataSF street centrelines minus half-widths),
// depth ≈ 42 m (estimated), four storeys (15 m) around a light court. Now the
// Transamerica Pyramid site.
const montgomeryBlock: Landmark = {
  id: 'montgomery_block',
  name: 'Montgomery Block ("Monkey Block")',
  kind: 'building',
  built: [1852.8, 1853.9],
  end: 1959.3,
  anchor: [-122.402883, 37.79527],
  build: b => {
    b.frame(0, 0, 0, -10, () => {
      const court = rect(2, 0, 14, 12);
      b.color('#CDC5B4').prism(rect(0, 0, 42, 37), 0, 15, {holes: [court]});
      b.color('#B3AA97').prism(rect(0, 0, 42.6, 37.6), 15, 15.8, {holes: [court]});
      piers(b, [-21, -18.5], [-21, 18.5], 3.5, 14, 3.6, 0.3, 1.0, '#BDB4A0'); // Montgomery St front
    });
  },
  facts: {
    Built: '1853 (G. P. Cummings) on a raft of redwood logs — the tallest building in the West',
    Height: '4 storeys, ≈ 15 m',
    Known: 'survived 1906; later a celebrated home of artists’ and writers’ studios',
    Demolished: '1959 (Transamerica Pyramid site from 1969)',
    Model: 'frontage from the DataSF street centrelines (Washington to Merchant St); depth and light court estimated (LOW CONFIDENCE)'
  },
  sources: [WIKI + 'Montgomery_Block', 'https://www.loc.gov/item/ca0675/']
};

// =========================================================== Old Mint (1874)
// OSM outline (frame 135°): portico on the 5th St front (−x, facing NE).
const oldMint: Landmark = {
  id: 'old_mint',
  name: 'Old San Francisco Mint ("The Granite Lady")',
  kind: 'building',
  built: [1869.25, 1874.85],
  end: 9999,
  anchor: [-122.407238, 37.782728],
  build: b => {
    b.frame(0, 0, 0, 135, () => {
      const ring: V2[] = [
        [-26.2, -20.5], [-26.1, -33.8], [-12.7, -33.8], [-12.7, -30.1], [12.7, -30.0], [12.7, -32.3], [23.9, -32.3], [23.7, -9.5],
        [28.9, -9.5], [28.7, 9.4], [24.0, 9.4], [23.9, 34.5], [13.5, 34.4], [13.5, 30.0], [-13.6, 30.0], [-13.6, 33.2], [-24.8, 33.2],
        [-24.7, 21.8], [-21.6, 21.8], [-21.5, 11.2], [-21.1, -8.8], [-21.2, -20.5]
      ];
      const stone = '#B8B2A4';
      b.color(stone).prism(ring, 0, 14.5);
      cornice(b, ring, 14.5, 1.5, '#C8C2B4', 1.01);
      // raised basement + Doric portico of six columns and pediment on 5th St
      b.color(stone).box(-25, 1.2, 0, 8, 20, 4);
      b.color('#CCC6B8');
      for (const y of [-7.5, -4.4, -1.3, 1.8, 4.9, 8]) b.cylinder(-27.6, y + 1.2, 0.8, 4, 13, 10);
      b.color(stone).box(-26.5, 1.2, 13, 4.6, 20, 2).gable(-26.5, 1.2, 4.6, 20, 15, 2.6, false);
    });
  },
  replaces: [rotRect(0, 0, 66, 72, 135)],
  facts: {
    Built: '1869–74 (Alfred B. Mullett), Greek Revival, sandstone on granite',
    '1906': 'one of the few downtown buildings to survive the fire — its vaults held a third of the US gold reserve',
    Height: '52.5 ft (16 m)',
    Model: OSM_NOTE + '; portico columns from photo'
  },
  sources: [WIKI + 'Old_San_Francisco_Mint']
};

// =========================================================== Flood Building (1904)
const floodBuilding: Landmark = {
  id: 'flood_building',
  name: 'Flood Building',
  kind: 'building',
  built: [1902.5, 1904.5],
  end: 9999,
  anchor: [-122.407429, 37.785118],
  build: b => {
    b.frame(0, 0, 0, 171, () => {
      const ring: V2[] = [
        [4.9, 40.1], [-32.8, 13.1], [-21.1, -1.9], [-21.3, -37.3], [20.9, -37.0], [20.3, 32.5], [18.8, 32.7], [20.1, 38.7],
        [17.7, 42.8], [13.0, 44.4], [8.2, 42.9], [6.2, 38.7]
      ];
      const stone = '#C7C0B4';
      b.color(stone).prism(ring, 0, 45);
      cornice(b, ring, 45, 1.4, '#D6D0C4', 1.01);
      b.color('#B5AEA1').prism(scaleRing(ring, 0.96), 46.4, 49);
      // rounded corner bay at Powell & Market with its low dome
      b.color(stone).cylinder(13, 37.5, 6.5, 0, 47, 14);
      b.color('#8E8C88').dome(13, 37.5, 6.5, 47, 2.5, 14, 2);
    });
  },
  replaces: [rect(0, 0, 50, 80)],
  facts: {Completed: '1904 (Albert Pissis) for James L. Flood', '1906': 'survived the earthquake; gutted by the fire, restored', Height: '12 storeys, 49 m (OSM)', Model: OSM_NOTE},
  sources: [WIKI + 'Flood_Building']
};

// =========================================================== Russ Building (1927)
const RUSS: V2 = [-122.402862, 37.791419];
const russBuilding: Landmark = {
  id: 'russ_building',
  name: 'Russ Building',
  kind: 'tower',
  built: [1926.0, 1927.75],
  end: 9999,
  anchor: RUSS,
  build: b => {
    const terra = '#DCD3C2';
    b.frame(0, 0, 0, 171, () => {
      const base: V2[] = [
        [17.3, 2.2],
        [17.1, 43.1],
        [-21.5, 42.9],
        [-21.1, -39.6],
        [24.8, -39.4],
        [24.6, 2.3]
      ];
      b.color(terra).prism(base, 0, 54);
    });
    part(b, RUSS, [-122.402724, 37.791418], 171, () => {
      const tower: V2[] = [
        [6.2, -16.1], [6.2, -11.7], [9.6, -11.7], [9.1, 11.9], [6.1, 11.9], [6.0, 16.1], [-6.2, 16.0], [-6.2, 11.9], [-9.4, 11.9],
        [-9.2, -12.3], [-5.4, -12.3], [-5.4, -16.2]
      ];
      b.color(terra).prism(scaleRing(tower, 1.25, 1.12), 54, 96).prism(tower, 96, 118);
      b.color('#CFC5B2').prism(scaleRing(tower, 0.75), 118, 124).prism(scaleRing(tower, 0.45), 124, 127.4);
      // Gothic pinnacles at the crown corners
      for (const [x, y] of [
        [-7, -12],
        [7, -12],
        [7, 12],
        [-7, 12]
      ])
        b.color('#E6DECF').pyramid(rect(x, y, 2, 2), 118, [x, y, 126]);
    });
  },
  replaces: [rect(-2, 0, 50, 86)],
  facts: {Completed: '1927 (George W. Kelham), Gothic Revival', Height: '127.4 m — the city’s tallest until 1964', Floors: '31', Model: OSM_NOTE + '; base height and crown estimated from photos'},
  sources: [WIKI + 'Russ_Building']
};

// =========================================================== Shell Building (1929)
const shellBuilding: Landmark = {
  id: 'shell_building',
  name: 'Shell Building',
  kind: 'tower',
  built: [1928.3, 1929.6],
  end: 9999,
  anchor: [-122.39998, 37.791572],
  build: b => {
    const terra = '#E3D9C3';
    b.frame(0, 0, 0, 171, () => {
      b.color(terra).prism(roundedRect(0, 0, 37.1, 41.7, 2.5, 1), 0, 72);
      b.color(terra).prism(roundedRect(-2.5, 3.9, 32, 34, 2.5, 1), 72, 92);
      b.color(terra).prism(roundedRect(-5.1, 7.8, 26.6, 26.2, 3, 1), 92, 106);
      b.color('#D6CBB2').prism(roundedRect(-5.1, 7.8, 20, 20, 3, 1), 106, 111).prism(roundedRect(-5.1, 7.8, 13, 13, 2, 1), 111, 115.2);
    });
  },
  replaces: [rect(0, 0, 40, 44)],
  facts: {Completed: '1929 (George W. Kelham) for Shell Oil', Height: '115.2 m', Floors: '29', Model: OSM_NOTE + '; setback heights estimated from photo'},
  sources: [WIKI + 'Shell_Building_(San_Francisco)']
};

// =========================================================== 450 Sutter (1929)
const SUTTER450: V2 = [-122.407875, 37.789638];
const sutter450: Landmark = {
  id: 'sutter_450',
  name: '450 Sutter Street',
  kind: 'tower',
  built: [1928.6, 1929.8],
  end: 9999,
  anchor: SUTTER450,
  build: b => {
    const tan = '#C9B58F';
    b.frame(0, 0, 0, 171, () => {
      const ring: V2[] = [
        [20.3, -25.4],
        [20.2, 23.7],
        [-21.1, 23.9],
        [-20.9, -21.5],
        [-3.4, -21.6],
        [-3.4, -25.4]
      ];
      b.color(tan).prism(ring, 0, 88);
      piers(b, [-21.1, 23.9], [20.2, 23.7], 4, 88, 3.4, 0.6, 1.4, '#D7C6A3');
    });
    part(b, SUTTER450, [-122.407861, 37.789589], 171, () => {
      const top: V2[] = [
        [8.8, 0.4],
        [18.1, 0.4],
        [18.0, 18.2],
        [-18.4, 18.5],
        [-18.4, 0.0],
        [-8.0, 0.0],
        [-8.1, -26.8],
        [8.9, -27.0]
      ];
      b.color(tan).prism(top, 88, 101);
      b.color('#B9A47D').prism(scaleRing(top, 0.85), 101, 105);
    });
  },
  replaces: [rect(0, 0, 44, 52)],
  facts: {Completed: 'Oct 1929 (Timothy Pflueger / Miller & Pflueger), Mayan-revival Art Deco', Height: '105 m', Floors: '26', Model: OSM_NOTE + '; top setback height estimated'},
  sources: [WIKI + '450_Sutter_Street']
};

// =========================================================== 140 New Montgomery (1925)
// Plan: the OSM outline (frame 135°: +v along New Montgomery St to the south-east, −u = the New Montgomery front),
// 44.8 × 48.8 m = the documented 147 × 160 ft L (Wikipedia); the two light-court slots that OSM shows cut into the back
// of the New Montgomery range carry up the tower, giving the "truncated E" plan (SAH Archipedia). Heights: top floor
// 413 ft (125.9 m), roof / crown 435 ft (132.7 m), spire 460 ft (140.2 m); eight 13 ft eagles on the crown.
const NM140_L: V2[] = [
  [9.0, 12.7], [9.0, 26.1], [1.8, 26.1], [1.8, 27.6], [-16.9, 27.7], [-16.6, -21.0], [28.1, -21.0], [28.1, -6.4], [9.0, -6.4],
  [9.0, 8.3], [6.4, 8.3], [6.3, 9.9], [-1.5, 9.9], [-1.5, 12.7]
];
/** Tower floors: the New Montgomery range with its two rear arms (light courts between them), as an outline. */
const NM140_E: V2[] = [
  [9.0, 13.2], [9.0, 27.6], [-16.9, 27.7], [-16.6, -21.0], [9.0, -21.0], [9.0, -2.6], [-1.5, -2.6], [-1.5, 0.4], [9.0, 0.4], [9.0, 9.6],
  [-1.5, 9.6], [-1.5, 13.2]
];
const newMontgomery140: Landmark = {
  id: 'new_montgomery_140',
  name: '140 New Montgomery (Pacific Telephone Building)',
  kind: 'tower',
  built: [1924.0, 1925.41],
  end: 9999,
  anchor: [-122.40001, 37.786679],
  build: b => {
    const white = '#E6E4DE';
    const shade = '#D8D5CC';
    const inset = (ring: V2[], d: number): V2[] => {
      // shrink a rectilinear outline toward its bounding-box centre by d on every side (setbacks)
      const xs = ring.map(p => p[0]);
      const ys = ring.map(p => p[1]);
      const [x0, x1, y0, y1] = [Math.min(...xs), Math.max(...xs), Math.min(...ys), Math.max(...ys)];
      return rect((x0 + x1) / 2, (y0 + y1) / 2, x1 - x0 - 2 * d, y1 - y0 - 2 * d);
    };
    b.frame(0, 0, 0, 135, () => {
      // base filling the lot; the rear (Minna St) wing of the L rises to ≈ 20 floors
      b.color(white).prism(NM140_L, 0, 22);
      b.color(white).prism([[9.0, -21.0], [28.1, -21.0], [28.1, -6.4], [9.0, -6.4]], 22, 88);
      // tower shaft on the truncated-E plan, straight up to the first setback (≈ floor 22)
      b.color(white).prism(NM140_E, 22, 99);
      // strong vertical piers on the New Montgomery front
      b.color(shade);
      for (let v = -19; v <= 26; v += 4.5) b.box(-17.1, v, 22, 0.5, 0.9, 77);
      // stepped crown after the Tribune Tower design: three setbacks to the top floor (413 ft) and the crown (435 ft)
      const front: V2[] = [[-16.9, -21.0], [9.0, -21.0], [9.0, 27.7], [-16.9, 27.7]];
      b.color(white).prism(inset(front, 2.2), 99, 111);
      b.color(shade).prism(inset(front, 5.5), 111, 119);
      b.color(white).prism(inset(front, 8.5), 119, 125.9);
      b.color(shade).prism(inset(front, 10.5), 125.9, 132.7);
      // eight 13 ft eagles on the corners of the two upper setbacks
      b.color('#F1EFEA');
      const eagles = (r: V2[], z: number) => r.forEach(([x, y]) => b.box(x, y, z, 1.6, 1.6, 4));
      eagles(inset(front, 3.2), 111);
      eagles(inset(front, 9.3), 125.9);
      b.color('#8A8C8E').cylinder(-3.95, 3.35, 0.25, 132.7, 140.2, 4); // spire / flagpole
    });
  },
  replaces: [rotRect(5.6, 3.35, 46, 50, 135)],
  facts: {
    Built: 'Jan 1924 – opened May 30, 1925 (Miller & Pflueger, Timothy Pflueger, with A. A. Cantin): Art Deco headquarters of Pacific Telephone & Telegraph',
    Height: '26 floors; top floor 413 ft (125.9 m), roof 435 ft (132.7 m), spire 460 ft (140.2 m)',
    Plan: 'L-shaped, 147 × 160 ft (Wikipedia); light courts make the tower a "truncated E" (SAH Archipedia); setbacks after the Tribune Tower design; eight 13 ft terra-cotta eagles on the crown (fibreglass replicas since the 1989 earthquake)',
    Model:
      OSM_NOTE +
      '; the light courts are the two OSM slots carried up the tower; podium height (22 m), rear-wing height, setback levels and insets, and the eagles’ positions estimated from photographs — no HABS drawing was read'
  },
  sources: [WIKI + '140_New_Montgomery', 'https://sah-archipedia.org/node/83240', 'https://www.loc.gov/item/ca3887/']
};

// =========================================================== 555 California (1969)
// Carnelian-granite slab with full-height sawtooth bay windows; the OSM top-floor
// outline (51.9 × 21.3 m) is scaled up to the 73 × 43 m main shaft (OSM part).
const CA555_TOP: V2[] = [
  [-21.4, 10.5], [-25.9, 6.0], [-23.9, 2.8], [-25.9, -0.1], [-23.9, -3.2], [-25.9, -5.9], [-21.4, -10.6], [-18.4, -9.0], [-15.1, -10.6],
  [-12.5, -9.0], [-9.1, -10.5], [-6.4, -9.0], [-3.0, -10.5], [-0.2, -9.0], [3.1, -10.5], [5.9, -9.0], [9.0, -10.5], [11.9, -9.0],
  [15.2, -10.5], [17.9, -9.0], [21.1, -10.5], [25.8, -6.2], [23.8, -3.0], [25.9, -0.2], [23.8, 3.1], [25.9, 6.2], [21.1, 10.8],
  [17.8, 8.8], [15.2, 10.9], [12.2, 8.9], [9.0, 10.8], [6.1, 8.9], [2.7, 10.8], [-0.0, 8.8], [-3.3, 10.7], [-6.0, 8.8], [-9.4, 10.7],
  [-12.1, 8.7], [-15.3, 10.6], [-18.3, 8.6]
];
const california555: Landmark = {
  id: 'california_555',
  name: '555 California Street (Bank of America Center)',
  kind: 'tower',
  built: [1966.8, 1969.5],
  end: 9999,
  anchor: [-122.403776, 37.7921],
  build: b => {
    const granite = '#5B403A';
    b.frame(0, 0, 0, 171, () => {
      b.color(granite).prism(scaleRing(CA555_TOP, 1.415, 2.0), 0, 196);
      b.color(granite).prism(scaleRing(CA555_TOP, 1.25, 1.55), 196, 214).prism(scaleRing(CA555_TOP, 1.12, 1.25), 214, 226);
      b.color('#4C3631').prism(CA555_TOP, 226, 237.4);
    });
  },
  replaces: [rect(0, 0, 76, 46)],
  facts: {
    Completed: '1969 (Wurster, Bernardi & Emmons with SOM) — the city’s tallest until 1972',
    Height: '237.4 m (779 ft), 52 floors',
    Cladding: 'carnelian granite, sawtooth bay windows',
    Model: OSM_NOTE + ' (top-floor outline and main-shaft size); the irregular setbacks of the top floors simplified'
  },
  sources: [WIKI + '555_California_Street']
};

// =========================================================== Embarcadero Center 1–4 (1971–1982) + Hyatt Regency (1973)
// Thin slab towers with serrated (setback) ends; OSM outlines, frame 171°.
function ecTower(id: string, n: number, anchor: V2, ring: V2[], h: number, built: [number, number], floors: number): Landmark {
  return {
    id,
    name: `Embarcadero Center ${n}`,
    kind: 'tower',
    built,
    end: 9999,
    anchor,
    build: b => {
      b.frame(0, 0, 0, 171, () => {
        b.color('#CFCBC2').prism(ring, 0, h - 3);
        b.color('#BDB9B0').prism(scaleRing(ring, 0.96, 0.9), h - 3, h);
        // podium of the Center's retail galleries
        b.color('#B7B2A8').prism(scaleRing(ring, 1.08, 1.5), 0, 12, {top: true});
      });
    },
    replaces: [rect(0, 0, 82, 38)],
    facts: {
      Completed: `${Math.round(built[1])} (John Portman & Associates)`,
      Height: `${h} m, ${floors} floors (OSM / Wikipedia)`,
      Model: OSM_NOTE + '; podium height estimated'
    },
    sources: [WIKI + 'Embarcadero_Center']
  };
}
const EC1: V2[] = [
  [-38.9, 4.8], [-36.4, 4.6], [-36.4, -0.1], [-30.6, -0.2], [-30.7, -5.0], [-28.1, -5.1], [-28.1, -11.1], [-17.5, -11.0], [-17.5, -16.1],
  [24.0, -16.3], [24.0, -11.1], [36.2, -11.0], [36.2, -0.4], [31.9, -0.4], [31.9, 4.1], [29.8, 4.1], [29.9, 10.5], [17.6, 10.7], [17.7, 16.2],
  [-19.1, 16.7], [-19.2, 11.1], [-38.8, 11.4]
];
const EC2: V2[] = [
  [-37.6, -16.6], [35.2, -16.3], [35.2, -10.7], [41.4, -10.7], [41.4, 1.2], [35.7, 1.1], [35.7, 6.5], [33.2, 6.4], [33.2, 10.5], [28.6, 10.5],
  [28.5, 17.4], [-37.5, 17.2], [-37.4, 6.9], [-33.8, 6.9], [-33.7, -6.0], [-37.7, -6.1]
];
const EC3: V2[] = [
  [-32.9, -16.7], [37.3, -17.2], [37.3, -7.7], [34.8, -7.7], [34.8, 3.8], [37.8, 3.7], [37.9, 17.4], [-30.0, 17.8], [-30.1, 11.1], [-34.7, 11.1],
  [-34.7, 1.7], [-41.1, 1.7], [-41.2, -13.4], [-32.9, -13.5]
];
const EC4: V2[] = [
  [23.9, -13.5], [29.5, -13.4], [29.4, -6.4], [31.2, -6.4], [31.2, -0.5], [29.7, -0.5], [29.7, 18.4], [-27.0, 18.5], [-27.0, 11.0], [-29.5, 11.0],
  [-29.5, 4.7], [-32.2, 4.7], [-32.2, -1.2], [-29.8, -1.2], [-29.2, -13.5], [-27.4, -13.4], [-27.4, -18.8], [23.9, -18.9]
];
const EMBARCADERO_CENTER: Landmark[] = [
  ecTower('embarcadero_center_1', 1, [-122.399637, 37.794484], EC1, 173, [1969.5, 1971.6], 45),
  ecTower('embarcadero_center_2', 2, [-122.398495, 37.794997], EC2, 130, [1972.6, 1974.5], 31),
  ecTower('embarcadero_center_3', 3, [-122.397373, 37.795125], EC3, 130, [1975.5, 1977.5], 31),
  ecTower('embarcadero_center_4', 4, [-122.396205, 37.795297], EC4, 174, [1980.2, 1982.5], 45)
];

// Hyatt Regency: right-angled trapezoid; the long diagonal (south-east) face is
// the stepped, sloping wall of the 17-storey atrium (photo), full height at the
// north-west. Floor plates shrink toward the NW as the building rises.
const hyattRegency: Landmark = {
  id: 'hyatt_regency',
  name: 'Hyatt Regency San Francisco',
  kind: 'building',
  built: [1971.3, 1973.3],
  end: 9999,
  anchor: [-122.395831, 37.794347],
  build: b => {
    b.frame(0, 0, 0, 171, () => {
      // footprint (OSM): +x = west (Drumm St), +y = south
      const base: V2[] = [
        [44.9, 47.7], [6.7, 47.8], [6.7, 41.0], [-71.4, -13.7], [-57.8, -32.9], [44.4, -33.2], [44.4, -23.0], [48.7, -23.0], [48.7, -13.3], [44.7, -13.3]
      ];
      // the stepped face is parallel to the diagonal A–B and recedes 55 m toward the NW corner at the top
      const A: V2 = [6.7, 41.0];
      const n: V2 = [0.573, -0.819];
      const steps = 10;
      const H = 77;
      for (let k = 0; k < steps; k++) {
        const ring = clipHalfPlane(base, A, n, (55 * k) / steps);
        if (ring.length >= 3) b.color(k % 2 ? '#CBC6BC' : '#D8D3CA').prism(ring, (H * k) / steps, (H * (k + 1)) / steps);
      }
    });
  },
  replaces: [rect(0, 0, 120, 80)],
  facts: {
    Opened: '1973 (John Portman), 20 floors, 77 m',
    Atrium: '17-storey sloping atrium — the stepped south-east face is its outer wall',
    Model: OSM_NOTE + '; slope of the stepped face estimated from photo'
  },
  sources: [WIKI + 'Hyatt_Regency_San_Francisco']
};

// =========================================================== 101 California (1982)
const CA101_TOWER: V2[] = [
  [28.3, -5.9], [29.4, 2.3], [28.3, 3.2], [29.1, 4.0], [28.0, 5.1], [28.3, 7.5], [26.1, 9.3], [27.1, 10.4], [26.4, 13.5], [18.4, 21.5],
  [7.4, 25.7], [-6.8, 25.7], [-17.8, 21.4], [-23.2, 15.9], [-28.2, 3.8], [-27.3, -7.4], [-21.1, -18.1], [-12.8, -25.2], [-3.4, -28.7],
  [0.8, -29.1], [1.8, -28.0], [2.8, -29.0], [15.8, -15.5], [19.4, -19.1], [23.5, -16.9], [23.0, -15.6], [25.4, -13.3], [24.8, -12.0],
  [26.3, -11.3], [26.3, -8.2]
];
const california101: Landmark = {
  id: 'california_101',
  name: '101 California Street',
  kind: 'tower',
  built: [1979.5, 1982.5],
  end: 9999,
  anchor: [-122.397952, 37.792871],
  build: b => {
    b.frame(0, 0, 0, 171, () => {
      b.color('#8EA3B2').prism(CA101_TOWER, 0, 175);
      b.color('#9DB0BE').prism(scaleRing(CA101_TOWER, 0.94), 175, 183);
      // granite fins of the sawtooth base (the stepped south-east quadrant)
      b.color('#CFC6B5').prism(scaleRing(CA101_TOWER, 1.04), 0, 9, {top: true});
    });
    // sloping glass entrance atrium on the plaza (Philip Johnson)
    b.color('#A9C0CC').loft(
      [
        [
          [-14, -38],
          [12, -38],
          [12, -30],
          [-14, -30]
        ],
        [
          [-12, -36],
          [10, -36],
          [10, -31.5],
          [-12, -31.5]
        ]
      ],
      [0, 21],
      {top: true}
    );
  },
  replaces: [circle(0, 0, 30, 12)],
  facts: {Completed: '1982 (Johnson/Burgee)', Height: '183 m, 48 floors', Form: 'faceted glass cylinder with a sawtooth base and a sloping glass atrium', Model: OSM_NOTE + '; atrium size and position estimated'},
  sources: [WIKI + '101_California_Street']
};

// =========================================================== Millennium Tower (2009), 181 Fremont (2018)
const millenniumTower: Landmark = {
  id: 'millennium_tower',
  name: 'Millennium Tower',
  kind: 'tower',
  built: [2005.5, 2009.3],
  end: 9999,
  anchor: [-122.39619, 37.790409],
  build: b => {
    b.frame(0, 0, 0, 135, () => {
      const ring: V2[] = [
        [-3.7, -24.3], [12.9, -24.5], [13.0, -14.3], [16.1, -14.3], [16.4, 23.1], [-14.6, 23.5], [-14.7, 9.7], [-16.8, 8.3], [-16.9, -11.9],
        [-14.9, -13.2], [-15.0, -23.2], [-3.7, -23.4]
      ];
      b.color('#8FA6B6').prism(ring, 0, 184);
      b.color('#A9BCC8').prism(scaleRing(ring, 0.9), 184, 192).prism(scaleRing(ring, 0.6), 192, 197);
      b.color('#B5C3CC').prism(scaleRing(ring, 1.03), 0, 14);
    });
  },
  replaces: [rect(0, 0, 38, 40)],
  facts: {
    Completed: '2009 (Handel Architects), 58 floors',
    Height: '184 m roof (605 ft); 197 m to the top of the crown (OSM)',
    Note: 'known for settling and tilting since 2016',
    Model: OSM_NOTE + '; crown height from OSM'
  },
  sources: [WIKI + 'Millennium_Tower_(San_Francisco)']
};
const fremont181: Landmark = {
  id: 'fremont_181',
  name: '181 Fremont',
  kind: 'tower',
  built: [2013.5, 2018.4],
  end: 9999,
  anchor: [-122.395333, 37.789765],
  build: b => {
    b.frame(0, 0, 0, 135, () => {
      const ring: V2[] = [
        [-21.7, 8.8],
        [-21.6, -16.3],
        [18.8, -16.4],
        [18.6, 19.2],
        [-7.8, 19.2],
        [-7.8, 8.8]
      ];
      b.color('#9DB7C4').prism(ring, 0, 185);
      // chamfered crown: faces slope in toward the roof
      b.color('#A9C1CC').loft([ring, scaleRing(ring, 0.62, 0.7, 2, -1)], [185, 213], {top: true});
      // white diagonal exoskeleton braces on the two street faces
      b.color('#EEF0F0');
      for (const [z0, z1] of [
        [0, 90],
        [90, 185]
      ]) {
        b.beam([-21.6, -16.3, z0], [-1.4, -16.4, z1], 1.2).beam([18.8, -16.4, z0], [-1.4, -16.4, z1], 1.2);
        b.beam([18.8, -16.4, z0], [18.7, 1.4, z1], 1.2).beam([18.6, 19.2, z0], [18.7, 1.4, z1], 1.2);
      }
      b.color('#D9DDDF').cylinder(0, 0, 0.8, 213, 244, 6);
    });
  },
  replaces: [rect(0, 0, 42, 38)],
  facts: {Completed: 'May 2018 (Heller Manus)', Height: '213 m roof (700 ft), 244 m spire (802 ft)', Floors: '57', Model: OSM_NOTE + '; brace pattern simplified from photo'},
  sources: [WIKI + '181_Fremont']
};

// =========================================================== SFMOMA (Botta 1995, Snøhetta 2016)
const SFMOMA: V2 = [-122.40066, 37.785895];
const sfmoma1995: Landmark = {
  id: 'sfmoma_1995',
  name: 'San Francisco Museum of Modern Art (Mario Botta building)',
  kind: 'building',
  built: [1992.2, 1995.05],
  end: 9999,
  anchor: SFMOMA,
  build: b => {
    part(b, SFMOMA, [-122.400945, 37.785787], 135, () => {
      const brick = '#9E5A3C';
      // stepped brick volumes around the central oculus (frame 135°: −x faces Third St)
      b.color(brick).box(-22, -16, 0, 15, 33, 12).box(-22, 16, 0, 15, 33, 12);
      b.color(brick).box(-4, -20, 0, 22, 26, 20).box(-4, 21, 0, 22, 22, 20);
      b.color(brick).box(10, 0, 0, 19, 64, 28);
      b.color('#8A4E35').box(-14, 0, 0, 12, 22, 24);
      // black-and-white striped truncated cylinder, skylight 130 ft (39.6 m)
      const cx = -9;
      const cy = -2;
      for (let k = 0; k < 6; k++) b.color(k % 2 ? '#2E2E30' : '#F2F1EE').cylinder(cx, cy, 8.5, 24 + k * 2.6, 24 + (k + 1) * 2.6, 16, {top: false});
      b.color('#A9C0CC').loft([circle(cx, cy, 8.5, 16), circle(cx + 1.5, cy, 7.5, 16)], [39.6, 33], {top: true});
    });
  },
  facts: {
    Opened: 'January 1995 (Mario Botta)',
    Form: 'five-storey stepped brick building around a striped cylindrical oculus with a 130 ft (39.6 m) high sloping skylight',
    Model: 'site from the OSM building part; stepped volumes estimated from photos'
  },
  sources: [WIKI + 'San_Francisco_Museum_of_Modern_Art']
};
const sfmoma2016: Landmark = {
  id: 'sfmoma_2016',
  name: 'SFMOMA expansion (Snøhetta)',
  kind: 'building',
  built: [2013.4, 2016.37],
  end: 9999,
  anchor: SFMOMA,
  build: b => {
    part(b, SFMOMA, [-122.400423, 37.785936], 135, () => {
      const ring: V2[] = [
        [-13.1, -53.7],
        [14.5, -53.6],
        [14.9, 54.6],
        [-11.7, 54.4],
        [-16.2, -0.7]
      ];
      // rippled white FRP facade: alternating bands
      for (let k = 0; k < 10; k++) b.color(k % 2 ? '#F1F1EE' : '#E4E5E2').prism(scaleRing(ring, 1 - 0.006 * (k % 3), 1), k * 6, (k + 1) * 6);
      b.color('#D9DBDA').prism(scaleRing(ring, 0.9), 60, 62);
    });
  },
  replaces: [rotRect(0, 0, 90, 110, 135)],
  facts: {
    Opened: 'May 14, 2016 (Snøhetta)',
    Size: '7 gallery levels + 3 support floors, fibre-reinforced-plastic panels rippled after the bay fog',
    Model: 'footprint from OSM; height ≈ 60 m estimated from photos'
  },
  sources: [WIKI + 'San_Francisco_Museum_of_Modern_Art']
};

// =========================================================== Grace Cathedral (1928–1964)
// Frame 81°: +y east (Taylor St front with the twin towers), −y west (apse).
const graceCathedral: Landmark = {
  id: 'grace_cathedral',
  name: 'Grace Cathedral',
  kind: 'building',
  built: [1928.0, 1964.0],
  end: 9999,
  anchor: [-122.413472, 37.79185],
  build: b => {
    const conc = '#B8B3AA';
    const roof = '#7D8086';
    b.frame(0, 0, 0, 81, () => {
      // nave and aisles
      b.color(conc).box(0, 17.2, 0, 27, 52.6, 28);
      b.color(roof).gable(0, 17.2, 27.4, 53, 28, 7, true);
      // transepts and crossing
      b.color(conc).box(0, -15.6, 0, 43.4, 13, 28);
      b.color(roof).gable(0, -15.6, 43.8, 13.4, 28, 7, false);
      // chancel and apse
      b.color(conc).box(0.4, -32.4, 0, 17.7, 21, 26);
      b.color(roof).gable(0.4, -32.4, 18, 21.4, 26, 6, true);
      b.color(conc).cylinder(0.4, -43, 8.6, 0, 26, 10);
      b.color(roof).dome(0.4, -43, 8.8, 26, 5, 10, 2);
      // twin west-front (Taylor St) towers, 53 m (OSM)
      for (const x of [-9.3, 9.3]) {
        b.color(conc).box(x, 39.5, 0, 10.9, 8.2, 47);
        b.color('#ADA89F').box(x, 39.5, 47, 9.8, 7.2, 6);
      }
      b.color(conc).box(0, 41.5, 0, 7.8, 4, 36); // rose-window gable between the towers
      b.color('#5C6B7A').cylinder(0, 43.6, 3.2, 20, 26.4, 12, {top: false});
      // flèche over the crossing (height estimated from photo)
      b.color('#6F7D78').pyramid(rect(0, -15.6, 3.2, 3.2), 35, [0, -15.6, 72]);
    });
  },
  replaces: [rotRect(0, 0, 46, 98, 81)],
  facts: {
    Construction: '1928 – 1964 (cornerstone 1910; consecrated 1964), Lewis P. Hobart, French Gothic in reinforced concrete',
    Towers: '53 m (OSM)',
    Doors: 'cast of Ghiberti’s Gates of Paradise',
    Model: OSM_NOTE + '; roof pitches and the flèche height estimated from photo'
  },
  sources: [WIKI + 'Grace_Cathedral,_San_Francisco']
};

// =========================================================== Fairmont Hotel (1907) + tower (1961)
const fairmont1907: Landmark = {
  id: 'fairmont_hotel',
  name: 'Fairmont Hotel',
  kind: 'building',
  built: [1902.5, 1907.3],
  end: 9999,
  anchor: [-122.410306, 37.792417],
  build: b => {
    b.frame(0, 0, 0, 171, () => {
      const ring: V2[] = [
        [30.0, 9.9],
        [29.9, 42.4],
        [-33.4, 42.4],
        [-33.4, -41.6],
        [31.2, -41.6],
        [31.2, -11.4],
        [38.0, -11.4],
        [37.9, 9.9]
      ];
      const courts = [rect(-2, -22, 30, 18), rect(-2, 23, 30, 18)];
      b.color('#E8E1D0').prism(ring, 0, 31, {holes: courts});
      cornice(b, ring, 31, 1.2, '#DCD4C1', 1.01);
      b.color('#CFC7B3').prism(scaleRing(ring, 0.96), 32.2, 35, {holes: courts});
      // Mason St portico (columns)
      b.color('#F1ECE0');
      for (let y = -6; y <= 6; y += 3) b.cylinder(38.6, y, 0.7, 2, 14, 8);
    });
  },
  replaces: [rect(-3, 0, 72, 86)],
  facts: {
    Built: '1902–06 (Reid Brothers); gutted by the 1906 fire just before opening; restored by Julia Morgan, opened Apr 18, 1907',
    Height: '35 m (OSM), 8 floors',
    Model: OSM_NOTE + '; light courts estimated'
  },
  sources: [WIKI + 'Fairmont_San_Francisco']
};
const fairmontTower: Landmark = {
  id: 'fairmont_tower_1961',
  name: 'Fairmont Hotel Tower',
  kind: 'tower',
  built: [1960.0, 1961.5],
  end: 9999,
  anchor: [-122.409685, 37.792788],
  build: b => {
    b.frame(0, 0, 0, 81, () => {
      const ring: V2[] = [
        [8.7, -18.4],
        [8.8, -9.6],
        [10.7, -9.6],
        [9.6, 19.1],
        [-9.7, 19.1],
        [-9.7, -20.5]
      ];
      b.color('#DAD5CA').prism(ring, 0, 104);
      b.color('#C5BFB2').prism(scaleRing(ring, 0.8), 104, 108);
    });
  },
  replaces: [rect(0, 0, 22, 42)],
  facts: {Opened: '1961 (Mario Gaidano), modernist addition behind the 1907 hotel', Height: '108 m (OSM; measured from the lower Mason St side)', Model: OSM_NOTE},
  sources: [WIKI + 'Fairmont_San_Francisco']
};

// =========================================================== Mark Hopkins (1926)
const MH: V2 = [-122.410211, 37.791454];
const markHopkins: Landmark = {
  id: 'mark_hopkins',
  name: 'Mark Hopkins Hotel',
  kind: 'tower',
  built: [1925.3, 1926.95],
  end: 9999,
  anchor: MH,
  build: b => {
    const brick = '#D2C1A0';
    b.frame(0, 0, 0, 171, () => {
      const base: V2[] = [
        [-27.8, -33.3], [9.7, -33.5], [9.7, -28.3], [13.1, -24.8], [14.9, -26.4], [17.6, -25.8], [19.0, -23.0], [23.5, -20.0], [23.8, -17.6],
        [22.2, -15.6], [26.6, -11.3], [31.5, -11.3], [31.6, 28.5], [-27.4, 29.8]
      ];
      b.color(brick).prism(base, 0, 20);
    });
    part(b, MH, [-122.410461, 37.79137], 171, () => {
      b.color(brick).prism(
        [
          [8.3, -17.0],
          [8.4, 11.4],
          [-10.8, 11.6],
          [-10.9, -3.3],
          [-8.4, -3.3],
          [3.4, -14.8],
          [3.4, -17.0]
        ],
        20,
        66
      );
    });
    part(b, MH, [-122.410163, 37.79169], 171, () => {
      b.color(brick).prism(
        [
          [17.9, -8.4],
          [18.0, -3.2],
          [15.7, -3.2],
          [3.9, 8.4],
          [3.9, 10.6],
          [-12.5, 10.7],
          [-12.5, -8.2]
        ],
        20,
        66
      );
    });
    part(b, MH, [-122.410358, 37.791553], 171, () => {
      const c: V2[] = [
        [-1.4, -15.4],
        [15.5, 1.6],
        [15.5, 3.9],
        [3.7, 15.3],
        [1.2, 15.3],
        [-15.5, -1.6],
        [-15.5, -3.9],
        [-3.7, -15.4]
      ];
      b.color(brick).prism(c, 20, 84);
      b.color('#C4B290').prism(scaleRing(c, 0.8), 84, 89).prism(scaleRing(c, 0.55), 89, 93);
    });
  },
  replaces: [rect(0, 0, 60, 64)],
  facts: {
    Opened: 'Dec 1926 (Weeks & Day) on the site of Mark Hopkins’ mansion (burned 1906)',
    Height: '93 m, 19 floors; "Top of the Mark" sky lounge from 1939',
    Model: 'base, wings and centre tower from the OSM 3D parts; crown steps from photo'
  },
  sources: [WIKI + 'InterContinental_Mark_Hopkins_San_Francisco']
};

// =========================================================== Pacific-Union Club (Flood Mansion, 1886)
const pacificUnionClub: Landmark = {
  id: 'pacific_union_club',
  name: 'Pacific-Union Club (James C. Flood Mansion)',
  kind: 'building',
  built: [1885.3, 1886.8],
  end: 9999,
  anchor: [-122.411404, 37.792222],
  build: b => {
    b.frame(0, 0, 0, 171, () => {
      const ring: V2[] = [
        [5.3, -19.9], [17.1, -19.9], [16.8, -3.1], [27.5, -3.3], [30.2, 3.9], [25.9, 10.7], [17.7, 10.8], [17.5, 18.5], [8.0, 18.7], [8.1, 25.2],
        [-8.2, 25.7], [-8.1, 19.1], [-16.4, 19.4], [-16.2, 10.5], [-25.4, 10.4], [-29.1, 6.5], [-29.2, 0.4], [-25.7, -3.8], [-16.9, -3.8],
        [-16.7, -19.9], [-9.5, -19.9], [-9.5, -28.0], [5.3, -27.9]
      ];
      b.color('#8C6E57').prism(ring, 0, 15.5);
      cornice(b, ring, 15.5, 1, '#7E6250', 1.02);
      b.color('#8C6E57').prism(scaleRing(ring, 0.75), 16.5, 18);
      b.color('#9A7C64');
      for (const x of [-3, 1]) b.cylinder(x, -28.6, 0.6, 1, 8, 8); // California St portico
    });
  },
  replaces: [rect(0, 0, 58, 54)],
  facts: {
    Built: '1886 (Augustus Laver) for silver king James C. Flood — Connecticut brownstone',
    '1906': 'the only Nob Hill mansion whose stone shell survived the fire',
    Club: 'remodelled 1911–12 by Willis Polk (wings, third floor) for the Pacific-Union Club; the model shows this footprint',
    Model: OSM_NOTE
  },
  sources: [WIKI + 'Pacific-Union_Club']
};

// =========================================================== St. Mary's Cathedral (1971)
// Square of 63 m (OSM shell part); eight hyperbolic-paraboloid shells rise from
// four corner pylons to a cross-shaped skylight 58 m (190 ft) above the floor; a
// vertical window slot runs up the middle of each side. Cross on top to 77.7 m (OSM).
function hyparPatch(b: MeshBuilder, c: V3, m: V3, t: V3, o: V3, n = 6) {
  const P = (u: number, v: number): V3 => [
    (1 - u) * (1 - v) * c[0] + u * (1 - v) * m[0] + u * v * t[0] + (1 - u) * v * o[0],
    (1 - u) * (1 - v) * c[1] + u * (1 - v) * m[1] + u * v * t[1] + (1 - u) * v * o[1],
    (1 - u) * (1 - v) * c[2] + u * (1 - v) * m[2] + u * v * t[2] + (1 - u) * v * o[2]
  ];
  for (let i = 0; i < n; i++)
    for (let j = 0; j < n; j++) b.quad(P(i / n, j / n), P((i + 1) / n, j / n), P((i + 1) / n, (j + 1) / n), P(i / n, (j + 1) / n));
}
const stMarysCathedral: Landmark = {
  id: 'st_marys_cathedral',
  name: 'Cathedral of Saint Mary of the Assumption',
  kind: 'building',
  built: [1967.0, 1971.35],
  end: 9999,
  anchor: [-122.425388, 37.784235],
  build: b => {
    b.frame(0, 0, 0, 171, () => {
      const H = 31.5;
      // glazed base between the corner pylons
      b.color('#5E6C78').prism(rect(0, 0, 2 * H - 10, 2 * H - 10), 0, 9);
      b.color('#E8E6E0');
      for (const [sx, sy] of [
        [1, 1],
        [-1, 1],
        [-1, -1],
        [1, -1]
      ])
        b.box(sx * (H - 3), sy * (H - 3), 0, 6, 6, 12);
      // eight shells: corner → side mid-point slot (low) → arm tip (high) → apex
      b.color('#D2CFC7');
      const top = 58;
      for (let k = 0; k < 4; k++) {
        const a = (k * Math.PI) / 2;
        const ca = Math.cos(a);
        const sa = Math.sin(a);
        const rot = (x: number, y: number, z: number): V3 => [x * ca - y * sa, x * sa + y * ca, z];
        for (const side of [-1, 1]) {
          const gap = 1.4 * side; // the window slot between the two shells of a side
          // the slot edge rises almost vertically up the middle of the side (photo)
          hyparPatch(b, rot(H, side * H, 12), rot(H - 1, gap, 18), rot(H - 9, gap, top - 3), rot(0, 0, top), 6);
        }
      }
      // cross-shaped skylight ridges and the cross
      b.color('#D9D7D0').box(0, 0, top - 1.5, 2 * (H - 9), 3, 2).box(0, 0, top - 1.5, 3, 2 * (H - 9), 2);
      b.color('#C9A43A').box(0, 0, top + 0.5, 1, 1, 77.7 - top - 0.5).box(0, 0, 71, 6, 0.8, 0.8);
    });
  },
  replaces: [rect(0, 0, 70, 70)],
  facts: {
    Dedicated: 'May 5, 1971 (Pier Luigi Nervi, Pietro Belluschi; local architects McSweeney, Ryan & Lee)',
    Height: '58 m (190 ft) shell; cross to 77.7 m (OSM)',
    Form: 'eight hyperbolic-paraboloid concrete shells forming a cross-shaped skylight',
    Model: 'square and cross from the OSM 3D parts; corner and slot heights estimated from photo'
  },
  sources: [WIKI + 'Cathedral_of_Saint_Mary_of_the_Assumption_(San_Francisco)']
};

// =========================================================== Saints Peter and Paul Church (1924)
// Facade faces south onto Washington Square (frame 171°: +y = south).
const saintsPeterPaul: Landmark = {
  id: 'saints_peter_paul',
  name: 'Saints Peter and Paul Church',
  kind: 'building',
  built: [1912.5, 1924.5],
  end: 9999,
  anchor: [-122.410237, 37.801601],
  build: b => {
    const white = '#EEECE6';
    b.frame(0, 0, 0, 171, () => {
      b.color(white).box(-1.2, 1, 0, 32.8, 47.9, 20);
      b.color('#B9BCBF').gable(-1.2, 1, 33.4, 48.4, 20, 8, true);
      b.color(white).box(19.7, -18, 0, 9, 9.8, 14); // side wing (OSM)
      // twin openwork Gothic spires on the Filbert St front (height estimated from photo)
      for (const x of [-13.5, 11.1]) {
        b.color(white).box(x, 21.5, 0, 6.5, 6.5, 34);
        b.color(white).box(x, 21.5, 34, 5.2, 5.2, 7);
        b.color('#E2E0D8').pyramid(rect(x, 21.5, 4.6, 4.6), 41, [x, 21.5, 55]);
      }
      b.color(white).box(-1.2, 23.5, 20, 16, 2, 9); // gable front with the rose window
      b.color('#9DA9B5').cylinder(-1.2, 24.6, 2.6, 13, 18.2, 12, {top: false});
    });
  },
  replaces: [rect(0, 0, 44, 50)],
  facts: {
    Completed: '1924 (Charles Fantoni), Italian Romanesque/Gothic — "the Italian Cathedral of the West"',
    Facade: 'faces south across Washington Square',
    Model: OSM_NOTE + '; spire height (≈ 55 m) estimated from photo'
  },
  sources: [WIKI + 'Saints_Peter_and_Paul_Church,_San_Francisco']
};

// =========================================================== Old St. Mary's Cathedral (1854)
const oldStMarys: Landmark = {
  id: 'old_st_marys',
  name: "Old St. Mary's Cathedral",
  kind: 'building',
  built: [1853.4, 1854.98],
  end: 9999,
  anchor: [-122.405758, 37.792879],
  build: b => {
    const brick = '#9A4A35';
    b.frame(0, 0, 0, 171, () => {
      // nave (OSM: x −6.5…14.6, y −19.5…19) with transept stubs; +y = California St (south)
      b.color(brick).box(4.05, -0.25, 0, 21.1, 38.5, 13);
      b.color('#5F5B58').gable(4.05, -0.25, 21.6, 39, 13, 6, true);
      b.color(brick).box(-11.3, -4, 0, 9.6, 17, 9).box(16.2, -11, 0, 3.3, 12.7, 9);
      // Gothic bell tower over the California St entrance (≈ 27 m, estimated from photo)
      b.color(brick).box(4.1, 22.5, 0, 7.4, 7.5, 24);
      for (const [x, y] of [
        [0.8, 19.2],
        [7.4, 19.2],
        [7.4, 25.8],
        [0.8, 25.8]
      ])
        b.color('#B8AFA4').pyramid(rect(x, y, 1.2, 1.2), 24, [x, y, 28.5]);
      b.color('#EDE6D6').cylinder(4.1, 26.3, 1.4, 15, 16.5, 8); // clock face
    });
  },
  replaces: [rect(0, 0, 40, 46)],
  facts: {
    Built: '1853–54 — California’s first cathedral; brick shipped round Cape Horn, granite from China',
    '1906': 'burned; walls and tower survived, restored 1909',
    Model: OSM_NOTE + '; tower height (≈ 27 m) estimated from photo'
  },
  sources: [WIKI + "Old_St._Mary's_Cathedral"]
};

// =========================================================== Haas–Lilienthal House (1886)
const haasLilienthal: Landmark = {
  id: 'haas_lilienthal_house',
  name: 'Haas–Lilienthal House',
  kind: 'building',
  built: [1886.0, 1886.9],
  end: 9999,
  anchor: [-122.424968, 37.79329],
  build: b => {
    const body = '#8E918A';
    b.frame(0, 0, 0, 171, () => {
      b.color(body).box(-1, -2.5, 0, 26, 13, 10.5);
      b.color(body).box(12, 3.5, 0, 14, 11, 8);
      b.color('#5E605C').gable(-1, -2.5, 26.6, 13.6, 10.5, 4.5, true).gable(12, 3.5, 14.6, 11.6, 8, 3.5, true);
      // round corner turret with a witch's-hat roof (Franklin St corner)
      b.color(body).cylinder(-14, -6.5, 2.6, 0, 14, 10);
      b.color('#4E504D').frustum(-14, -6.5, 2.9, 0.15, 14, 19.5, 10, false);
      b.color('#EDEBE4').box(-14, 1, 0, 3, 3, 3); // porch
    });
  },
  replaces: [rect(0, 0, 40, 24)],
  facts: {
    Built: '1886 (Peter R. Schmidt) for William Haas — Queen Anne; survived 1906',
    Museum: 'San Francisco Heritage house museum since 1973',
    Model: OSM_NOTE + '; gable and turret heights estimated from photo'
  },
  sources: [WIKI + 'Haas%E2%80%93Lilienthal_House']
};

// =========================================================== Castro Theatre (1922)
const castroTheatre: Landmark = {
  id: 'castro_theatre',
  name: 'Castro Theatre',
  kind: 'building',
  built: [1921.8, 1922.47],
  end: 9999,
  anchor: [-122.434749, 37.762008],
  build: b => {
    b.frame(0, 0, 0, 176, () => {
      // +x = west: the Castro St facade
      b.color('#D9CDB5').box(-11, 0, 0, 28, 25.7, 15);
      b.color('#9A9690').box(-11, 0, 15, 28, 25.7, 1);
      b.color('#EDE7DA').box(12, 0, 0, 19, 30, 17);
      b.color('#F4F0E6').box(22.6, 0, 17, 1.2, 14, 4); // ornate gable crest
      // marquee and the vertical CASTRO blade sign
      b.color('#B5332B').box(24.5, 0, 4, 2.6, 15, 2.4);
      b.color('#C23A30').box(24, -5.5, 6, 1.4, 1.6, 19);
    });
  },
  replaces: [rect(0, 0, 50, 32)],
  facts: {Opened: 'Jun 22, 1922 (Timothy Pflueger), Spanish-Colonial-Baroque facade', Sign: 'vertical neon CASTRO blade sign', Model: OSM_NOTE + ' and 3D parts (17 m); sign size estimated'},
  sources: [WIKI + 'Castro_Theatre']
};

// =========================================================== Civic Center: War Memorial (1932), Civic Auditorium (1915),
// old Main Library (1917, Asian Art Museum since 2003), Davies Symphony Hall (1980)
const OPERA_RING: V2[] = [
  [-42.2, -34.6], [-39.2, -36.4], [-26.3, -36.1], [-25.0, -30.0], [-22.3, -28.0], [33.4, -28.0], [37.0, -27.0], [37.1, -22.8], [54.6, -24.0],
  [54.4, 24.1], [36.9, 23.7], [37.2, 27.3], [33.8, 27.8], [-22.4, 27.9], [-25.0, 29.9], [-26.5, 35.7], [-30.3, 36.7], [-40.9, 35.8], [-42.8, 29.3],
  [-49.2, 24.3], [-49.2, -0.2], [-49.0, -24.4], [-46.0, -26.0], [-46.2, -28.2], [-42.4, -29.7]
];
const operaHouse: Landmark = {
  id: 'war_memorial_opera_house',
  name: 'War Memorial Opera House',
  kind: 'building',
  built: [1931.0, 1932.79],
  end: 9999,
  anchor: [-122.420905, 37.778575],
  build: b => {
    const stone = '#D4CFC3';
    b.frame(0, 0, 0, 171, () => {
      // +x = west (Franklin St, stage), −x = Van Ness Ave front
      b.color(stone).prism(OPERA_RING, 0, 22);
      b.color('#8C9A97').prism(scaleRing(OPERA_RING, 0.9, 0.85), 22, 27); // mansard roof
      b.color(stone).box(42, 0, 0, 22, 42, 44); // fly tower (OSM 44 m)
      b.color('#E2DDD2');
      for (let y = -22; y <= 22; y += 4.4) b.cylinder(-50.2, y, 0.9, 7, 20, 8); // Van Ness colonnade
    });
  },
  replaces: [rect(0, 0, 100, 70)],
  facts: {Opened: 'Oct 15, 1932 (Arthur Brown Jr.)', '1945': 'UN Charter signed in the Veterans Building / Opera House', Height: '44 m fly tower (OSM)', Model: OSM_NOTE + '; roof and colonnade from photo'},
  sources: [WIKI + 'War_Memorial_Opera_House']
};
const veteransBuilding: Landmark = {
  id: 'war_memorial_veterans_building',
  name: 'War Memorial Veterans Building',
  kind: 'building',
  built: [1931.0, 1932.79],
  end: 9999,
  anchor: [-122.421021, 37.779546],
  build: b => {
    const ring: V2[] = [
      [41.6, -24.7], [42.8, -20.6], [41.7, 24.7], [-17.7, 25.7], [-20.4, 26.7], [-20.7, 33.6], [-32.5, 33.6], [-33.3, 26.4], [-35.9, 26.6], [-37.1, 22.7],
      [-40.2, 22.7], [-39.9, -22.9], [-36.9, -22.9], [-37.0, -25.8], [-32.9, -26.8], [-32.1, -33.8], [-21.0, -33.7], [-20.2, -26.7], [-17.5, -25.7]
    ];
    b.frame(0, 0, 0, 171, () => {
      b.color('#D4CFC3').prism(ring, 0, 24);
      b.color('#8C9A97').prism(scaleRing(ring, 0.9, 0.85), 24, 28);
      b.color('#E2DDD2');
      for (let y = -18; y <= 18; y += 4.4) b.cylinder(-41, y, 0.9, 7, 20, 8);
    });
  },
  replaces: [rect(0, 0, 80, 66)],
  facts: {Opened: '1932 (Arthur Brown Jr.), twin of the Opera House; Herbst Theatre', Height: '28 m (OSM)', Model: OSM_NOTE},
  sources: [WIKI + 'San_Francisco_War_Memorial_and_Performing_Arts_Center']
};
const civicAuditorium: Landmark = {
  id: 'civic_auditorium',
  name: 'Bill Graham Civic Auditorium (Exposition Auditorium)',
  kind: 'building',
  built: [1913.95, 1915.17],
  end: 9999,
  anchor: [-122.417327, 37.778053],
  build: b => {
    const ring: V2[] = [
      [41.6, -37.0], [62.3, -36.9], [60.8, -7.2], [63.8, -7.2], [63.7, 2.9], [60.7, 2.9], [60.7, 7.4], [63.8, 7.4], [63.7, 17.1], [60.7, 17.1],
      [60.6, 34.8], [49.2, 34.7], [49.1, 38.9], [-60.2, 37.8], [-59.7, 17.2], [-64.2, 17.2], [-64.1, 7.6], [-60.2, 7.7], [-60.1, 2.1], [-64.1, 2.1],
      [-64.1, -7.8], [-60.6, -7.7], [-61.7, -37.3], [-41.5, -37.3], [-41.5, -39.7], [-28.6, -39.7], [-28.6, -37.2], [28.6, -37.0], [28.6, -39.9], [41.6, -39.8]
    ];
    b.frame(0, 0, 0, 171, () => {
      b.color('#CFCBC1').prism(ring, 0, 24);
      cornice(b, ring, 24, 1.2, '#C2BDB2', 1.01);
      // central low dome over the arena (OSM 37 m)
      b.color('#8E9C9A').dome(0, 0, 34, 25.2, 11.8, 20, 4);
      // arched windows on the Grove St (north, −y) front
      b.color('#7B848A');
      for (let x = -24; x <= 24; x += 8) b.box(x, -40.1, 6, 4.5, 0.4, 12);
    });
  },
  replaces: [rect(0, 0, 128, 80)],
  facts: {Opened: 'Mar 2, 1915 (John Galen Howard, Frederick Meyer, John Reid Jr.) for the PPIE', Height: '37 m (OSM)', Model: OSM_NOTE + '; dome profile estimated from photo'},
  sources: [WIKI + 'Bill_Graham_Civic_Auditorium']
};
const oldMainLibrary: Landmark = {
  id: 'asian_art_museum',
  name: 'Old Main Library / Asian Art Museum',
  kind: 'building',
  built: [1915.0, 1917.12],
  end: 9999,
  anchor: [-122.416044, 37.780253],
  build: b => {
    const ring: V2[] = [
      [31.0, -30.1], [47.4, -30.3], [46.8, 24.4], [-45.5, 25.5], [-45.7, 12.6], [-58.5, 12.7], [-59.0, -13.3], [-22.3, -13.7], [-22.4, -17.9],
      [-15.0, -18.0], [-15.1, -27.7], [31.0, -28.1]
    ];
    b.frame(0, 0, 0, 171, () => {
      b.color('#D3CEC2').prism(ring, 0, 24);
      cornice(b, ring, 24, 1.4, '#C4BFB3', 1.01);
      b.color('#B9B4A8').prism(scaleRing(ring, 0.9, 0.8), 25.4, 27);
      b.color('#E2DDD2');
      for (let x = -12; x <= 28; x += 4) b.cylinder(x, 25.9, 0.8, 6, 20, 8); // Larkin St colonnade
    });
  },
  replaces: [rect(0, 0, 106, 56)],
  facts: {
    Opened: 'Feb 15, 1917 as the Main Library (George Kelham), Beaux-Arts granite',
    'Asian Art Museum': 'since Mar 2003 (Gae Aulenti conversion)',
    Model: OSM_NOTE + '; height ≈ 27 m estimated from photos (OSM tag 46 m includes the 2017 pavilion)'
  },
  sources: [WIKI + 'Asian_Art_Museum_(San_Francisco)']
};
const daviesHall: Landmark = {
  id: 'davies_symphony_hall',
  name: 'Louise M. Davies Symphony Hall',
  kind: 'building',
  built: [1978.5, 1980.71],
  end: 9999,
  anchor: [-122.420586, 37.777614],
  build: b => {
    const ring: V2[] = [
      [34.2, -47.1], [43.1, -47.2], [43.2, -41.2], [29.4, -41.1], [28.8, 1.4], [63.8, 1.5], [63.8, 35.1], [-52.2, 35.1], [-52.3, 23.7], [-55.8, 22.2],
      [-57.8, 17.7], [-56.1, 13.7], [-52.5, 11.9], [-50.8, -12.9], [-47.1, -21.2], [-36.4, -33.9], [-19.3, -42.0], [2.1, -43.4], [5.6, -45.5],
      [10.1, -44.1], [12.5, -40.3], [12.6, -49.2], [34.1, -49.2]
    ];
    b.frame(0, 0, 0, 171, () => {
      b.color('#C9CBC9').prism(ring, 0, 28);
      // curved glass lobby wall at the Van Ness / Grove corner
      b.color('#7E98A8').prism(scaleRing(ring.slice(13, 21).concat([[-10, -10]]), 1.01), 0, 26);
      // the hall's rounded roof (OSM 49 m)
      b.color('#B5B8B6').loft([roundedRect(-5, -5, 70, 66, 26, 4), roundedRect(-5, -5, 52, 48, 20, 4)], [28, 49], {top: true});
    });
  },
  replaces: [rect(0, 0, 122, 86)],
  facts: {Opened: 'Sep 16, 1980 (SOM, Pietro Belluschi)', Height: '49 m (OSM)', Model: OSM_NOTE + '; roof profile estimated from photo'},
  sources: [WIKI + 'Louise_M._Davies_Symphony_Hall']
};

// =========================================================== St. Ignatius Church (1914)
// Twin towers on the Fulton St (south) front, crossing dome at the north end
// (orthophoto); frame 172°: +y = south.
const stIgnatius: Landmark = {
  id: 'st_ignatius_church',
  name: 'Saint Ignatius Church',
  kind: 'building',
  built: [1912.0, 1914.6],
  end: 9999,
  anchor: [-122.452485, 37.775523],
  build: b => {
    const tan = '#E1CFA6';
    b.frame(0, 0, 0, 172, () => {
      b.color(tan).box(0, -1, 0, 46, 72, 20);
      b.color('#8C8E90').gable(0, -1, 46.6, 72.6, 20, 7, true);
      b.color(tan).cylinder(-2, -30, 9, 20, 27, 14);
      b.color('#7F8A8E').dome(-2, -30, 9.4, 27, 7, 14, 4);
      for (const x of [-14.5, 14.5]) {
        b.color(tan).box(x, 33, 0, 9, 9, 50);
        b.color('#D8C59C').cylinder(x, 33, 3.6, 50, 58, 10);
        b.color('#8C8E90').dome(x, 33, 3.8, 58, 4, 10, 2);
        b.color('#C9A43A').cylinder(x, 33, 0.25, 62, 65, 4);
      }
      b.color(tan).box(0, 36.5, 0, 22, 4, 26); // two-tier colonnaded front
    });
  },
  replaces: [rect(0, 0, 50, 82)],
  facts: {
    Dedicated: '1914 (Charles J. I. Devlin), Jesuit church of the University of San Francisco',
    Towers: '≈ 65 m (213 ft, commonly cited; not verified)',
    Model: OSM_NOTE + '; tower and dome positions from the orthophoto; heights estimated from photo'
  },
  sources: [WIKI + 'St._Ignatius_Church_(San_Francisco)']
};

// =========================================================== Treasure Island (Golden Gate International Exposition, 1939–40)
// Building 1 (Administration, intended as the airport terminal) and the two
// exposition palaces built as future seaplane hangars (Buildings 2 and 3) — all
// standing; OSM outlines, frame 152°.
const TI_B1: V2 = [-122.371037, 37.817184];
const treasureIslandBuilding1: Landmark = {
  id: 'treasure_island_building_1',
  name: 'Treasure Island Administration Building (Building 1)',
  kind: 'building',
  built: [1937.0, 1938.6],
  end: 9999,
  anchor: TI_B1,
  build: b => {
    const ring: V2[] = [
      [-31.2, 10.9], [-31.2, -11.0], [-26.5, -25.2], [-22.6, -31.9], [-10.9, -44.8], [4.9, -54.5], [13.8, -57.4], [31.5, -59.1], [31.6, -53.8],
      [34.0, -53.8], [34.0, -49.6], [35.7, -49.6], [35.8, -38.7], [34.1, -38.7], [34.1, -33.9], [17.7, -32.3], [6.0, -26.7], [8.0, -22.3],
      [2.6, -16.5], [-0.8, -9.6], [-2.4, 2.0], [0.4, 12.6], [7.7, 22.1], [5.8, 25.9], [20.3, 32.9], [33.9, 33.6], [33.9, 38.5], [35.7, 38.4],
      [35.7, 47.9], [33.9, 47.9], [33.9, 52.7], [31.2, 52.7], [31.3, 58.7], [9.9, 56.4], [0.6, 52.8], [-13.8, 42.7], [-25.1, 27.8]
    ];
    b.frame(0, 0, 0, 152, () => {
      b.color('#EDE6D3').prism(ring, 0, 13);
      cornice(b, ring, 13, 0.8, '#E0D8C2', 1.0);
      b.color('#EDE6D3').box(-22, 0, 0, 16, 22, 20); // central block on the crescent's outer side
    });
  },
  replaces: [rect(0, 0, 70, 120)],
  facts: {
    Built: '1937–38 as the Exposition’s administration building, designed to become the terminal of a planned airport',
    Exposition: 'Golden Gate International Exposition, Feb 18 – Oct 29, 1939 and May 25 – Sep 29, 1940',
    Model: OSM_NOTE + '; central block height estimated from photo'
  },
  sources: [WIKI + 'Treasure_Island,_San_Francisco', WIKI + 'Golden_Gate_International_Exposition']
};
function hangar(b: MeshBuilder, ring: V2[], span: number, wall: number, crown: number) {
  b.color('#E3DED0').prism(ring, 0, wall);
  const n = 10;
  const hx = span / 2;
  const xs = ring.map(p => p[0]);
  const x0 = Math.min(...xs) + 2;
  const x1 = Math.max(...xs) - 2;
  const z = (y: number) => wall + (crown - wall) * (1 - (y / hx) ** 2);
  b.color('#B9B6AC');
  for (let i = 0; i < n; i++) {
    const y0 = -hx + (span * i) / n;
    const y1 = -hx + (span * (i + 1)) / n;
    b.quad([x0, y0, z(y0)], [x1, y0, z(y0)], [x1, y1, z(y1)], [x0, y1, z(y1)]);
  }
}
const treasureIslandHangars: Landmark = {
  id: 'treasure_island_hangars',
  name: 'Treasure Island Buildings 2 and 3 (Exposition palaces / hangars)',
  kind: 'building',
  built: [1937.0, 1938.6],
  end: 9999,
  anchor: [-122.367812, 37.818479],
  build: b => {
    b.frame(0, 0, 0, 152, () =>
      hangar(
        b,
        [
          [45.1, -44.1], [50.9, -44.2], [49.7, 26.3], [50.8, 26.3], [50.8, 31.4], [45.0, 31.4], [44.9, 42.5], [-51.9, 42.6], [-51.8, 32.8],
          [-49.5, 32.8], [-49.0, 26.1], [-49.5, -44.2], [-43.6, -44.2], [-43.6, -41.9], [45.1, -42.2]
        ],
        84,
        13,
        20
      )
    );
    part(b, [-122.367812, 37.818479], [-122.365883, 37.819406], 152, () =>
      hangar(
        b,
        [
          [67.7, -49.9], [67.6, 42.2], [49.2, 43.2], [49.2, 52.4], [-38.3, 52.7], [-38.3, 42.8], [-45.3, 42.8], [-45.3, 41.0], [-68.5, 41.0],
          [-68.9, -48.8], [-46.4, -48.6], [-46.5, -50.2], [2.6, -49.7], [2.6, -47.6], [5.4, -47.6], [9.4, -43.0], [13.4, -42.2], [17.6, -43.6],
          [20.8, -47.6], [23.7, -47.6], [23.7, -49.7]
        ],
        92,
        13,
        20
      )
    );
  },
  replaces: [
    rotRect(0, 0, 106, 90, 152),
    (() => {
      const p = lngLatToLocal([-122.367812, 37.818479], [-122.365883, 37.819406]);
      return rotRect(p[0], p[1], 140, 106, 152);
    })()
  ],
  facts: {
    Built: '1937–38 as Exposition halls (Building 3: Palace of Fine and Decorative Arts; Building 2: transportation hall), designed for later use as airport hangars',
    Height: '≈ 20 m (OSM)',
    Model: OSM_NOTE + '; vault rise estimated'
  },
  sources: [WIKI + 'Treasure_Island,_San_Francisco', 'https://commons.wikimedia.org/wiki/File:Contextual_view_of_Treasure_Island_showing_Palace_of_Fine_and_Decorative_Arts_(building_3)_at_right,and_Port_of_the_Trade_Winds_is_in_foreground,_camera_facing_north_-_Golden_Gate_HABS_CA-2785-2.tif']
};

// =========================================================== Aquatic Park Bathhouse (1939)
const aquaticParkBathhouse: Landmark = {
  id: 'aquatic_park_bathhouse',
  name: 'Aquatic Park Bathhouse (Maritime Museum)',
  kind: 'building',
  built: [1936.5, 1939.06],
  end: 9999,
  anchor: [-122.423897, 37.806408],
  build: b => {
    const ring: V2[] = [
      [-32.0, -8.0], [31.9, -8.5], [35.2, -7.3], [37.9, -4.5], [38.9, -0.7], [38.2, 3.4], [35.5, 6.5], [31.7, 7.7], [-31.6, 8.7], [-35.2, 7.5],
      [-37.7, 4.8], [-38.4, 0.9], [-37.6, -3.3], [-35.2, -6.5]
    ];
    b.frame(0, 0, 0, 170, () => {
      b.color('#F2F1EC').prism(ring, 0, 5.5);
      b.color('#8EA7B5').prism(scaleRing(ring, 0.995, 0.9), 2, 5); // ribbon windows
      b.color('#F2F1EC').prism(scaleRing(ring, 0.9, 0.78), 5.5, 9.5).prism(scaleRing(ring, 0.45, 0.6), 9.5, 12.5);
      b.color('#DADCDA').cylinder(0, 0, 0.2, 12.5, 20, 4); // mast
    });
  },
  replaces: [rect(0, 0, 78, 20)],
  facts: {Opened: '1939 (WPA), Streamline Moderne "ship" bathhouse', Museum: 'San Francisco Maritime Museum since 1951', Model: OSM_NOTE + '; deck heights estimated from photo'},
  sources: [WIKI + 'Aquatic_Park_Historic_District']
};

// =========================================================== Fleishhacker Pool (1925–1971)
// 1,000 × 150 ft salt-water pool under today's zoo car park (orthophoto: the
// lot is the only clearing of that size, aligned N–S along the Great Highway).
const fleishhackerPool: Landmark = {
  id: 'fleishhacker_pool',
  name: 'Fleishhacker Pool',
  kind: 'park',
  built: [1924.5, 1925.31],
  end: 1971.5,
  anchor: [-122.505886, 37.733678],
  build: b => {
    b.frame(0, 0, 0, -3, () => {
      b.color('#D9D6CC').prism(rect(0, 0, 54, 313), 0, 0.6);
      b.color('#79B3C4').cap(rect(0, 0, 46, 305), 0.65);
      // Mediterranean-revival bathhouse beside the pool (position estimated from the 1930s HABS aerial)
      b.color('#EDE4D2').box(-40, 95, 0, 22, 80, 9);
      b.color('#B5654A').hip(-40, 95, 22.6, 80.6, 9, 3);
    });
  },
  facts: {
    Opened: '1925 (built 1924–25) — one of the largest outdoor pools in the world, 1,000 × 150 ft, heated sea water',
    Closed: '1971 (storm damage to the intake); later filled for the zoo car park; the bathhouse burned in 2012',
    Model: 'pool size documented; position and N–S alignment from the car-park clearing on the orthophoto; bathhouse position estimated (LOW CONFIDENCE)'
  },
  sources: [WIKI + 'Fleishhacker_Pool', 'https://commons.wikimedia.org/wiki/File:AERIAL_VIEW_OF_ENTIRE_POOL_FROM_SOUTHEAST_-_Fleischhacker_Pool_and_Bath_House,_Sloat_Boulevard_and_Great_Highway,_San_Francisco,_San_Francisco_County,_CA_HABS_CAL,38-SANFRA,136-18.tif']
};

// =========================================================== Mount Davidson Cross (1934)
const mountDavidsonCross: Landmark = {
  id: 'mount_davidson_cross',
  name: 'Mount Davidson Cross',
  kind: 'monument',
  built: [1933.7, 1934.25],
  end: 9999,
  anchor: [-122.4539, 37.7383],
  build: b => {
    b.color('#EDEBE4').box(0, 0, 0, 3.2, 3.2, 31.4).box(0, 0, 21, 3.0, 12, 3.2);
    b.color('#C9C5BA').box(0, 0, 0, 6, 6, 1.2);
  },
  facts: {
    Dedicated: 'Easter 1934 (concrete, 103 ft / 31.4 m) — on the city’s highest hill (282 m)',
    Model: 'height documented; arm span and exact position estimated (summit coordinates)'
  },
  sources: [WIKI + 'Mount_Davidson']
};

// =========================================================== Cliff House Sutro wing (2004)
const cliffHouse2004: Landmark = {
  id: 'cliff_house_2004_wing',
  name: 'Cliff House — Sutro wing (2004)',
  kind: 'building',
  built: [2003.0, 2004.6],
  end: 9999,
  anchor: [-122.514044, 37.778557],
  build: b => {
    b.frame(0, 0, 0, 335, () => {
      b.color('#EDEBE5').box(-2, 11.4, 0, 15, 15, 10);
      b.color('#A9C0CC').prism(
        [
          [-10.3, 6.9], [-12.0, 3.9], [-13.6, 0.5], [-15.0, -3.3], [-16.0, -6.9], [-16.9, -10.5], [-17.6, -14.1], [-18.2, -17.6], [-18.5, -24.5],
          [-11.9, -24.5], [-11.9, 6.9]
        ],
        0,
        7
      );
      b.color('#D8DCDC').prism(
        [
          [7.0, 5.5], [8.5, 7.2], [9.9, 9.2], [11.0, 11.2], [12.0, 13.5], [12.8, 16.0], [13.2, 18.7], [13.2, 21.7], [12.8, 24.2], [12.0, 26.8],
          [10.9, 29.2], [9.6, 31.6], [8.2, 33.5], [1.4, 18.8], [5.5, 4.0]
        ],
        0,
        8
      );
    });
  },
  facts: {Opened: '2004, part of the NPS restoration of the Cliff House', Model: 'from the OSM Cliff House outline north of the 1909 block; heights estimated'},
  sources: ['https://en.wikipedia.org/wiki/Cliff_House,_San_Francisco']
};

// =========================================================== Panama-Pacific International Exposition (1915): Tower of Jewels
// "Main tower breaking southern wall, facing South Gardens … 433 feet high …
// seven stages; arch 110 feet high, 60 feet broad; 1,200 feet from the Tower of
// Jewels to the Column of Progress" (J. D. Barry, The City of Domes, 1915).
// Position (batch 4): traced from the 1915 Sanborn map of the Exposition
// (georeferenced on DataSF street centrelines, ±3 m): tower base 39 m square on
// the Court of the Universe axis, with 60-ft double colonnades either side to
// the walls of the Palaces of Liberal Arts and Manufactures; frame = Marina grid.
const towerOfJewels: Landmark = {
  id: 'ppie_tower_of_jewels',
  name: 'Tower of Jewels (Panama-Pacific Exposition)',
  kind: 'tower',
  built: [1914.0, 1915.13],
  end: 1916.2,
  anchor: [-122.441599, 37.802394],
  build: b => {
    const ivory = '#E6D9B8';
    const shade = '#D6C7A2';
    b.frame(0, 0, 0, -9.11, () => {
      // double colonnades 60 ft high either side, to the palace walls (Sanborn)
      for (const sx of [-1, 1])
        for (const y of [-12.9, 12.9]) {
          b.color(ivory).box(sx * 30.5, y, 0, 22, 4, 18.3);
          b.color(shade).box(sx * 30.5, y, 15.5, 22.4, 4.4, 1.2);
        }
      // base: arch 110 ft × 60 ft through a 38 m block
      b.color(ivory).box(-14, 0, 0, 10, 38, 33.5).box(14, 0, 0, 10, 38, 33.5);
      b.color(ivory).box(0, 0, 33.5, 38, 38, 8);
      // stage 2 with corner kiosks and statues
      b.color(ivory).box(0, 0, 41.5, 32, 32, 14);
      for (const [x, y] of [
        [-13, -13],
        [13, -13],
        [13, 13],
        [-13, 13]
      ])
        b.color(shade).cylinder(x, y, 2.4, 55.5, 64, 8).color(ivory).dome(x, y, 2.6, 64, 2, 8, 2);
      // stages 3–7: colonnaded drums diminishing to the globe
      b.color(ivory).box(0, 0, 55.5, 26, 26, 18);
      b.color(shade).cylinder(0, 0, 11, 73.5, 87, 16);
      b.color(ivory).cylinder(0, 0, 11.8, 87, 89, 16);
      b.color(shade).cylinder(0, 0, 7, 89, 101, 12);
      b.color(ivory);
      for (let i = 0; i < 12; i++) {
        const a = (i / 12) * Math.PI * 2;
        b.cylinder(Math.cos(a) * 8.6, Math.sin(a) * 8.6, 0.6, 89, 100, 6);
      }
      b.cylinder(0, 0, 9.2, 100, 102, 12).cylinder(0, 0, 6, 102, 112, 12);
      b.color(shade).cylinder(0, 0, 3.6, 112, 123, 10);
      b.color('#C9B98F').dome(0, 0, 3.4, 123, 6.8, 10, 4);
      b.color(ivory).cylinder(0, 0, 0.4, 129.8, 132.6, 4);
    });
  },
  facts: {
    Built: '1914 (Thomas Hastings of Carrère & Hastings) — staff over wood and steel',
    Height: '435 ft (132.6 m); 102,000+ cut-glass "Novagems" hung to shimmer',
    Exposition: 'Feb 20 – Dec 4, 1915; demolished 1916',
    Model: 'height, seven stages and arch size documented (Barry 1915); stage proportions from period photographs; position, base and colonnades from the 1915 Sanborn map (±3 m)'
  },
  sources: [WIKI + 'Tower_of_Jewels_(Panama%E2%80%93Pacific_International_Exposition)', 'https://www.gutenberg.org/ebooks/3151', 'https://www.loc.gov/item/sanborn00813_025/']
};

// =========================================================== California Midwinter International Exposition (1894)
// Grand Court of Honor = today's Music Concourse. The Bonet Electric Tower stood
// in its centre (placed on the concourse's central fountain); the Administration
// Building at the west end where the Temple of Music now stands; the Mechanical
// Arts Building (300 × 160 ft) where the Academy of Sciences stands.
const electricTower: Landmark = {
  id: 'midwinter_fair_electric_tower',
  name: 'Electric (Bonet) Tower — Midwinter Fair',
  kind: 'tower',
  built: [1893.75, 1894.07],
  end: 1896.0,
  anchor: [-122.46734, 37.770545],
  build: b => {
    b.color('#4E4A46');
    const legs = (z: number) => 9 * Math.pow(1 - z / 81, 1.6) + 1.2;
    const zs = [0, 12, 24, 38, 52, 66, 76];
    for (const [sx, sy] of [
      [1, 1],
      [-1, 1],
      [-1, -1],
      [1, -1]
    ])
      for (let i = 0; i < zs.length - 1; i++) b.beam([sx * legs(zs[i]), sy * legs(zs[i]), zs[i]], [sx * legs(zs[i + 1]), sy * legs(zs[i + 1]), zs[i + 1]], 0.9);
    for (const z of [12, 38, 66]) b.prism(rect(0, 0, 2 * legs(z) + 2, 2 * legs(z) + 2), z, z + 1.2, {holes: [rect(0, 0, 2 * legs(z) - 1, 2 * legs(z) - 1)]});
    b.color('#D8D2C4').box(0, 0, 76, 3, 3, 3).cylinder(0, 0, 0.3, 79, 81, 4);
    b.color('#B9B2A3').cylinder(0, 0, 11, 0, 1.2, 16); // fountain/plinth court
  },
  facts: {
    Built: '1893–94 (Leopold Bonet), modelled on the Eiffel Tower',
    Height: '266 ft (81 m), 3,200 coloured electric lights',
    Fate: 'stood about two years; blown up on John McLaren’s order',
    Model: 'height documented; lattice proportions from the 1894 photograph; placed at the centre of the Grand Court (today’s Music Concourse)'
  },
  sources: [WIKI + 'California_Midwinter_International_Exposition_of_1894']
};
const midwinterHalls: Landmark = {
  id: 'midwinter_fair_halls',
  name: 'Midwinter Fair — Administration and Mechanical Arts buildings',
  kind: 'building',
  built: [1893.65, 1894.07],
  end: 1894.65,
  anchor: [-122.46734, 37.770545],
  build: b => {
    // Administration Building (A. Page Brown): three storeys and a 135 ft (41 m) dome
    const ad = lngLatToLocal([-122.46734, 37.770545], [-122.4686, 37.769872]);
    b.frame(ad[0], ad[1], 0, 48, () => {
      b.color('#E6DCC6').box(0, 0, 0, 34, 34, 15);
      b.color('#E6DCC6').cylinder(0, 0, 9, 15, 26, 12);
      b.color('#B98D62').dome(0, 0, 9.5, 26, 12, 12, 4);
      b.color('#E6DCC6').cylinder(0, 0, 1.6, 38, 41, 6);
    });
    // Mechanical Arts Building (Edward Swain): 300 × 160 ft
    const ma = lngLatToLocal([-122.46734, 37.770545], [-122.466126, 37.769853]);
    b.frame(ma[0], ma[1], 0, 48, () => {
      b.color('#E2D6BC').box(0, 0, 0, 48.8, 91.4, 12);
      b.color('#A98F70').gable(0, 0, 49.4, 92, 12, 7, true);
      b.color('#E2D6BC').box(0, 0, 19, 10, 80, 3);
    });
  },
  facts: {
    Exposition: 'Jan 27 – Jul 4, 1894, Golden Gate Park',
    'Administration Building': 'A. Page Brown, three storeys, 135 ft dome — where the Temple of Music stands',
    'Mechanical Arts Building': 'Edward Swain, 300 × 160 ft — where the Academy of Sciences stands',
    Model: 'sizes and sites documented; footprints, orientation and roofs estimated (LOW CONFIDENCE)'
  },
  sources: [WIKI + 'California_Midwinter_International_Exposition_of_1894']
};

export const BATCH3: Landmark[] = [
  palace1875,
  palace1909,
  callBuilding,
  centralTower,
  millsBuilding,
  millsTower,
  montgomeryBlock,
  oldMint,
  floodBuilding,
  russBuilding,
  shellBuilding,
  sutter450,
  newMontgomery140,
  california555,
  ...EMBARCADERO_CENTER,
  hyattRegency,
  california101,
  millenniumTower,
  fremont181,
  sfmoma1995,
  sfmoma2016,
  graceCathedral,
  fairmont1907,
  fairmontTower,
  markHopkins,
  pacificUnionClub,
  stMarysCathedral,
  saintsPeterPaul,
  oldStMarys,
  haasLilienthal,
  castroTheatre,
  operaHouse,
  veteransBuilding,
  civicAuditorium,
  oldMainLibrary,
  daviesHall,
  stIgnatius,
  treasureIslandBuilding1,
  treasureIslandHangars,
  aquaticParkBathhouse,
  fleishhackerPool,
  mountDavidsonCross,
  cliffHouse2004,
  towerOfJewels,
  electricTower,
  midwinterHalls
];
