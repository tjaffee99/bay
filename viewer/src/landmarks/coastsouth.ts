/**
 * Santa Cruz County, the south Santa Clara Valley and east Contra Costa reconstructions —
 * data/research/landmarks_coastsouth.md.
 *
 * Outlines are the OpenStreetMap outlines of the standing structures (© OpenStreetMap
 * contributors, ODbL; read from the OSM API and Overture 2026-10-21.0) in a frame aligned
 * with the building (`b.frame(0, 0, 0, bearing)`: local +y at `bearing`, +x at
 * `bearing + 90°`). Roof, tower and spire heights, ridge lines, deck levels and the height
 * of the Giant Dipper along its track were MEASURED on the USGS 3DEP lidar point clouds
 * (CA_SantaCruzCounty_2020, CA_SantaClaraCounty_2020, CA_ContraCosta_1_2022; public
 * domain) — where the lidar and the OSM outline disagree by a few metres the model follows
 * the lidar and `replaces` follows the OSM outline. Documented dimensions (70 ft lift hill,
 * 39 ft and 41.5 ft lighthouses, the 35 ft covered bridge, the 112 × 29 × 25 ft mission
 * church, 65 ft tower, 135 ft clearance …) are cited per model and were checked against the
 * lidar where the structure stands. Wind turbines stand at their U.S. Wind Turbine
 * Database positions with the database's hub height and rotor diameter. Every estimate is
 * named in the model's facts ("Model: …"); vanished structures placed from a description
 * say LOW CONFIDENCE.
 */
import {MeshBuilder, circle, localToLngLat, rect, rotRect, type V2, type V3} from './kit';
import type {Landmark} from './types';
import {elevationAt} from '../layers/elevation';

const WIKI = 'https://en.wikipedia.org/wiki/';
const FT = 0.3048;
const LIDAR_SC = 'https://www.usgs.gov/3d-elevation-program (lidar point cloud CA_SantaCruzCounty_2020)';
const LIDAR_SCL = 'https://www.usgs.gov/3d-elevation-program (lidar point cloud CA_SantaClaraCounty_2020)';
const LIDAR_CC = 'https://www.usgs.gov/3d-elevation-program (lidar point cloud CA_ContraCosta_1_2022)';
const OSM_NOTE = 'outline from OpenStreetMap (© OSM contributors, ODbL)';

// ------------------------------------------------------------------ helpers

/** Box from edges [u0, u1, v0, v1]. */
function boxR(b: MeshBuilder, r: [number, number, number, number], z0: number, z1: number, top = true) {
  b.prism(rect((r[0] + r[1]) / 2, (r[2] + r[3]) / 2, r[1] - r[0], r[3] - r[2]), z0, z1, {top});
}

/** Gabled roof over edges [u0, u1, v0, v1]; ridge along v unless `alongU`. */
function gableR(b: MeshBuilder, r: [number, number, number, number], z0: number, h: number, alongU = false) {
  b.gable((r[0] + r[1]) / 2, (r[2] + r[3]) / 2, r[1] - r[0], r[3] - r[2], z0, h, !alongU);
}

/** Hipped roof over edges [u0, u1, v0, v1]. */
function hipR(b: MeshBuilder, r: [number, number, number, number], z0: number, h: number) {
  b.hip((r[0] + r[1]) / 2, (r[2] + r[3]) / 2, r[1] - r[0], r[3] - r[2], z0, h);
}

/** Octagon (flat sides facing the frame axes) of circumradius r. */
function octagon(cx: number, cy: number, r: number): V2[] {
  const a = Math.PI / 8;
  return circle(0, 0, r, 8).map(([x, y]) => [cx + x * Math.cos(a) - y * Math.sin(a), cy + x * Math.sin(a) + y * Math.cos(a)] as V2);
}

/** Polygon in a rotated frame → anchor-local metres (for `replaces`). */
function rotPoly(ring: V2[], bearing: number, dx = 0, dy = 0): V2[] {
  const a = (bearing * Math.PI) / 180;
  const ex: V2 = [Math.cos(a), -Math.sin(a)];
  const ey: V2 = [Math.sin(a), Math.cos(a)];
  return ring.map(([u, v]) => [dx + u * ex[0] + v * ey[0], dy + u * ex[1] + v * ey[1]] as V2);
}

function inPoly(x: number, y: number, poly: V2[]) {
  let inside = false;
  for (let i = 0, j = poly.length - 1; i < poly.length; j = i++) {
    const [xi, yi] = poly[i];
    const [xj, yj] = poly[j];
    if (yi > y !== yj > y && x < ((xj - xi) * (y - yi)) / (yj - yi) + xi) inside = !inside;
  }
  return inside;
}

/** Timber piles on a lattice under a deck outline (pier / wharf), from below the water to the deck. */
function piles(b: MeshBuilder, ring: V2[], zTop: number, su: number, sv: number, w = 0.45) {
  const us = ring.map(p => p[0]);
  const vs = ring.map(p => p[1]);
  for (let u = Math.min(...us) + su / 2; u < Math.max(...us); u += su) {
    for (let v = Math.min(...vs) + sv / 2; v < Math.max(...vs); v += sv) {
      if (inPoly(u, v, ring)) b.beam([u, v, -1.5], [u, v, zTop], w);
    }
  }
}

/** Ground height at a point of a landmark's local east / north frame relative to the anchor's ground. */
function groundDz(anchor: V2, x: number, y: number) {
  const p = localToLngLat(anchor, [x, y]);
  return elevationAt(p[0], p[1]) - elevationAt(anchor[0], anchor[1]);
}

function landmark(
  id: string,
  name: string,
  kind: Landmark['kind'],
  built: [number, number],
  end: number,
  anchor: V2,
  build: (b: MeshBuilder) => void,
  facts: Record<string, string>,
  sources: string[],
  replaces?: V2[][]
): Landmark {
  return {id, name, kind, built, end, anchor, build, facts, sources, replaces};
}

const CREAM = '#EDE6D3';
const TILE = '#B96A50';
const ADOBE = '#EFE7D6';
const SLATE = '#5F6168';
const WOOD_WHITE = '#EFEDE6';
const DECK_WOOD = '#8C7A66';
const PILE = '#5E5246';
const CONCRETE = '#A7A39A';

// =================================================================== SANTA CRUZ BEACH BOARDWALK

const BOARDWALK_SRC = WIKI + 'Santa_Cruz_Beach_Boardwalk';
const BOARDWALK_TIMELINE = 'https://beachboardwalk.com/history-timeline/';

// ---- Giant Dipper (1924): OSM track centreline, heights from the 2020 lidar
const GIANT_DIPPER: V2 = [-122.015326, 36.964718];
/**
 * [x, y, z]… every ~4 m along the OSM roller_coaster=track way (anchor frame, metres). z = highest
 * 2020 lidar return within 1.6 m of the centreline above the Boardwalk's ground (6.1 m NAVD88),
 * 3-point median — the upper circuit where two are stacked (scratch tools track.py / gen2.py).
 */
const GD_TRACK: number[] = [-26.1,-8.3,2.8,-22.7,-7.8,2.8,-19.2,-7.2,3.3,-15.8,-6.7,4.6,-11.2,-6.1,6.4,-6.6,-5.5,7.4,-2.0,-4.9,9.2,2.7,-4.4,10.3,7.6,-3.8,13.4,12.5,-3.2,16.0,16.1,-2.8,16.8,19.8,-2.5,17.6,23.0,-2.0,19.6,26.2,-1.5,19.6,31.0,-0.8,20.8,35.2,0.4,21.2,39.5,1.9,21.2,45.0,3.9,17.0,50.2,6.0,12.7,54.5,7.4,7.4,58.8,8.7,3.8,63.0,9.5,2.1,67.9,10.3,2.1,72.5,10.7,5.2,76.6,11.3,6.9,79.9,11.6,8.7,81.8,11.7,10.7,83.5,12.1,12.8,85.1,13.1,12.8,86.7,14.6,14.0,87.8,15.9,14.3,88.6,17.6,14.8,89.1,19.1,15.6,89.2,21.0,16.2,89.2,22.9,16.4,89.0,24.7,16.5,88.3,26.5,16.6,87.7,27.9,16.6,86.9,29.2,16.5,85.7,30.5,15.6,84.3,32.0,14.8,82.1,33.6,13.3,79.5,34.8,11.0,77.2,35.4,8.4,75.0,35.4,7.3,73.1,35.1,6.6,71.1,34.4,6.6,69.0,32.7,5.7,66.4,30.2,5.7,63.6,26.9,5.8,61.4,23.8,7.6,58.7,20.1,11.1,56.7,17.9,12.1,53.8,15.6,13.1,50.6,13.5,13.7,47.2,11.8,13.8,44.7,11.0,13.8,39.2,9.8,13.8,33.4,9.2,14.6,28.3,9.0,14.6,22.7,8.7,9.8,19.4,8.3,2.6,16.2,8.0,2.3,12.7,7.3,2.6,9.2,6.6,2.8,5.0,5.4,16.7,0.9,4.2,16.7,-3.2,3.0,6.4,-6.8,2.0,5.6,-10.5,0.9,6.4,-14.1,-0.2,6.7,-17.7,-1.2,6.7,-21.1,-2.1,6.7,-24.6,-2.9,13.9,-28.0,-3.8,13.9,-31.4,-4.6,5.5,-35.8,-5.5,5.5,-40.2,-6.4,7.8,-44.6,-7.3,11.1,-49.0,-8.1,12.3,-53.2,-8.8,12.7,-57.3,-9.4,12.7,-61.4,-10.1,12.6,-65.4,-10.6,12.5,-69.4,-11.2,12.3,-73.5,-11.8,12.1,-77.8,-12.6,12.1,-80.3,-13.6,12.2,-82.0,-14.8,13.6,-83.6,-16.6,13.6,-84.6,-18.5,11.8,-85.2,-20.7,11.8,-85.2,-23.0,12.2,-84.8,-24.9,12.2,-83.8,-26.8,12.0,-82.4,-28.4,12.0,-80.8,-29.9,12.2,-78.7,-31.0,12.2,-76.7,-31.4,12.2,-74.8,-31.3,11.5,-72.5,-30.9,10.4,-70.4,-29.6,8.2,-68.6,-28.1,7.0,-67.2,-26.3,5.9,-65.3,-23.1,4.5,-63.2,-19.1,4.5,-61.5,-16.8,4.7,-59.4,-14.5,6.2,-57.1,-13.1,7.1,-55.1,-12.2,7.7,-53.3,-11.4,8.1,-50.6,-10.7,8.6,-46.9,-10.1,8.6,-42.2,-9.3,8.6,-36.8,-8.1,6.3];
/** OSM outline of the ride (attraction=roller_coaster), anchor-local metres. */
const GD_OUTLINE: V2[] = [[-85.2,-11.3],[-91.3,-16.3],[-90.9,-19.1],[-89.6,-18.9],[-87.3,-36.9],[-78.5,-37.3],[-78.8,-35.5],[-69.8,-34.2],[-69.4,-36.3],[-65.0,-35.6],[-65.4,-33.1],[-51.9,-31.1],[-54.4,-14.4],[-19.7,-9.8],[-18.9,-15.4],[-6.1,-13.7],[-6.9,-7.8],[33.6,-1.3],[54.9,5.4],[84.7,11.0],[89.7,15.4],[91.5,24.1],[88.8,31.3],[83.4,36.0],[75.3,36.9],[70.2,34.6],[56.5,21.7],[46.6,15.6],[-27.0,-2.5]];
/** Low arcade buildings under and in front of the structure (OSM outlines as rectangles): [x, y, width, length, bearing, roof height above the Boardwalk (lidar median)]. */
const GD_ARCADES: number[][] = [[78, -18, 15.8, 30.6, 82.4, 3.0], [49, -23, 8.7, 9.1, 66.7, 7.6], [30, -22, 10.4, 12, 93.1, 4.9], [16, -33, 7.5, 9.1, 80.9, 4.9], [79, 26, 21.2, 22.8, 179.7, 5.7], [-8, -16, 17.4, 42.8, 82.1, 3.3], [66, 4, 7.7, 38.2, 79.1, 3.8]];

function woodenCoaster(b: MeshBuilder, T: number[], track: string, wood: string) {
  const P: V3[] = [];
  for (let i = 0; i < T.length; i += 3) P.push([T[i], T[i + 1], T[i + 2]]);
  const n = P.length;
  const side = (i: number): V2 => {
    const a = P[i];
    const c = P[(i + 1) % n];
    const L = Math.hypot(c[0] - a[0], c[1] - a[1]) || 1;
    return [-(c[1] - a[1]) / L, (c[0] - a[0]) / L];
  };
  b.color(track);
  for (let i = 0; i < n; i++) {
    const a = P[i];
    const c = P[(i + 1) % n];
    const [nx, ny] = side(i);
    b.quad([a[0] - nx * 0.8, a[1] - ny * 0.8, a[2]], [a[0] + nx * 0.8, a[1] + ny * 0.8, a[2]], [c[0] + nx * 0.8, c[1] + ny * 0.8, c[2]], [c[0] - nx * 0.8, c[1] - ny * 0.8, c[2]]);
    b.quad([a[0], a[1], a[2] - 0.7], [a[0], a[1], a[2]], [c[0], c[1], c[2]], [c[0], c[1], c[2] - 0.7]);
  }
  // white timber trestle: a bent every second sample, ledgers every ~5 m of height
  b.color(wood);
  let prev: [V3, V3] | null = null;
  for (let i = 0; i < n; i += 2) {
    const [x, y, z] = P[i];
    if (z < 2.5) {
      prev = null;
      continue;
    }
    const [nx, ny] = side(i);
    const w = 1.3 + z * 0.07; // batter: the bents widen toward the ground
    const l0: V3 = [x - nx * w, y - ny * w, 0];
    const r0: V3 = [x + nx * w, y + ny * w, 0];
    b.beam(l0, [x - nx * 0.9, y - ny * 0.9, z - 0.6], 0.32).beam(r0, [x + nx * 0.9, y + ny * 0.9, z - 0.6], 0.32);
    b.beam(l0, [x + nx * 0.9, y + ny * 0.9, z - 0.6], 0.2);
    if (prev) {
      for (let h = 5; h < Math.min(z, prev[0][2]) - 1; h += 5) {
        const t0 = h / prev[0][2];
        const t1 = h / z;
        b.beam([prev[1][0] + (prev[0][0] - prev[1][0]) * t0, prev[1][1] + (prev[0][1] - prev[1][1]) * t0, h], [x + (l0[0] - x) * (1 - t1), y + (l0[1] - y) * (1 - t1), h], 0.18);
      }
    }
    prev = [[x, y, z], l0];
  }
}

const giantDipper = landmark(
  'giant_dipper_santa_cruz',
  'Giant Dipper (Santa Cruz Beach Boardwalk)',
  'park',
  [1924.25, 1924.38],
  9999,
  GIANT_DIPPER,
  b => {
    woodenCoaster(b, GD_TRACK, '#B5382E', WOOD_WHITE);
    for (const [x, y, w, l, brg, h] of GD_ARCADES) b.frame(x, y, 0, brg, () => b.color('#D9D2C2').box(0, 0, 0, w, l, h));
  },
  {
    Opened: 'May 17, 1924 — wooden coaster designed by Frank Prior and Frederick Church and built by Arthur Looff; National Historic Landmark (with the Looff Carousel) since 1987',
    Size: 'lift hill 70 ft (21.3 m), first drop 65 ft, 2,640 ft (805 m) of track, 55 mph; 327,000 board feet of lumber',
    Model:
      'track centreline from OpenStreetMap (© OSM contributors, ODbL; one 387 m circuit mapped — the ride is a double out-and-back, its second circuit runs inside / under the first); heights along it are measured: highest 2020 USGS lidar return within 1.6 m of the centreline (upper circuit where two are stacked), which tops out 21.2 m above the Boardwalk — the documented 70 ft; trestle bents schematic; the low arcade buildings under and in front of it are boxes on their OpenStreetMap outlines with lidar roof heights (3–7.6 m)'
  },
  [WIKI + 'Giant_Dipper_(Santa_Cruz_Beach_Boardwalk)', LIDAR_SC],
  [GD_OUTLINE, ...GD_ARCADES.slice(0, 4).map(([x, y, w, l, brg]) => rotRect(x, y, w + 1, l + 1, brg))]
);

// ---- Sky Glider (1967): two-way chairlift along the Boardwalk (OSM aerialway), frame of the Giant Dipper anchor
const skyGlider = landmark(
  'sky_glider_santa_cruz',
  'Sky Glider (Santa Cruz Beach Boardwalk)',
  'park',
  [1967.0, 1967.4],
  9999,
  GIANT_DIPPER,
  b => {
    const X0 = -252.5;
    const X1 = 7.4;
    const yA = (x: number) => -67.7 + ((x - X0) * 35.1) / (X1 - X0);
    // cable height: stations ≈ 5.5 m, towers / spans ≈ 13.6 m above the Boardwalk (lidar)
    const TOWERS: [number, number][] = [[-202.4, 13.6], [-148.4, 13.6], [-94.7, 13.6], [-41, 12]];
    const line: [number, number][] = [[X0, 5.5], ...TOWERS, [X1, 5.5]];
    const cz = (x: number) => {
      for (let i = 0; i < line.length - 1; i++) {
        if (x <= line[i + 1][0]) return line[i][1] + ((line[i + 1][1] - line[i][1]) * (x - line[i][0])) / (line[i + 1][0] - line[i][0]);
      }
      return 5.5;
    };
    for (const off of [0, -3.1]) {
      b.color('#3F4347').polyline(line.map(([x, z]) => [x, yA(x) + off, z] as V3), 0.14);
      // chairs (static), alternating colours
      let k = 0;
      for (let x = X0 + 6; x < X1 - 3; x += 9.5) {
        const z = cz(x);
        b.color('#3F4347').beam([x, yA(x) + off, z], [x, yA(x) + off, z - 2.4], 0.1);
        b.color(['#D8473A', '#2F7FB8', '#E6B33A', '#3E9A62'][k++ % 4]).box(x, yA(x) + off, z - 3.3, 1.7, 0.7, 0.9);
      }
    }
    b.color('#E3E4E2');
    for (const [x, z] of TOWERS) {
      const y = yA(x) - 1.55;
      b.beam([x, y, 0], [x, y, z + 1.6], 0.7);
      b.beam([x, y - 2.6, z + 1.0], [x, y + 2.6, z + 1.0], 0.4);
    }
    // end stations: open canopies over the bullwheels
    for (const x of [X0 - 1, X1 + 1.5]) {
      const y = yA(x) - 1.55;
      b.color('#E3E4E2');
      for (const [dx, dy] of [[-4, -3], [4, -3], [4, 3], [-4, 3]]) b.beam([x + dx, y + dy, 0], [x + dx, y + dy, 5], 0.35);
      b.color('#C8443A').box(x, y, 5, 10, 7.5, 0.5);
    }
  },
  {
    Opened: '1967 — a two-way chairlift carrying riders along the length of the Boardwalk, over the promenade',
    Model:
      'line and end stations from the OpenStreetMap aerialway (© OSM contributors, ODbL; 262 m each way); cable ≈ 13.6 m above the Boardwalk and three tower positions (54 m apart) from the 2020 USGS lidar, the fourth tower continues that spacing; chairs static and schematic, colours estimated'
  },
  [BOARDWALK_SRC, LIDAR_SC]
);

// ---- Casino / Cocoanut Grove (1907), frame 73.2° (+y ENE along the beach, +x toward the beach)
const CASINO: V2 = [-122.020006, 36.963871];
const CASINO_OUTLINE: V2[] = [[-23.6,-33.4],[11.2,-33.4],[11.2,-32.8],[17.3,-32.8],[17.3,-10.8],[20.8,-9.1],[23.6,-6.7],[25.6,-3.1],[26.4,0.7],[26.1,3.5],[24.9,6.2],[22.9,8.8],[20.1,10.7],[20.7,15.9],[17.0,16.4],[19.2,33.4],[-13.0,32.9],[-23.7,33.3],[-23.7,23.5],[-23.1,23.3],[-23.3,11.5],[-26.1,11.6],[-26.3,-9.1],[-23.5,-9.2],[-23.8,-24.1],[-26.0,-24.0],[-25.9,-32.1],[-23.6,-32.0]];
const casino = landmark(
  'boardwalk_casino',
  'Casino and Cocoanut Grove (Santa Cruz Beach Boardwalk)',
  'building',
  [1906.75, 1907.46],
  9999,
  CASINO,
  b => {
    b.frame(0, 0, 0, 73.2, () => {
      b.color(CREAM).prism(CASINO_OUTLINE, 0, 13);
      // ballroom roof over the middle of the block (lidar 17 m), red tile
      b.color(CREAM);
      boxR(b, [-14.5, 5.5, -24, 27], 13, 15.4);
      b.color(TILE);
      hipR(b, [-14.5, 5.5, -24, 27], 15.4, 1.8);
      // the rounded pavilion facing the beach (colonnade below, low dome above: lidar 17–19 m)
      const c: V2 = [16.8, 1.2];
      const arc = (r: number): V2[] => {
        const out: V2[] = [];
        for (let i = 0; i <= 12; i++) {
          const a = (-90 + i * 15) * (Math.PI / 180);
          out.push([c[0] + Math.cos(a) * r, c[1] + Math.sin(a) * r]);
        }
        return out;
      };
      b.color(CREAM).prism(arc(10), 13, 14.4);
      b.color(TILE).loft([arc(10.4), arc(7.2), arc(2.5)], [14.4, 16.4, 18.6]);
      // colonnade piers round the pavilion
      b.color('#D9D0B8');
      for (const p of arc(10.6)) b.box(p[0], p[1], 0, 0.9, 0.9, 5.2);
    });
  },
  {
    Built: 'opened June 15, 1907 with the Plunge next door, after the first, onion-domed Neptune Casino (opened June 14, 1904) burned in 1906; architect William H. Weeks',
    Name: 'the ballroom became the Cocoanut Grove during Prohibition',
    Model:
      OSM_NOTE + ' (52.7 × 66.8 m); roof levels measured on the 2020 USGS lidar: block 13 m, ballroom roof 17 m, the rounded beach pavilion 17–19 m (its high roof 14 m across); pavilion drum (radius 10 m) fitted to the OSM outline; colonnade, roof forms and colours estimated; the 1907 building had Moorish domes and has been altered — drawn in its present massing for every year (earlier roofline LOW CONFIDENCE)'
  },
  [BOARDWALK_SRC, BOARDWALK_TIMELINE, LIDAR_SC],
  [rotPoly(CASINO_OUTLINE, 73.2)]
);

// ---- The Plunge natatorium (1907), today Neptune's Kingdom; frame 80.1° (+y east along the beach, +x toward the beach)
const PLUNGE: V2 = [-122.019145, 36.964069];
const PLUNGE_OUTLINE: V2[] = [[-18.3,-29.0],[-18.4,-12.4],[-23.1,-12.5],[-23.3,0.9],[-18.5,0.8],[-18.5,19.6],[-21.0,19.6],[-20.8,29.2],[-16.8,29.3],[-16.8,28.6],[-10.9,28.4],[15.4,28.8],[15.4,27.1],[23.4,27.1],[23.4,-28.6]];
const plunge = landmark(
  'boardwalk_plunge',
  'The Plunge natatorium / Neptune\'s Kingdom (Santa Cruz Beach Boardwalk)',
  'building',
  [1906.75, 1907.46],
  9999,
  PLUNGE,
  b => {
    b.frame(0, 0, 0, 80.1, () => {
      b.color(CREAM).prism(PLUNGE_OUTLINE, 0, 10);
      // pool hall: 20.7 m wide, 51.5 m long, ridge 17.2 m (lidar)
      boxR(b, [-17.8, 2.9, -27.8, 23.7], 10, 12.3, false);
      b.color('#8C8F8A');
      gableR(b, [-17.8, 2.9, -27.8, 23.7], 12.3, 4.9);
      // entrance block on the street side
      b.color(CREAM);
      boxR(b, [-23.2, -18.4, -12.5, 0.9], 10, 12);
    });
  },
  {
    Built: 'opened June 15, 1907 with the Casino (architect William H. Weeks): a heated salt-water natatorium, main pool 144 × 64 ft holding 408,000 gallons',
    Later: 'the Plunge closed in 1963; the hall is now Neptune\'s Kingdom (arcade and indoor miniature golf)',
    Model:
      OSM_NOTE + ' (46.6 × 58.5 m); the pool hall (20.7 × 51.5 m, ridge 17 m) and the 10 m beach-side wing are measured on the 2020 USGS lidar; roof covering and colours estimated; present massing for every year'
  },
  [BOARDWALK_SRC, WIKI + 'Casa_del_Rey_Hotel', LIDAR_SC],
  [rotPoly(PLUNGE_OUTLINE, 80.1)]
);

// ---- Looff Carousel building (1911)
const CAROUSEL: V2 = [-122.017443, 36.96438];
const looffCarousel = landmark(
  'looff_carousel_santa_cruz',
  'Looff Carousel (Santa Cruz Beach Boardwalk)',
  'park',
  [1911.2, 1911.6],
  9999,
  CAROUSEL,
  b => {
    b.color(WOOD_WHITE).cylinder(0, 0, 10.7, 0, 4.2, 20, {top: false});
    b.color('#B5382E').frustum(0, 0, 11.2, 2.6, 4.2, 9.8, 20, false);
    b.color(WOOD_WHITE).cylinder(0, 0, 2.5, 9.8, 10.8, 12, {top: false});
    b.color('#B5382E').pyramid(circle(0, 0, 2.9, 12), 10.8, [0, 0, 12.3]);
  },
  {
    Built: '1911: carousel bought new from Charles I. D. Looff\'s factory in Long Beach, with 73 carved horses; its 342-pipe band organ was built in 1894; National Historic Landmark with the Giant Dipper (1987)',
    Model: 'round building ' + OSM_NOTE + ' (21.5 m across); eave 4 m, conical roof to 10 m and cupola to 12.3 m measured on the 2020 USGS lidar; colours estimated'
  },
  [BOARDWALK_SRC, LIDAR_SC],
  [circle(0, 0, 11, 16)]
);

// ---- Santa Cruz Municipal Wharf (1914), frame 133.3° (+y out to sea); z from sea level
const SC_WHARF: V2 = [-122.02018, 36.960312];
const SC_WHARF_OUTLINE: V2[] = [[28.2,-371.7],[10.5,-370.2],[9.7,-349.2],[2.9,-350.1],[2.0,-339.5],[7.9,-339.2],[8.0,-330.6],[1.9,-222.8],[-6.4,-208.6],[-25.3,126.2],[-44.8,126.2],[-54.0,281.8],[-30.9,282.3],[-20.0,301.4],[-23.0,303.4],[-18.3,311.6],[-16.9,310.8],[-10.7,323.4],[-8.1,321.9],[20.8,371.8],[25.8,370.3],[54.1,352.6],[42.2,332.9],[43.9,327.3],[30.6,302.0],[29.1,302.3],[22.1,289.3],[24.1,251.0],[16.7,237.9],[9.6,237.3],[24.3,-19.6],[28.6,-24.7],[30.7,-66.5],[11.0,-67.4],[15.3,-143.5],[28.8,-142.7],[29.9,-162.6],[17.2,-163.3],[17.2,-180.0],[18.8,-179.8],[20.7,-207.4],[18.1,-207.6]];
/** Buildings on the wharf (OSM outlines as rectangles): [u, v, width, length, bearing relative to the frame, height above the deck (lidar)]. */
const SC_WHARF_BUILDINGS: number[][] = [[23.8,-153.0,9.0,18.6,-3.6,3.1],[8.5,-50.2,1.3,18.0,-1.6,4.1],[12.5,-49.6,7.0,18.4,-2.6,4.4],[16.3,-28.4,16.0,20.9,-3.0,4.5],[14.9,-4.7,15.6,34.9,-3.5,5.0],[10.1,75.4,16.4,124.1,-3.4,5.1],[2.5,205.3,17.0,45.4,-3.3,7.4],[4.2,280.0,14.1,27.1,29.6,8.1],[20.3,309.7,13.2,45.5,30.9,7.8]];
const scWharf = landmark(
  'santa_cruz_wharf',
  'Santa Cruz Municipal Wharf',
  'bridge',
  [1913.6, 1914.93],
  9999,
  SC_WHARF,
  b => {
    b.frame(0, 0, 0, 133.3, () => {
      b.color(DECK_WOOD).prism(SC_WHARF_OUTLINE, 6.0, 7.0, {bottom: true});
      b.color(PILE);
      piles(b, SC_WHARF_OUTLINE, 6.0, 9, 14);
      for (const [u, v, w, l, brg, h] of SC_WHARF_BUILDINGS) {
        b.frame(u, v, 7.0, brg, () => {
          b.color('#E4DED0').box(0, 0, 0, w, l, h - 1.2);
          b.color('#7C7F82').hip(0, 0, w + 0.6, l + 0.6, h - 1.2, 1.2);
        });
      }
    });
  },
  {
    Built: 'opened Dec 5, 1914 — the most recent of six wharves built on this site; base of the north Monterey Bay fishing fleet',
    Size: '2,745 ft (837 m) long before the 2024 storm — the longest pier on the West Coast',
    '2024': 'about 150 ft at the end collapsed in high surf on Dec 23, 2024 (drawn at full length)',
    Model:
      'deck outline and the buildings on it from OpenStreetMap (© OSM contributors, ODbL; buildings as rectangles); deck level 7.0 m (NAVD88) and building heights from the 2020 USGS lidar; pile count and spacing schematic; roofs simplified'
  },
  [WIKI + 'Santa_Cruz_Wharf', LIDAR_SC],
  [rotPoly(SC_WHARF_OUTLINE, 133.3)]
);

// =================================================================== MISSION HILL (Santa Cruz)

/** OSM centroid of Holy Cross Church; frame 349.9° (+y north along the nave, +x east). */
const HOLY_CROSS: V2 = [-122.02992, 36.978745];
const HOLY_CROSS_OUTLINE: V2[] = [[9.6,21.4],[-9.7,21.5],[-9.7,-15.1],[-4.5,-15.2],[-4.5,-21.3],[1.8,-21.3],[1.8,-14.7],[9.6,-14.8]];

const missionSantaCruz = landmark(
  'mission_santa_cruz_1794',
  'Mission Santa Cruz (adobe church)',
  'building',
  [1793.15, 1794.36],
  1857.03,
  HOLY_CROSS,
  b => {
    b.frame(0, 0, 0, 349.9, () => {
      const L = 112 * FT;
      const W = 29 * FT;
      const H = 25 * FT;
      const r: [number, number, number, number] = [-2.2 - W / 2, -2.2 + W / 2, -15, -15 + L];
      b.color(ADOBE);
      boxR(b, r, 0, H, false);
      b.color(TILE);
      gableR(b, [r[0] - 0.5, r[1] + 0.5, r[2], r[3]], H, 2.5);
      // stone front: a plain gabled wall a little above the roof
      b.color('#DAD3C2');
      boxR(b, [r[0] - 0.4, r[1] + 0.4, -15.9, -15], 0, H + 0.4);
      b.tri([r[0] - 0.4, -15.9, H + 0.4], [r[1] + 0.4, -15.9, H + 0.4], [-2.2, -15.9, H + 3.1]).tri([r[0] - 0.4, -15, H + 0.4], [r[1] + 0.4, -15, H + 0.4], [-2.2, -15, H + 3.1]);
      b.color('#6E5A4A').box(-2.2, -16, 0, 2.6, 0.2, 4);
    });
  },
  {
    Built: 'mission founded Aug 28, 1791 on the river flat and moved up to the hill by 1793; the first permanent church, of adobe with a stone front, was completed and dedicated in 1794',
    Size: '112 ft long, 29 ft wide, 25 ft high, walls 5 ft thick, with a stone front',
    Fate: 'the bell tower fell in the 1840 earthquake; the front wall and much of the church collapsed after the Fort Tejon earthquake of Jan 9, 1857; the ruin was cleared for Holy Cross Church (1889)',
    Model:
      'documented length, width and wall height; placed on the axis of Holy Cross Church, which was built "over (in the same orientation) part of the original sanctuary and cemetery" — exact position, roof pitch, front and door estimated; the bell tower (no dimensions) is not modelled (LOW CONFIDENCE)'
  },
  [WIKI + 'Mission_Santa_Cruz', 'https://www.californiamissions.com/mission-santa-cruz']
);

const holyCross = landmark(
  'holy_cross_church_santa_cruz',
  'Holy Cross Church (Santa Cruz)',
  'building',
  [1888.0, 1889.7],
  9999,
  HOLY_CROSS,
  b => {
    b.frame(0, 0, 0, 349.9, () => {
      const WALL = '#EAE5D6';
      b.color(WALL);
      boxR(b, [-11.7, 7.3, -8.4, 20], 0, 12.9, false);
      boxR(b, [-11.7, 7.3, 20, 25], 0, 16.5, false);
      boxR(b, [-10.5, 6, 25, 29], 0, 9.5, false);
      b.color(SLATE);
      gableR(b, [-12.1, 7.7, -8.4, 20], 12.9, 8.6); // ridge 21.5 m
      gableR(b, [-12.1, 7.7, 20, 25], 16.5, 7.5); // raised sanctuary roof, 24 m
      gableR(b, [-10.9, 6.4, 25, 29], 9.5, 7); // apse end
      // front tower: 7.6 m square to 22 m, 5.9 m to 28.2 m, an octagonal stage to 37 m and the spire to 45.0 m — all lidar
      const [tx, ty] = [-2.45, -11.9];
      b.color(WALL).box(tx, ty, 0, 7.6, 7.6, 22).box(tx, ty, 22, 5.9, 5.9, 6.2);
      b.prism(octagon(tx, ty, 2.0), 28.2, 37);
      b.color(SLATE).pyramid(octagon(tx, ty, 2.1), 37, [tx, ty, 45]);
      b.color(WALL);
      for (const [dx, dy] of [[-2.6, -2.6], [2.6, -2.6], [2.6, 2.6], [-2.6, 2.6]]) b.pyramid(rect(tx + dx, ty + dy, 0.8, 0.8), 28.2, [tx + dx, ty + dy, 31]);
      b.color('#6E5A4A').box(tx, ty - 3.85, 0, 2.4, 0.2, 4.6);
    });
  },
  {
    Built: '1889: Gothic Revival brick parish church built over part of the mission church\'s sanctuary and cemetery, in the same orientation (a wooden church of 1858 had stood next door)',
    Height: 'spire 45.0 m (148 ft), nave ridge 21.5 m, eaves 12.9 m — measured on the 2020 USGS lidar',
    Model:
      'nave 19 × 28 m, raised sanctuary roof (24 m), apse and the tower (7.6 m square below, 5.9 m above 22 m, a 3.7 m octagonal stage from 28 to 37 m under the spire) placed from the lidar (the OpenStreetMap outline, used for the footprint it replaces, lies ≈ 6 m further south); pinnacles, door and colours estimated; construction start estimated'
  },
  [WIKI + 'Mission_Santa_Cruz', LIDAR_SC],
  [rotPoly(HOLY_CROSS_OUTLINE, 349.9)]
);

// ---- the 1931 replica chapel, frame 98.5° (+y east along the nave, +x south)
const MISSION_REPLICA: V2 = [-122.029423, 36.978046];
const MISSION_REPLICA_OUTLINE: V2[] = [[-7.1,10.6],[3.8,10.4],[4.0,-4.3],[7.1,-4.3],[7.0,-8.0],[4.0,-8.0],[4.0,-10.6],[3.2,-10.6],[3.2,-9.4],[-2.9,-9.3],[-2.9,-10.5],[-3.7,-10.5],[-3.5,4.5],[-3.1,4.5],[-3.1,6.4],[-7.1,6.5]];
const missionReplica = landmark(
  'mission_santa_cruz_replica',
  'Mission Santa Cruz (1931 replica chapel)',
  'building',
  [1931.0, 1931.9],
  9999,
  MISSION_REPLICA,
  b => {
    b.frame(0, 0, 0, 98.5, () => {
      b.color(ADOBE);
      boxR(b, [-3.9, 3.7, -8.9, 11.6], 0, 5.7, false);
      boxR(b, [-7.1, -3.9, 5.8, 11.6], 0, 3.4);
      b.color(TILE);
      gableR(b, [-4.3, 4.0, -8.9, 11.6], 5.7, 1.2); // ridge 6.9 m (lidar)
      // bell tower beside the front (OSM 3.1 × 3.7 m), tiled dome
      b.color(ADOBE);
      boxR(b, [3.2, 6.8, -6.65, -2.95], 0, 10.7);
      b.color(TILE).dome(5.0, -4.8, 1.6, 10.7, 1.9, 8, 3);
      b.color('#5A5048').beam([5.0, -4.8, 12.6], [5.0, -4.8, 14.4], 0.15);
    });
  },
  {
    Built: '1931: a one-half-size replica of the 1794 mission church near its site, made possible by Gladys Sullivan Doyle; chapel of Holy Cross parish',
    Model:
      OSM_NOTE + ' (nave 7.7 × 21 m); nave and tower placed from the 2020 USGS lidar (≈ 1.5 m east of the OSM outline): ridge 6.9 m, eaves 5.7 m, tower 3.7 m square, ≈ 12.6 m with its dome, cross to 14.4 m — the tower is partly under trees, ± 1 m; dome form estimated'
  },
  [WIKI + 'Mission_Santa_Cruz', LIDAR_SC],
  [rotPoly(MISSION_REPLICA_OUTLINE, 98.5)]
);

// =================================================================== LIGHTHOUSES (Santa Cruz)

// ---- first Santa Cruz Light (1869–1948): position and size LOW CONFIDENCE
const SC_LIGHT_1869: V2 = [-122.02672, 36.95202];
const scLight1869 = landmark(
  'santa_cruz_light_1869',
  'Santa Cruz Lighthouse (1869)',
  'tower',
  [1869.5, 1869.95],
  1948.38,
  SC_LIGHT_1869,
  b => {
    b.frame(0, 0, 0, 0, () => {
      b.color(WOOD_WHITE).box(0, 0, 0, 8.6, 10.4, 4.3, {top: false});
      b.color('#8E4A3C');
      gableR(b, [-4.6, 4.6, -5.4, 5.4], 4.3, 3.2);
      // square light tower through the middle of the roof, octagonal lantern
      b.color(WOOD_WHITE).box(0, 0, 4.3, 2.9, 2.9, 5.2);
      b.color('#2B2D2F').prism(octagon(0, 0, 2.0), 9.5, 9.8).cylinder(0, 0, 1.25, 9.8, 11.4, 8);
      b.dome(0, 0, 1.35, 11.4, 0.8, 8, 2);
    });
  },
  {
    Built: 'wooden lighthouse on a brick foundation, built in the summer of 1869 from the plans of the Ediz Hook light (Washington Territory): a one-and-a-half-storey keeper\'s house with a pitched roof and a square light tower; fifth-order Fresnel lens first lit Jan 1, 1870',
    Moved: 'in 1879, with sea caves cutting under the point, it was jacked up and rolled about 300 ft north (drawn at that second site throughout)',
    Fate: 'replaced in Feb 1941 by a 26 ft wooden framework tower 200 ft seaward; sold in 1948 and dismantled for its lumber from May 20, 1948',
    Model: 'no dimensions found: house (8.6 × 10.4 m) and tower (≈ 11.4 m to the lantern roof) estimated from photographs; placed about 300 ft north of the tip of Lighthouse Point, ± 40 m (LOW CONFIDENCE)'
  },
  ['https://www.lighthousefriends.com/light.asp?ID=87']
);

// ---- Mark Abbott Memorial Lighthouse (1967), frame 144.4° (+y south-east)
const ABBOTT: V2 = [-122.026709, 36.95146];
const markAbbott = landmark(
  'mark_abbott_memorial_lighthouse',
  'Mark Abbott Memorial Lighthouse',
  'tower',
  [1967.0, 1967.9],
  9999,
  ABBOTT,
  b => {
    b.frame(0, 0, 0, 144.4, () => {
      const BRICK = '#A8614A';
      b.color(BRICK);
      boxR(b, [-4.3, 2.6, -0.3, 8.7], 0, 3.6, false);
      b.color('#6B6E70');
      gableR(b, [-4.6, 2.9, -0.3, 8.7], 3.6, 1.3);
      // square brick tower, 39 ft with the lantern
      b.color(BRICK).box(-0.65, -2.2, 0, 3.9, 3.9, 8.6);
      b.color('#F1F0EA').box(-0.65, -2.2, 8.6, 4.4, 4.4, 0.3);
      b.color('#2B2D2F').cylinder(-0.65, -2.2, 1.2, 8.9, 10.8, 8);
      b.dome(-0.65, -2.2, 1.3, 10.8, 1.1, 8, 2);
    });
  },
  {
    Built: '1967: brick lighthouse given by the parents of Mark Abbott, who drowned bodysurfing off Pleasure Point on Feb 28, 1965; it took over from the Coast Guard\'s 1941 framework tower. Since June 1986 it houses the Santa Cruz Surfing Museum',
    Tower: '39 ft (12 m) square brick tower attached to a one-storey brick building; focal plane 60 ft',
    Model: 'footprint from OpenStreetMap (© OSM contributors, ODbL; 6.8 × 11.2 m); tower position (north-west end), its 3.9 m square and 11.9 m top checked on the 2020 USGS lidar (building 7.1 m wide); lantern proportions estimated'
  },
  ['https://www.lighthousefriends.com/light.asp?ID=87', WIKI + 'Santa_Cruz_Surfing_Museum', 'https://www.ibiblio.org/lighthouse/ca.htm', LIDAR_SC],
  [rotPoly(rect(-0.85, 2.3, 8.6, 13.4), 144.4)]
);

// ---- Walton Lighthouse (Santa Cruz Harbor west jetty)
const WALTON: V2 = [-122.002191, 36.960676];
const waltonLighthouse = landmark(
  'walton_lighthouse',
  'Walton Lighthouse (Santa Cruz Breakwater Light)',
  'tower',
  [2001.3, 2001.95],
  9999,
  WALTON,
  b => {
    b.color('#F3F2EC').frustum(0, 0, 1.9, 1.25, 0, 9.2, 12);
    b.color('#2F8F5B').cylinder(0, 0, 1.3, 8.1, 8.7, 12);
    b.color('#F3F2EC').cylinder(0, 0, 1.9, 9.2, 9.5, 12);
    b.color('#C9D2D4').cylinder(0, 0, 1.05, 9.5, 11.3, 10);
    b.color('#2F8F5B').dome(0, 0, 1.25, 11.3, 1.1, 10, 2);
    b.beam([0, 0, 12.4], [0, 0, 12.65], 0.1);
  },
  {
    Built: '2001: the current light on the west jetty of the Santa Cruz Small Craft Harbor (first breakwater light 1964); named for Charles Walton, who gave much of its cost in memory of his brother Derek, a merchant seaman',
    Tower: '41.5 ft (12.6 m) tapered cylindrical tower with balcony and lantern, white with a narrow green band; focal plane 59.5 ft',
    Model: 'position and height (12.8 m above the jetty) from the 2020 USGS lidar, 3 m south of the OpenStreetMap node; taper and lantern proportions estimated'
  },
  [WIKI + 'Santa_Cruz_Breakwater_Light', LIDAR_SC]
);

// =================================================================== SEACLIFF, CAPITOLA, FELTON

// ---- SS Palo Alto, the "Cement Ship" (Seacliff State Beach), frame 26° (+y toward the beach); z from sea level
const PALO_ALTO: V2 = [-121.914016, 36.969489];
const PALO_ALTO_HULL: V2[] = [[-8.4,46.9],[-8.7,-8.1],[-7.6,-50.6],[-4.6,-60.1],[-1.3,-65.2],[3.6,-61.2],[8.8,-51.0],[8.3,49.1],[5.8,61.4],[3.1,65.2],[-2.0,65.2],[-5.2,59.4]];
const ssPaloAlto = landmark(
  'ss_palo_alto',
  'SS Palo Alto, the "Cement Ship" (Seacliff)',
  'bridge',
  [1930.06, 1930.49],
  9999,
  PALO_ALTO,
  b => {
    b.frame(0, 0, 0, 26, () => {
      b.color(CONCRETE).prism(PALO_ALTO_HULL, -1.5, 5.6);
      // raised forecastle (seaward) and poop (toward the pier)
      const part = (v0: number, v1: number) => PALO_ALTO_HULL.filter(p => p[1] >= v0 - 1e-6 && p[1] <= v1 + 1e-6);
      const bow: V2[] = [[-7.6, -46], ...part(-66, -46.1), [8.6, -46]];
      const stern: V2[] = [[8.3, 47], ...part(47.1, 66), [-8.4, 47]];
      b.color('#B3AFA6').prism(bow, 5.6, 8).prism(stern, 5.6, 8);
      b.color('#8F8B83').box(0, 2, 5.6, 9, 12, 0.6);
    });
  },
  {
    Built: 'concrete tanker launched at Oakland on May 29, 1919, too late for the war and never in service; sold as a hulk in 1924',
    Seacliff: 'bought by the Seacliff Amusement Corporation, towed from Oakland on Jan 21–22, 1930 and sunk on the sea floor off the beach on Jan 25, bow to the waves; with a dance floor, a café and a swimming pool it opened on June 28, 1930; the company failed in 1932, the ship was stripped, bought by the State for $1 in 1936 and used as a fishing pier',
    Size: '420 ft between perpendiculars, 434 ft (132 m) overall, beam 54 ft, depth 35 ft',
    Fate: 'a crack of 1932 split the hull in a 1963 storm; closed 1980–83 and again from 2016; a storm tore the stern off on Jan 21, 2017; drawn whole',
    Model: 'hull outline from OpenStreetMap (© OSM contributors, ODbL; 130.4 × 17.5 m, bow seaward); deck ≈ 5.6 m and the ends ≈ 8 m above sea level after what is left on the 2020 USGS lidar (3–9 m); the 1930 dance hall, café and pool are not modelled'
  },
  [WIKI + 'SS_Palo_Alto', 'https://semperaltius.com.plesk01.alentus.com/palo_alto_history.htm', LIDAR_SC]
);

const SEACLIFF_PIER_DECK: V2[] = [[-7.4, 66], [4.8, 66], [7.6, 256], [-4.6, 256]];
const seacliffPier = landmark(
  'seacliff_pier',
  'Seacliff pier (to the Cement Ship)',
  'bridge',
  [1930.0, 1930.45],
  2023.02,
  PALO_ALTO,
  b => {
    b.frame(0, 0, 0, 26, () => {
      b.color(DECK_WOOD).prism(SEACLIFF_PIER_DECK, 5.75, 6.45, {bottom: true});
      b.color(PILE);
      piles(b, SEACLIFF_PIER_DECK, 5.75, 5.5, 9, 0.4);
    });
  },
  {
    Built: '1930: timber pier from the beach to the grounded SS Palo Alto — 630 ft long and 40 ft wide, finished in early June 1930 (other accounts say 500 or 600 ft)',
    Fate: 'a fishing pier of Seacliff State Beach from 1936; wrecked by storm surf on Jan 5, 2023 and removed',
    Model: 'measured on the 2020 USGS lidar: deck 6.45 m (NAVD88), 12.2 m (40 ft) wide, 190 m (623 ft) from the ship to the beach; piles schematic'
  },
  ['https://semperaltius.com.plesk01.alentus.com/palo_alto_history.htm', 'https://history.santacruzpl.org/omeka/items/show/9799', 'https://www.pierfishing.com/seacliff-state-beach-pier-2-aptos/', WIKI + 'SS_Palo_Alto', LIDAR_SC]
);

// ---- Capitola Wharf, frame 168.6° (+y out to sea); z from sea level
const CAPITOLA_WHARF: V2 = [-121.95345, 36.9702];
const CAPITOLA_HEAD: V2[] = [[4.8,-35.3],[5.7,37.7],[8.8,37.9],[10.3,41.4],[10.5,49.9],[15.1,57.5],[15.2,127.1],[5.7,134.4],[-4.8,124.9],[-4.3,57.5],[-1.2,49.9],[-1.4,-35.3]];
const CAPITOLA_STEM: V2[] = [[-1.4, -130], [4.6, -130], [4.6, -124.1], [9.9, -124.1], [10.1, -103.4], [4.8, -103.4], [4.8, -35.2], [-1.4, -35.2]];
const capitolaWharf = landmark(
  'capitola_wharf',
  'Capitola Wharf',
  'bridge',
  [1856.8, 1857.5],
  9999,
  CAPITOLA_WHARF,
  b => {
    b.frame(0, 0, 0, 168.6, () => {
      b.color(DECK_WOOD).prism(CAPITOLA_STEM, 6.2, 7.0, {bottom: true}).prism(CAPITOLA_HEAD, 6.2, 7.0, {bottom: true});
      b.color(PILE);
      piles(b, CAPITOLA_STEM, 6.2, 4, 9, 0.4);
      piles(b, CAPITOLA_HEAD, 6.2, 5, 9, 0.4);
    });
  },
  {
    Built: '1857: a 450 ft wharf, "Soquel Landing", built for F. A. Hihn by the carpenter Sedgwick Lynch; lengthened to 1,200 ft within a few years; today 855 ft (261 m)',
    Storms: 'surf broke the wharf in two in January 2023; rebuilt with new piles and a deck widened from 20 to 36 ft, reopened Sep 25, 2024',
    Model:
      'today\'s outline for every year since 1857 (OpenStreetMap, © OSM contributors, ODbL — the 20 ft deck before the 2024 widening; 264 m long); deck level 7.0 m (NAVD88) from the 2020 USGS lidar; the 19th-century wharf differed in length (LOW CONFIDENCE before the 20th century); the buildings at its head (bait shop, restaurant; removed 2024) are not modelled; piles schematic'
  },
  ['https://www.cityofcapitola.org/node/22140', 'https://www.santacruz.org/press-blog/historic-capitola-wharf-reopens-following-10-million-renovation/', LIDAR_SC],
  [rotPoly(CAPITOLA_HEAD, 168.6)]
);

// ---- Felton Covered Bridge (1892), frame 63.9° (+y east-north-east across the San Lorenzo River)
const FELTON_BRIDGE: V2 = [-122.070936, 37.050809];
const feltonBridge = landmark(
  'felton_covered_bridge',
  'Felton Covered Bridge',
  'building',
  [1892.0, 1892.9],
  9999,
  FELTON_BRIDGE,
  b => {
    b.frame(0, 0, 0, 63.9, () => {
      const D = 4; // deck above the river bed (lidar: bed 76.0 m, deck 80.0 m NAVD88)
      const REDWOOD = '#7E5238';
      b.color('#6B5A4A').box(1.5, 1, D - 0.6, 6.4, 52, 0.6, {bottom: true});
      // board-sided housing: walls to the eaves (8.0 m above the deck), ridge 10.5 m (34.5 ft) above it
      b.color(REDWOOD);
      for (const u of [-1.9, 4.9]) b.box(u, 1, D, 0.3, 52, 8);
      // portals: gable ends above a 5 m opening
      for (const v of [-25, 27]) {
        b.box(1.5, v, D + 5, 6.8, 0.3, 3);
        b.tri([-3.5, v, D + 8], [6.5, v, D + 8], [1.5, v, D + 10.5]);
      }
      b.color('#5A4A3E');
      gableR(b, [-3.5, 6.5, -26, 28], D + 8, 2.5);
      // piers and abutments (schematic)
      b.color('#8B8B86');
      for (const v of [-25.5, -11.2, 13.2, 27.5]) b.box(1.5, v, -1, 6, 1.6, D + 0.4);
    });
  },
  {
    Built: '1892: a covered truss bridge (Brown truss per Wikipedia, Pratt per PCAD) over the San Lorenzo River, the main way into Felton for 45 years; altered for pedestrians in 1938; California Historical Landmark (1957), National Register 1973; restored 1987 after the storms of 1982',
    Size: '35 ft (10.7 m) from deck to ridge — considered the tallest covered bridge in the United States; span given as 80 ft (Wikipedia) or 140 ft (PCAD)',
    Model:
      'measured on the 2020 USGS lidar: roof 54 m long and 10 m wide (OpenStreetMap outline 50.4 × 9.4 m), ridge 10.5 m and eaves 8.0 m above the deck, deck 4 m above the river bed; wall line under the eaves, portals and the piers estimated (the truss is not modelled)'
  },
  [WIKI + 'Felton_Covered_Bridge', 'https://pcad.lib.washington.edu/building/17597/', LIDAR_SC],
  [rotPoly(rect(1.2, 1, 12, 56), 63.9)]
);

// =================================================================== DOWNTOWN SANTA CRUZ

// ---- Town Clock (1976)
const TOWN_CLOCK: V2 = [-122.026926, 36.977171];
const townClock = landmark(
  'santa_cruz_town_clock',
  'Santa Cruz Town Clock',
  'monument',
  [1976.0, 1976.6],
  9999,
  TOWN_CLOCK,
  b => {
    b.frame(0, 0, 0, 71.8, () => {
      const BRICK = '#9C5B45';
      b.color(BRICK).box(0, 0, 0, 6.4, 6.4, 7).box(0, 0, 7, 5.6, 5.6, 5.6);
      b.color('#EDE8DA').box(0, 0, 12.6, 4.7, 4.7, 3.6);
      b.color('#F7F5EE');
      for (const [dx, dy] of [[0, 2.4], [0, -2.4], [2.4, 0], [-2.4, 0]]) b.box(dx, dy, 13.3, dx ? 0.15 : 2.2, dx ? 2.2 : 0.15, 2.2); // clock faces
      b.color('#5F6168').pyramid(rect(0, 0, 5.1, 5.1), 16.2, [0, 0, 18.6]);
      b.beam([0, 0, 18.6], [0, 0, 19.6], 0.15);
    });
  },
  {
    Built: 'dedicated in 1976 for the Bicentennial at the head of Pacific Avenue (Water and Front streets): a new brick tower for the town clock of the Odd Fellows building — the first clock (1873) burned in May 1899, its replacement is dated Jan 22, 1900 and was taken down in the 1964 remodelling',
    Height: '19.6 m (64 ft) to the top, measured on the 2020 USGS lidar',
    Model: 'position and the stepped silhouette from the lidar (6.4 m square base to 7 m, shaft to 12.6 m, 4.7 m clock stage, roof and finial to 19.6 m; the OpenStreetMap node is 1.5 m west); openings, clock faces and roof form estimated'
  },
  ['https://history.santacruzpl.org/omeka/items/show/139301', 'https://history.santacruzpl.org/omeka/items/show/105643', LIDAR_SC],
  [rect(-1.5, 0, 7, 7)]
);

// ---- Hotel Palomar (1928–29), frame 346° (+y north-north-west along Pacific Avenue, +x toward Front Street)
const PALOMAR: V2 = [-122.025821, 36.97424];
const PALOMAR_OUTLINE: V2[] = [[-23.9,27.8],[11.6,28.3],[11.8,11.9],[18.4,11.9],[18.4,13.8],[24.5,13.7],[24.5,-1.7],[23.4,-1.7],[23.5,-28.4],[-24.5,-28.4]];
const palomar = landmark(
  'hotel_palomar_santa_cruz',
  'Hotel Palomar (Santa Cruz)',
  'building',
  [1928.3, 1929.78],
  9999,
  PALOMAR,
  b => {
    b.frame(0, 0, 0, 346, () => {
      const WALL = '#D9CDB4';
      b.color('#CFC4AE').prism(PALOMAR_OUTLINE, 0, 10.2);
      b.color(WALL);
      boxR(b, [-21.2, -5.2, -26.3, 11.5], 10.2, 25);
      boxR(b, [-21.1, -5.2, -12.1, -1], 25, 29);
      b.color('#B9AE98').beam([-18.8, -8.7, 29], [-18.8, -8.7, 34.1], 0.25);
    });
  },
  {
    Built: '1928–29: hotel on Pacific Avenue — the first building in the area more than three storeys tall; a Chrysler dealership opened in its ground floor on Oct 12, 1929. It came through the 1989 earthquake; today the Palomar Inn apartments over shops',
    Height: 'roof 25 m, central penthouse floor 29 m, mast top 34.1 m — measured on the 2020 USGS lidar',
    Model: OSM_NOTE + ' (the whole Palomar block, 49 × 57 m); tower slab (16 × 38 m along Pacific Avenue) and its raised centre (16 × 11 m) placed from the lidar; the low arcade / shop wings at 10 m; Art Deco ornament not modelled; construction start estimated'
  },
  ['https://localwiki.org/santacruz/Hotel_Palomar', 'https://pcad.lib.washington.edu/building/22619/', LIDAR_SC],
  [rotPoly(PALOMAR_OUTLINE, 346)]
);

// =================================================================== WATSONVILLE

// ---- St. Patrick's Church (1903; rebuilt to the same design 1994), frame 55.4° (+y north-east toward the front)
const ST_PATRICK: V2 = [-121.761567, 36.914416];
const ST_PATRICK_OUTLINE: V2[] = [[-9.4,24.3],[5.0,24.3],[5.0,25.4],[9.9,25.4],[9.9,19.5],[11.1,18.2],[11.0,16.1],[9.6,14.6],[7.3,14.6],[7.2,4.7],[10.5,4.7],[10.4,-7.0],[7.6,-7.0],[7.6,-14.5],[11.6,-14.5],[11.5,-23.1],[8.1,-23.1],[8.1,-25.1],[3.3,-25.1],[3.3,-23.3],[-3.3,-23.2],[-3.3,-25.4],[-9.4,-25.4],[-9.4,-23.4],[-11.5,-23.4],[-11.5,-14.9],[-7.7,-14.9],[-7.7,-7.2],[-10.6,-7.2],[-10.5,4.6],[-7.5,4.6],[-7.5,14.5],[-10.1,14.4],[-11.4,15.7],[-11.5,18.6],[-9.5,19.9]];
function stPatricks(b: MeshBuilder) {
  b.frame(0, 0, 0, 55.4, () => {
    const BRICK = '#9B4F3F';
    b.color(BRICK);
    boxR(b, [-7.7, 7.6, -17.5, 24.3], 0, 8.6, false);
    boxR(b, [-10.6, 10.5, -7.1, 4.7], 0, 8.6, false);
    boxR(b, [-9.4, 8.1, -25.3, -17.5], 0, 6.2, false);
    b.color(SLATE);
    gableR(b, [-8, 7.9, -17.5, 24.3], 8.6, 7); // ridge 15.6 m
    gableR(b, [-10.9, 10.8, -7.1, 4.7], 8.6, 5, true); // transept, ridge 13.6 m
    gableR(b, [-9.4, 8.1, -25.3, -17.5], 6.2, 1.4, true);
    b.pyramid(octagon(1, -1, 0.9), 15, [1, -1, 22]); // fleche over the crossing
    // corner tower (lidar: 6.4 m square to 13 m, 5 m belfry to 18 m) and the slender slate spire to 38.3 m
    const [tx, ty] = [8, 21.4];
    b.color(BRICK).box(tx, ty, 0, 6.4, 6.4, 13).box(tx, ty, 13, 5, 5, 5);
    b.color(SLATE).pyramid(octagon(tx, ty, 2.5), 18, [tx, ty, 38.3]);
    b.color(BRICK);
    for (const [dx, dy] of [[-2.2, -2.2], [2.2, -2.2], [2.2, 2.2], [-2.2, 2.2]]) b.pyramid(rect(tx + dx, ty + dy, 0.7, 0.7), 18, [tx + dx, ty + dy, 20.5]);
    // front gable wall
    b.tri([-8, 24.3, 8.6], [4.4, 24.3, 8.6], [-0.05, 24.3, 15.6]);
  });
}
const stPatrick1903 = landmark(
  'st_patricks_watsonville_1903',
  'St. Patrick\'s Church, Watsonville (1903)',
  'building',
  [1902.0, 1903.5],
  1989.79,
  ST_PATRICK,
  stPatricks,
  {
    Built: '1903: red-brick Gothic Revival church by William H. Weeks with a slate-roofed steeple, replacing the parish\'s first church (1865–1903)',
    Fate: 'wrecked by the Loma Prieta earthquake of Oct 17, 1989 and taken down',
    Model: 'the 1994 church repeats the 1903 design, so this is the same model: outline of the standing church (OpenStreetMap), heights from the 2020 USGS lidar of the rebuilt church (LOW CONFIDENCE for 1903 details)'
  },
  ['https://pcad.lib.washington.edu/building/19762/', 'https://www.watsonville.gov/DocumentCenter/View/1141', LIDAR_SC]
);
const stPatrick1994 = landmark(
  'st_patricks_watsonville',
  'St. Patrick\'s Church, Watsonville',
  'building',
  [1992.0, 1994.3],
  9999,
  ST_PATRICK,
  stPatricks,
  {
    Built: 'rebuilt by the Diocese of Monterey after the Loma Prieta earthquake to the design of the 1903 brick church; dedicated in 1994',
    Height: 'spire 38.3 m (126 ft), nave ridge 15.6 m, transept 13.6 m, fleche 22 m — measured on the 2020 USGS lidar',
    Model: OSM_NOTE + ' (23 × 51 m); corner tower (6.4 m square to 13 m, belfry to 18 m, slender spire) placed from the lidar; pinnacles, buttresses and colours estimated; construction start estimated'
  },
  ['https://pcad.lib.washington.edu/building/19760/', LIDAR_SC],
  [rotPoly(ST_PATRICK_OUTLINE, 55.4)]
);

// =================================================================== GILROY AND MORGAN HILL

// ---- Gilroy Old City Hall (1905), frame 71.1° (+y east-north-east; the tower stands on the Monterey Street front)
const GILROY_HALL: V2 = [-121.568385, 37.007056];
const GILROY_HALL_OUTLINE: V2[] = [[-3.5,-14.1],[-3.5,-0.1],[-9.5,-0.2],[-9.4,14.0],[9.4,14.1],[9.4,-14.0]];
const gilroyOldCityHall = landmark(
  'gilroy_old_city_hall',
  'Old City Hall (Gilroy)',
  'building',
  [1904.6, 1905.9],
  9999,
  GILROY_HALL,
  b => {
    b.frame(0, 0, 0, 71.1, () => {
      const WALL = '#D3B58A';
      b.color(WALL).prism(GILROY_HALL_OUTLINE, 0, 9.6, {top: false});
      boxR(b, [-6.5, 9.4, -18.6, -14], 0, 9.6, false); // the Monterey Street front (lidar; beyond the OSM outline)
      b.color(TILE);
      hipR(b, [-3.8, 9.7, -18.9, 14.4], 9.6, 2.2); // main roof, 11.8 m
      hipR(b, [-6.8, -3.8, -18.9, -14], 9.6, 1);
      hipR(b, [-9.8, -3.5, -0.4, 14.3], 9.6, 1.2);
      // ornamental gables on the two street fronts
      b.color('#E3D2B0');
      b.tri([5.6, -18.7, 9.6], [9.4, -18.7, 9.6], [7.5, -18.7, 12.6]).tri([9.5, -8, 9.6], [9.5, 0, 9.6], [9.5, -4, 13]);
      // corner clock tower: lidar top 18.6 m
      const [tx, ty] = [2.85, -15.3];
      b.color(WALL).box(tx, ty, 0, 4.5, 4.5, 16.5);
      b.color('#F4F1E6');
      for (const [dx, dy] of [[0, 2.3], [0, -2.3], [2.3, 0], [-2.3, 0]]) b.box(tx + dx, ty + dy, 13.3, dx ? 0.15 : 1.9, dx ? 1.9 : 0.15, 1.9); // clock faces
      b.color(TILE).frustum(tx, ty, 2.9, 1.5, 16.5, 17.5, 8, true);
      b.dome(tx, ty, 1.4, 17.5, 0.7, 8, 2);
      b.beam([tx, ty, 18.2], [tx, ty, 18.6], 0.15);
    });
  },
  {
    Built: '1905, by the San José architects Wolfe & McKenzie (with Samuel Newsom): city offices, court, jail and fire company under one roof; the Seth Thomas tower clock was given in 1914; National Register 1975; repaired after the 1989 earthquake',
    Height: 'main roof ≈ 11.8 m, tower 18.6 m — measured on the 2020 USGS lidar',
    Model: OSM_NOTE + ' (18.9 × 28.2 m); the Monterey Street front and the tower (4.5 m square to 16.5 m, cap and finial to 18.6 m) from the lidar — the OpenStreetMap outline stops 4.5 m short of that front; ornamental gables, clock faces and the tiled cupola simplified (estimated proportions)'
  },
  [WIKI + 'Old_City_Hall_(Gilroy,_California)', 'https://npgallery.nps.gov/AssetDetail/NRIS/75000480', LIDAR_SCL],
  [rotPoly(GILROY_HALL_OUTLINE, 71.1)]
);

// ---- Villa Mira Monte (Morgan Hill, 1886), frame 144.7°
const MIRA_MONTE: V2 = [-121.657304, 37.134791];
const villaMiraMonte = landmark(
  'villa_mira_monte',
  'Villa Mira Monte (Morgan Hill)',
  'building',
  [1885.6, 1886.6],
  9999,
  MIRA_MONTE,
  b => {
    b.frame(0, 0, 0, 144.7, () => {
      b.color('#E9E3D2');
      boxR(b, [-9.8, 2.9, -9.8, 8.2], 0, 7, false);
      b.color('#6F6B66');
      hipR(b, [-10.2, 3.3, -10.2, 8.6], 7, 2.8); // ridge 9.8 m (lidar)
      // verandah along the front
      b.color('#DAD3C0');
      boxR(b, [2.9, 5.5, -9.8, 8.2], 3.6, 4.2);
      for (let v = -9.5; v <= 8; v += 2.9) b.box(5.3, v, 0, 0.25, 0.25, 3.6);
    });
  },
  {
    Built: '1886: Stick / Eastlake country house of Hiram Morgan Hill, for whom the town is named, and Diana Helen Murphy Hill, daughter of Daniel Murphy; National Register; the Morgan Hill Museum (a 1911 farmhouse) stands beside it',
    Model: 'body (12.7 × 18 m), verandah, eaves ≈ 7 m and the short ridge at 9.8 m placed from the 2020 USGS lidar — ≈ 3 m north-east of the OpenStreetMap outline (13.2 × 19.3 m); roof simplified to one hip, verandah posts schematic'
  },
  [WIKI + 'Villa_Mira_Monte', LIDAR_SCL],
  [rotPoly(rect(-2, -0.8, 16.6, 19.8), 144.7)]
);

// =================================================================== EAST CONTRA COSTA

// ---- Antioch Bridge (1978), frame 359.85° (+y north to Sherman Island); z from sea level
const ANTIOCH_BRIDGE: V2 = [-121.75157, 38.027806];
const antiochBridge = landmark(
  'antioch_bridge_1978',
  'Antioch Bridge (Senator John A. Nejedly Bridge)',
  'bridge',
  [1976.0, 1978.95],
  9999,
  ANTIOCH_BRIDGE,
  b => {
    b.frame(0, 0, 0, 359.85, () => {
      const S = -1232; // south abutment (OSM)
      const N = 1648; // north end on Sherman Island (OSM)
      const CREST = 135 * FT + 4.4; // 135 ft clearance + girder
      // deck profile (ESTIMATED): parabolic crest over the 460 ft main span, 3.3 % grades, low viaduct on Sherman Island
      const zd = (v: number) => {
        const a = Math.abs(v);
        const z = a <= 150 ? CREST - (0.033 * a * a) / 300 : CREST - 2.475 - 0.033 * (a - 150);
        return Math.max(z, 7.5);
      };
      const vs: number[] = [];
      for (let v = S; v < N; v += 24) vs.push(v);
      vs.push(N);
      const W = (38.1 * FT) / 2;
      const STEEL = '#70503F'; // weathering steel
      for (let i = 0; i < vs.length - 1; i++) {
        const [v0, v1] = [vs[i], vs[i + 1]];
        const [z0, z1] = [zd(v0), zd(v1)];
        b.color('#B9B6AE');
        b.quad([-W, v0, z0], [W, v0, z0], [W, v1, z1], [-W, v1, z1]);
        for (const u of [-W, W]) b.quad([u, v0, z0 - 0.5], [u, v1, z1 - 0.5], [u, v1, z1 + 0.8], [u, v0, z0 + 0.8]);
        // two plate girders, deeper over the main piers
        const d = (v: number) => 3.4 + 2.6 * Math.max(0, 1 - Math.abs(Math.abs(v) - 70.1) / 45);
        b.color(STEEL);
        for (const u of [-3.2, 3.2]) b.quad([u, v0, z0 - 0.5], [u, v1, z1 - 0.5], [u, v1, z1 - 0.5 - d(v1)], [u, v0, z0 - 0.5 - d(v0)]);
      }
      // piers: the two channel piers at ± 230 ft (OSM fenders), approach piers every 76 m (schematic)
      b.color('#A9A59B');
      const pier = (v: number) => {
        const top = zd(v) - 4;
        if (top < 3) return;
        for (const u of [-3.2, 3.2]) b.box(u, v, -2, 2.2, 2.6, top + 2);
        b.box(0, v, top - 1.6, 9, 2.8, 1.6);
      };
      pier(-70.1);
      pier(70.1);
      for (let v = 70.1 + 76; v < N - 20; v += 76) pier(v);
      for (let v = -70.1 - 76; v > S + 20; v -= 76) pier(v);
      // fenders round the channel piers
      b.color('#6E6A62');
      for (const v of [-67, 67]) b.box(0, v, -1, 17, 56, 3.2);
    });
  },
  {
    Built: 'opened December 1978, replacing the 1926 lift bridge beside it (whose piers carry the fishing pier of the Antioch / Oakley Regional Shoreline): State Route 160 across the San Joaquin River from Antioch to Sherman Island',
    Size: '9,504 ft (1.8 mi, 2.9 km) long, 38.1 ft wide (two lanes), steel plate girders; main span 460 ft with 135 ft (41 m) of clearance',
    Model:
      'alignment and length from OpenStreetMap (© OSM contributors, ODbL); main span centred on the two channel-pier fenders OSM maps (134 m apart ≈ the documented 460 ft); the deck profile is ESTIMATED — crest at clearance + girder depth, 3.3 % grades, low viaduct over Sherman Island (no lidar here); girder depths, approach pier spacing and colours estimated; construction start estimated'
  },
  [WIKI + 'Antioch_Bridge', 'https://mtc.ca.gov/operations/bridges-roadways/bridges/antioch-bridge']
);

// ---- John Marsh's Stone House (1856), frame 147.1° (+y south-south-east)
const MARSH_HOUSE: V2 = [-121.723047, 37.891916];
const SANDSTONE = '#CBB78F';
const marshHouse = landmark(
  'john_marsh_house',
  'John Marsh Stone House (Rancho Los Meganos)',
  'building',
  [1853.5, 1856.67],
  9999,
  MARSH_HOUSE,
  b => {
    b.frame(0, 0, 0, 147.1, () => {
      const r: [number, number, number, number] = [-8, 5, -8.7, 10.4];
      b.color(SANDSTONE);
      boxR(b, r, 0, 7.6, false);
      b.color('#77706A');
      gableR(b, [r[0] - 0.4, r[1] + 0.4, r[2], r[3]], 7.6, 4.4); // ridge 12 m (lidar)
      // three cross gables on each long front
      for (const v of [-4.9, 0.85, 6.6]) gableR(b, [r[0] - 0.4, r[1] + 0.4, v - 1.9, v + 1.9], 7.6, 3, true);
      b.color(SANDSTONE);
      b.tri([r[0], r[2], 7.6], [r[1], r[2], 7.6], [-1.5, r[2], 12]).tri([r[0], r[3], 7.6], [r[1], r[3], 7.6], [-1.5, r[3], 12]);
      // portico along the tower front and both ends
      b.color('#D9CFB8');
      boxR(b, [-10.4, -8, -11.1, 12.8], 3.2, 3.5);
      boxR(b, [-8, 5, -11.1, -8.7], 3.2, 3.5);
      boxR(b, [-8, 5, 10.4, 12.8], 3.2, 3.5);
      for (let v = -10.9; v <= 12.7; v += 3.93) b.box(-10.2, v, 0, 0.3, 0.3, 3.2);
    });
  },
  {
    Built: 'begun 1853, completed 1856 for John Marsh (1799–1856) of Rancho Los Meganos, by the architect Thomas Boyd: Gothic Revival house, three storeys, its walls faced with locally quarried sandstone, with a portico on octagonal pillars; Marsh moved in about Sep 1, 1856, before it was quite finished, and died that year',
    Size: '2,100 sq ft on each of three floors (HABS CA-1500)',
    Later: 'badly damaged in the 1868 and 1906 earthquakes; given to Contra Costa County in 1960; now in Marsh Creek State Park (named 2012), under long restoration',
    Model:
      'body 13 × 19 m: the OpenStreetMap outline (© OSM contributors, ODbL; 12.4 × 19.0 m) agrees with the walls on the 2022 USGS lidar (HABS: 2,100 sq ft of floor inside them); ridge 12 m from the lidar, eaves ≈ 7.6 m; the three gables a side, the portico (drawn on the tower front and both ends) and colours estimated — drawn complete for every year'
  },
  [WIKI + 'Marsh_Creek_State_Park', 'https://www.johnmarshhouse.com/timeline-of-ownership', LIDAR_CC],
  [rotPoly(rect(-1.5, 0.85, 13.6, 19.6), 147.1)]
);
const marshTower = landmark(
  'john_marsh_house_tower',
  'John Marsh Stone House — the stone tower',
  'tower',
  [1853.5, 1856.67],
  1868.81,
  MARSH_HOUSE,
  b => {
    b.frame(0, 0, 0, 147.1, () => {
      const S = 12 * FT;
      const H = 65 * FT;
      const [tx, ty] = [-5.05, 2.9];
      b.color(SANDSTONE).box(tx, ty, 0, S, S, H - 0.8);
      // crenellated top
      for (const [dx, dy] of [[-1, -1], [1, -1], [1, 1], [-1, 1], [0, -1], [0, 1], [-1, 0], [1, 0]]) b.box(tx + (dx * (S - 0.7)) / 2, ty + (dy * (S - 0.7)) / 2, H - 0.8, 0.7, 0.7, 0.8);
    });
  },
  {
    Built: '1856: the observation tower of the Stone House rose 65 ft (20 m) — Marsh wanted to see strangers coming from a long way off; 144 sq ft in plan (HABS)',
    Fate: 'the stone tower came down in the Hayward earthquake of Oct 21, 1868 ("partially destroyed", Contra Costa Gazette) and was rebuilt in wood imitating the stone battlements; that tower fell after the 1906 earthquake (its height is not recorded: not modelled)',
    Model: 'documented height and plan area (12 ft square); placed where the 2022 USGS lidar shows the highest part of the shell (west front); battlements schematic (LOW CONFIDENCE position)'
  },
  [WIKI + 'Marsh_Creek_State_Park', 'https://commons.wikimedia.org/wiki/File:John_Marsh_House_ca._1856._Contra_Costa_County,_California.jpg', LIDAR_CC]
);

// =================================================================== ALTAMONT / VASCO WIND TURBINES

/**
 * U.S. Wind Turbine Database (USGS / LBNL / ACP; public domain), queried 2026-11-10 for Contra Costa and
 * Alameda counties: every turbine at its database position (local metres from the group anchor), with the
 * database's hub height and rotor diameter. Rotors are static, facing the prevailing west-south-west wind.
 */
const USWTDB = 'https://energy.usgs.gov/uswtdb/';
type WindGroup = {anchor: V2; hh: number; rd: number; pts: number[]};
const WIND: Record<string, WindGroup> = {"Buena Vista":{"anchor":[-121.6583,37.8009],"hh":55.0,"rd":61.4,"pts":[1241,-520,-720,231,-192,-443,326,299,-747,310,-17,862,459,166,-474,-310,168,531,-684,55,907,-243,-43,1084,960,-398,-131,-587,-764,386,-1116,-123,203,441,599,-189,-254,-388,476,-155,-1231,-100,-646,-30,-526,-243,371,-144,467,66,-632,-123,4,998,1153,-488,-561,-172,-720,132,-791,475,1031,-453,265,365,-368,-354,880,-155,933,-310,-140,-499,388,231]},"Vasco (repower)":{"anchor":[-121.7048,37.792],"hh":80.0,"rd":101.0,"pts":[-1723,-377,-1407,-841,-78,-443,3309,166,335,719,1285,-807,-1838,-774,-78,1404,-940,-818,-1934,1414,1620,-377,-26,231,1118,-475,3713,100,-896,-178,133,1183,-1353,431,-1802,299,2200,-464,-501,-343,-1027,-1249,-1539,-1283,-1750,1171,-1292,-343,45,-797,-448,242,520,453,283,-222,-614,-1128,2526,-123,-78,1847,-1697,741,-105,663,4136,0]},"Diablo Winds":{"anchor":[-121.6318,37.7634],"hh":60.0,"rd":47.0,"pts":[-2322,1237,-1583,962,-148,1436,996,-2014,1075,-2090,-166,552,-1636,1039,1127,177,934,221,-306,1714,-1495,917,1057,-1537,591,-1935,1031,209,1110,-985,-2331,1460,1013,-941,1215,-1041,1489,-1,-202,641,1005,-1460,555,-1836,-1909,1261,547,-1747,-175,741,-148,1559,-214,1627,811,-521,-1690,1132,-1398,885,1154,-1614]},"Golden Hills":{"anchor":[-121.6326,37.7156],"hh":80.0,"rd":100.0,"pts":[-1931,-548,-316,-586,891,-102,-940,328,1767,153,-602,-914,358,103,-3278,-362,1968,724,-1390,-176,100,-517,-2321,-609,-1401,338,-2433,-379,727,-552,685,406,-1534,-754,1586,1377,1958,-385,1980,-682,-969,-1351,2275,614,-712,-491,424,912,572,1295,-381,-208,1891,1026,271,-1219,-3494,-227,1456,1071,1087,-613,488,629,-2229,-1107,-961,-268,1518,721,234,-794,-3671,-20,128,-218,1161,1311,577,-75,1596,357,2700,825,615,-1285,-719,108,960,839,-523,483,2446,1172,-2563,-160]},"Golden Hills North":{"anchor":[-121.6405,37.7697],"hh":80.0,"rd":116.0,"pts":[2173,-1351,1734,-1016,-1041,1631,2095,-2068,-1342,-219,-2212,1965,2174,-1011,659,233,-2271,1387,-1374,1046,-1128,781,-1905,1815,-1468,10,965,55,2159,-2581,-1849,1364,1704,-1422,-1362,1679,1343,-126,1021,-2216]},"Patterson Pass":{"anchor":[-121.6144,37.6991],"hh":24.0,"rd":16.0,"pts":[299,139,107,686,-296,-167,-116,-398,313,-306,-300,48]},"Summit Wind Repowering":{"anchor":[-121.6816,37.7634],"hh":90.0,"rd":116.0,"pts":[-898,-1737,552,1760,403,857,-997,-2548,-1031,1845,-263,1658,1186,641,316,2294,286,1935,-57,-3778,-887,-475,454,535,-362,-2925,1643,771,-890,-2127,-386,2020,-88,-3428,-164,1372,1573,1217,-1038,-1382,1246,1214,448,1233,-1108,-979]}};
const ROTOR_FACING = 245; // bearing the rotors face (prevailing Altamont Pass wind; estimated)

function turbine(b: MeshBuilder, x: number, y: number, z: number, hh: number, rd: number, phase: number) {
  const r0 = Math.max(0.8, hh * 0.027);
  b.color('#ECEDEC').frustum(x, y, r0, r0 * 0.58, z - 1, z + hh - 1, 8, false);
  b.frame(x, y, z + hh, ROTOR_FACING, () => {
    const nl = rd * 0.1;
    const nw = Math.max(1.4, rd * 0.036);
    b.box(0, -nl * 0.25, -nw / 2, nw, nl, nw, {bottom: true}); // nacelle, mostly downwind of the tower
    const yh = nl * 0.25 + nw * 0.4;
    b.box(0, yh - nw * 0.2, -nw * 0.3, nw * 0.6, nw * 0.6, nw * 0.6, {bottom: true}); // hub
    const R = rd / 2;
    for (let k = 0; k < 3; k++) {
      const a = phase + (k * 2 * Math.PI) / 3;
      const [dx, dz] = [Math.cos(a), Math.sin(a)];
      const [px, pz] = [-dz, dx];
      const c0 = R * 0.04;
      const c1 = R * 0.011;
      const s = nw * 0.3;
      b.quad([dx * s - px * c0, yh, dz * s - pz * c0], [dx * s + px * c0, yh, dz * s + pz * c0], [dx * R + px * c1, yh, dz * R + pz * c1], [dx * R - px * c1, yh, dz * R - pz * c1]);
    }
  });
}

function windFarm(id: string, key: string, name: string, year: number, facts: Record<string, string>, src: string[] = []) {
  const g = WIND[key];
  return landmark(
    id,
    name,
    'tower',
    [year + 0.2, year + 0.95],
    9999,
    g.anchor,
    b => {
      for (let i = 0; i < g.pts.length; i += 2) {
        const [x, y] = [g.pts[i], g.pts[i + 1]];
        turbine(b, x, y, groundDz(g.anchor, x, y), g.hh, g.rd, ((x * 7 + y * 13) % 120) * (Math.PI / 180));
      }
    },
    {
      ...facts,
      Altamont:
        'the thousands of small 1980s Altamont Pass turbines removed since are not in the database and are not drawn',
      Model:
        'each turbine at its U.S. Wind Turbine Database position, with the database hub height and rotor diameter; online year from the database (month not given: drawn from the end of that year); tower taper, nacelle and blade shapes schematic; rotors static, facing west-south-west'
    },
    [USWTDB, ...src]
  );
}

const windPatterson = windFarm('altamont_patterson_pass_1985', 'Patterson Pass', 'Patterson Pass wind turbines (1985 survivors)', 1985, {
  Turbines: '6 still standing of two 1985 projects (Patterson Pass, 201 turbines; Patterson Wind, 112): Nordtank NTK65 and Bonus 65 kW machines, hub 24 m, rotor 16 m'
});
const windDiablo = windFarm('altamont_diablo_winds', 'Diablo Winds', 'Diablo Winds wind farm (Altamont Pass)', 2004, {
  Turbines: '31 Vestas V47 of 660 kW (20.5 MW), hub 60 m, rotor 47 m, 83.5 m to the blade tip; online 2004 — an early Altamont repowering'
});
const windBuenaVista = windFarm('vasco_buena_vista', 'Buena Vista', 'Buena Vista wind farm (Vasco Road)', 2006, {
  Turbines: '38 Mitsubishi MWT62/1.0 of 1 MW (38 MW), hub 55 m, rotor 61.4 m, 85.6 m to the blade tip; online 2006'
});
const windVasco = windFarm('vasco_winds', 'Vasco (repower)', 'Vasco Winds wind farm', 2011, {
  Turbines: '34 Siemens SWT-2.3-101 of 2.3 MW (78.2 MW), hub 80 m, rotor 101 m, 130.5 m to the blade tip; online 2011, on the Contra Costa side of the Altamont (one turbine in Alameda County)'
});
const windGoldenHills = windFarm('altamont_golden_hills', 'Golden Hills', 'Golden Hills wind farm (Altamont Pass)', 2015, {
  Turbines: '48 GE 1.7-100 of 1.7 MW (85.9 MW), hub 80 m, rotor 100 m, 130.1 m to the blade tip; online 2015'
});
const windGoldenHillsNorth = windFarm('altamont_golden_hills_north', 'Golden Hills North', 'Golden Hills North wind farm (Altamont Pass)', 2017, {
  Turbines: '20 GE 2.3-116 of 2.3 MW (46 MW), hub 80 m, rotor 116 m, 138.1 m to the blade tip; online 2017'
});
const windSummit = windFarm('altamont_summit_wind', 'Summit Wind Repowering', 'Summit Wind wind farm (Altamont Pass)', 2021, {
  Turbines: '23 GE 2.7-116 of 2.7 MW (62.1 MW), hub 90 m, rotor 116 m, 148.1 m to the blade tip; online 2021'
});

export const COASTSOUTH: Landmark[] = [
  giantDipper,
  skyGlider,
  casino,
  plunge,
  looffCarousel,
  scWharf,
  missionSantaCruz,
  holyCross,
  missionReplica,
  scLight1869,
  markAbbott,
  waltonLighthouse,
  ssPaloAlto,
  seacliffPier,
  capitolaWharf,
  feltonBridge,
  townClock,
  palomar,
  stPatrick1903,
  stPatrick1994,
  gilroyOldCityHall,
  villaMiraMonte,
  antiochBridge,
  marshHouse,
  marshTower,
  windPatterson,
  windDiablo,
  windBuenaVista,
  windVasco,
  windGoldenHills,
  windGoldenHillsNorth,
  windSummit
];
