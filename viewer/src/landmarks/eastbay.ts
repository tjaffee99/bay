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
import {MeshBuilder, circle, ellipse, localToLngLat, rect, rotRect, type V2, type V3} from './kit';
import type {Landmark} from './types';
import {elevationAt} from '../layers/elevation';

const WIKI = 'https://en.wikipedia.org/wiki/';
const OSM_NOTE = 'footprint from OpenStreetMap (© OSM contributors, ODbL)';

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
  built: [1913.0, 1915.0],
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
    Construction: 'built 1914, completed 1915, opened to the public 1916 (construction start estimated)',
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
      b.color('#D8D3C6').cap(arc(11.5), -0.4).cap(rect(2.2, -0.9, 4.4, 38), -0.4); // orchestra floor and pit
      bowl(b, arc(11.5), arc(23), 0.6, 3.6, seat, conc, -1.5);
      b.color(conc).ribbon(arc(23).map(p => [p[0], p[1], 3.6] as V3), arc(24.5).map(p => [p[0], p[1], 3.8] as V3)); // diazoma walk
      bowl(b, arc(24.5), arc(33), 3.8, 6.8, seat, conc, 2);
      b.color('#7FA05E').ribbon(arc(33).map(p => [p[0], p[1], 6.8] as V3), arc(44).map(p => [p[0], p[1], 10.0] as V3)); // grassy mound
      // stage: 38.7 × 8.5 m platform 2 m above the orchestra, front at x = 4.3
      b.color(conc).box(8.6, -0.9, -2.5, 8.6, 40.4, 4.3);
      // scaenae frons: wall with 16 engaged Doric columns, 10.7 m above the stage
      b.color('#D3CEC1').box(14.4, -0.9, -2.5, 3.0, 40.4, 15.2);
      b.color('#DCD7CA');
      rowOf(b, [12.8, -19.9], [12.8, 18.1], 16, 0.9, 0.6, 1.8, 11.4);
      b.color('#CFCABD').box(14.2, -0.9, 11.4, 3.6, 41.4, 1.4); // entablature
      b.color('#4A4E50').box(12.85, -0.9, 1.8, 0.2, 2.6, 4.2); // central doorway
      // end pylons projecting toward the audience
      for (const y of [-23.0, 21.2]) b.color('#D3CEC1').box(10.5, y, -2.5, 9.0, 4.2, 15.6);
      // backstage block (1957, Ernest Born) behind the wall
      b.color('#BDB8AC').box(19.5, -0.9, -3.5, 7.2, 49.4, 8.5);
      b.color('#8E8B84').box(19.5, -0.9, 5.0, 7.2, 49.4, 0.4);
    });
  },
  replaces: [rotRing(rect(15, -3, 60, 60), 141.5)],
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
      b.color(GRANITE).box(-6, -15.5, -2, 25.4, 31, 19.5).box(-6, 15.5, -2, 25.4, 31, 19.5);
      doeRoofs(b, -18.7, 6.7, -31, 0);
      doeRoofs(b, -18.7, 6.7, 0, 31);
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
  replaces: [rotRing(rect(-4.6, -0.7, 53, 61), 26.3)],
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
  // the OSM outline itself (a 2-storey neighbour lies 5 m off the south-east corner)
  // the theatre's OSM outline drawn in ~4 m (local metres): the 74 m Forma apartment tower (2022) on the
  // 21st St side is within the ~12 m "tall neighbour" reach of replacedMask and vanished with the full outline
  replaces: [
    [[-8.9, -17.5], [-33.7, -4.5], [-25.3, 31.9], [-17.6, 32.0], [-19.1, 23.9], [-12.7, 22.6], [-13.0, 18.9], [-0.3, 13.5], [1.0, 16.1], [12.7, 10.3],
     [17.6, 22.7], [22.8, 21.5], [18.3, -8.0], [43.1, -21.3], [39.9, -27.6], [12.6, -13.7], [8.1, -22.5], [5.5, -22.4], [-8.2, -15.0]]
  ],
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
    Renovated: '1996–97 (HNTB, $121 M): interior gutted and a new bowl built inside the original walls, roof and foundation; ≈19,600 seats; the Warriors played 1996–97 in San José',
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
    for (let k = 0; k <= 3; k++) {
      const t = k / 3;
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

// ------------------------------------------------------------ Oakland Coliseum (1966, and with Mount Davis 1996)
// OSM 3D parts in a 145° frame (+x = 235°, toward home plate; −x = 55°, centre field):
// "Field Level", "Plaza Level" and "Upper Deck" crescents, "Mount Davis" (172 × 44 m) and
// the two outfield "Bleachers". Home plate ≈ (66, 0): backstop 60 ft from the field-level
// front row, CF fence 400 ft out at the Mount Davis front (x ≈ −57). The field lies 21 ft
// (6.4 m) below sea level inside an earth berm (only the third deck shows from outside);
// the terrain mesh never drops below +0.9 m, so the field and the lower bowl are raised to
// sit on it (the decks keep their height above the outside concourse, ≈ +6.5 m).
// Mount Davis (1995–96) was specified not to exceed the existing stadium's height.
const COLISEUM: V2 = [-122.200474, 37.751665];
const COL_FIELD: V2[] = [[-30.6, 80.4], [-22.2, 66.3], [-2.1, 74.0], [12.5, 62.5], [29.9, 59.7], [49.2, 66.0], [61.7, 58.1], [61.8, 41.4], [69.9, 28.9], [73.0, 21.1], [83.2, 14.4], [84.3, 2.8], [84.3, -1.7], [83.1, -12.2], [72.7, -18.6], [69.9, -26.2], [60.4, -40.1], [61.6, -55.2], [49.3, -63.2], [31.1, -56.4], [25.6, -58.5], [13.3, -59.2], [-2.0, -71.4], [-19.8, -65.0], [-27.8, -79.2]];
const COL_FIELD_OUT: V2[] = [[-14.4, 87.6], [9.3, 91.9], [32.8, 89.8], [43.8, 86.5], [64.8, 75.9], [74.3, 68.1], [89.0, 51.6], [95.2, 41.4], [103.0, 18.9], [104.2, 5.7], [102.1, -17.8], [98.9, -29.0], [88.3, -50.1], [80.7, -59.4], [72.5, -67.9], [52.5, -80.9], [29.9, -87.9], [18.2, -89.3], [-5.7, -87.2]];
const COL_PLAZA_IN: V2[] = [[-37.8, 70.7], [-23.1, 79.3], [-12.8, 83.3], [9.7, 87.3], [32.0, 85.3], [53.1, 77.7], [71.5, 64.5], [85.1, 48.8], [95.2, 28.6], [98.0, 18.0], [99.7, -2.9], [95.8, -24.8], [86.1, -45.4], [71.5, -62.6], [52.7, -75.3], [31.7, -82.8], [9.4, -84.9], [-12.8, -80.8], [-23.4, -76.7], [-37.9, -67.7]];
const COL_PLAZA_OUT: V2[] = [[-47.9, 83.4], [-29.8, 94.5], [-4.4, 102.2], [9.1, 104.0], [22.7, 103.4], [48.6, 98.0], [72.4, 85.6], [83.0, 77.1], [100.4, 56.3], [112.0, 31.6], [115.1, 18.5], [116.3, -3.6], [114.7, -16.9], [111.4, -30.0], [100.0, -54.0], [92.0, -64.8], [72.1, -83.0], [60.6, -89.9], [35.4, -99.2], [9.0, -101.3], [-17.5, -96.4], [-30.1, -91.5], [-47.9, -80.8]];
const COL_UPPER_IN: V2[] = [[-43.0, 78.6], [-27.2, 87.5], [-15.2, 92.3], [9.1, 96.8], [34.0, 94.6], [57.1, 86.2], [77.7, 71.8], [94.0, 52.6], [104.6, 29.6], [109.1, 5.9], [107.7, -15.9], [104.8, -27.9], [94.0, -50.6], [78.0, -69.6], [57.1, -83.9], [33.8, -92.3], [8.9, -94.2], [-15.9, -90.0], [-27.6, -85.8], [-43.4, -75.4]];
const COL_UPPER_OUT: V2[] = [[-52.8, 90.9], [-33.0, 102.2], [-19.1, 107.2], [-5.3, 111.1], [9.1, 112.4], [37.8, 109.6], [52.3, 105.2], [73.4, 94.9], [88.9, 82.8], [107.6, 60.5], [119.6, 33.7], [123.2, 19.1], [124.7, -3.7], [122.9, -17.9], [114.6, -45.3], [106.9, -58.5], [88.4, -80.6], [73.2, -92.9], [51.8, -103.1], [23.2, -109.0], [8.9, -109.5], [-5.5, -108.0], [-19.8, -104.6], [-33.1, -99.2], [-51.9, -88.3]];
const COL_BRG = 145;
const COL_CONCOURSE = 6.8;
function coliseumBowl(b: MeshBuilder, davis: boolean) {
  const n = 48;
  const seats = '#2F5A4A';
  const conc = '#C9C4B8';
  const deck = (inn: V2[], out: V2[], z0: number, z1: number, col: string) => {
    const A = resample(inn, n);
    const B = resample(out, n);
    b.color(col).ribbon(A.map(p => [p[0], p[1], z0] as V3), B.map(p => [p[0], p[1], z1] as V3));
    b.color(conc).wallProfile(B, z1 - 4, z1 + 1.2); // back wall / fascia
    b.color('#D6D1C6').wallProfile(A, z0 - 2.5, z0 + 0.6); // front fascia
    b.color(conc).quad([A[0][0], A[0][1], z0 - 2.5], [B[0][0], B[0][1], z1 - 4], [B[0][0], B[0][1], z1 + 1.2], [A[0][0], A[0][1], z0 + 0.6]);
    b.quad([A[n][0], A[n][1], z0 - 2.5], [B[n][0], B[n][1], z1 - 4], [B[n][0], B[n][1], z1 + 1.2], [A[n][0], A[n][1], z0 + 0.6]);
  };
  // field (raised onto the terrain mesh) with the infield dirt
  b.color('#5D9A47').cap(circle(8, 0, 76, 40), 1.6);
  b.color('#A9845E').cap(circle(8, 0, 76, 40), 1.62, [circle(8, 0, 70, 40)]); // warning track
  const home: V2 = [66, 0];
  b.frame(home[0], home[1], 0, 270, () => {
    const d = 27.43 * Math.SQRT1_2;
    b.color('#B98E66').cap([[0, -4], [d + 5, d - 2], [0, 2 * d + 7], [-d - 5, d - 2]], 1.75);
    b.color('#5D9A47').cap([[0, 3], [d - 4, d], [0, 2 * d - 3], [-d + 4, d]], 1.85);
  });
  // lower bowl (field level) up to the main concourse, then the plaza and upper decks
  const fieldIn = COL_FIELD.slice().reverse();
  const fieldOut = COL_FIELD_OUT.slice().reverse();
  deck(fieldIn, fieldOut, 2.6, COL_CONCOURSE, seats);
  b.color('#B7B2A6').ribbon(
    resample(fieldOut, n).map(p => [p[0], p[1], COL_CONCOURSE] as V3),
    resample(COL_PLAZA_OUT.slice().reverse(), n).map(p => [p[0] * 0.97 + 0.3, p[1] * 0.97, COL_CONCOURSE] as V3)
  ); // concourse walk
  deck(COL_PLAZA_IN, COL_PLAZA_OUT, COL_CONCOURSE + 4.5, COL_CONCOURSE + 13, seats);
  deck(COL_UPPER_IN, COL_UPPER_OUT, COL_CONCOURSE + 16.5, COL_CONCOURSE + 27, seats);
  // rim, light standards (six round the upper deck)
  const top = resample(COL_UPPER_OUT.slice().reverse(), 10);
  for (const i of [1, 3, 5, 7, 9]) {
    const [x, y] = top[i];
    b.color('#7B7F82').beam([x, y, COL_CONCOURSE + 28], [x, y, COL_CONCOURSE + 47], 1.0);
    b.color('#5E6266').box(x, y, COL_CONCOURSE + 45, 7, 2, 3.5);
  }
  if (!davis) {
    // 1966–95: open outfield with bleachers, the scoreboards and the view of the hills
    for (const sy of [-1, 1]) {
      const ring: V2[] = [[-57.3, sy * 24.6], [-50.1, sy * 24.7], [-38.6, sy * 44.9], [-29.5, sy * 67.1], [-46.5, sy * 74.2], [-57.3, sy * 48.2]];
      b.color(seats).prism(ring, 1.6, 6.5);
      b.color('#33373A').box(-62, sy * 45, 1.6, 2.0, 30, 14);
      b.color('#5A5E62').box(-62, sy * 45, 1.6, 1.0, 2.0, 7);
    }
    b.color(conc).wallProfile(ellArc(8, 0, 75, 86, (2 * Math.PI) / 3, (4 * Math.PI) / 3, 12), 1.6, 3.4); // outfield wall
  } else {
    // Mount Davis (1995–96): a steep outfield grandstand with suites, as high as the stadium
    const md: V2[] = [[-48.0, 70.1], [-73.0, 87.3], [-92.0, 55.8], [-91.9, -52.1], [-74.0, -84.7], [-47.9, -67.3], [-57.2, -45.0], [-57.3, 48.2]];
    const front = resample([[-47.9, -67.3], [-57.2, -45.0], [-57.3, 48.2], [-48.0, 70.1]], 16);
    const back = resample([[-74.0, -84.7], [-91.9, -52.1], [-92.0, 55.8], [-73.0, 87.3]], 16);
    const mid = front.map((p, i) => [(p[0] + back[i][0]) / 2, (p[1] + back[i][1]) / 2] as V2);
    b.color(seats).ribbon(front.map(p => [p[0], p[1], 3.5] as V3), mid.map(p => [p[0], p[1], 14] as V3));
    b.color('#3B4A50').ribbon(mid.map(p => [p[0], p[1], 14] as V3), mid.map(p => [p[0] - 2.5, p[1], 19.5] as V3)); // suites
    b.color(seats).ribbon(mid.map(p => [p[0] - 2.5, p[1], 19.5] as V3), back.map(p => [p[0], p[1], COL_CONCOURSE + 27.5] as V3));
    b.color(conc).prism(md, -1, 3.5, {top: false}).wallProfile(back, -1, COL_CONCOURSE + 29);
    b.color('#2B2F33').box(-93.5, 0, COL_CONCOURSE + 12, 1.5, 44, 11); // video board on the back
    // lower outfield bleachers under Mount Davis
    for (const sy of [-1, 1]) {
      const ring: V2[] = [[-57.3, sy * 24.6], [-50.1, sy * 24.7], [-38.6, sy * 44.9], [-29.5, sy * 67.1], [-46.5, sy * 74.2], [-57.3, sy * 48.2]];
      b.color(seats).prism(ring, 1.6, 4.5);
    }
  }
}
const coliseum1966: Landmark = {
  id: 'oakland_coliseum_1966',
  name: 'Oakland–Alameda County Coliseum (1966)',
  kind: 'stadium',
  built: [1964.29, 1966.71],
  end: 1995.85,
  anchor: COLISEUM,
  build: b => b.frame(0, 0, 0, COL_BRG, () => coliseumBowl(b, false)),
  facts: {
    Construction: 'groundbreaking Apr 15, 1964; opened Sep 18, 1966 (Raiders 1966–81, A’s from 1968)',
    Design: 'Skidmore, Owings & Merrill (Myron Goldsmith); field 21 ft below sea level inside an earth berm',
    Outfield: 'open to the Oakland hills, with bleachers and scoreboards',
    Model: 'deck outlines from the OSM 3D parts; deck heights estimated; field raised to the terrain surface (see eastbay.ts)'
  },
  sources: [WIKI + 'Oakland_Coliseum', 'https://pcad.lib.washington.edu/building/7178']
};
const coliseum1996: Landmark = {
  id: 'oakland_coliseum',
  name: 'Oakland Coliseum',
  kind: 'stadium',
  built: [1995.85, 1996.62],
  end: 9999,
  anchor: COLISEUM,
  build: b => b.frame(0, 0, 0, COL_BRG, () => coliseumBowl(b, true)),
  replaces: [rotRing(rect(15, 0, 250, 250), COL_BRG)],
  facts: {
    Renovation: 'Nov 1995 – Aug 1996 (HNTB) for the Raiders’ return: “Mount Davis”, a 10,000+-seat, 90-suite outfield grandstand, closes the bowl',
    Tenants: 'A’s until 2024, Raiders until 2019; cricket and soccer since 2025',
    Names: 'Oakland–Alameda County Coliseum 1966–98, 2008–11 and 2016–19 · Network Associates Coliseum 1998–2004 · McAfee Coliseum 2004–08 · Overstock.com / O.co Coliseum 2011–16 · RingCentral Coliseum 2019–23 · Oakland Coliseum since 2023',
    Fences: 'LF 330 ft · LC 388 · CF 400 · RC 388 · RF 330',
    Model: 'Mount Davis outline from OSM; its height set to the existing upper deck (as specified in 1995); deck heights estimated'
  },
  sources: [WIKI + 'Oakland_Coliseum', WIKI + 'Mount_Davis_(Oakland)']
};

// =================================================================== OAKLAND HILLS AND WEST OAKLAND

// ------------------------------------------------------------ Oakland California Temple
// OSM in a 5° frame: the temple's cross-shaped plan 56 × 33 m on a terrace building
// (91 × 63.5 m, rooftop garden and reflecting pool), the central spire part 15.8 m to 52 m
// (170 ft, Wikipedia). Five spires: a stepped central tower with a pierced spire and four
// corner spires at the re-entrant corners; Sierra white granite over concrete. Stage
// heights from the photo; the terrace follows the hillside (foundations sunk 3 m).
const temple: Landmark = {
  id: 'oakland_california_temple',
  name: 'Oakland California Temple',
  kind: 'building',
  built: [1962.4, 1964.88],
  end: 9999,
  anchor: [-122.1991, 37.807818],
  build: b => {
    const granite = '#ECEAE3';
    const shade = '#DAD7CE';
    const spire = '#E3DCC5';
    b.frame(0, 0, 0, 5, () => {
      const terrace: V2[] = [[31.4, -18.0], [31.1, 23.6], [21.9, 23.6], [21.7, 67.1], [10.6, 67.0], [11.7, 29.5], [-12.6, 29.4], [-12.8, 66.7], [-22.2, 66.6], [-22.2, 55.7], [-32.1, 55.7], [-32.1, 48.4], [-21.7, 48.5], [-21.5, 22.9], [-32.4, 22.9], [-32.2, -18.1], [-30.7, -18.1], [-30.7, -24.3], [28.7, -23.9], [28.7, -18.0]];
      b.color(shade).prism(terrace, -3, 4.5);
      b.color('#6C8D9C').box(0, -20.5, 4.5, 30, 4, 0.2); // reflecting pool
      const cross: V2[] = [[-14.2, 7.7], [-28.1, 7.7], [-28.1, -8.0], [-14.3, -8.0], [-15.1, -15.1], [-8.0, -14.3], [-8.0, -16.7], [8.2, -16.7], [8.2, -14.2], [14.8, -15.0], [13.8, -7.7], [28.1, -7.7], [28.1, 8.0], [14.3, 8.0], [15.2, 15.3], [7.9, 14.6], [7.9, 16.5], [-8.3, 16.5], [-8.3, 14.2], [-15.0, 15.1]];
      b.color(granite).prism(cross, 4.5, 15.8);
      b.color(shade).prism(scaleRing(cross, 1.01), 15.8, 16.6);
      // stepped central tower (OSM part 15.8 m) and pierced spire to 52 m
      b.color(granite).box(-1, 3.7, 16.6, 19, 19, 3.4);
      b.color(granite).box(-1, 3.7, 20, 15.8, 15.8, 10.5);
      b.color(shade).box(-1, 3.7, 30.5, 11.4, 11.4, 4.0);
      b.color(granite).box(-1, 3.7, 34.5, 8.6, 8.6, 3.2);
      b.color(spire).pyramid(rect(-1, 3.7, 7.2, 7.2), 37.7, [-1, 3.7, 51.2]);
      b.color('#D4AF52').frustum(-1, 3.7, 0.4, 0.05, 51.2, 52.2, 6, false);
      // four corner spires
      for (const [x, y] of [[-14.7, -15.1], [14.8, -15.0], [-15.0, 15.2], [15.2, 15.3]] as V2[]) {
        b.color(granite).box(x, y, 4.5, 3.6, 3.6, 17.5);
        b.color(spire).pyramid(rect(x, y, 3.0, 3.0), 22, [x, y, 30.5]);
      }
    });
  },
  replaces: [rotRing(rect(0, 21, 66, 96), 5)],
  facts: {
    Construction: 'groundbreaking May 26, 1962 (David O. McKay); dedicated Nov 17, 1964',
    Height: '170 ft (52 m) central spire; five spires; Sierra white granite over reinforced concrete',
    Design: 'Harold W. Burton — Mid-century Modern, Asian and Art Deco; terrace garden and reflecting pool',
    Model: 'plan and spire footprint from OSM; stage and corner-spire heights estimated from photos'
  },
  sources: [WIKI + 'Oakland_California_Temple']
};

// ------------------------------------------------------------ Southern Pacific 16th Street Station
// Jarvis Hunt, Beaux-Arts; opened Aug 3, 1912, last train Aug 21, 1994 (Wikipedia). OSM
// footprint in a 43.7° frame: the main hall's three-arch front (37.8 m) faces SE (+x),
// one-storey wings either side and along the tracks; the 16th Street signal tower 100 m
// north. Heights scaled from the 2007 photo (door ≈4 m): cornice ≈17 m, attic ≈19.5 m.
const station16th: Landmark = {
  id: 'sp_16th_street_station',
  name: '16th Street Station (Southern Pacific)',
  kind: 'building',
  built: [1910.6, 1912.59],
  end: 9999,
  anchor: [-122.297166, 37.81547],
  build: b => {
    const stone = '#D7D2C6';
    b.frame(0, 0, 0, 43.7, () => {
      // one-storey wings
      b.color(stone).box(0.55, -33.05, -1, 22.5, 8.7, 9.5).box(0.55, 13.5, -1, 22.5, 8.8, 9.5).box(-4, 32.6, -1, 13.4, 29.4, 8.5);
      b.color('#C5BFB2').box(0.55, -33.05, 8.5, 23, 9.2, 0.8).box(0.55, 13.5, 8.5, 23, 9.3, 0.8).box(-4, 32.6, 7.5, 13.9, 29.9, 0.8);
      // main hall
      b.color(stone).box(1.45, -9.8, -1, 24.3, 37.8, 18);
      b.color('#C5BFB2').box(1.45, -9.8, 17, 25, 38.5, 1.2);
      b.color(stone).box(1.45, -9.8, 18.2, 23.5, 37, 1.8); // balustraded attic
      b.color('#7E9C7A').hip(1.45, -9.8, 21, 34, 18.2 + 1.8, 3.2); // green roof (1918 postcard)
      // three great arched windows on the front, and the canopy
      b.color('#4D6670');
      for (const y of [-21.5, -9.8, 1.9]) b.box(13.65, y, 4.5, 0.2, 7.6, 10.5);
      b.color('#3F5048').box(15.2, -9.8, 4.2, 3.0, 9, 0.5);
      // 16th Street signal tower
      b.color('#B9A58A').box(-31.4, 96.4, -1, 6.8, 11.6, 12);
      b.color('#6E6A62').hip(-31.4, 96.4, 7.4, 12.2, 11, 2);
    });
  },
  replaces: [rotRing(rect(1.5, 5, 28, 90), 43.7), rotRing(rect(-31.4, 96.4, 9, 14), 43.7)],
  facts: {
    Opened: 'Aug 3, 1912 (Jarvis Hunt), replacing an 1870s wooden depot on the then shoreline',
    Served: 'Southern Pacific mainline trains and the SP Red Trains’ interurban platforms; Amtrak until Aug 21, 1994',
    Since: 'damaged in 1989, closed 1994; restored as an event venue',
    Model: OSM_NOTE + '; heights scaled from the 2007 photo; signal tower date assumed with the station'
  },
  sources: [WIKI + 'Oakland_16th_Street_station']
};

// ------------------------------------------------------------ El Embarcadero Pergola and Colonnade
// 1913 (Wikipedia: "an elaborate Mission Revival pergola … at the northeastern tip of the
// lake"), restored 2007. OSM outline: a semicircular colonnade 4.5 m deep opening SW to the
// lake (133.4° frame, +x toward the water), a hipped central pavilion and pyramid-roofed
// end pavilions. Column spacing and heights estimated (no measured drawing found).
const PERG_OUT: V2[] = [[15.6, -39.7], [12.5, -39.5], [6.6, -37.9], [0.5, -34.7], [-3.1, -32.1], [-6.6, -28.4], [-10.1, -22.9], [-12.4, -17.0], [-13.8, -9.9], [-14.4, 7.9], [-13.1, 17.5], [-5.3, 28.1], [-0.6, 32.2], [4.3, 35.4], [10.9, 38.5], [15.6, 38.7]];
const PERG_IN: V2[] = [[15.6, -35.2], [12.7, -35.1], [6.8, -33.8], [3.3, -32.3], [-0.7, -29.1], [-5.1, -24.1], [-6.5, -21.8], [-8.1, -18.1], [-9.7, -10.0], [-9.4, 7.6], [-9.1, 11.7], [-7.2, 18.6], [-2.7, 24.9], [-0.3, 27.4], [2.1, 29.0], [11.4, 33.3], [15.7, 33.6]];
const pergola: Landmark = {
  id: 'lake_merritt_pergola',
  name: 'El Embarcadero Pergola, Lake Merritt',
  kind: 'monument',
  built: [1912.6, 1913.5],
  end: 9999,
  anchor: [-122.249804, 37.80846],
  build: b => {
    const col = '#EDE6D2';
    b.frame(0, 0, 0, 133.4, () => {
      const n = 24;
      const A = resample(PERG_IN, n);
      const B = resample(PERG_OUT, n);
      b.color('#D9D2BE').ribbon(A.map(p => [p[0], p[1], 0.4] as V3), B.map(p => [p[0], p[1], 0.4] as V3));
      b.color(col);
      for (let i = 0; i <= n; i++) {
        b.box(A[i][0], A[i][1], 0.4, 0.7, 0.7, 4.0).box(B[i][0], B[i][1], 0.4, 0.7, 0.7, 4.0);
      }
      b.polyline(A.map(p => [p[0], p[1], 4.6] as V3), 0.5).polyline(B.map(p => [p[0], p[1], 4.6] as V3), 0.5);
      b.color('#8C6E4E');
      for (let i = 0; i <= n; i++) {
        const dx = B[i][0] - A[i][0];
        const dy = B[i][1] - A[i][1];
        b.beam([A[i][0] - dx * 0.15, A[i][1] - dy * 0.15, 5.0], [B[i][0] + dx * 0.15, B[i][1] + dy * 0.15, 5.0], 0.25, 0.35);
      }
      // central pavilion (hipped tile roof) and the end pavilions (pyramid roofs)
      b.color(col).box(-11.5, -1.1, 0.4, 11, 17.9, 5.2);
      b.color('#B5654A').hip(-11.5, -1.1, 12, 18.9, 5.6, 2.6);
      for (const y of [-37.65, 35.25]) {
        b.color(col).box(19.85, y, 0.4, 8.3, 8.2, 5.0);
        b.color('#B5654A').pyramid(rect(19.85, y, 9.1, 9.0), 5.4, [19.85, y, 8.2]);
      }
    });
  },
  replaces: [rotRing(rect(3.5, 0, 45, 84), 133.4)],
  facts: {
    Built: '1913, City Beautiful improvements of Lake Merritt (Lakeside Park); restored 2007 (Measure DD)',
    Style: 'Mission Revival: a semicircle of columns carrying a timber trellis, with tiled pavilions',
    Model: 'outline from OSM; column spacing, heights and roof colours estimated (no photo or drawing downloaded); construction months estimated'
  },
  sources: [WIKI + 'Lake_Merritt']
};

// =================================================================== MILLS COLLEGE, MISSION SAN JOSÉ

// ------------------------------------------------------------ Mills Hall
// 1871, S. C. Bugbee & Son (NRHP): the Second Empire seminary building Cyrus and Susan Mills
// moved their school into. OSM outline in a 123.8° frame (65 m main block with three
// pavilions, a rear wing). From the photo: painted wood (grey-green, white trim), three
// tall storeys under a slate mansard with dormers, pavilions with higher mansard roofs.
const millsHall: Landmark = {
  id: 'mills_hall',
  name: 'Mills Hall, Mills College',
  kind: 'building',
  built: [1870.0, 1871.6],
  end: 9999,
  anchor: [-122.182039, 37.779656],
  build: b => {
    const wall = '#A9B3AC';
    const trim = '#F1F0EA';
    const slate = '#6F767A';
    b.frame(0, 0, 0, 123.8, () => {
      const blocks: [number, number, number, number][] = [
        [6.4, -7.4, 18.0, 65.0], // main block
        [-16.3, 19.4, 27.8, 13.2] // rear wing
      ];
      for (const [cx, cy, sx, sy] of blocks) {
        b.color(wall).box(cx, cy, -1.5, sx, sy, 15);
        b.color(trim).box(cx, cy, 13.5, sx + 0.8, sy + 0.8, 0.6);
        b.color(slate).loft([rect(cx, cy, sx + 0.4, sy + 0.4), rect(cx, cy, sx - 3.5, sy - 3.5)], [14.1, 18.6], {top: true});
      }
      // end and centre pavilions with taller mansards
      for (const [cx, cy, sx, sy, h] of [
        [6.4, -33.9, 19.5, 12, 21],
        [6.9, 18.9, 19.5, 12.4, 21],
        [5, -7.3, 21.5, 15.5, 23]
      ] as [number, number, number, number, number][]) {
        b.color(wall).box(cx, cy, -1.5, sx, sy, 15.5);
        b.color(trim).box(cx, cy, 14, sx + 0.8, sy + 0.8, 0.6);
        b.color(slate).loft([rect(cx, cy, sx + 0.4, sy + 0.4), rect(cx, cy, sx - 1.6, sy - 1.6), rect(cx, cy, sx - 5, sy - 5)], [14.6, h - 1.5, h], {top: true});
      }
      // front porch at the centre pavilion
      b.color(trim).box(17.6, -7.3, 0, 3, 8, 4.2);
      b.color('#5E676B').box(17.6, -7.3, 4.2, 3.4, 8.6, 0.4);
    });
  },
  replaces: [rotRing(rect(-7.4, -5.8, 49, 72), 123.8)],
  facts: {
    Built: '1871 (S. C. Bugbee & Son) — Mills Seminary moved here from Benicia in 1871; Mills College from 1885',
    Style: 'Second Empire, painted wood, mansard roofs; National Register of Historic Places',
    Model: OSM_NOTE + '; storey and mansard heights estimated from the photo; construction start estimated'
  },
  sources: [WIKI + 'Mills_College']
};

// ------------------------------------------------------------ Mission San José
// The adobe church (dedicated Apr 22, 1809) was shattered by the Hayward Fault earthquake of
// Oct 21, 1868; a wooden Gothic church was built over its tiled floor (moved away 1982); the
// adobe church was reconstructed on the original site and completed in 1985 (Wikipedia).
// OSM outline in a 261° frame (+y west, the facade on Mission Blvd; +x north): nave
// 14.6 × 50.4 m, bell tower at the north-west corner (4 × 7.4 m), low north-side rooms. The
// surviving padres' wing (museum) stands 23 m south. Heights from the 2011 photo (door
// ≈2.6 m): walls ≈9.5 m, ridge ≈13 m, tower ≈13 m + tiled cap.
const MSJ: V2 = [-121.919663, 37.533894];
function adobeChurch(b: MeshBuilder) {
  const white = '#F1EEE6';
  const tile = '#A85A3C';
  b.frame(0, 0, 0, 261, () => {
    b.color('#8F8576').box(-1.2, 0, -3, 15.6, 51.4, 4); // fieldstone base / floor platform
    b.color(white).box(-1.2, -0.6, 1, 14.6, 50.4, 8.5);
    b.color(tile).gable(-1.2, -0.6, 16.0, 51.8, 9.3, 3.6, true);
    b.color(white).tri([-8.5, 24.65, 9.5], [6.1, 24.65, 9.5], [-1.2, 24.65, 13.1]); // front gable
    // bell tower (two bell openings, tiled cap, cross)
    b.color(white).box(8.2, 20.3, -1, 4.0, 7.4, 13.8);
    b.color('#5A4A3A').box(8.2, 24.05, 9, 1.4, 0.1, 1.8).box(8.2, 24.05, 5.3, 1.4, 0.1, 1.8);
    b.color(tile).hip(8.2, 20.3, 4.8, 8.2, 12.8, 1.4);
    b.color('#3E3A36').beam([8.2, 20.3, 14.2], [8.2, 20.3, 16.2], 0.15);
    // low rooms on the north side
    for (const [cy, sy] of [[-9.9, 4.6], [1.3, 12.0], [12.35, 4.1], [-23.2, 4.0]] as V2[]) {
      b.color(white).box(7.8, cy, 0, 3.4, sy, 5);
      b.color(tile).hip(7.8, cy, 3.8, sy + 0.4, 5, 1.2);
    }
    // buttresses on the south wall
    b.color('#E7E2D6');
    for (const y of [-14, -2, 9]) b.loft([rect(-9.6, y, 2.2, 2.6), rect(-8.8, y, 0.6, 2.6)], [0, 8], {top: true});
    // front steps and door
    b.color('#A35A44').box(-1.2, 27.5, -2.5, 16, 5, 3.6);
    b.color('#5B4632').box(-1.2, 24.66, 1.1, 2.0, 0.1, 2.7);
  });
}
const missionSanJose1809: Landmark = {
  id: 'mission_san_jose_1809',
  name: 'Mission San José — adobe church (1809)',
  kind: 'building',
  built: [1806.5, 1809.31],
  end: 1868.81,
  anchor: MSJ,
  build: adobeChurch,
  facts: {
    Mission: 'founded Jun 11, 1797 (Fermín Lasuén), the 14th California mission',
    Church: 'first permanent adobe church dedicated Apr 22, 1809',
    Destroyed: 'Oct 21, 1868 Hayward Fault earthquake shattered the walls and roof',
    Model: 'same massing as the 1985 reconstruction (a near-perfect replica on the original site); construction start estimated'
  },
  sources: [WIKI + 'Mission_San_Jos%C3%A9_(California)']
};
const missionSanJoseGothic: Landmark = {
  id: 'mission_san_jose_1869',
  name: 'St. Joseph’s Church, Mission San José (1869)',
  kind: 'building',
  built: [1868.9, 1869.8],
  end: 1982.3,
  anchor: MSJ,
  build: b =>
    b.frame(0, 0, 0, 261, () => {
      const white = '#EEECE5';
      const roof = '#4F5254';
      b.color(white).box(-1.2, -2, -1, 12, 42, 9);
      b.color(roof).gable(-1.2, -2, 12.6, 42.6, 8, 6.5, true);
      // front steeple (square tower, belfry, octagonal spire)
      b.color(white).box(-1.2, 20.5, -1, 4.6, 4.6, 16);
      b.color('#D9D6CE').box(-1.2, 20.5, 15, 4.0, 4.0, 4);
      b.color(roof).pyramid(ngon(-1.2, 20.5, 2.4, 8), 19, [-1.2, 20.5, 31]);
    }),
  facts: {
    Built: 'after the 1868 earthquake: a wood-framed Gothic church over the original red-tiled floor',
    Moved: '1982, to make way for the reconstruction of the adobe church',
    Model: 'LOW CONFIDENCE — size and steeple height estimated from a c. 1900 stereo photograph; built and removal dates approximate'
  },
  sources: [WIKI + 'Mission_San_Jos%C3%A9_(California)']
};
const missionSanJose1985: Landmark = {
  id: 'mission_san_jose',
  name: 'Mission San José — reconstructed church',
  kind: 'building',
  built: [1982.4, 1985.5],
  end: 9999,
  anchor: MSJ,
  build: adobeChurch,
  replaces: [rotRect(0, 0, 22, 54, 261)],
  facts: {
    Reconstruction: 'completed 1985 by the Committee for the Restoration of Mission San Jose and the Diocese of Oakland — a near-perfect replica with a concealed steel frame',
    Interior: 'reredos, chandeliers and side altars after the 1830s inventories',
    Model: OSM_NOTE + '; wall, ridge and tower heights scaled from the 2011 photo'
  },
  sources: [WIKI + 'Mission_San_Jos%C3%A9_(California)']
};
const missionSanJoseWing: Landmark = {
  id: 'mission_san_jose_padres_wing',
  name: 'Mission San José — padres’ quarters (museum)',
  kind: 'building',
  built: [1808.5, 1810.0],
  end: 9999,
  anchor: MSJ,
  build: b =>
    b.frame(0, 0, 0, 261, () => {
      b.color('#F1EEE6').box(-56.45, 14.6, -1.5, 49.5, 12.5, 6);
      b.color('#A85A3C').gable(-56.45, 14.6, 50.3, 13.3, 4.5, 2.6, false);
      // corridor (arcade) on the street side
      b.color('#A85A3C').box(-56.45, 20.6, 3.6, 49.5, 2.2, 0.35);
      b.color('#E5DFD0');
      for (let x = -80; x <= -33; x += 3.6) b.box(x, 21.2, 0, 0.6, 0.6, 3.6);
    }),
  replaces: [rotRing(rect(-56.45, 12.35, 52, 21), 261)],
  facts: {
    Built: 'part of the mission quadrangle (c. 1810, LOW CONFIDENCE date); the only surviving original adobe, saved by the Native Sons of the Golden West (1915, 1950) as the museum',
    Model: OSM_NOTE + '; roof, corridor and heights estimated'
  },
  sources: [WIKI + 'Mission_San_Jos%C3%A9_(California)']
};

// =================================================================== ALAMEDA, RICHMOND, ALBANY, MOUNT DIABLO

// ------------------------------------------------------------ USS Hornet (CV-12)
// Museum ship at Pier 3 of the former NAS Alameda, opened Oct 17, 1998. Essex class:
// 872 ft overall, 820 ft at the waterline, beam 93 ft (Wikipedia). OSM flight-deck outline
// (270 × 65 m with the SCB-125 angled deck, 90.1° frame: bow east, island to starboard =
// south) and the island parts. Hangar deck ≈9 m, flight deck ≈16 m above the waterline
// (estimated from the photo); island, funnel and lattice mast heights estimated.
const HORNET: V2 = [-122.30292, 37.77272];
const HORNET_DECK: V2[] = [[27.7, 134.5], [26.2, 136.2], [-1.8, 138.2], [-3.2, 136.9], [-6.0, 103.3], [-9.4, 100.5], [-8.7, 92.4], [-10.2, 88.3], [-9.3, 82.0], [-8.8, 72.6], [-11.7, 66.3], [-14.6, 30.9], [-24.6, 30.0], [-27.6, -6.2], [-27.4, -12.2], [-33.0, -13.1], [-34.7, -14.3], [-34.6, -15.6], [-27.3, -16.0], [-26.4, -49.8], [-25.1, -61.8], [-27.2, -66.5], [-25.3, -81.6], [-24.4, -110.7], [-25.9, -115.0], [-24.2, -128.9], [-23.3, -131.9], [6.3, -129.3], [7.7, -127.2], [11.9, -72.5], [14.8, -67.8], [12.8, -62.1], [20.2, -57.3], [22.1, -51.9], [28.8, -52.4], [30.0, -33.8], [20.3, -33.1], [15.7, -24.7], [17.9, -8.5], [21.4, 11.8], [22.2, 22.2], [21.0, 36.7], [23.8, 36.7], [24.4, 43.7], [21.8, 44.9], [24.0, 79.1], [26.5, 79.0], [28.5, 88.3], [27.1, 92.7], [30.0, 95.3], [30.1, 98.0], [25.4, 99.1]];
const ussHornet: Landmark = {
  id: 'uss_hornet_museum',
  name: 'USS Hornet (CV-12) museum ship',
  kind: 'monument',
  built: [1998.77, 1998.79],
  end: 9999,
  anchor: HORNET,
  // the waterline sits at sea level whatever the height lookup gives at the pier
  build: b =>
    b.frame(0, 0, 0.5 - elevationAt(HORNET[0], HORNET[1]), 90.1, () => {
      const cx = 3.7;
      const hull: V2[] = [[cx - 9.5, -122], [cx + 9.5, -122], [cx + 14.15, -105], [cx + 14.15, 70], [cx + 9, 110], [cx, 128], [cx - 9, 110], [cx - 14.15, 70], [cx - 14.15, -105]];
      b.color('#61676D').prism(hull, -1, 9);
      const upper: V2[] = [[cx - 13, -126], [cx + 14, -126], [cx + 17.5, -105], [cx + 17.5, 72], [cx + 12, 118], [cx, 136], [cx - 12, 118], [cx - 17.5, 72], [cx - 17.5, -105]];
      b.color('#787E85').prism(upper, 9, 15.5);
      b.color('#4D5257').prism(HORNET_DECK, 15.5, 16.4);
      b.color('#E9E9E2').box(cx, 0, 16.45, 0.6, 240, 0.05); // centreline
      // island, bridge, funnel and mast
      const island: V2[] = [[12.7, 27.7], [11.2, -3.4], [12.4, -5.1], [16.1, -5.2], [17.7, -3.8], [20.4, 13.8], [20.7, 23.8], [19.4, 32.1], [18.5, 33.4], [16.8, 33.8], [13.5, 32.0]];
      b.color('#8A9096').prism(island, 16.4, 26.5);
      b.color('#9AA0A6').prism([[13.2, 4.5], [13.8, 2.8], [14.8, 2.2], [16.0, 2.7], [17.6, 12.0], [18.2, 27.5], [17.9, 28.4], [15.6, 29.1], [13.9, 26.7], [13.3, 23.5]], 26.5, 31);
      b.color('#5E6369').box(16.3, 17, 31, 3.8, 7, 3.5);
      b.color('#2E3236').box(16.3, 17, 34.5, 3.6, 6.8, 0.4);
      b.color('#6D7378').beam([15.2, 8, 31], [15.2, 8, 47], 0.8);
      b.box(15.2, 8, 42, 6, 1.2, 0.8);
    }),
  replaces: [rotRing(scaleRing(HORNET_DECK, 1.03), 90.1)], // the deck outline: pier kiosks alongside stay
  facts: {
    Ship: 'Essex-class carrier, laid down Aug 3, 1942, commissioned Nov 29, 1943; recovered the Apollo 11 and 12 crews (1969); decommissioned 1970',
    Museum: 'opened Oct 17, 1998 on the southernmost pier of the former Naval Air Station Alameda (closed 1997)',
    Size: '872 ft (266 m) overall, beam 93 ft at the waterline; angled flight deck since the SCB-27A/125 refits',
    Model: 'flight deck and island outline from OSM; deck heights and mast estimated from the photo; shown from the museum opening'
  },
  sources: [WIKI + 'USS_Hornet_(CV-12)', WIKI + 'USS_Hornet_Museum']
};

// ------------------------------------------------------------ Mount Diablo Summit Building
// Sandstone summit building and beacon tower built by the Civilian Conservation Corps,
// 1939–42 (Wikipedia caption); the "Eye of Diablo" aviation beacon (1928, Standard Oil) sits
// on the tower and is relit every Dec 7. OSM outline in a 145.6° frame (26 × 12 m) with the
// tower part. The terrain mesh rounds the 1,173 m peak to ≈1,152 m and the viewer's height
// lookup (240 m) to ≈1,127 m, so the model is lifted onto the mesh surface.
const DIABLO: V2 = [-121.914189, 37.881754];
const DIABLO_MESH_TOP = 1152.4;
const diabloSummit: Landmark = {
  id: 'mount_diablo_summit_building',
  name: 'Mount Diablo Summit Building and beacon',
  kind: 'building',
  built: [1939.3, 1942.0],
  end: 9999,
  anchor: DIABLO,
  build: b => {
    const dz = Math.max(0, DIABLO_MESH_TOP - elevationAt(DIABLO[0], DIABLO[1]));
    const stone = '#B39A78';
    b.frame(0, 0, dz, 145.6, () => {
      const main: V2[] = [[5.1, -7.0], [2.4, 4.2], [3.7, 6.2], [3.2, 8.6], [1.1, 10.0], [-5.7, 8.1], [-2.5, -8.7], [-5.8, -9.2], [-5.1, -13.7], [4.0, -12.2], [3.0, -7.4]];
      b.color(stone).prism(main, -8, 5.5);
      b.color('#A08867').prism(scaleRing(main, 1.02), 5.5, 6.4); // parapet of the roof promenade
      // beacon tower
      const tower = ngon(0.5, 6.8, 3.4, 8);
      b.color(stone).prism(tower, -8, 11.5);
      b.color('#A08867').prism(ngon(0.5, 6.8, 3.7, 8), 11.5, 12.3);
      b.color('#C9442F').cylinder(0.5, 6.8, 0.9, 12.3, 13.8, 8);
      b.color('#565656').dome(0.5, 6.8, 1.0, 13.8, 0.6, 8, 2);
    });
  },
  replaces: [rotRing(rect(0, -1.5, 15, 28), 145.6)],
  facts: {
    Built: '1939 – 1942 by the Civilian Conservation Corps, of sandstone quarried on the mountain; museum and visitor centre',
    Beacon: 'the "Eye of Diablo" (Standard Oil aviation beacon, 1928) on the tower; relit every Pearl Harbor Day since 1964',
    Summit: '3,849 ft (1,173 m)',
    Model: OSM_NOTE + '; heights estimated (no measured drawing); placed on the terrain mesh’s rounded summit (≈1,152 m)'
  },
  sources: [WIKI + 'Mount_Diablo']
};

// ------------------------------------------------------------ Golden Gate Fields
// Opened Feb 1, 1941 with its grandstand built against the eastern slope of Fleming Point on
// filled marsh; one-mile main track, 7 f 132 ft turf course (1972); last race Jun 9, 2024
// (Wikipedia). OSM grandstand outline in a 162.4° frame (+x up the hill to the WSW); the
// track oval (402 m straights, 128 m turns) runs along the grandstand front at track level
// (terrain ≈3.5 m). Grandstand section, roof height and the infield layout estimated from
// the infield photo.
const GGF: V2 = [-122.313132, 37.884133];
const goldenGateFields: Landmark = {
  id: 'golden_gate_fields',
  name: 'Golden Gate Fields',
  kind: 'stadium',
  built: [1940.0, 1941.08],
  end: 9999,
  anchor: GGF,
  build: b => {
    const brg = 162.4;
    const dzT = groundDz(GGF, brg, -183, 0) + 0.35;
    b.frame(0, 0, 0, brg, () => {
      // track oval: dirt main track, turf course, infield
      const stadiumShape = (r: number, n = 18): V2[] => [
        ...ellArc(-183, 186, r, r, 0, Math.PI, n),
        ...ellArc(-183, -216, r, r, Math.PI, 2 * Math.PI, n)
      ];
      b.color('#9C7A58').cap(stadiumShape(140), dzT, [stadiumShape(118)]);
      b.color('#5F9A4B').cap(stadiumShape(113), dzT + 0.05, [stadiumShape(92)]);
      b.color('#7FB061').cap(stadiumShape(92), dzT + 0.02);
      b.color('#6F9EAE').cap(ellipse(-215, -85, 28, 60, 16), dzT + 0.1).cap(ellipse(-215, 65, 26, 55, 16), dzT + 0.1); // infield lakes
      b.color('#2F5E3E').box(-100, -15, dzT, 2, 72, 5.2); // tote board
      b.color('#E8E8E2').polyline(stadiumShape(140.5, 24).map(p => [p[0], p[1], dzT + 1.1] as V3), 0.15); // outer rail
      // grandstand: building mass on the slope, raked seats facing the track, cantilever roof
      const ring: V2[] = [[-33.3, -15.7], [-46.6, -126.0], [14.4, -133.1], [26.6, -30.5], [29.2, -24.9], [34.9, -7.7], [44.8, -5.4], [55.7, 2.9], [61.0, 12.3], [62.2, 24.7], [59.1, 34.1], [55.3, 39.8], [45.3, 47.1], [47.6, 64.4], [28.3, 67.8], [25.2, 95.7], [20.2, 114.3], [11.4, 134.3], [5.6, 138.4], [-9.6, 131.2], [-22.2, 136.7], [-29.6, 133.2], [-28.3, 120.5], [-19.0, 101.8], [-29.6, 98.1], [-25.0, 79.1], [-42.1, 80.6], [-46.6, 44.1], [-36.2, 76.1], [-24.6, 75.1], [-28.4, 25.1], [-35.4, 23.3], [-32.8, -8.8]];
      b.color('#D8D3C4').prism(ring, dzT - 0.5, 4.0);
      const front = resample([[-44, -122], [-36, -8], [-30, 68], [-24, 128]], 12);
      const back = front.map(([x, y]) => [x + 40, y] as V2);
      b.color('#3F6E55').ribbon(front.map(p => [p[0], p[1], 2.0] as V3), back.map(p => [p[0], p[1], 15.0] as V3));
      b.color('#D8D3C4').wallProfile(back, dzT, 19.5).wallProfile(front, dzT, 2.0);
      b.color('#EDEBE4').ribbon(front.map(p => [p[0] - 3, p[1], 19.5] as V3), back.map(p => [p[0] + 2, p[1], 19.5] as V3));
      b.color('#9C9A92');
      for (let i = 0; i <= 12; i += 2) b.beam([front[i][0] + 2, front[i][1], 2], [front[i][0] + 2, front[i][1], 19.5], 0.6);
      // clubhouse on the hill side
      b.color('#E2DCCB').prism([[26.6, -30.5], [34.9, -7.7], [55.7, 2.9], [62.2, 24.7], [55.3, 39.8], [45.3, 47.1], [26, 50]], dzT, 12);
    });
  },
  replaces: [rotRing(rect(8, 2, 115, 280), 162.4)],
  facts: {
    Opened: 'Feb 1, 1941 (grandstand against Fleming Point, track on filled marsh); turf course Feb 22, 1972',
    Facilities: 'one-mile main track, 9/10-mile turf course, grandstand ≈8,000 and clubhouse ≈5,200 seats',
    Closed: 'final race card Jun 9, 2024, after 83 years',
    Model: 'grandstand outline from OSM; seating section, roof and clubhouse heights, and the oval geometry (one mile: 402 m straights, 128 m turns) estimated'
  },
  sources: [WIKI + 'Golden_Gate_Fields']
};

// ------------------------------------------------------------ Claremont Hotel
// Begun after the 1905 purchase, halted by the 1906 earthquake, resumed 1910, opened 1915
// (Charles W. Dickey, Walter D. Reed); a wooden building whose central tower, 160 ft (49 m),
// is one of the tallest wooden structures in the world (Wikipedia). OSM outline 181 × 84 m
// in a 155.3° frame (+x = WSW, downhill toward the bay). From the photos: white walls, steep
// light-grey cross-gabled roofs, the tower with an arcaded belvedere and cupola. Wings
// simplified to five gabled blocks over the OSM outline; the building steps down the
// ≈12 m slope across its width (foundations reach the lower ground).
const CLAREMONT: V2 = [-122.242066, 37.85941];
const claremontHotel: Landmark = {
  id: 'claremont_hotel',
  name: 'Claremont Hotel',
  kind: 'building',
  built: [1906.0, 1915.3],
  end: 9999,
  anchor: CLAREMONT,
  build: b => {
    const white = '#F3F2EC';
    const roof = '#C3C6C8';
    b.frame(0, 0, 0, 155.3, () => {
      const ring: V2[] = [[31.4, 1.7], [47.2, 6.8], [24.3, 80.6], [13.1, 77.3], [13.6, 74.9], [-4.0, 70.1], [-1.9, 61.7], [-28.7, 51.4], [-24.0, 37.6], [-36.7, 32.7], [-30.7, 14.7], [-24.1, 16.5], [-28.4, 4.1], [-34.9, 5.1], [-34.2, -3.7], [-16.9, -8.6], [-17.9, -11.8], [-22.9, -10.3], [-23.8, -13.6], [-32.7, -11.0], [-36.7, -25.6], [-29.1, -40.0], [-33.3, -42.3], [-31.7, -48.0], [-29.9, -50.9], [-26.0, -48.8], [-14.9, -71.0], [-19.0, -92.9], [3.3, -100.9], [11.4, -77.2], [16.8, -71.3], [14.9, -66.7], [10.4, -64.0], [3.3, -49.8], [7.2, -47.7], [8.1, -43.3], [3.8, -41.9], [15.3, -2.9], [20.6, -1.4], [21.5, -3.8], [31.8, -0.7]];
      b.color(white).prism(ring, -10, 19);
      b.color('#E2E1DA').cap(ring, 19.05);
      // gabled wings (centre, size, axis rotation in the frame)
      const wings: [number, number, number, number, number, number][] = [
        [-10, -20, 30, 52, 0, 8], // spine
        [27, 40, 17, 78, -17, 8], // north-west range (the long front)
        [-17, 43, 18, 44, 22, 7],
        [-4, -72, 22, 50, 18, 7.5],
        [-22, 3, 24, 22, 0, 7]
      ];
      for (const [cx, cy, sx, sy, rot, h] of wings) b.frame(cx, cy, 0, rot, () => b.color(roof).gable(0, 0, sx, sy, 19, h, true));
      // cross gables facing the bay
      for (const [cx, cy] of [[33, 18], [27, 40], [21, 62], [6, -22], [8, -80]] as V2[]) b.frame(cx, cy, 0, 90, () => b.color(roof).gable(0, 0, 9, 12, 19, 8.5, true));
      // central tower with belvedere and cupola (top 49 m)
      b.color(white).box(16, 0, -6, 10, 10, 44);
      b.color('#D9D9D2').box(16, 0, 38, 10.8, 10.8, 0.8);
      b.color(white).box(16, 0, 38.8, 8.4, 8.4, 5.2);
      b.color('#5E6670').box(16, 0, 39.6, 8.6, 3.0, 3.4).box(16, 0, 39.6, 3.0, 8.6, 3.4);
      b.color(roof).loft([rect(16, 0, 9, 9), rect(16, 0, 4.5, 4.5), rect(16, 0, 1.2, 1.2)], [44, 47.5, 49], {top: true});
      b.color('#8A8C8E').beam([16, 0, 49], [16, 0, 54], 0.2);
    });
  },
  replaces: [rotRing(rect(5, -10, 92, 190), 155.3)],
  facts: {
    Construction: 'begun 1906 after the Claremont Hotel Company bought the site (Nov 1905); halted by the 1906 earthquake, resumed 1910; opened 1915',
    Design: 'Charles W. Dickey and Walter D. Reed; wood frame — the 160 ft (49 m) tower is among the tallest wooden structures',
    Notes: 'the Key System "E" line ran to its doors until 1958; spared by the 1991 Oakland firestorm',
    Model: 'outline from OSM; wings simplified to gabled blocks; eave (≈19 m) and roof heights estimated from photos'
  },
  sources: [WIKI + 'Claremont_Hotel_%26_Spa']
};

// ------------------------------------------------------------ Cathedral of Christ the Light
// Craig W. Hartman (SOM); groundbreaking May 21, 2005, dedicated Sep 25, 2008. A vesica
// piscis of glass and Douglas-fir louvres rising from a concrete plaza podium over the
// Lake Merritt shore, the crown ringed by aluminium fins (photo). OSM: cathedral part
// 56 × 44 m (162.7° frame), height 41 m; the podium/conference wing 156 × 63 m. The shells
// lean outward: base lens ≈32 × 48 m (estimated) widening to the OSM lens at the top.
const CTL: V2 = [-122.263122, 37.810532];
function vesica(cy: number, w: number, L: number, n = 12): V2[] {
  const R = (L * L + w * w) / (2 * w);
  const right: V2[] = [];
  for (let i = 0; i <= n; i++) {
    const y = -L + (2 * L * i) / n;
    right.push([-(R - w) + Math.sqrt(Math.max(R * R - y * y, 0)), cy + y]);
  }
  const left = right.slice(1, -1).reverse().map(([x, y]) => [-x, y] as V2);
  return [...right, ...left];
}
const cathedralChristTheLight: Landmark = {
  id: 'cathedral_christ_the_light',
  name: 'Cathedral of Christ the Light',
  kind: 'building',
  built: [2005.39, 2008.73],
  end: 9999,
  anchor: CTL,
  build: b => {
    b.frame(0, 0, 0, 162.7, () => {
      const podium: V2[] = [[-5.3, 38.9], [-17.8, 32.8], [-47.7, -13.4], [-8.2, -36.5], [2.7, -37.2], [8.8, -36.0], [12.8, -32.8], [25.6, -13.5], [27.3, -14.4], [84.7, 86.7], [41.7, 111.5], [37.1, 103.4], [31.9, 106.5]];
      b.color('#BDB8AE').prism(podium, -2, 5.5, {holes: [[[21.7, 53.5], [41.0, 42.8], [36.7, 35.2], [17.5, 45.9]]]});
      b.color('#C7C2B8').box(47.2, 34.2, 5.5, 22, 22, 11.4); // conference / rectory block
      // glass lens of the cathedral, widening upward
      const base = vesica(-3.2, 16, 24);
      const top = vesica(-3.2, 21.9, 28.2);
      b.color('#A7BFC8').loft([base, top], [5.5, 36], {top: false});
      b.color('#B98E5E').cap(vesica(-3.2, 21, 27.5), 34.5); // Douglas-fir louvred vault seen from above
      // crown of aluminium fins
      b.color('#D9DCDD');
      for (let i = 0; i < top.length; i += 1) {
        const [x, y] = top[i];
        b.box(x, y, 36, 0.35, 0.35, 5.5);
      }
      // entrance plaza steps
      b.color('#A8A39A').box(-2, 34, -1.5, 20, 8, 3.5);
    });
  },
  // the cathedral centre's own OSM outline (local metres); the 140 × 160 m rectangle also took the Ordway
  // Building (1970, 123 m — Oakland's tallest) and the Lake Merritt Tower (1990) on the same block
  replaces: [
    [[16.6, -35.6], [1.2, -111.2], [-4.7, -109.8], [-6.6, -118.8], [-55.0, -108.0], [-30.4, 5.6], [-28.5, 5.3], [-22.0, 27.5], [-19.2, 31.7], [-13.7, 34.7],
     [-3.0, 37.3], [41.5, 27.0], [26.7, -26.1]]
  ],
  facts: {
    Construction: 'groundbreaking May 21, 2005; consecrated and dedicated Sep 25, 2008',
    Design: 'Craig W. Hartman, Skidmore Owings & Merrill — a vesica piscis of glass and Douglas-fir louvres; Omega window with the image of Christ (from Chartres)',
    Height: '41 m (OSM)',
    Model: 'top lens and podium from OSM; the base lens size and the fin crown height estimated from the photo'
  },
  sources: [WIKI + 'Cathedral_of_Christ_the_Light_(Oakland,_California)']
};

// ------------------------------------------------------------ Cathedral Building
// 1914, Benjamin Geer McDougall (as the Federal Realty Building): the first Gothic Revival
// skyscraper in the West, a narrow wedge on Latham Square where Telegraph Avenue leaves
// Broadway (Wikipedia). OSM wedge 31.6 × 10.8 m, 42 m, 12 floors. White terra cotta shaft,
// arcaded crown with pinnacles and a steep pale-green mansard (photo).
const cathedralBuilding: Landmark = {
  id: 'cathedral_building_oakland',
  name: 'Cathedral Building',
  kind: 'tower',
  built: [1913.2, 1914.6],
  end: 9999,
  anchor: [-122.270244, 37.806232],
  build: b => {
    const wedge: V2[] = [[8.9, 9.5], [-0.8, 14.3], [-7.3, -17.6], [-5.1, -18.8]];
    b.color('#EEEBE2').prism(wedge, -1, 30);
    b.color('#DDD8CC').prism(scaleRing(wedge, 1.04), 4.2, 5.2).prism(scaleRing(wedge, 1.05), 30, 31.2);
    b.color('#EEEBE2').prism(scaleRing(wedge, 0.97), 31.2, 35);
    b.color('#A9C3BD').loft([scaleRing(wedge, 0.95), scaleRing(wedge, 0.45, 0.85)], [35, 42], {top: true});
    b.color('#E6E2D8');
    for (const p of wedge) b.frustum(p[0] * 0.95, p[1] * 0.95, 0.6, 0.05, 31.2, 38.5, 6, false);
  },
  replaces: [scaleRing([[8.9, 9.5], [-0.8, 14.3], [-7.3, -17.6], [-5.1, -18.8]], 1.15)],
  facts: {
    Built: '1914 (Benjamin Geer McDougall), the Federal Realty Building — "the Wedding Cake"',
    Height: '42 m, 12 floors (OSM)',
    Model: OSM_NOTE + '; crown, pinnacle and mansard proportions from the photo; construction start estimated'
  },
  sources: [WIKI + 'Cathedral_Building']
};

// ------------------------------------------------------------ Ford Assembly Building (Richmond)
// Albert Kahn, built 1930 (opened 1931): the largest assembly plant on the West Coast,
// ≈500,000 sq ft (Wikipedia); Jeep and tank assembly in WWII; closed 1956; damaged 1989;
// rehabilitated 2008 (the Craneway Pavilion). OSM outline 124 × 321 m (frame 0.1°), 17.3 m:
// the main assembly hall with white roof monitors (photo), the Craneway at the south end on
// the water, and the entrance pavilion between them.
const fordRichmond: Landmark = {
  id: 'ford_richmond_assembly_plant',
  name: 'Ford Assembly Building (Craneway)',
  kind: 'building',
  built: [1930.2, 1931.2],
  end: 9999,
  anchor: [-122.358387, 37.91058],
  build: b => {
    const brick = '#C9A66B';
    const glass = '#6F8794';
    // main assembly hall
    b.color(brick).box(-2.7, 33.3, -1, 99.2, 265.4, 3.5);
    b.color(glass).box(-2.7, 33.3, 2.5, 99.4, 265.6, 6.5);
    b.color(brick).box(-2.7, 33.3, 9, 99.2, 265.4, 2.2);
    b.color('#8E8A80').cap(rect(-2.7, 33.3, 99.2, 265.4), 11.2);
    b.color('#F0EFEA');
    for (let y = -88; y <= 160; y += 18) b.box(-2.7, y, 11.2, 92, 6, 2.8); // roof monitors (across the hall)
    // stair towers on the east side
    b.color(brick).box(48.3, -63, -1, 3, 16, 13).box(48.2, -2.4, -1, 3, 15.8, 13).box(48.5, 58.7, -1, 3.3, 15.4, 13).box(48.1, 119, -1, 2.4, 15.2, 13);
    // the Craneway (south end) and the entrance pavilion
    b.color(brick).box(9.65, -127.1, -1, 123.7, 55.4, 6);
    b.color(glass).box(9.65, -127.1, 5, 123.9, 55.6, 9.5);
    b.color(brick).box(9.65, -127.1, 14.5, 123.7, 55.4, 2.8);
    b.color('#2F3A44').box(9.65, -127.1, 17.3, 60, 40, 2.0); // raised monitor (solar panels today)
    b.color(brick).box(-46, -101, -1, 14, 16, 18.5);
    b.color(glass).box(-53.2, -101, 4, 0.3, 10, 12);
  },
  replaces: [rect(6, 5, 128, 325)],
  facts: {
    Built: '1930 – 31 (Albert Kahn) on Richmond’s inner harbour; ≈500,000 sq ft',
    History: 'Ford assembly 1931–56 (Jeeps and tanks in WWII); Loma Prieta damage 1989; rehabilitated 2008; part of Rosie the Riveter/WWII Home Front NHP',
    Model: OSM_NOTE + '; wall, monitor and Craneway heights estimated from the photo (OSM height 17.3 m); construction months estimated'
  },
  sources: [WIKI + 'Ford_Assembly_Building']
};

// =================================================================== export

export const EASTBAY: Landmark[] = [
  satherTower,
  satherGate,
  greekTheatre,
  memorialStadium1923,
  memorialStadium2012,
  doeNorth,
  doeSouth,
  cityHallOakland,
  foxOakland,
  paramountOakland,
  tribuneBase,
  tribuneTower,
  oaklandArena,
  necklace1925,
  necklace1987,
  coliseum1966,
  coliseum1996,
  temple,
  station16th,
  pergola,
  millsHall,
  missionSanJose1809,
  missionSanJoseGothic,
  missionSanJose1985,
  missionSanJoseWing,
  ussHornet,
  diabloSummit,
  goldenGateFields,
  claremontHotel,
  cathedralChristTheLight,
  cathedralBuilding,
  fordRichmond
];
