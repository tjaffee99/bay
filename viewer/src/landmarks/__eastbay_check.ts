/**
 * East Bay reconstructions (Alameda and Contra Costa counties) —
 * data/research/landmarks_eastbay.md.
 *
 * Footprints are the OpenStreetMap outlines and 3D building parts (via Overture
 * 2026-10-21.0, © OpenStreetMap contributors, ODbL) of the standing buildings,
 * in a frame aligned with the building (`b.frame(0, 0, 0, bearing)`: local +y at
 * `bearing`, +x at `bearing + 90°`) and anchored on the OSM centroid (or, for
 * stadiums and theatres in the round, on the field / orchestra centre). Heights
 * come from Wikipedia, National Register nominations, official figures or the OSM
 * height tags, as named in each model's facts; massing, setbacks and colours
 * from the reference photographs listed in the research note
 * (data/raw/reference_photos/<id>/). Hillside sites (the Greek Theatre, Memorial
 * Stadium, the Temple, Mount Diablo) were checked against the terrain grids
 * (data/interim/grid_*_elev.npy) so seating bowls sit just above the draped
 * terrain; foundations reach a few metres below grade so nothing floats where
 * the ground falls away. Everything estimated is named in the model's facts
 * ("Model: …").
 */
import {MeshBuilder, circle, ellipse, lngLatToLocal, localToLngLat, rect, rotRect, type V2, type V3} from './kit';
import type {Landmark} from './types';
import {elevationAt} from '../layers/elevation';

const WIKI = 'https://en.wikipedia.org/wiki/';
const OSM_NOTE = 'footprint from OpenStreetMap (© OSM contributors, ODbL)';
const FT = 0.3048;

// ------------------------------------------------------------------ helpers

/** Ground height at a point of a landmark's local frame (bearing `brg`) relative to the anchor's ground. */
function groundDz(anchor: V2, brg: number, x: number, y: number) {
  const a = (brg * Math.PI) / 180;
  const p = localToLngLat(anchor, [x * Math.cos(a) + y * Math.sin(a), -x * Math.sin(a) + y * Math.cos(a)]);
  return elevationAt(p[0], p[1]) - elevationAt(anchor[0], anchor[1]);
}

/** Points on an ellipse (semi-axes ax along x, ay along y) from angle a0 to a1 (radians, 0 = +x, CCW). */
function ellArc(cx: number, cy: number, ax: number, ay: number, a0: number, a1: number, n: number): V2[] {
  const out: V2[] = [];
  for (let i = 0; i <= n; i++) {
    const a = a0 + ((a1 - a0) * i) / n;
    out.push([cx + Math.cos(a) * ax, cy + Math.sin(a) * ay]);
  }
  return out;
}

/** Resample an open polyline to n+1 points evenly spaced along its length. */
function resample(path: V2[], n: number): V2[] {
  const d = [0];
  for (let i = 1; i < path.length; i++) d.push(d[i - 1] + Math.hypot(path[i][0] - path[i - 1][0], path[i][1] - path[i - 1][1]));
  const L = d[d.length - 1];
  const out: V2[] = [];
  let k = 0;
  for (let i = 0; i <= n; i++) {
    const s = (L * i) / n;
    while (k < path.length - 2 && d[k + 1] < s) k++;
    const t = (s - d[k]) / (d[k + 1] - d[k] || 1);
    out.push([path[k][0] + (path[k + 1][0] - path[k][0]) * t, path[k][1] + (path[k + 1][1] - path[k][1]) * t]);
  }
  return out;
}

/** Sloped seating between two matching polylines (z per edge), with a back wall down to zBase. */
function bowl(b: MeshBuilder, inner: V2[], outer: V2[], zIn: number, zOut: number, seats: string, wall: string, zBase = 0, closed = false) {
  b.color(seats).ribbon(
    inner.map(p => [p[0], p[1], zIn] as V3),
    outer.map(p => [p[0], p[1], zOut] as V3),
    closed
  );
  b.color(wall).wallProfile(outer, zBase, zOut, closed).wallProfile(inner, zBase, zIn, closed);
}

/** Vertical disc (clock face, oculus) centred at (x, y, z) facing horizontal direction (nx, ny). */
function vdisc(b: MeshBuilder, x: number, y: number, z: number, r: number, nx: number, ny: number, segs = 12) {
  const tx = -ny;
  const ty = nx;
  const c: V3 = [x, y, z];
  for (let i = 0; i < segs; i++) {
    const a0 = (i / segs) * Math.PI * 2;
    const a1 = ((i + 1) / segs) * Math.PI * 2;
    b.tri(c, [x + tx * Math.cos(a0) * r, y + ty * Math.cos(a0) * r, z + Math.sin(a0) * r], [x + tx * Math.cos(a1) * r, y + ty * Math.cos(a1) * r, z + Math.sin(a1) * r]);
  }
}

/** Regular n-gon ring (first vertex at angle `rot`, radians). */
function ngon(cx: number, cy: number, r: number, n: number, rot = Math.PI / n): V2[] {
  const out: V2[] = [];
  for (let i = 0; i < n; i++) out.push([cx + Math.cos(rot + (i * 2 * Math.PI) / n) * r, cy + Math.sin(rot + (i * 2 * Math.PI) / n) * r]);
  return out;
}

/** Scale a ring about its vertex mean. */
function scaleRing(ring: V2[], sx: number, sy = sx): V2[] {
  const cx = ring.reduce((s, p) => s + p[0], 0) / ring.length;
  const cy = ring.reduce((s, p) => s + p[1], 0) / ring.length;
  return ring.map(([x, y]) => [cx + (x - cx) * sx, cy + (y - cy) * sy] as V2);
}

/** A local-frame ring (bearing `brg`) as anchor-frame polygon (for `replaces`). */
function rotRing(ring: V2[], brg: number, dx = 0, dy = 0): V2[] {
  const a = (-brg * Math.PI) / 180;
  const c = Math.cos(a);
  const s = Math.sin(a);
  return ring.map(([x, y]) => [dx + c * x - s * y, dy + s * x + c * y] as V2);
}

/** Row of evenly spaced boxes along a straight wall from p to q (pilasters, columns, piers). */
function rowOf(b: MeshBuilder, p: V2, q: V2, n: number, w: number, d: number, z0: number, z1: number) {
  const brg = (Math.atan2(q[0] - p[0], q[1] - p[1]) * 180) / Math.PI;
  for (let i = 0; i < n; i++) {
    const t = n === 1 ? 0.5 : i / (n - 1);
    b.frame(p[0] + (q[0] - p[0]) * t, p[1] + (q[1] - p[1]) * t, 0, brg, () => b.box(0, 0, z0, d, w, z1 - z0));
  }
}

// =================================================================== UC BERKELEY

const UCB_SRC = 'https://npgallery.nps.gov/AssetDetail/NRIS/64000062';
const GRANITE = '#DDD8CC';
const GRANITE_SH = '#C9C3B6';
const UC_TILE = '#B4583F';

// ------------------------------------------------------------ Sather Tower (the Campanile)
// OSM footprint 10.4 m square, faces 74.7° / 164.7° (campus grid). Wikipedia: 307 ft
// (94 m), observation deck (belfry) 200 ft (61 m). Belfry arcades, cornice, corner
// pinnacles and the octagonal granite spire from the reference photo.
const CAMPANILE: V2 = [-122.257832, 37.87206];
const satherTower: Landmark = {
  id: 'sather_tower',
  name: 'Sather Tower (the Campanile)',
  kind: 'tower',
  built: [1913.0, 1914.9],
  end: 9999,
  anchor: CAMPANILE,
  build: b => {
    b.frame(0, 0, 0, 74.7, () => {
      const W = 10.4;
      // granite shaft with a slightly wider plinth
      b.color(GRANITE_SH).box(0, 0, -3, W + 0.8, W + 0.8, 5);
      b.color(GRANITE).box(0, 0, 2, W, W, 57.5);
      b.color(GRANITE_SH).box(0, 0, 59.5, W + 0.5, W + 0.5, 1.2); // string course / balcony
      // clock faces (four, ~5.2 m dials) below the belfry
      b.color('#B9B3A5');
      for (const [nx, ny] of [[1, 0], [-1, 0], [0, 1], [0, -1]] as V2[]) vdisc(b, (nx * W) / 2 + nx * 0.06, (ny * W) / 2 + ny * 0.06, 53.5, 2.6, nx, ny, 16);
      // belfry: three open arches per side between corner piers (dark core reads as the openings)
      b.color('#4B4F52').box(0, 0, 60.7, W - 1.6, W - 1.6, 8.3);
      b.color(GRANITE);
      for (const sx of [-1, 1]) for (const sy of [-1, 1]) b.box((sx * (W - 2.2)) / 2, (sy * (W - 2.2)) / 2, 60.7, 2.2, 2.2, 8.3);
      for (const [nx, ny] of [[1, 0], [-1, 0], [0, 1], [0, -1]] as V2[]) {
        // two slender mullion piers on each face
        for (const t of [-1.3, 1.3]) {
          const x = nx !== 0 ? (nx * (W - 0.8)) / 2 : t;
          const y = ny !== 0 ? (ny * (W - 0.8)) / 2 : t;
          b.box(x, y, 60.7, 0.8, 0.8, 8.3);
        }
      }
      b.color(GRANITE_SH).box(0, 0, 69, W + 0.9, W + 0.9, 1.6); // cornice
      b.color(GRANITE).box(0, 0, 70.6, W, W, 2.0); // balustraded attic
      // corner pinnacles
      for (const sx of [-1, 1]) for (const sy of [-1, 1]) b.pyramid(rect((sx * (W - 1.1)) / 2, (sy * (W - 1.1)) / 2, 1.1, 1.1), 72.6, [(sx * (W - 1.1)) / 2, (sy * (W - 1.1)) / 2, 77.2]);
      // octagonal spire (OSM part 6.9 m across) with small gabled lucarnes at its foot
      const oct = ngon(0, 0, 3.6, 8);
      b.color('#E8E5DD').prism(oct, 72.6, 74.6, {top: false});
      b.pyramid(oct, 74.6, [0, 0, 91.6]);
      for (const [nx, ny] of [[1, 0], [-1, 0], [0, 1], [0, -1]] as V2[]) {
        b.frame(nx * 3.2, ny * 3.2, 0, (Math.atan2(nx, ny) * 180) / Math.PI, () => {
          b.box(0, 0, 74.6, 1.8, 1.0, 1.6);
          b.gable(0, 0, 1.8, 1.0, 76.2, 1.2, true);
        });
      }
      b.color('#5E6A60').cylinder(0, 0, 0.45, 91.6, 93.0, 6).frustum(0, 0, 0.3, 0.05, 93.0, 93.6, 6, false); // lantern + finial
    });
  },
  replaces: [rotRect(0, 0, 13, 13, 74.7)],
  facts: {
    Construction: '1913 – 1914 (completed 1914; opened to visitors 1916)',
    Height: '307 ft (94 m); belfry / observation deck at 200 ft (61 m)',
    Architect: 'John Galen Howard (after St Mark’s Campanile, Venice)',
    Carillon: '61 bells (12-bell chime 1917; 48 in 1979; 61 in 1983)',
    Model: 'shaft 10.4 m square from OSM; stage heights between the deck (61 m) and the top (94 m) estimated from photos'
  },
  sources: [WIKI + 'Sather_Tower', UCB_SRC]
};

// ------------------------------------------------------------ Sather Gate
// Wikipedia coordinates 37°52′12.78″N 122°15′34.13″W; the gate spans the walk at the
// south end of Sather Road (campus grid 73.6°). Granite pylons ≈1.8 m square, 6.2 m,
// bronze arch ≈9.6 m span to ≈8.7 m at the crest, bronze grille side gates: all
// scaled from the HABS/LoC photograph (pylon width assumed 1.8 m).
const satherGate: Landmark = {
  id: 'sather_gate',
  name: 'Sather Gate',
  kind: 'monument',
  built: [1909.6, 1910.4],
  end: 9999,
  anchor: [-122.259481, 37.870218],
  build: b => {
    const bronze = '#5E8F7E';
    b.frame(0, 0, 0, 343.6, () => {
      // +x = 73.6° along the gate line, +y = up Sather Road (north)
      for (const sx of [-1, 1]) {
        const px = sx * 5.7;
        b.color(GRANITE_SH).box(px, 0, -0.5, 2.1, 2.1, 1.0);
        b.color(GRANITE).box(px, 0, 0.5, 1.8, 1.8, 5.7);
        b.color(GRANITE_SH).box(px, 0, 6.2, 2.0, 2.0, 0.35);
        b.color('#4F6B62').cylinder(px, 0, 0.12, 6.55, 7.0, 6);
        b.color('#C9D2CC').dome(px, 0, 0.5, 7.0, 0.7, 8, 2); // lantern globe
        // side grille gates and the outer pylons
        b.color(bronze).box(sx * 8.4, 0, 0, 3.4, 0.35, 4.9);
        b.color('#3F5E54').box(sx * 8.4, 0, 0, 2.6, 0.2, 4.4);
        b.color(GRANITE).box(sx * 10.6, 0, -0.5, 1.0, 1.0, 6.3);
        b.color('#B9B5AC').box(sx * 9.7, 2.5, 0, 0.5, 5.5, 1.1); // bridge balustrade toward Strawberry Creek
      }
      // bronze arch (span 9.6 m between the pylons), segments of a semicircle
      b.color(bronze);
      const n = 10;
      for (let i = 0; i < n; i++) {
        const a0 = Math.PI - (Math.PI * i) / n;
        const a1 = Math.PI - (Math.PI * (i + 1)) / n;
        const P = (a: number): V3 => [Math.cos(a) * 4.5, 0, 4.6 + Math.sin(a) * 2.9];
        b.beam(P(a0), P(a1), 0.7, 0.9);
      }
      b.box(-4.5, 0, 0, 0.6, 0.6, 4.6).box(4.5, 0, 0, 0.6, 0.6, 4.6);
      b.color('#6E9C8A').dome(0, 0, 0.9, 7.4, 1.3, 8, 2); // crest medallion
    });
  },
  facts: {
    Completed: '1910 (John Galen Howard; built by Giovanni Meneghetti)',
    Panels: 'eight bas-reliefs by Earl Cummings (four men, four women; removed 1910, reinstalled 1977–79)',
    Restored: 'Oct 2008 – Apr 2009 (bronze and steel work)',
    Model: 'proportions scaled from the LoC photograph (pylon width assumed 1.8 m); construction months estimated'
  },
  sources: [WIKI + 'Sather_Gate', UCB_SRC]
};

// ------------------------------------------------------------ Hearst Greek Theatre
// OSM outline: bowl of radius ≈44 m around the orchestra (7.5, −2.5) in a 141.5° frame,
// opening SW to the stage. Stage 127 × 28 ft, upstage 170 ft, colonnade 35 ft above the
// stage, stage 6′5″ above the orchestra (Cal Performances tech sheet); 19 rows of
// concrete benches (NRHP). Bowl heights follow the terrain grid (rises ≈10 m to the rim).
const GREEK: V2 = [-122.254326, 37.87365];
const greekTheatre: Landmark = {
  id: 'hearst_greek_theatre',
  name: 'Hearst Greek Theatre',
  kind: 'stadium',
  built: [1903.05, 1903.73],
  end: 9999,
  anchor: GREEK,
  build: b => {
    const conc = '#C9C4B6';
    const seat = '#B5B0A3';
    b.frame(0, 0, 0, 141.5, () => {
      // seating bowl: semicircle opening toward +x (the stage), centre = orchestra centre
      const arc = (r: number) => ellArc(0, 0, r, r, Math.PI / 2, (3 * Math.PI) / 2, 24);
      b.color('#D8D3C6').cap(arc(11.5), -0.4); // orchestra floor
      bowl(b, arc(11.5), arc(23), 0.6, 3.6, seat, conc, -1.5);
      b.color(conc).ribbon(arc(23).map(p => [p[0], p[1], 3.6] as V3), arc(24.5).map(p => [p[0], p[1], 3.8] as V3)); // diazoma walk
      bowl(b, arc(24.5), arc(33), 3.8, 6.8, seat, conc, 2);
      b.color('#7FA05E').ribbon(arc(33).map(p => [p[0], p[1], 6.8] as V3), arc(44).map(p => [p[0], p[1], 10.0] as V3)); // grassy mound
      // stage: 38.7 × 8.5 m platform 2 m above the orchestra, front at x = 4.3
      b.color(conc).box(8.6, -3.5, -2.5, 8.6, 40.4, 4.3);
      // scaenae frons: wall with 16 engaged Doric columns, 10.7 m above the stage
      b.color('#D3CEC1').box(14.4, -3.5, -2.5, 3.0, 40.4, 15.2);
      b.color('#DCD7CA');
      rowOf(b, [12.8, -22.5], [12.8, 15.5], 16, 0.9, 0.6, 1.8, 11.4);
      b.color('#CFCABD').box(14.2, -3.5, 11.4, 3.6, 41.4, 1.4); // entablature
      b.color('#4A4E50').box(12.85, -3.5, 1.8, 0.2, 2.6, 4.2); // central doorway
      // end pylons projecting toward the audience
      for (const y of [-25.6, 18.6]) b.color('#D3CEC1').box(10.5, y, -2.5, 9.0, 4.2, 15.6);
      // backstage block (1957, Ernest Born) behind the wall
      b.color('#BDB8AC').box(21.5, -3.5, -3.5, 11.0, 49.4, 8.5);
      b.color('#8E8B84').box(21.5, -3.5, 5.0, 11.0, 49.4, 0.4);
    });
  },
  replaces: [rotRect(15, -3, 60, 60, 141.5)],
  facts: {
    Opened: 'Sep 24, 1903 (first used for Theodore Roosevelt’s commencement address, May 16, 1903)',
    Capacity: '8,500',
    Design: 'John Galen Howard (with Julia Morgan), after the theatre at Epidaurus; William Randolph Hearst paid for it',
    Stage: '127 × 28 ft; colonnade 35 ft above the stage; 19 rows of concrete benches; backstage added 1957 (Ernest Born)',
    Model: 'bowl and stage outline from OSM; row heights follow the terrain; backstage height estimated'
  },
  sources: [WIKI + 'Hearst_Greek_Theatre', 'https://calperformances.org/wp-content/uploads/venues/tech-specs/Hearst-Greek-Theatre-2324-updated.pdf', UCB_SRC]
};

// ------------------------------------------------------------ California Memorial Stadium
// NRHP nomination (2006): elliptical, about 760 × 570 ft, major axis NW–SE; facade up to
// 67 ft above adjacent grade, stands about 150 ft deep; Memorial Arch at the NW end of the
// axis with a concrete scoreboard ~50 ft wide rising 30+ ft above the rim, a matching one at
// the SE end; west half on a concrete frame behind a Roman facade, east half on the earth
// bank (no facade). OSM outline 235 × 179 m (axis 136.6°), field opening 80 × 139 m. Field
// at ≈125 m (Wikipedia), rim at Stadium Rim Way ≈470 ft (143 m) → rim ≈ +19 m.
const MEMORIAL: V2 = [-122.250743, 37.870995];
const MS_BRG = 136.6;
function memorialBowl(b: MeshBuilder, renovated: boolean) {
  const n = 64;
  const E = (ax: number, ay: number) => ellArc(0, 0, ax, ay, 0, Math.PI * 2, n);
  const inner = E(41, 69.5);
  const mid = E(64, 92);
  const outer = E(86, 114);
  const facade = E(89.5, 117.5);
  // field (lowered 4 ft in 2012) inside the low field wall
  const fz = renovated ? 0.3 : 0.5;
  b.color('#5E9445').cap(inner, fz);
  b.color('#6FA552').cap(rect(0, 0, 48.8, 91.4), fz + 0.1);
  // end zones (navy and gold since 2012)
  b.color(renovated ? '#1F3765' : '#5F9A49').cap(rect(0, -50.3, 48.8, 9.1), fz + 0.15).cap(rect(0, 50.3, 48.8, 9.1), fz + 0.15);
  b.color('#A9A49A').wallProfile(inner, -0.5, 2.0, true);
  // stands: lower rows to the vomitory cross-aisle, upper rows to the rim (gold seats since 2012)
  const lower = renovated ? '#D9AE45' : '#ADA89C';
  const upper = renovated ? '#CFA43C' : '#A39E92';
  b.color(lower).ribbon(inner.map(p => [p[0], p[1], 2.0] as V3), mid.map(p => [p[0], p[1], 10.2] as V3));
  b.color(upper).ribbon(mid.map(p => [p[0], p[1], 10.2] as V3), outer.map(p => [p[0], p[1], 19.0] as V3));
  // 28 vomitories half-way up (dark portals)
  b.color('#3E3B36');
  for (let i = 0; i < 28; i++) {
    const a = ((i + 0.5) / 28) * Math.PI * 2;
    const x = Math.cos(a) * 64;
    const y = Math.sin(a) * 92;
    b.frame(x, y, 0, (Math.atan2(Math.cos(a) / 64, Math.sin(a) / 92) * 180) / Math.PI, () => b.box(0, 0, 10.0, 2.6, 2.4, 1.6));
  }
  // promenade at the rim and the west facade (Roman arcade on a rusticated base)
  b.color('#BDB7A9').ribbon(outer.map(p => [p[0], p[1], 19.0] as V3), facade.map(p => [p[0], p[1], 19.0] as V3), true);
  // west half: indices from 3n/4 .. n .. n/4 (angles −90°..+90°)
  const westPath: V2[] = [];
  for (let k = -n / 4; k <= n / 4; k++) westPath.push(facade[(k + n) % n]);
  b.color('#D6CFBE').wallProfile(westPath, -8, 19.0).wallProfile(westPath.map(p => [p[0] * 0.995, p[1] * 0.995] as V2), -8, 19.0);
  b.color('#CFC8B6').wallProfile(westPath.map(p => [p[0] * 1.004, p[1] * 1.004] as V2), 19.0, 20.3); // parapet
  // arched openings (dark) along the facade in groups, emphasised single bays with balconies
  b.color('#5C5850');
  for (let k = 0; k < westPath.length - 1; k++) {
    const p = westPath[k];
    const q = westPath[k + 1];
    const m: V2 = [(p[0] + q[0]) / 2 * 1.006, (p[1] + q[1]) / 2 * 1.006];
    const brg = (Math.atan2(q[0] - p[0], q[1] - p[1]) * 180) / Math.PI;
    b.frame(m[0], m[1], 0, brg, () => b.box(0, 0, 7.5, 0.15, 4.0, 8.0));
  }
  // east half: low retaining edge only (the seats meet the hillside / Stadium Rim Way)
  const eastPath: V2[] = [];
  for (let k = n / 4; k <= (3 * n) / 4; k++) eastPath.push(facade[k % n]);
  b.color('#A9A397').wallProfile(eastPath, 14, 19.6);
  // Memorial Arch + scoreboard tablet (NW end, −y) and the south scoreboard (SE end, +y)
  for (const sy of [-1, 1]) {
    const y = sy * 117.5;
    b.color('#D9D2C1').box(0, y + sy * 1.5, -6, 15.2, 5, 25.5);
    b.color('#CBC4B2').box(0, y + sy * 1.2, 25.5, 16.4, 4.4, 1.0); // cornice
    b.color('#5C5850').box(0, y + sy * 4.05, sy < 0 ? -1 : 0, 7.0, 0.2, sy < 0 ? 15 : 4); // Memorial Arch opening / gate
    // post-1950 sheet-metal display boards peeking over the tablets (blue)
    b.color('#3A5C8C').box(0, y - sy * 1.0, 26.5, 18, 1.2, renovated ? 9 : 6);
  }
  // 15 pairs of flagpoles around the rim
  b.color('#8A7A60');
  for (let i = 0; i < 15; i++) {
    const a = (i / 15) * Math.PI * 2 + 0.1;
    for (const d of [-0.05, 0.05]) {
      const x = Math.cos(a + d) * 89;
      const y = Math.sin(a + d) * 117;
      b.beam([x, y, 19], [x, y, 31], 0.25);
    }
  }
}
const memorialStadium1923: Landmark = {
  id: 'memorial_stadium_berkeley_1923',
  name: 'California Memorial Stadium (1923)',
  kind: 'stadium',
  built: [1922.9, 1923.9],
  end: 2010.95,
  anchor: MEMORIAL,
  build: b => b.frame(0, 0, 0, MS_BRG, () => memorialBowl(b, false)),
  facts: {
    Construction: 'site clearing Dec 1922, groundbreaking Jan 1923; opened Nov 24, 1923 (Big Game)',
    Capacity: '≈75,000 (temporary bleachers to ≈85,000; record 83,000 in 1947)',
    Design: 'John Galen Howard; Roman-coliseum west half on a concrete frame, east half on an earthen bank, built across the Hayward Fault in two halves',
    'Press box': 'a lofty press box (1968) stood on the west rim until 2002 (not modelled)',
    Model: 'outline from OSM (235 × 179 m); rim ≈ +19 m above the field (Stadium Rim Way ≈470 ft, field ≈410 ft); row profile and arch rhythm estimated'
  },
  sources: [WIKI + 'California_Memorial_Stadium', 'https://npgallery.nps.gov/GetAsset/ffa8730b-60f5-430b-9898-bedc4539cfb5']
};
const memorialStadium2012: Landmark = {
  id: 'memorial_stadium_berkeley',
  name: 'California Memorial Stadium',
  kind: 'stadium',
  built: [2010.95, 2012.67],
  end: 9999,
  anchor: MEMORIAL,
  build: b =>
    b.frame(0, 0, 0, MS_BRG, () => {
      memorialBowl(b, true);
      // 2012 press box on the west rim (OSM part 123 × 25 m, x 63–90), glazed, three levels
      const pb: V2[] = [
        [81.5, 57.8],
        [65.5, 53.2],
        [71.8, 27.9],
        [72.3, 6.9],
        [69.5, -37.6],
        [62.6, -59.7],
        [78.9, -65.0],
        [84.6, -48.8],
        [88.5, -28.2],
        [89.8, 4.4],
        [85.2, 47.5]
      ];
      // cantilevered over the upper rows: dark glazed boxes under a white roof slab
      b.color('#46525C').prism(pb, 14.5, 25.5);
      b.color('#F2F1EC').prism(scaleRing(pb, 1.02), 25.5, 27.0);
      b.color('#DADDDF').prism(scaleRing(pb, 0.85), 27.0, 28.4);
      // the netted fence frame behind the press box
      b.color('#6B6F72');
      for (let y = -55; y <= 50; y += 15) b.beam([88, y, 19], [88, y, 36], 0.5);
    }),
  replaces: [rotRing(ellipse(0, 0, 92, 120, 32), MS_BRG)],
  facts: {
    Renovation: 'June 2010 – Sep 1, 2012: west side demolished and rebuilt behind the 1923 outer wall (HNTB / STUDIOS), new press box and club levels, field lowered 4 ft, fault-rupture blocks in the end zones',
    Opened: 'Nov 24, 1923; reopened Sep 1, 2012',
    Capacity: '≈63,000',
    Model: 'press box outline from OSM; its height (≈8 m above the rim, cantilevered over the upper rows) estimated from photos; gold seats and navy end zones as photographed in 2024'
  },
  sources: [WIKI + 'California_Memorial_Stadium', 'https://npgallery.nps.gov/GetAsset/ffa8730b-60f5-430b-9898-bedc4539cfb5']
};

// ------------------------------------------------------------ Doe Memorial Library
// UC Library Handbook 1918–19: outside dimensions 262 × 224 ft (OSM 80 × 69 m), California
// granite with a red mission-tile roof, steel frame; north reading room 210 × 53 ft. Built in
// two stages: 1907–1911 (north half, opened Jun 26, 1911) and 1914–1917 (south half, NRHP).
// Frame 73.6°: +y ENE (to the Campanile), +x SSE; the north (Memorial Glade) front is at
// x = −39.3. North facade from the 2018 photo: rusticated base 3.9 m, Corinthian colonnade
// (16 columns) to 14.5 m, entablature to 17.5 m, tile roof with copper skylights to ≈20.6 m.
const DOE: V2 = [-122.259497, 37.87219];
function doeRoofs(b: MeshBuilder, x0: number, x1: number, y0: number, y1: number) {
  const sx = x1 - x0;
  const sy = y1 - y0;
  b.color(GRANITE_SH).box((x0 + x1) / 2, (y0 + y1) / 2, 17.5, sx + 0.8, sy + 0.8, 0.5);
  b.color(UC_TILE).hip((x0 + x1) / 2, (y0 + y1) / 2, sx + 0.4, sy + 0.4, 18.0, 3.0);
}
const doeNorth: Landmark = {
  id: 'doe_library_1911',
  name: 'Doe Memorial Library (north half)',
  kind: 'building',
  built: [1907.5, 1911.45],
  end: 9999,
  anchor: DOE,
  build: b =>
    b.frame(0, 0, 0, 73.6, () => {
      // north wing with the reading room (full 69 m width)
      b.color(GRANITE_SH).box(-29, 0, -2, 20.6, 69.2, 5.9);
      b.color(GRANITE).box(-29, 0, 3.9, 19.6, 68.2, 13.6);
      doeRoofs(b, -39.3, -18.7, -34.6, 34.6);
      // copper skylight ridges
      b.color('#6F9C8B');
      for (const y of [-21, 0, 21]) b.box(-29, y, 20.4, 5, 12, 0.9);
      // colonnade of 16 Corinthian columns in front of the reading-room windows
      b.color('#565C60').box(-39.0, 0, 5, 0.3, 62, 8.5); // window wall behind the columns
      b.color('#EFECE4');
      rowOf(b, [-39.8, -32.6], [-39.8, 32.6], 16, 1.2, 1.2, 3.9, 14.5);
      b.color(GRANITE).box(-39.6, 0, 14.5, 1.6, 69.2, 3.0); // entablature
      // entrance terrace and stairs toward Memorial Glade
      b.color('#D3CEC2').box(-44.5, 0, -1.5, 9, 30, 2.3);
      b.color('#5B5F5E').box(-39.45, 0, 0.5, 0.3, 3.5, 4.2); // bronze doors
      // the first unit continues south to just past the middle of the plan
      b.color(GRANITE).box(-6, -16, -2, 25.4, 30, 19.5).box(-6, 16, -2, 25.4, 30, 19.5);
      doeRoofs(b, -18.7, 6.7, -31, -1);
      doeRoofs(b, -18.7, 6.7, 1, 31);
    }),
  replaces: [rotRect(0, 0, 84, 73, 73.6), rotRing(rect(-40, 57, 40, 48), 73.6)],
  facts: {
    Construction: '1907 – 1911 (north half; opened Jun 26, 1911); completed 1914 – 1917',
    Size: '262 × 224 ft; reading room 210 × 53 ft for 500 readers',
    Design: 'John Galen Howard, after Émile Bénard’s 1899 competition plan; California granite, red mission-tile roof, steel frame',
    Model: 'plan from OSM; north-front heights scaled from the 2018 photograph (16 columns, roof ≈20.6 m); split line between the 1911 and 1917 halves estimated'
  },
  sources: [WIKI + 'Doe_Memorial_Library', 'https://gutenberg.org/ebooks/51874', UCB_SRC]
};
const doeSouth: Landmark = {
  id: 'doe_library_1917',
  name: 'Doe Memorial Library (south half)',
  kind: 'building',
  built: [1914.5, 1917.6],
  end: 9999,
  anchor: DOE,
  build: b =>
    b.frame(0, 0, 0, 73.6, () => {
      // south half around two light courts; skylit central hall
      const ring = rect(23.85, 0, 34.3, 62);
      const courts = [rect(24, -15, 14, 16), rect(24, 15, 14, 16)];
      b.color(GRANITE).prism(ring, -2, 17.5, {holes: courts});
      b.color(GRANITE_SH).cap(ring, 17.5, courts);
      b.color(UC_TILE).hip(23.85, -23.5, 34.3, 15, 17.5, 3.0).hip(23.85, 23.5, 34.3, 15, 17.5, 3.0).hip(37.5, 0, 7, 32, 17.5, 2.6);
      b.color('#A9C1C6').box(18, 0, 17.5, 10, 16, 1.6);
    }),
  facts: {
    Completion: '1914 – 1917, funded by a state bond issue',
    Model: 'courts and roof layout estimated (the south half is hidden from most viewpoints)'
  },
  sources: [WIKI + 'Doe_Memorial_Library', 'https://gutenberg.org/ebooks/51874']
};

// =================================================================== DOWNTOWN OAKLAND

// ------------------------------------------------------------ Oakland City Hall
// "Wedding cake" in three tiers (Wikipedia): a 3-storey base, a 10-storey office tower and a
// 2-storey podium with the clock tower; 320 ft (98 m); white granite and terra cotta.
// OSM 3D parts in a 26.3° frame: base 49 × 58 m (13–16 m wings; the entrance portico faces
// Frank H. Ogawa Plaza, +x), tower 24.2 × 39 m (82 m), clock stage 13 × 20 m (90 m),
// cupola 5–7 m (98 m). Intermediate stage heights from the 2009 photo.
const cityHallOakland: Landmark = {
  id: 'oakland_city_hall',
  name: 'Oakland City Hall',
  kind: 'tower',
  built: [1910.6, 1914.5],
  end: 9999,
  anchor: [-122.272552, 37.805309],
  build: b => {
    const stone = '#E7E3D7';
    const shade = '#D4CFC1';
    b.frame(0, 0, 0, 26.3, () => {
      const base: V2[] = [
        [19.6, 28.2],
        [-20.7, 28.1],
        [-21.3, 12.1],
        [-29.1, 12.2],
        [-29.3, -11.4],
        [-21.9, -11.4],
        [-22.0, -29.7],
        [19.3, -29.7],
        [20.0, 9.1]
      ];
      b.color(shade).prism(base, -1.5, 1.0);
      b.color(stone).prism(base, 1.0, 14.5);
      b.color(shade).prism(scaleRing(base, 1.015), 14.5, 15.6); // cornice with the eagle frieze
      // entrance portico on the plaza front: four columns in antis, attic with eagles
      b.color(stone).box(15.6, -1, 1, 9.2, 20.2, 16.4);
      b.color('#565A5C').box(20.2, -1, 1.5, 0.3, 9, 9.5);
      b.color('#F0EDE5');
      rowOf(b, [20.6, -4.6], [20.6, 2.6], 4, 1.3, 1.3, 1.0, 12.5);
      // transitional storey with the great arched window, then the office tower
      const tower: V2[] = [
        [-12.5, 12.2],
        [-12.5, -11.3],
        [-12.0, -18.2],
        [11.7, -17.7],
        [11.0, 21.0],
        [-13.1, 20.5]
      ];
      b.color(stone).prism(tower, 15.6, 22.5);
      b.color('#5E6468').box(11.45, 1.4, 16.5, 0.25, 7.5, 5.2); // arched window over the portico
      b.color(stone).prism(scaleRing(tower, 0.985), 22.5, 66.5);
      // vertical window strips on the long faces
      b.color('#9AA0A0');
      for (let y = -14; y <= 18; y += 4) b.box(11.5, y, 25, 0.12, 1.6, 38).box(-12.9, y, 25, 0.12, 1.6, 38);
      for (let x = -9; x <= 9; x += 4.5) b.box(x, 21.05, 25, 1.6, 0.12, 38).box(x, -18.05, 25, 1.6, 0.12, 38);
      b.color(shade).prism(scaleRing(tower, 1.04), 66.5, 69.0); // heavy cornice
      b.color(stone).prism(scaleRing(tower, 0.93), 69.0, 75.5); // two-storey podium
      // clock tower stages (OSM 13.2 × 20 m to 90 m), cupola and dome to 98 m
      b.color(stone).box(-0.1, 0, 75.5, 13.2, 20.0, 3.5);
      b.color(stone).box(-0.1, 0, 79, 9.0, 9.0, 7.5);
      b.color('#3F4446');
      for (const [nx, ny] of [[1, 0], [-1, 0], [0, 1], [0, -1]] as V2[]) vdisc(b, nx * 4.56 - 0.1, ny * 4.56, 83.5, 1.7, nx, ny, 12);
      b.color(shade).box(-0.1, 0, 86.5, 10, 10, 1.0);
      b.color(stone).box(-0.1, 0, 87.5, 6.2, 6.2, 5.0);
      b.color(shade).cylinder(-0.1, 0, 2.7, 92.5, 93.7, 12);
      b.color('#DCD7CA').dome(-0.1, 0, 2.6, 93.7, 2.5, 12, 3);
      b.color('#BFB9AA').cylinder(-0.1, 0, 0.5, 96.2, 98.0, 6);
    });
  },
  replaces: [rotRect(-4.6, -0.7, 53, 61, 26.3)],
  facts: {
    Construction: '1910 – 1914 (Palmer & Hornbostel, competition of 1910)',
    Height: '320 ft (98 m) — the first high-rise city hall in the United States',
    Tiers: '3-storey base, 10-storey office tower, 2-storey podium with the clock tower; white granite and terra cotta',
    'After 1989': 'closed by the Loma Prieta earthquake; base-isolated on rubber bearings and reopened 1995',
    Model: 'plan and tier heights from the OSM 3D parts (13/16, 82, 90, 98 m); cornice, podium and cupola heights from the photo'
  },
  sources: [WIKI + 'Oakland_City_Hall']
};

// ------------------------------------------------------------ Fox Oakland Theatre
// OSM footprint 77.5 × 66 m in an 11° frame (+y north along Telegraph Ave, +x east); the
// Telegraph front is x ≈ 39 with chamfered corners. From the 2005 and 2018 photos: a
// three-storey crenellated office wing along the street (the Fox-Oakland Office Building,
// south; now the Oakland School for the Arts), the entrance pavilion left of centre with a
// tiled arch, two minaret towers and the tile-patterned dome, the vertical FOX OAKLAND blade
// sign and marquee; the auditorium block behind. No published heights: all estimated.
const foxOakland: Landmark = {
  id: 'fox_oakland_theatre',
  name: 'Fox Oakland Theatre',
  kind: 'building',
  built: [1926.9, 1928.82],
  end: 9999,
  anchor: [-122.270541, 37.808068],
  build: b => {
    const tc = '#D8C79C'; // glazed terra cotta
    const brick = '#B49A6A';
    b.frame(0, 0, 0, 11, () => {
      // auditorium and stage house behind the street wing
      const aud: V2[] = [
        [26, 33.0],
        [-37.9, 33.1],
        [-38.3, -32.9],
        [26, -33.2]
      ];
      b.color('#CDBF9F').prism(aud, -1, 21);
      b.color('#BDAE8C').box(-32, 0, 21, 12.5, 44, 5);
      // street wing (x 26 … 39.4) with crenellated parapet
      const wing: V2[] = [
        [26, 33.0],
        [26, -33.2],
        [28.9, -33.4],
        [39.1, -23.8],
        [39.4, 24.0],
        [30.6, 33.0]
      ];
      b.color(brick).prism(wing, -1, 15.5);
      b.color(tc).box(38.6, 4.5, 4.5, 1.6, 38, 1.0).box(38.6, -26, 4.5, 1.6, 6, 1.0); // storefront cornice
      b.color(tc);
      for (let y = -30; y <= 31; y += 2.4) if (y < -19.5 || y > -3.5) b.box(37.5, y, 15.5, 2.0, 1.2, 1.3);
      for (const y of [-30, -21, -2, 8, 18, 30]) b.cylinder(38, y, 0.5, 15.5, 18.2, 6); // pinnacles
      // entrance pavilion (y −19 … −4) with the great tiled arch
      b.color(tc).box(32.5, -11.5, -1, 14, 15, 25);
      b.color('#3E5F8C').box(39.55, -11.5, 6.5, 0.3, 6.4, 13); // blue-tiled arch recess
      b.color('#C9A04E').box(39.6, -11.5, 18.5, 0.3, 7.2, 1.2);
      // minaret towers flanking the arch
      for (const y of [-17.5, -5.5]) {
        b.color(tc).box(37.2, y, -1, 3.2, 3.2, 28);
        b.color('#C9A04E').dome(37.2, y, 1.7, 27, 2.2, 8, 2);
      }
      // drum and tile-patterned dome
      const oct = ngon(30.5, -11.5, 5.2, 8);
      b.color(tc).prism(oct, 24, 30.5);
      b.color('#B8A774').loft([oct, ngon(30.5, -11.5, 4.6, 8), ngon(30.5, -11.5, 2.4, 8)], [30.5, 34.5, 37.5], {top: true});
      b.color('#3E5F8C').cylinder(30.5, -11.5, 0.5, 37.5, 39.5, 6);
      // marquee and the vertical FOX OAKLAND blade sign
      b.color('#2C2A2E').box(41.5, -11.5, 4.3, 3.6, 16, 2.6);
      b.color('#E4E0D4').box(43.35, -11.5, 4.5, 0.1, 15, 2.2);
      b.color('#B8352B').box(42.2, -4.6, 7.2, 2.0, 0.6, 19.5);
      b.color('#D8B74A').box(42.2, -4.6, 26.7, 1.4, 0.5, 1.8);
    });
  },
  replaces: [rotRect(0, 0, 82, 72, 11)],
  facts: {
    Opened: 'Oct 27, 1928 as “The Oakland” (West Coast Theatres; Fox from Mar 1929); about two years in construction',
    Seats: '3,200 originally; 2,800 today',
    Design: 'Weeks and Day for Maury L. Diggs; Moorish / Indian-temple styled terra cotta with a tiled dome',
    History: 'closed Sep 14, 1965; bought by the city 1996; restored ($75 M) and reopened Feb 5, 2009',
    Model: OSM_NOTE + '; wing, pavilion, dome and sign heights estimated from photos (no published dimensions); construction start estimated'
  },
  sources: [WIKI + 'Fox_Oakland_Theatre']
};

// ------------------------------------------------------------ Paramount Theatre
// OSM outline and the 33 m part in a 282.7° frame (+y west to the Broadway front, +x
// north-north-east along Broadway). The Broadway front: a tile pylon with Gerald
// Fitzgerald's mosaic of puppeteer figures (gold, maroon tile piers) split by the
// projecting PARAMOUNT sign column, marquee below (1975 HABS-style photo, 2005 photo);
// beige auditorium block behind, stage house at the east end.
const paramountOakland: Landmark = {
  id: 'paramount_theatre_oakland',
  name: 'Paramount Theatre',
  kind: 'building',
  built: [1930.4, 1931.96],
  end: 9999,
  anchor: [-122.268596, 37.809855],
  build: b => {
    b.frame(0, 0, 0, 282.7, () => {
      const main: V2[] = [
        [-24.6, -15.8],
        [-15.4, -18.2],
        [-0.7, -23.4],
        [14.2, -22.6],
        [17.2, 6.3],
        [17.2, 22.6],
        [20.0, 32.5],
        [-14.9, 32.5],
        [-18.5, 21.8],
        [-14.4, 20.8],
        [-21.3, 0.9]
      ];
      b.color('#D7CAAE').prism(main, -1, 25);
      // stage house (east end)
      b.color('#CDBF9F').prism(
        [
          [-15.4, -18.2],
          [-23.0, -47.8],
          [-8.5, -51.6],
          [-0.7, -23.4]
        ],
        -1,
        29
      );
      // one-storey shops on the corner (OSM parts without height)
      b.color('#C9C2B5')
        .prism(
          [
            [14.4, -21.9],
            [30.1, -21.3],
            [30.1, -8.3],
            [17.7, -6.4],
            [17.2, 6.3]
          ],
          -1,
          6
        )
        .prism(
          [
            [17.6, 15.1],
            [29.3, 15.6],
            [29.7, 35.7],
            [20.0, 35.7],
            [17.2, 22.6]
          ],
          -1,
          6
        );
      // Broadway pylon: maroon tile piers, mosaic panels, projecting sign
      b.color('#7A2E2A').box(2.5, 34.2, -1, 17, 3.4, 34);
      b.color('#C9A548').box(-2.4, 36.0, 8.5, 5.6, 0.3, 24.5).box(7.6, 36.0, 8.5, 5.6, 0.3, 24.5);
      b.color('#C7473B').box(-2.4, 36.15, 12, 4.6, 0.12, 14).box(7.6, 36.15, 12, 4.6, 0.12, 14); // the dancing figures
      b.color('#D5D8DA').box(2.6, 37.0, 6, 2.6, 2.4, 31.5); // sign column, taller than the pylon
      b.color('#9E2B26').box(2.6, 38.25, 9, 1.6, 0.1, 25);
      // marquee
      b.color('#2B2827').box(2.5, 38.8, 4.2, 20, 4.6, 3.0);
      b.color('#EDE9DE').box(2.5, 41.15, 4.5, 19, 0.1, 2.4);
    });
  },
  replaces: [rotRect(2, -8, 62, 92, 282.7)],
  facts: {
    Opened: 'Dec 16, 1931 (premiere of The False Madonna); closed Jun 1932 – 1933',
    Design: 'Timothy Pflueger, Art Deco; facade mosaic by Gerald Fitzgerald; 3,476 seats (3,040 today)',
    Restored: 'bought by the Oakland Symphony 1972, restored and reopened 1973; National Historic Landmark 1977',
    Height: '≈33 m (OSM)',
    Model: OSM_NOTE + '; pylon, sign and marquee proportions from photos; auditorium height and construction start estimated'
  },
  sources: [WIKI + 'Paramount_Theatre_(Oakland,_California)']
};

// ------------------------------------------------------------ Tribune Tower
// 13th & Franklin. OSM 3D parts in a 26.5° frame: the six-storey 1906 base (D. Franklin
// Oliver, Breuner furniture store; the Tribune moved in 1918) fills the 28 × 31 m lot; the
// 1923 tower (Edward T. Foulkes) rises on the west corner (11.8 × 16.6 m) to a 305 ft
// (93 m) roof (Wikipedia, OSM); an 8-storey annex beside it. From the photo: buff brick
// with cream terra cotta, the corbelled 20th-floor gallery carrying TRIBUNE on every face,
// clock faces in the attic, a green copper mansard with oculus dormers and an 86 ft mast.
const TRIB: V2 = [-122.270827, 37.803054];
const tribuneBase: Landmark = {
  id: 'tribune_building_1906',
  name: 'Tribune Tower base (Breuner Building, 1906)',
  kind: 'building',
  built: [1905.3, 1906.3],
  end: 9999,
  anchor: TRIB,
  build: b =>
    b.frame(0, 0, 0, 26.5, () => {
      const ring: V2[] = [
        [-2.3, -10.8],
        [-14.0, -10.8],
        [-14.0, -15.7],
        [14.1, -15.5],
        [14.0, 15.6],
        [-2.2, 15.6],
        [-2.3, -1.0]
      ];
      b.color('#C9A27E').prism(ring, -1, 22.5);
      b.color('#E6DCC6').prism(scaleRing(ring, 1.012), 22.5, 24.0);
      b.color('#E6DCC6').prism(scaleRing(ring, 1.006), 3.5, 4.6);
    }),
  replaces: [rotRect(0, 0, 31, 34, 26.5)],
  facts: {
    Completed: '1906 (D. Franklin Oliver) as the Breuner furniture store; the Oakland Tribune moved here in 1918',
    Height: 'six storeys',
    Model: OSM_NOTE + '; storey height estimated'
  },
  sources: [WIKI + 'Tribune_Tower_(Oakland)']
};
const tribuneTower: Landmark = {
  id: 'tribune_tower_oakland',
  name: 'Tribune Tower',
  kind: 'tower',
  built: [1922.4, 1923.99],
  end: 9999,
  anchor: TRIB,
  build: b =>
    b.frame(0, 0, 0, 26.5, () => {
      const brick = '#C79A76';
      const tc = '#EFE8D8';
      // 8-storey annex beside the tower
      b.color(brick).box(-8.15, -5.9, -1, 11.7, 9.8, 30.5);
      b.color(tc).box(-8.15, -5.9, 29.5, 12.1, 10.2, 1.0);
      // tower shaft 11.8 × 16.6 m
      const cx = -8.1;
      const cy = 7.3;
      b.color(brick).box(cx, cy, -1, 11.8, 16.6, 73);
      b.color(tc).box(cx, cy, 72, 13.8, 18.6, 1.4); // corbelled gallery
      b.color('#F4EFE2').box(cx, cy, 73.4, 13.6, 18.4, 2.6); // TRIBUNE letters band
      b.color('#B0362C').box(cx, cy, 74.1, 13.7, 18.5, 1.2);
      b.color(brick).box(cx, cy, 76, 11.8, 16.6, 7.5);
      b.color(tc).box(cx, cy, 83.5, 12.6, 17.4, 1.4);
      b.color(tc).box(cx, cy, 84.9, 11.2, 16.0, 2.4);
      b.color('#2E3335');
      for (const [nx, ny, h] of [[1, 0, 5.6], [-1, 0, 5.6], [0, 1, 8.0], [0, -1, 8.0]] as [number, number, number][]) vdisc(b, cx + nx * (h + 0.06), cy + ny * (h + 0.06), 86.6, 1.5, nx, ny, 12);
      // green copper mansard with oculus dormers
      b.color('#5FA38A').loft([rect(cx, cy, 10.8, 15.6), rect(cx, cy, 5.6, 10.2)], [87.3, 93.0], {top: true});
      b.color('#B9C0BC').beam([cx, cy, 93], [cx, cy, 119.2], 0.35); // 86 ft flagpole
    }),
  facts: {
    Tower: '1923 (Edward T. Foulkes), added to the 1906 base; opened by Joseph R. Knowland Jan 1, 1924',
    Height: '305 ft (93 m), 22 storeys; 86 ft flagpole; clock faces and TRIBUNE neon on all four sides',
    Later: 'damaged 1989, empty until 1995, renovated; the Tribune returned 1999–2007',
    Model: 'tower and annex outlines from the OSM 3D parts; gallery, clock and mansard heights scaled from the photo; construction start estimated'
  },
  sources: [WIKI + 'Tribune_Tower_(Oakland)']
};

// =================================================================== OAKLAND–ALAMEDA COUNTY COLISEUM COMPLEX
// Skidmore, Owings & Merrill (Myron Goldsmith); groundbreaking Apr 15, 1964.

// ------------------------------------------------------------ Oakland Arena
// OSM: a circle of radius 65.2 m. The 1996–97 renovation gutted the interior and built a new
// bowl but kept the original walls, roof and foundation (Wikipedia) — the exterior is
// unchanged, so one model covers both. Exterior from the photos: concourse podium, glass
// drum crossed by giant concrete X-braces (16 bays), thick roof ring, shallow roof.
const oaklandArena: Landmark = {
  id: 'oakland_arena',
  name: 'Oakland Arena',
  kind: 'stadium',
  built: [1964.29, 1966.86],
  end: 9999,
  anchor: [-122.202932, 37.750279],
  build: b => {
    const R = 65.2;
    b.color('#B9B4AA').cylinder(0, 0, R - 0.5, -1.5, 5, 48); // concourse podium
    b.color('#4E5A60').cylinder(0, 0, R - 3.5, 5, 21.5, 48, {top: false}); // glass drum
    b.color('#CFCBC2');
    const n = 16;
    for (let i = 0; i < n; i++) {
      const a0 = (i / n) * Math.PI * 2;
      const a1 = ((i + 1) / n) * Math.PI * 2;
      const r = R - 2.4;
      const P = (a: number, z: number): V3 => [Math.cos(a) * r, Math.sin(a) * r, z];
      b.beam(P(a0, 5), P(a1, 21.5), 1.1, 1.4);
      b.beam(P(a1, 5), P(a0, 21.5), 1.1, 1.4);
    }
    b.color('#A8A39A').cylinder(0, 0, R + 0.3, 21.5, 25.0, 48); // compression ring / fascia
    b.color('#C7C3BA').dome(0, 0, R - 1, 25.0, 4.5, 32, 3);
  },
  replaces: [circle(0, 0, 68, 24)],
  facts: {
    Opened: 'Nov 9, 1966 (Oakland–Alameda County Coliseum Arena); Golden State Warriors 1971–2019',
    Renovated: '1996–97 (HNTB): interior gutted and a new bowl built inside the original walls and roof; reopened Nov 1997 with ≈19,600 seats',
    Design: 'Skidmore, Owings & Merrill (Myron Goldsmith) — glass drum under a concrete roof ring, X-braced',
    Model: 'outline from OSM (Ø 130 m); bay count and heights (≈29 m) estimated from photos'
  },
  sources: [WIKI + 'Oakland_Arena', 'https://pcad.lib.washington.edu/building/7178']
};

// =================================================================== LAKE MERRITT

// ------------------------------------------------------------ Necklace of Lights
// 126 lampposts and 3,400 "pearly bulbs" round the lake, first lit 1925, removed 1941 for
// the wartime blackout, relit 1987 (Wikipedia). Posts spaced evenly along the TIGER 2024
// shoreline offset 4.5 m onto the shore path (≈39 m apart); bulb strings hang between them.
const MERRITT: V2 = [-122.256979, 37.804073];
const NECKLACE: V2[] = [[-521, 426], [-511, 464], [-498, 502], [-489, 540], [-483, 579], [-475, 618], [-464, 656], [-449, 692], [-418, 715], [-381, 709], [-369, 673], [-372, 633], [-375, 594], [-381, 554], [-388, 516], [-393, 476], [-396, 437], [-394, 398], [-390, 358], [-373, 323], [-337, 314], [-299, 307], [-283, 272], [-273, 234], [-250, 203], [-221, 177], [-201, 143], [-186, 106], [-161, 77], [-124, 72], [-88, 88], [-53, 105], [-20, 128], [6, 127], [15, 131], [45, 156], [56, 192], [48, 230], [61, 266], [82, 299], [107, 328], [143, 343], [182, 347], [221, 344], [261, 342], [301, 340], [340, 339], [376, 353], [406, 379], [435, 405], [464, 432], [497, 454], [536, 458], [571, 474], [599, 502], [634, 492], [655, 460], [650, 421], [637, 384], [623, 348], [608, 311], [597, 273], [585, 235], [578, 197], [565, 159], [546, 125], [528, 89], [499, 64], [462, 55], [429, 34], [391, 26], [353, 15], [322, -8], [305, -44], [289, -80], [274, -117], [256, -152], [230, -181], [211, -216], [213, -255], [219, -294], [218, -333], [210, -372], [185, -402], [154, -425], [116, -433], [77, -427], [37, -427], [-1, -434], [-38, -449], [-73, -467], [-104, -491], [-132, -519], [-157, -550], [-178, -584], [-212, -591], [-245, -570], [-280, -551], [-314, -532], [-348, -511], [-380, -487], [-397, -453], [-397, -413], [-397, -374], [-393, -335], [-390, -297], [-394, -258], [-379, -223], [-381, -192], [-360, -168], [-351, -129], [-341, -91], [-329, -53], [-318, -15], [-316, 23], [-337, 56], [-367, 82], [-400, 104], [-427, 133], [-447, 167], [-468, 201], [-488, 234], [-506, 270], [-517, 308], [-519, 347], [-520, 387]];
function necklace(b: MeshBuilder) {
  // ground under each post (the anchor is on the water, so offsets are absolute heights)
  const z = NECKLACE.map(([x, y]) => Math.max(groundDz(MERRITT, 0, x, y), 1.4));
  const H = 4.6;
  for (let i = 0; i < NECKLACE.length; i++) {
    const [x, y] = NECKLACE[i];
    b.color('#3C4743').beam([x, y, z[i]], [x, y, z[i] + H], 0.3);
    b.color('#FFF6D8').box(x, y, z[i] + H, 0.8, 0.8, 0.8);
    const [x2, y2] = NECKLACE[(i + 1) % NECKLACE.length];
    const z2 = z[(i + 1) % NECKLACE.length];
    if (Math.hypot(x2 - x, y2 - y) > 70) continue; // no string across the Glen Echo inlet gap
    const pts: V3[] = [];
    for (let k = 0; k <= 6; k++) {
      const t = k / 6;
      pts.push([x + (x2 - x) * t, y + (y2 - y) * t, z[i] + (z2 - z[i]) * t + H - 0.3 - 1.6 * 4 * t * (1 - t)]);
    }
    b.color('#FFF2C4').polyline(pts, 0.28);
  }
}
const necklace1925: Landmark = {
  id: 'lake_merritt_necklace_1925',
  name: 'Necklace of Lights, Lake Merritt (1925)',
  kind: 'monument',
  built: [1925.0, 1925.5],
  end: 1941.95,
  anchor: MERRITT,
  build: necklace,
  facts: {
    Lit: '1925 — 126 lampposts and 3,400 "pearly bulbs" strung round the lake',
    Dark: 'removed in 1941 for the World War II blackout',
    Model: 'posts spaced evenly on the TIGER shoreline (positions estimated); strings drawn thicker than real so they read at map scale; months estimated'
  },
  sources: [WIKI + 'Lake_Merritt']
};
const necklace1987: Landmark = {
  id: 'lake_merritt_necklace',
  name: 'Necklace of Lights, Lake Merritt',
  kind: 'monument',
  built: [1986.8, 1987.3],
  end: 9999,
  anchor: MERRITT,
  build: necklace,
  facts: {
    Relit: '1987, after a decade-long campaign by the Lake Merritt Breakfast Club (first lit 1925, dark 1941–87)',
    Model: 'posts spaced evenly on the TIGER shoreline (positions estimated); strings drawn thicker than real'
  },
  sources: [WIKI + 'Lake_Merritt']
};
export const EASTBAY_CHECK = [satherTower,satherGate,greekTheatre,memorialStadium1923,memorialStadium2012,doeNorth,doeSouth,cityHallOakland,foxOakland,paramountOakland,tribuneBase,tribuneTower,oaklandArena,necklace1925,necklace1987];
