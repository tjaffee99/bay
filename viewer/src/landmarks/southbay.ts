/**
 * Peninsula, South Bay and Marin reconstructions (San Mateo, Santa Clara and
 * Marin counties) — data/research/landmarks_southbay.md.
 *
 * Footprints are the OpenStreetMap outlines and 3D building parts (via Overture
 * 2026-10-21.0, © OpenStreetMap contributors, ODbL) of the standing buildings,
 * in a frame aligned with the building (`b.frame(0, 0, 0, bearing)`: local +y at
 * `bearing`, +x at `bearing + 90°`); positions and roof layouts were checked on
 * an orthophoto (Esri World Imagery, viewed only). Heights come from Wikipedia /
 * official figures or the OSM height tags, as named in each model's facts;
 * massing, roof pitches and colours from reference photographs. Demolished and
 * replaced structures (old Stanford Stadium, the 1903 Memorial Church spire,
 * Hangar One's skin, San José's electric light tower …) are placed from
 * documented positions. Every estimate is named in the model's facts ("Model: …").
 */
import {MeshBuilder, circle, ellipse, localToLngLat, rect, roundedRect, type V2, type V3} from './kit';
import type {Landmark} from './types';
import {elevationAt} from '../layers/elevation';

const WIKI = 'https://en.wikipedia.org/wiki/';
const FT = 0.3048;

// ------------------------------------------------------------------ helpers

/** Ring of an annulus sector: points at radius r between bearings a0..a1 (deg, clockwise from north). */
function arcPts(cx: number, cy: number, r: number, a0: number, a1: number, n: number): V2[] {
  const out: V2[] = [];
  for (let i = 0; i <= n; i++) {
    const a = ((a0 + ((a1 - a0) * i) / n) * Math.PI) / 180;
    out.push([cx + Math.sin(a) * r, cy + Math.cos(a) * r]);
  }
  return out;
}

/** Annulus (ring band) as a polygon with a hairline slit, for `replaces` (centroid tests). */
function annulusPoly(cx: number, cy: number, r0: number, r1: number, n = 48): V2[] {
  const outer = arcPts(cx, cy, r1, 0.5, 359.5, n);
  const inner = arcPts(cx, cy, r0, 359.5, 0.5, n);
  return [...outer, ...inner];
}

/** Revolved surface: radial profile [r, z][] swept between bearings a0..a1 (segments of `step` deg). */
function revolve(b: MeshBuilder, cx: number, cy: number, prof: [number, number][], a0 = 0, a1 = 360, step = 10) {
  const n = Math.max(1, Math.round((a1 - a0) / step));
  for (let i = 0; i < n; i++) {
    const t0 = ((a0 + ((a1 - a0) * i) / n) * Math.PI) / 180;
    const t1 = ((a0 + ((a1 - a0) * (i + 1)) / n) * Math.PI) / 180;
    for (let k = 0; k < prof.length - 1; k++) {
      const [ra, za] = prof[k];
      const [rb, zb] = prof[k + 1];
      b.quad(
        [cx + Math.sin(t0) * ra, cy + Math.cos(t0) * ra, za],
        [cx + Math.sin(t1) * ra, cy + Math.cos(t1) * ra, za],
        [cx + Math.sin(t1) * rb, cy + Math.cos(t1) * rb, zb],
        [cx + Math.sin(t0) * rb, cy + Math.cos(t0) * rb, zb]
      );
    }
  }
}

/** Hipped roof (b.hip) over a rectangle given by its edges [u0, u1, v0, v1] in the current frame. */
function hipR(b: MeshBuilder, r: [number, number, number, number], z0: number, h: number) {
  b.hip((r[0] + r[1]) / 2, (r[2] + r[3]) / 2, r[1] - r[0], r[3] - r[2], z0, h);
}

/** Box from edges [u0, u1, v0, v1]. */
function boxR(b: MeshBuilder, r: [number, number, number, number], z0: number, z1: number, top = true) {
  b.prism(rect((r[0] + r[1]) / 2, (r[2] + r[3]) / 2, r[1] - r[0], r[3] - r[2]), z0, z1, {top});
}

/** Octagon (flat sides facing the frame axes) of circumradius r. */
function octagon(cx: number, cy: number, r: number): V2[] {
  return circle(0, 0, r, 8).map(([x, y]) => {
    const a = Math.PI / 8;
    return [cx + x * Math.cos(a) - y * Math.sin(a), cy + x * Math.sin(a) + y * Math.cos(a)] as V2;
  });
}

/**
 * Ground height at a point of a landmark's local frame (bearing `brg`) relative to the
 * anchor's ground — for long buildings over uneven ground (as in batch4.ts).
 */
function groundDz(anchor: V2, brg: number, u: number, v: number) {
  const a = (brg * Math.PI) / 180;
  const p = localToLngLat(anchor, [u * Math.cos(a) + v * Math.sin(a), -u * Math.sin(a) + v * Math.cos(a)]);
  return elevationAt(p[0], p[1]) - elevationAt(anchor[0], anchor[1]);
}

/** Polygon in a rotated frame → anchor-local metres (for `replaces`). */
function rotPoly(ring: V2[], bearing: number, dx = 0, dy = 0): V2[] {
  const a = (bearing * Math.PI) / 180;
  const ex: V2 = [Math.cos(a), -Math.sin(a)];
  const ey: V2 = [Math.sin(a), Math.cos(a)];
  return ring.map(([u, v]) => [dx + u * ex[0] + v * ey[0], dy + u * ex[1] + v * ey[1]] as V2);
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

// =================================================================== APPLE PARK (Cupertino)

const GLASS = '#A7BBC5';
const GLASS_DARK = '#7F96A4';
const WHITE = '#ECEDEA';
const PV = '#3E434A';

/**
 * Ring centre: OSM centroid of the ring (-122.009029, 37.334836) moved by the
 * centre of the roof edges measured on the orthophoto at the four cardinal
 * points (+1.5 m E, +2.0 m N; the roof's relief displacement is ~±3 m).
 */
const APPLE_RING: V2 = [-122.009012, 37.334854];
/** Bearings of the nine atria (radial glass roofs) measured on the orthophoto. */
const APPLE_ATRIA = [0, 31, 60, 90, 134, 180, 227, 270, 316];

const appleRing = landmark(
  'apple_park_ring',
  'Apple Park — the Ring',
  'building',
  [2013.9, 2017.3],
  9999,
  APPLE_RING,
  b => {
    const R_GLASS_OUT = 461 / 2; // Wikipedia: diameter 1,512 ft (461 m)
    const R_ROOF_OUT = 236.4; // orthophoto: outer roof edge
    const R_ROOF_IN = 170.3; // orthophoto: inner roof edge
    const R_GLASS_IN = R_ROOF_IN + (R_ROOF_OUT - R_GLASS_OUT); // same canopy depth inside (estimate)
    const EAVE = 57 * FT; // 57 ft at the edge
    const CROWN = 75 * FT; // 75 ft at the centre of the roof
    const SKY0 = 198.5;
    const SKY1 = 208.5;
    const step = 2;
    const inAtrium = (a: number) => APPLE_ATRIA.some(t => Math.abs(((a - t + 540) % 360) - 180) < 3.6);
    for (let a = 0; a < 360; a += step) {
      const mid = a + step / 2;
      const atr = inAtrium(mid);
      // facades: curved glass, 4 storeys
      b.color(atr ? GLASS_DARK : GLASS);
      revolve(b, 0, 0, [[R_GLASS_OUT, 0], [R_GLASS_OUT, EAVE - 0.6]], a, a + step, step);
      revolve(b, 0, 0, [[R_GLASS_IN, 0], [R_GLASS_IN, EAVE - 0.6]], a, a + step, step);
      // white glass sunshade canopies at each floor, both faces (~3 m deep)
      b.color(WHITE);
      for (const z of [4.6, 8.9, 13.2]) {
        revolve(b, 0, 0, [[R_GLASS_OUT, z], [R_GLASS_OUT + 3, z]], a, a + step, step);
        revolve(b, 0, 0, [[R_GLASS_IN, z], [R_GLASS_IN - 3, z]], a, a + step, step);
      }
      // roof: white canopy edges, PV fields sloping up to the central skylight band
      const zIn = EAVE + 0.2 + (CROWN - 1.3 - EAVE) * 0.2;
      b.color(WHITE);
      revolve(b, 0, 0, [[R_ROOF_OUT, EAVE - 0.6], [R_ROOF_OUT, EAVE], [R_GLASS_OUT, EAVE + 0.2]], a, a + step, step);
      revolve(b, 0, 0, [[R_GLASS_IN, EAVE + 0.2], [R_ROOF_IN, EAVE], [R_ROOF_IN, EAVE - 0.6]], a, a + step, step);
      revolve(b, 0, 0, [[R_ROOF_OUT, EAVE - 0.6], [R_GLASS_OUT, EAVE - 0.6]], a, a + step, step);
      revolve(b, 0, 0, [[R_GLASS_IN, EAVE - 0.6], [R_ROOF_IN, EAVE - 0.6]], a, a + step, step);
      b.color(atr ? GLASS_DARK : PV);
      revolve(b, 0, 0, [[R_GLASS_OUT, EAVE + 0.2], [SKY1, CROWN - 1.3]], a, a + step, step);
      revolve(b, 0, 0, [[SKY0, CROWN - 1.3], [R_GLASS_IN, zIn]], a, a + step, step);
      // skylight band (glazed, raised) on the ring's centre line
      b.color(atr ? GLASS_DARK : '#8EA6B4');
      revolve(b, 0, 0, [[SKY1, CROWN - 1.3], [SKY1, CROWN], [SKY0, CROWN], [SKY0, CROWN - 1.3]], a, a + step, step);
    }
    // the inner slope's lower edge closes onto the inner canopy
    b.color(PV);
    revolve(b, 0, 0, [[R_GLASS_IN, EAVE + 0.2 + (CROWN - 1.3 - EAVE) * 0.2], [R_GLASS_IN, EAVE + 0.2]], 0, 360, 4);
  },
  {
    Built: 'Cupertino approved the plans Oct 15, 2013 and demolition of the former HP campus followed; construction 2014–17; employees moved in from Apr 2017',
    Architect: 'Foster + Partners (Norman Foster); engineers Arup',
    Size: 'ring 1,512 ft (461 m) in diameter, 4,805 ft (1.46 km) round; four storeys; 2.8 million sq ft; eight sections between nine atria',
    Height: 'about 57 ft (17.4 m) at the edge and 75 ft (22.9 m) at the centre of the roof',
    Roof: '≈ 17 MW of solar panels; white glass canopies at every floor on both faces',
    Model:
      'ring and roof edges measured on the orthophoto (roof 472.8 m across, inner edge 340.6 m); glazed central skylight band and the nine radial atrium roofs from the orthophoto; inner facade radius, canopy depth (3 m) and floor levels estimated',
    Previously: 'Hewlett-Packard Cupertino campus (1970s), demolished 2013–14'
  },
  [WIKI + 'Apple_Park', 'https://www.fosterandpartners.com/projects/apple-park'],
  [annulusPoly(0, 0, 165, 245, 64), circle(0, 0, 8, 12)]
);

const STEVE_JOBS_THEATER: V2 = [-122.007454, 37.330878];
const steveJobsTheater = landmark(
  'steve_jobs_theater',
  'Steve Jobs Theater',
  'building',
  [2015.0, 2017.7],
  9999,
  STEVE_JOBS_THEATER,
  b => {
    // 41 m glass cylinder, 7 m high, no mullions; 47 m carbon-fibre disc roof (155 ft)
    b.color('#B9CDD6').cylinder(0, 0, 20.5, 0, 6.6, 40, {top: false});
    b.color('#D7D9DA');
    revolve(b, 0, 0, [[0, 7.15], [20.5, 7.1], [23.6, 6.95], [23.6, 6.75], [20.5, 6.6], [0, 6.6]], 0, 360, 9);
    // stone paving ring around the pavilion (orthophoto: light disc ≈ 58 m across)
    b.color('#CFC9BD').cap(circle(0, 0, 29, 40), 0.15, [circle(0, 0, 20.5, 40)]);
  },
  {
    Opened: 'Sep 12, 2017 (iPhone X keynote); 1,000-seat auditorium underground',
    Pavilion: 'glass cylinder 41 m across and ≈ 7 m high, the structural glass carrying the roof',
    Roof: 'carbon-fibre disc 155 ft (47 m) across, 44 radial panels (Premier Composite Technologies, Dubai)',
    Model: 'roof thickness and the paved ring around the pavilion from the orthophoto (estimated)'
  },
  [WIKI + 'Apple_Park', 'https://www.istructe.org/structural-awards/projects/2018/steve-jobs-theater-pavillion/', 'https://www.pct.ae/steve-jobs-theater'],
  [circle(0, 0, 24, 16)]
);

const APPLE_VISITOR: V2 = [-122.005375, 37.332847];
const appleVisitorCenter = landmark(
  'apple_park_visitor_center',
  'Apple Park Visitor Center',
  'building',
  [2015.5, 2017.88],
  9999,
  APPLE_VISITOR,
  b => {
    // glass box under a thin carbon-fibre roof (orthophoto: roof 28.5 × 73.5 m, OSM: 10.6 m)
    b.color(GLASS).prism(roundedRect(0, 0, 25, 70, 4.5, 4), 0, 9.9, {top: false});
    b.color('#D9CFBE').box(0, 0, 0, 12, 46, 9.9); // stone core under the roof terrace
    b.color('#E3E4E2').prism(roundedRect(0, 0, 28.5, 73.5, 6, 4), 9.9, 10.6);
    // roof terrace with a timber louvre canopy (orthophoto)
    b.color('#A98B6A').box(0, 0, 10.6, 12, 44, 0.2);
    b.color('#B9A285');
    for (let y = -21; y <= 21; y += 2) b.box(0, y, 13.4, 13, 0.5, 0.35);
    for (const x of [-6, 6]) for (const y of [-21, 0, 21]) b.box(x, y, 10.6, 0.4, 0.4, 2.8);
  },
  {
    Opened: 'Nov 17, 2017',
    Size: 'two storeys, 20,135 sq ft (1,871 m²): shop, café, model of the campus; roof terrace over an olive grove',
    Model: 'roof outline from the orthophoto (28.5 × 73.5 m); glass line, stone core and terrace louvres estimated from the orthophoto'
  },
  [WIKI + 'Apple_Park'],
  [roundedRect(0, 0, 30, 75, 6, 2)]
);


// =================================================================== STANFORD UNIVERSITY

/** Main Quad grid: the campus axis Palm Drive → Oval → Quad → Memorial Church runs at 195°/15°. */
const QUAD: V2 = [-122.170217, 37.427648];
const STANFORD_BRG = 15;
const SANDSTONE = '#D5BB8E';
const SANDSTONE_SH = '#C6A97A';
const TILE = '#B96A50';
const TILE_DARK = '#A65D46';
const QUAD_PITCH = Math.tan((27 * Math.PI) / 180);

// ---- generated from the OSM "Main Quad" outline (quad frame, metres; scratch tool rects.py):
// wings = greedy maximal rectangles covering the plan (minus the inner courtyard arcade and the church),
// [u0, u1, v0, v1, zone] with zone 1 = Inner Quad ring (one tall storey), 2 = Outer Quad (two storeys)
const QUAD_WINGS: [number, number, number, number, number][] = [[-134.3,-19.3,82.3,107.3,2],[32.2,134.7,84.3,107.8,2],[-94.3,-68.3,56.3,107.3,2],[71.2,93.7,58.3,107.8,2],[-53.3,-28.8,63.8,107.3,2],[-141.3,-119.8,51.8,100.3,2],[30.2,54.7,64.8,107.3,2],[-140.8,-119.8,-128.2,-80.2,2],[121.7,142.7,53.3,99.8,2],[-140.8,-117.8,-62.2,-25.2,2],[103.7,135.7,-135.2,-108.7,2],[-134.8,-101.8,-134.2,-108.7,2],[134.7,142.2,-10.2,101.8,2],[119.2,142.2,-10.2,26.3,2],[-141.3,-133.8,-10.2,100.3,2],[-141.3,-118.3,-10.2,25.8,2],[120.2,142.2,-60.7,-24.7,2],[122.2,142.7,-129.2,-91.7,2],[-59.8,-24.3,-77.7,-58.2,1],[135.2,141.7,-130.7,-24.7,2],[93.7,112.2,-60.7,-24.7,1],[93.7,111.7,-10.2,26.3,1],[26.2,60.7,-77.2,-58.2,1],[-59.3,-18.8,25.3,41.3,1],[20.2,60.7,25.3,41.3,1],[20.2,27.7,25.3,107.3,2],[-110.3,-93.8,-9.7,26.3,1],[-109.8,-93.8,-62.2,-25.2,1],[-26.3,-19.3,25.3,107.3,2],[-89.8,-66.8,-134.2,-111.2,2],[68.7,135.7,-135.2,-127.7,2],[69.2,91.2,-135.2,-112.7,2],[-90.3,-65.8,-77.7,-58.2,1],[68.7,91.2,-76.2,-58.2,1],[-89.8,-66.8,25.3,41.3,1],[68.2,91.2,25.3,41.3,1],[121.2,142.2,-94.2,-86.7,2],[6.7,14.7,98.3,108.8,2],[-13.3,-5.3,98.3,108.8,2]];
const QUAD_PLAN: {o: V2[]; h: V2[][]}[] = [{"o":[[20.2,25.4],[20.4,99.6],[14.6,99.6],[14.6,98.1],[6.6,98.2],[6.7,108.7],[14.7,108.7],[14.7,107.3],[133.9,107.7],[137.4,106.8],[141.6,102.8],[142.6,99.3],[142.2,-10.5],[97.1,-10.4],[97.0,-24.6],[142.3,-24.6],[142.5,-128.9],[138.7,-134.0],[134.8,-135.2],[68.7,-135.2],[69.2,-112.6],[91.0,-112.8],[91.2,-127.6],[103.2,-127.8],[103.4,-108.9],[122.0,-108.7],[121.6,-94.3],[118.9,-92.1],[118.4,-90.1],[119.1,-88.1],[121.6,-86.9],[121.7,-81.0],[134.9,-81.0],[134.9,-60.8],[91.2,-60.9],[91.2,-76.3],[68.5,-76.3],[68.6,-61.2],[60.8,-61.2],[60.8,-77.0],[26.1,-77.0],[26.1,-61.4],[14.6,-61.4],[14.7,-58.4],[93.8,-58.4],[93.8,25.4]],"h":[[[30.3,64.8],[30.2,80.6],[27.9,80.6],[27.9,41.1],[60.6,41.3],[61.0,26.1],[68.3,26.2],[68.3,41.2],[91.1,41.3],[91.3,26.0],[134.6,26.2],[134.6,53.3],[121.8,53.2],[121.8,58.5],[118.3,60.9],[118.7,64.7],[121.2,66.5],[121.1,80.7],[97.5,80.6],[96.7,78.1],[93.5,75.8],[93.7,58.4],[71.0,58.5],[71.2,75.8],[68.2,78.3],[67.4,80.6],[57.4,80.7],[57.4,84.1],[54.5,84.1],[54.6,64.9]],[[112.4,-53.5],[119.9,-53.5],[120.0,-32.4],[112.4,-32.3]],[[119.3,-2.8],[119.4,18.2],[111.9,18.2],[111.7,-2.7]]]},{"o":[[-24.1,-77.7],[-59.8,-77.6],[-59.8,-62.1],[-65.8,-62.1],[-65.9,-77.8],[-90.3,-77.8],[-90.3,-62.2],[-133.1,-62.1],[-133.2,-80.2],[-119.9,-80.2],[-119.9,-86.8],[-116.6,-90.4],[-117.6,-92.8],[-120.1,-94.4],[-120.1,-108.6],[-101.6,-108.6],[-101.6,-126.6],[-89.6,-126.6],[-89.6,-111.3],[-66.9,-111.3],[-66.9,-134.2],[-133.8,-134.4],[-139.9,-130.4],[-140.8,-127.5],[-141.0,-25.2],[-96.3,-25.0],[-96.3,-10.0],[-141.1,-10.2],[-141.3,99.6],[-140.2,103.1],[-137.3,106.0],[-134.1,107.0],[-13.5,107.3],[-13.4,108.7],[-5.5,108.7],[-5.5,98.1],[-13.5,98.1],[-13.6,99.6],[-19.1,99.5],[-19.0,25.4],[-93.7,25.4],[-93.7,-58.4],[-12.1,-58.4],[-12.1,-61.4],[-24.1,-61.4]],"h":[[[-106.6,78.9],[-106.6,82.0],[-120.1,82.2],[-120.0,65.2],[-118.3,63.8],[-117.6,60.5],[-120.0,57.7],[-120.0,51.7],[-133.8,51.8],[-133.3,26.0],[-89.8,26.4],[-89.8,41.3],[-66.8,41.4],[-66.9,26.4],[-59.4,26.3],[-59.2,41.4],[-26.8,41.5],[-26.5,79.9],[-28.9,79.9],[-28.8,64.0],[-53.5,63.8],[-53.5,81.3],[-55.5,81.3],[-55.5,79.5],[-68.5,79.5],[-68.5,56.4],[-94.1,56.3],[-94.1,79.0]],[[-110.1,-32.8],[-117.8,-32.8],[-117.9,-54.1],[-110.3,-54.0]],[[-110.5,18.5],[-118.2,18.5],[-118.0,-2.5],[-110.4,-2.4]]]}];

/** Inner Quad courtyard (OSM hole) and its arcade band. */
const QUAD_COURT: [number, number, number, number] = [-88.5, 88.6, -53.2, 20.2];

function quadWings(b: MeshBuilder, zone: number, eave: number) {
  for (const w of QUAD_WINGS) {
    if (w[4] !== zone) continue;
    const r: [number, number, number, number] = [w[0], w[1], w[2], w[3]];
    b.color(SANDSTONE);
    boxR(b, r, 0, eave, false);
    b.color(TILE);
    hipR(b, [r[0] - 0.6, r[1] + 0.6, r[2] - 0.6, r[3] + 0.6], eave, (Math.min(r[1] - r[0], r[3] - r[2]) / 2 + 0.6) * QUAD_PITCH);
  }
}

const innerQuad = landmark(
  'stanford_inner_quad',
  'Stanford Main Quad — Inner Quad',
  'building',
  [1887.37, 1891.75],
  9999,
  QUAD,
  b => {
    b.frame(0, 0, 0, STANFORD_BRG, () => {
      quadWings(b, 1, 7.5);
      // arcade round the courtyard: sandstone piers carrying a tiled lean-to
      const [u0, u1, v0, v1] = QUAD_COURT;
      const W = 5.2;
      b.color(TILE_DARK);
      const lean = (a: V3, c: V3, d: V3, e: V3) => b.quad(a, c, d, e);
      lean([u0, v1, 5.2], [u1, v1, 5.2], [u1 + W, v1 + W, 6.6], [u0 - W, v1 + W, 6.6]);
      lean([u0, v0, 5.2], [u1, v0, 5.2], [u1 + W, v0 - W, 6.6], [u0 - W, v0 - W, 6.6]);
      lean([u0, v0, 5.2], [u0, v1, 5.2], [u0 - W, v1 + W, 6.6], [u0 - W, v0 - W, 6.6]);
      lean([u1, v0, 5.2], [u1, v1, 5.2], [u1 + W, v1 + W, 6.6], [u1 + W, v0 - W, 6.6]);
      b.color(SANDSTONE_SH);
      b.wallProfile([[u0, v0], [u1, v0], [u1, v1], [u0, v1]], 3.9, 5.2, true);
      b.color(SANDSTONE);
      const pier = (x: number, y: number) => b.box(x, y, 0, 1.0, 1.0, 3.9);
      for (let u = u0; u <= u1 + 0.1; u += (u1 - u0) / 44) {
        pier(u, v0);
        pier(u, v1);
      }
      for (let v = v0 + (v1 - v0) / 18; v < v1 - 0.1; v += (v1 - v0) / 18) {
        pier(u0, v);
        pier(u1, v);
      }
    });
  },
  {
    Built: 'cornerstone May 14, 1887; the twelve one-storey buildings round the Inner Quad were ready for the university\'s opening on Oct 1, 1891',
    Architects: 'Shepley, Rutan & Coolidge (successors of H. H. Richardson), plan by Frederick Law Olmsted',
    Material: 'buff sandstone from the Greystone quarry (Almaden, San José), red clay tile roofs, arcades round the courtyard',
    Model:
      'plan from the OpenStreetMap outline of the Main Quad (© OSM contributors, ODbL), split into wings by maximal rectangles; courtyard 177 × 73 m (OSM); eave height (7.5 m), roof pitch (27°) and the arcade (5.2 m deep, 45 bays) estimated from photographs and the orthophoto'
  },
  [WIKI + 'Main_Quad_(Stanford_University)', WIKI + 'Stanford_University'],
  [rotPoly(rect(0, -14, 286, 246), STANFORD_BRG, 0, 0)]
);

const outerQuad = landmark(
  'stanford_outer_quad',
  'Stanford Main Quad — Outer Quad',
  'building',
  [1898.5, 1903.0],
  9999,
  QUAD,
  b => {
    b.frame(0, 0, 0, STANFORD_BRG, () => {
      // whole plan (incl. the rounded outer corners) as a low base; wings rise above it
      b.color(SANDSTONE);
      for (const p of QUAD_PLAN) b.prism(p.o, 0, 6.8, {holes: p.h, top: false});
      b.color(TILE_DARK);
      for (const p of QUAD_PLAN) b.cap(p.o, 6.8, p.h);
      quadWings(b, 2, 11.5);
    });
  },
  {
    Built: 'the fourteen buildings of the Outer Quad and Memorial Court were completed about 1903 under Charles Coolidge, for Jane Stanford',
    '1906': 'damaged in the earthquake of Apr 18, 1906; restored by 1909',
    Model:
      'plan from the OpenStreetMap outline (© OSM contributors, ODbL), wings by maximal rectangles; two-storey eave (11.5 m) and roof pitch estimated; construction start (1898) estimated'
  },
  [WIKI + 'Main_Quad_(Stanford_University)']
);

/** Memorial Arch over the entrance of Memorial Court: its two piers stand on as the 8 × 10.6 m pavilions (OSM). */
const memorialArch = landmark(
  'stanford_memorial_arch',
  'Stanford Memorial Arch',
  'monument',
  [1899.2, 1902.5],
  1906.3,
  QUAD,
  b => {
    b.frame(0, 0, 0, STANFORD_BRG, () => {
      const v0 = 98.1;
      const v1 = 108.7;
      b.color(SANDSTONE);
      for (const s of [-1, 1]) boxR(b, [s > 0 ? 5.5 : -13.5, s > 0 ? 13.5 : -5.5, v0, v1], 0, 30.5);
      // semicircular arch (span 11 m, springing at 12.5 m) and the attic above it
      const pts: V3[] = [];
      for (let i = 0; i <= 10; i++) {
        const a = Math.PI * (1 - i / 10);
        pts.push([Math.cos(a) * 5.5, 0, 12.5 + Math.sin(a) * 5.5]);
      }
      for (const v of [v0, v1]) {
        for (let i = 0; i < 10; i++) {
          b.quad([pts[i][0], v, pts[i][2]], [pts[i + 1][0], v, pts[i + 1][2]], [pts[i + 1][0], v, 24.4], [pts[i][0], v, 24.4]);
        }
      }
      for (let i = 0; i < 10; i++) b.quad([pts[i][0], v0, pts[i][2]], [pts[i + 1][0], v0, pts[i + 1][2]], [pts[i + 1][0], v1, pts[i + 1][2]], [pts[i][0], v1, pts[i][2]]);
      boxR(b, [-5.5, 5.5, v0, v1], 24.4, 30.5);
      // frieze "The Progress of Civilization in America", 12 ft high round all four sides
      b.color('#C4A574');
      boxR(b, [-13.7, 13.7, v0 - 0.2, v1 + 0.2], 24.4, 28.1);
      b.color('#B79A6E');
      boxR(b, [-14.2, 14.2, v0 - 0.6, v1 + 0.6], 30.5, 31.3);
    });
  },
  {
    Built: 'mostly in 1899; the frieze "The Progress of Civilization in America" (12 ft high, 232 ft round the four sides) finished in 1902',
    Height: 'about 100 ft (30.5 m)',
    Fate: 'destroyed in the earthquake of Apr 18, 1906 and never rebuilt; its two pier stubs remain as the pavilions at the entrance of Memorial Court',
    Model:
      'piers on the two 8 × 10.6 m pavilions of the OSM outline (their perimeter matches the 232 ft frieze); arch span and springing height estimated from photographs (LOW CONFIDENCE)'
  },
  ['https://pcad.lib.washington.edu/building/5117', 'https://quake06.stanford.edu/3-earthquake-impacts-prestige', WIKI + 'Main_Quad_(Stanford_University)']
);

// ---- Memorial Church: frame 15°, anchor = OSM part centroid; facade (north) at v = 31.5
const MEMCHU: V2 = [-122.170471, 37.426893];

function semi(cx: number, cy: number, r: number, a0: number, n = 10): V2[] {
  return arcPts(cx, cy, r, a0, a0 + 180, n);
}

function memChuBody(b: MeshBuilder, crossingTop: number) {
  // nave (21 m wide), gable roof along the axis
  b.color(SANDSTONE);
  boxR(b, [-10.2, 10.8, 3.5, 31.5], 0, 15);
  b.color(TILE).gable(0.3, 17.5, 22, 28.4, 15, 8, true);
  // facade gable (mosaic: 84 ft wide at the base, 30 ft high)
  b.color(SANDSTONE);
  b.quad([-11.2, 31.6, 15], [11.8, 31.6, 15], [11.8, 32.6, 15], [-11.2, 32.6, 15]);
  boxR(b, [-11.2, 11.8, 31.5, 32.6], 0, 15);
  b.tri([-11.2, 32.6, 15], [11.8, 32.6, 15], [0.3, 32.6, 24.5]).tri([-11.2, 31.5, 15], [11.8, 31.5, 15], [0.3, 31.5, 24.5]);
  b.quad([-11.2, 31.5, 15], [0.3, 31.5, 24.5], [0.3, 32.6, 24.5], [-11.2, 32.6, 15]);
  b.quad([11.8, 31.5, 15], [0.3, 31.5, 24.5], [0.3, 32.6, 24.5], [11.8, 32.6, 15]);
  b.color('#C9A24E'); // gold-ground mosaic
  b.quad([-8.5, 32.7, 8.5], [9.1, 32.7, 8.5], [9.1, 32.7, 15.5], [-8.5, 32.7, 15.5]);
  b.tri([-6, 32.7, 15.5], [6.6, 32.7, 15.5], [0.3, 32.7, 21]);
  // turrets flanking the nave
  for (const x of [-10.1, 10.9]) {
    b.color(SANDSTONE).cylinder(x, 23.2, 2.3, 0, 17, 10);
    b.color(TILE).pyramid(circle(x, 23.2, 2.6, 10), 17, [x, 23.2, 21.5]);
  }
  // transepts and apse: walls with half-cone roofs
  b.color(SANDSTONE);
  boxR(b, [-15, -9.4, -15, 3.5], 0, 13);
  boxR(b, [9.9, 16, -15, 3.5], 0, 13);
  b.prism(semi(-15, -5.75, 9.25, 180), 0, 13, {top: false});
  b.prism(semi(16, -5.75, 9.25, 0), 0, 13, {top: false});
  boxR(b, [-8.3, 9.3, -19.5, -15], 0, 13);
  b.prism(semi(0.5, -19.5, 8.3, 90), 0, 13, {top: false});
  b.color(TILE);
  b.pyramid(semi(-15, -5.75, 9.6, 180), 13, [-15, -5.75, 19.5]);
  b.pyramid(semi(16, -5.75, 9.6, 0), 13, [16, -5.75, 19.5]);
  b.pyramid(semi(0.5, -19.5, 8.7, 90), 13, [0.5, -19.5, 19]);
  b.gable(-12.2, -5.75, 6.4, 19.1, 13, 6.5, false);
  b.gable(12.9, -5.75, 6.4, 19.1, 13, 6.5, false);
  b.gable(0.5, -17.2, 17.6, 4.8, 13, 6, true);
  // round chapel (south-west) and the low sacristies beside the crossing
  b.color(SANDSTONE).cylinder(-21.4, -21.6, 4.8, 0, 8, 12);
  b.color(TILE).pyramid(circle(-21.4, -21.6, 5.1, 12), 8, [-21.4, -21.6, 11.5]);
  b.color(SANDSTONE);
  boxR(b, [-12.6, -10.2, 2, 7.2], 0, 7);
  boxR(b, [10.8, 15.2, 2, 7.3], 0, 7);
  // crossing tower walls
  boxR(b, [-9.4, 10, -15, 3.5], 0, crossingTop);
}

const memChu1903 = landmark(
  'stanford_memorial_church_1903',
  'Stanford Memorial Church (1903)',
  'building',
  [1900.0, 1903.07],
  1906.3,
  MEMCHU,
  b => {
    b.frame(0, 0, 0, STANFORD_BRG, () => {
      memChuBody(b, 34);
      // clock and bell tower over the crossing with corner pinnacles and a twelve-sided 80 ft spire
      b.color(SANDSTONE);
      for (const [x, y] of [[-9.4, -15], [10, -15], [10, 3.5], [-9.4, 3.5]] as V2[]) {
        b.cylinder(x, y, 1.4, 34, 37, 8);
        b.color(TILE).pyramid(circle(x, y, 1.5, 8), 37, [x, y, 40]).color(SANDSTONE);
      }
      b.color('#EDE6D4');
      b.quad([-2, 3.6, 28], [2.6, 3.6, 28], [2.6, 3.6, 32], [-2, 3.6, 32]); // clock face toward the court
      b.color(TILE).pyramid(circle(0.3, -5.75, 7.6, 12), 34, [0.3, -5.75, 34 + 80 * FT]);
    });
  },
  {
    Built: 'groundbreaking May 1899, construction from Jan 1900; dedicated Jan 25, 1903 — Jane Stanford\'s memorial to Leland Stanford',
    Design: 'Charles A. Coolidge and Clinton Day after H. H. Richardson; buff sandstone, red tile',
    Tower: 'clock and bell tower over the crossing with a twelve-sided spire about 80 ft (24 m) tall',
    Fate: 'Apr 18, 1906: the spire and clock tower fell onto the chancel roof, the facade fell into the Inner Quad; most of the church was taken down stone by stone and rebuilt',
    Model:
      'plan from the OpenStreetMap outline (© OSM contributors, ODbL); spire height documented; crossing tower height (34 m), pinnacles and wall heights estimated from photographs (LOW CONFIDENCE)'
  },
  [WIKI + 'Stanford_Memorial_Church', 'https://orsl.stanford.edu/memorial-church-history']
);

const memChu1913 = landmark(
  'stanford_memorial_church',
  'Stanford Memorial Church',
  'building',
  [1908.0, 1913.5],
  9999,
  MEMCHU,
  b => {
    b.frame(0, 0, 0, STANFORD_BRG, () => {
      memChuBody(b, 22);
      // low crossing roof with the domed skylight that replaced the tower
      b.color(TILE).pyramid(rect(0.3, -5.75, 20.2, 19.3), 22, [0.3, -5.75, 29]);
      b.color('#9FB1B8').pyramid(rect(0.3, -5.75, 7.4, 7.4), 26.5, [0.3, -5.75, 30.5]);
    });
  },
  {
    Rebuilt: 'repairs from 1908; reopened 1913 without the tower (a domed skylight over the crossing); facade mosaic remade; interior mosaics finished 1917',
    '1989': 'Loma Prieta earthquake damage; closed until the rededication of Nov 1, 1992 (30,000 new red clay tiles)',
    Size: 'about 190 × 150 ft (58 × 46 m); facade mosaic 84 ft wide, 30 ft high',
    Model:
      'plan from the OpenStreetMap outline (© OSM contributors, ODbL); roof shapes from the orthophoto; wall, ridge and crossing heights estimated from photographs'
  },
  [WIKI + 'Stanford_Memorial_Church', 'https://orsl.stanford.edu/memorial-church-history']
);

// ---- Hoover Tower (OSM 3D parts, frame 15°)
const HOOVER: V2 = [-122.166993, 37.427622];
const hooverTower = landmark(
  'hoover_tower',
  'Hoover Tower',
  'tower',
  [1939.6, 1941.47],
  9999,
  HOOVER,
  b => {
    b.frame(0, 0, 0, STANFORD_BRG, () => {
      const TAN = '#D9C7A4';
      b.color(TAN);
      boxR(b, [-18.7, 18.7, -19.2, 17.6], 0, 11);
      boxR(b, [-12.2, 13, -12.7, 12.1], 11, 14.3);
      boxR(b, [-8.8, 10, -9.8, 8.8], 14.3, 65);
      // entrance pavilion (north-east face) with its pyramidal lantern
      boxR(b, [-6.7, 7.1, 8.6, 22.5], 0, 18.5);
      b.color('#B65E40').pyramid(octagon(0.3, 13.8, 4.9), 18.5, [0.3, 13.8, 21.9]);
      // belfry (carillon, observation deck at 250 ft) — octagon with arched openings
      b.color(TAN).prism(octagon(0.5, -0.2, 7.6), 65, 75);
      b.color('#4A4640');
      for (const [x, y, w, d] of [[0.5, 6.85, 6, 0.3], [0.5, -7.25, 6, 0.3], [7.55, -0.2, 0.3, 6], [-6.55, -0.2, 0.3, 6]] as [number, number, number, number][]) {
        b.box(x, y, 67, w, d, 5.5);
      }
      b.color(TAN).prism(octagon(0.5, -0.2, 7.9), 74.2, 75);
      // red-tiled dome and lantern
      b.color('#BD6142').dome(0.6, -0.1, 6.8, 75, 6.5, 16, 4);
      b.color(TAN).cylinder(0.4, -0.2, 2.2, 81.3, 84.5, 10);
      b.color('#BD6142').dome(0.4, -0.2, 2.4, 84.5, 2.5, 10, 2);
    });
  },
  {
    Built: 'groundbreaking Aug 1939; carillon first played Mar 1941; dedicated Jun 20, 1941 for the university\'s 50th anniversary',
    Architect: 'Arthur Brown Jr. (after the tower of the New Cathedral of Salamanca)',
    Height: '285 ft (87 m); observation deck at 250 ft (76 m); 48-bell carillon',
    Model: 'massing from the OpenStreetMap 3D parts (© OSM contributors, ODbL: 11 / 14.3 / 65 / 75 / 81.5 / 87 m); openings and colours from photographs'
  },
  [WIKI + 'Hoover_Tower', 'https://www.hoover.org/research/i-ring-only-peace'],
  [rotPoly(rect(0, -0.8, 39, 41), STANFORD_BRG)]
);

// ---- Green Library, Bing Wing (the 1919 Main Library), OSM outline in frame 15°
const GREEN: V2 = [-122.167615, 37.42692];
const greenLibrary = landmark(
  'stanford_green_library',
  'Stanford Main Library (Green Library, Bing Wing)',
  'building',
  [1916.8, 1919.5],
  9999,
  GREEN,
  b => {
    b.frame(0, 0, 0, STANFORD_BRG, () => {
      const wings: [number, number, number, number][] = [
        [-35.7, 34.9, 15.5, 29.5],
        [-36, 34.4, -28.6, -16.3],
        [-39.1, -24, -16.3, 15.5],
        [24.5, 42.9, -12.6, 13.4]
      ];
      b.color(SANDSTONE);
      for (const w of wings) boxR(b, w, 0, 17, false);
      boxR(b, [-24, 24.5, -16.3, 15.5], 0, 14);
      b.color(TILE);
      for (const w of wings) hipR(b, [w[0] - 0.5, w[1] + 0.5, w[2] - 0.5, w[3] + 0.5], 17, (Math.min(w[1] - w[0], w[3] - w[2]) / 2 + 0.5) * QUAD_PITCH);
      b.color(SANDSTONE_SH).box(3, 2.8, 14, 14, 14, 4);
      b.color(TILE).pyramid(rect(3, 2.8, 15, 15), 18, [3, 2.8, 24.9]);
      // arched entrance loggia on the east front
      b.color(SANDSTONE).box(44.5, 0.4, 0, 3.2, 18, 12);
    });
  },
  {
    Built: 'approved 1913, completed 1919 as the university\'s Main Library; repaired after the 1989 Loma Prieta earthquake (gift of Peter Bing) and renamed the Bing Wing; the large East Wing (1980) is not modelled',
    Architect: 'Arthur Brown Jr. (Bakewell & Brown)',
    Model:
      'outline from OpenStreetMap (© OSM contributors, ODbL; height 24.9 m); wings, the flat central block and the central pyramid from the orthophoto; eave height and the entrance loggia estimated'
  },
  [WIKI + 'Cecil_H._Green_Library'],
  [rotPoly(rect(1.9, -3.5, 82, 66), STANFORD_BRG)]
);

// ---- Stanford Stadium (frame 137.8°: +v = south-east end, field runs NW–SE)
const STANFORD_STADIUM: V2 = [-122.16109, 37.43452];
const STAD_BRG = 137.8;

/** Earcut cap whose vertices take their height from zf (sloped seating decks). */
function slopedCap(b: MeshBuilder, ring: V2[], zf: (u: number, v: number) => number) {
  const tmp = new MeshBuilder();
  tmp.cap(ring, 0);
  const pos = tmp.build().positions.value;
  for (let i = 0; i < pos.length; i += 9) {
    const P = (k: number): V3 => [pos[i + k], pos[i + k + 1], zf(pos[i + k], pos[i + k + 1])];
    b.tri(P(0), P(3), P(6));
  }
}

// OSM 3D parts of the 2006 stadium (frame metres): lower bowl (to 10 m), upper decks (12 m → top), press box
const SS_LOWER: V2[][] = [
  [[-33.5, 62.4], [-63.7, 75.1], [-63.8, -73.1], [-33.5, -60.7]],
  [[35.5, -61.0], [65.2, -73.7], [65.6, 73.9], [35.5, 61.4]],
  [[-43.0, -94.4], [43.7, -94.9], [31.7, -64.7], [-30.0, -64.3]],
  [[32.1, 64.8], [44.6, 95.3], [-42.5, 96.1], [-36.0, 79.6], [-27.7, 79.5], [-27.7, 65.2]],
  [[-43.0, -94.4], [-30.0, -64.3], [-33.5, -60.7], [-63.8, -73.1]],
  [[43.7, -94.9], [65.2, -73.7], [35.5, -61.0], [31.7, -64.7]],
  [[-63.7, 75.1], [-52.3, 70.0], [-36.0, 62.6], [-36.0, 79.6], [-42.5, 96.1]],
  [[35.5, 61.4], [65.6, 73.9], [44.6, 95.3], [32.1, 64.8]]
];
const SS_UPPER: {ring: V2[]; top: number}[] = [
  {ring: [[-85.5, -67.9], [-78.7, -67.9], [-78.7, -73.3], [-69.2, -73.3], [-69.2, -75.3], [-52.3, -68.4], [-52.3, 70.0], [-68.1, 77.2], [-68.5, 75.0], [-78.4, 75.1], [-78.4, 69.6], [-85.5, 69.7]], top: 30},
  {ring: [[54.3, -69.0], [70.5, -76.0], [70.5, -74.3], [81.6, -74.4], [81.5, -33.1], [77.3, -33.1], [77.5, 33.0], [81.5, 33.0], [81.6, 68.5], [70.5, 68.6], [70.5, 75.9], [54.2, 69.1]], top: 27},
  {ring: [[45.9, -100.4], [39.2, -83.5], [-38.0, -82.8], [-45.2, -99.4]], top: 20},
  {ring: [[-52.3, -68.4], [-69.2, -75.3], [-45.2, -99.4], [-38.0, -82.8]], top: 20},
  {ring: [[39.2, -83.5], [45.9, -100.4], [70.5, -76.0], [54.3, -69.0]], top: 20},
  {ring: [[-37.8, 84.2], [39.7, 83.6], [46.5, 100.0], [-44.4, 100.7]], top: 20},
  {ring: [[-68.1, 77.2], [-52.3, 70.0], [-37.8, 84.2], [-44.4, 100.7]], top: 20},
  {ring: [[39.7, 83.6], [54.2, 69.1], [70.5, 75.9], [46.5, 100.0]], top: 20}
];
const SS_OUTLINE: V2[] = [
  [45.9, -100.4], [70.5, -76.0], [70.5, -74.3], [81.6, -74.4], [81.6, -26.6], [77.4, -26.6], [77.4, 26.6], [81.4, 26.5], [81.6, 68.5], [70.5, 68.6],
  [70.5, 75.9], [46.5, 100.0], [-44.4, 100.7], [-68.1, 77.2], [-68.5, 75.0], [-78.4, 75.1], [-78.4, 69.6], [-85.5, 69.7], [-85.5, -67.9], [-78.7, -67.9],
  [-78.7, -73.3], [-69.2, -73.3], [-69.2, -75.3], [-45.2, -99.4]
];

/** 0 at the field's edge → 1 at the stadium's outer edge (chamfered-rectangle distance). */
function ssDepth(u: number, v: number, inU: number, inV: number, outU: number, outV: number) {
  const su = (Math.abs(u) - inU) / (outU - inU);
  const sv = (Math.abs(v) - inV) / (outV - inV);
  return Math.min(1, Math.max(0, su, sv, (Math.abs(u) + Math.abs(v) - inU - inV - 30) / (outU + outV - inU - inV - 30)));
}

const stanfordStadium2006 = landmark(
  'stanford_stadium_2006',
  'Stanford Stadium',
  'stadium',
  [2005.9, 2006.71],
  9999,
  STANFORD_STADIUM,
  b => {
    b.frame(0, 0, 0, STAD_BRG, () => {
      b.color('#4C8A3C').cap(rect(1, -2, 70, 128), 0.3);
      b.color('#F2F2EE').box(1, -2, 0.32, 0.6, 1, 0.02);
      // concourse ring (OSM: 12 m) under the decks
      b.color('#B7B2A8').prism(SS_OUTLINE, 0, 12, {top: false});
      // lower bowl rising from the field to 10 m
      b.color('#8E7365');
      for (const r of SS_LOWER) slopedCap(b, r, (u, v) => 0.6 + 9.4 * ssDepth(u, v, 33.5, 61, 64, 95));
      // upper decks from 12 m to their OSM top heights
      b.color('#C3BEB5');
      for (const d of SS_UPPER) {
        slopedCap(b, d.ring, (u, v) => 12 + (d.top - 12) * ssDepth(u, v, 52.3, 82.8, Math.abs(u) > 60 ? 84 : 81, 100.5));
        b.color('#A9A49B').walls(d.ring, 10, 12).color('#C3BEB5');
      }
      // press box and suites on the west (home) side
      b.color('#C9CBCB');
      boxR(b, [77.4, 92.6, -26.7, 26.6], 0, 17);
      b.color('#6E8A98');
      boxR(b, [77.4, 92.6, -26.7, 26.6], 17, 37);
      b.color('#D4D6D6');
      boxR(b, [76.9, 93, -27.2, 27.1], 37, 38);
      for (const v of [-29.8, 29.8]) boxR(b, [77.4, 81.5, v - 3.2, v + 3.2], 0, 25);
      // video boards behind both end zones
      b.color('#2E3236');
      for (const v of [-116.8, 117]) {
        boxR(b, [-9, 11.3, v - 0.8, v + 0.8], 30, 38);
        boxR(b, [-4, -2.8, v - 0.5, v + 0.5], 0, 30);
        boxR(b, [5, 6.2, v - 0.5, v + 0.5], 0, 30);
      }
    });
  },
  {
    Built: 'demolition and construction began minutes after the last home game of Nov 26, 2005; opened Sep 16, 2006 (Stanford v Navy)',
    Capacity: '≈ 50,400; no running track; field 29 ft (8.8 m) below the surrounding ground',
    Architect: 'Hoover and Associates; Vance Brown Builders',
    Model:
      'stands, decks, press box and video boards from the OpenStreetMap 3D parts (© OSM contributors, ODbL) and the orthophoto; field drawn at ground level (the terrain grid does not resolve the sunken bowl)'
  },
  [WIKI + 'Stanford_Stadium'],
  [rotPoly(rect(-2, 0, 180, 205), STAD_BRG)]
);

/** Earthen bowl of the 1921 stadium round a running track (track oval: half-width 40 m, straights ±36 m). */
function oldStanfordBowl(b: MeshBuilder, rows: number, openS: number) {
  const D = rows * 0.79; // horizontal depth of the seating slope
  const H = rows * 0.27; // rim height above the field
  const R = 40;
  const S = 36;
  const pts: {p: V2; n: V2; t: number}[] = [];
  const N = 40;
  for (let i = 0; i <= N; i++) {
    // angle clockwise from the +v (south-east) axis; two semicircles joined by the straights
    const a = (Math.PI * 2 * i) / N;
    const sx = Math.sin(a);
    const cy = Math.cos(a);
    pts.push({p: [R * sx, (cy >= 0 ? S : -S) + R * cy], n: [sx, cy], t: Math.abs((((a * 180) / Math.PI + 180) % 360) - 180)});
  }
  const inner: V3[] = [];
  const outer: V3[] = [];
  const flush = () => {
    if (inner.length > 1) {
      b.color('#9C8F7A').ribbon(inner, outer);
      b.color('#7F8C5A').wallProfile(outer.map(p => [p[0], p[1]] as V2), 0, H);
      for (const k of [0, inner.length - 1]) b.quad([inner[k][0], inner[k][1], 0.4], [outer[k][0], outer[k][1], 0.4], outer[k], inner[k]);
    }
    inner.length = 0;
    outer.length = 0;
  };
  for (const q of pts) {
    // t = angular distance from the +v (south-east) axis; the open end has no seats
    if (q.t < openS) {
      flush();
      continue;
    }
    inner.push([q.p[0], q.p[1], 0.8]);
    outer.push([q.p[0] + q.n[0] * D, q.p[1] + q.n[1] * D, H]);
  }
  flush();
  // field and cinder track
  b.color('#B98B67').cap(roundedRect(0, 0, 2 * R - 0.5, 2 * (S + R) - 0.5, R - 0.3, 8), 0.25);
  b.color('#5F8F45').cap(rect(0, 0, 49, 110), 0.35);
}

function oldStanford(id: string, built: [number, number], end: number, rows: number, openS: number, facts: Record<string, string>) {
  return landmark(
    id,
    'Stanford Stadium (1921)',
    'stadium',
    built,
    end,
    STANFORD_STADIUM,
    b => b.frame(0, 0, 0, STAD_BRG, () => oldStanfordBowl(b, rows, openS)),
    {
      ...facts,
      Construction: 'earthen horseshoe with wooden bleachers on a steel frame, dug into the ground (the earth from the bowl built the embankments); cinder track',
      Model:
        'centred on today\'s stadium (same site); track oval, row depth (0.79 m) and rise estimated; open end at the south-east (one source) — LOW CONFIDENCE geometry, no plan or historic aerial was reachable'
    },
    [WIKI + 'Stanford_Stadium', 'https://stanfordmag.org/contents/a-short-history-of-stanford-stadium']
  );
}
const stanfordStadium1921 = oldStanford('stanford_stadium_1921', [1921.42, 1921.88], 1925.6, 66, 50, {
  Built: 'groundbreaking Jun 1, 1921, about five months; first game Nov 19, 1921 (Big Game, Cal 42–7)',
  Capacity: '60,000 in 66 rows (U-shape; second in size only to the Yale Bowl)'
});
const stanfordStadium1925 = oldStanford('stanford_stadium_1925', [1925.6, 1925.72], 1927.6, 66, 22, {
  '1925': '10,200 seats added, nearly enclosing the horseshoe (70,200)'
});
const stanfordStadium1927 = oldStanford('stanford_stadium_1927', [1927.6, 1927.72], 2005.9, 80, 22, {
  '1927': 'fourteen more rows (80 rows; 85,500–89,000 seats)',
  End: 'demolished from Nov 26, 2005 and rebuilt within the old bowl'
});

// =================================================================== STADIUMS AND ARENAS (Santa Clara County)

/** Chamfered rectangle (8 vertices: top edge, right, bottom, left) around (cx, cy). */
function oct8(cx: number, cy: number, L: number, R: number, B: number, T: number, c: number): V2[] {
  return [
    [cx - L + c, cy + T],
    [cx + R - c, cy + T],
    [cx + R, cy + T - c],
    [cx + R, cy - B + c],
    [cx + R - c, cy - B],
    [cx - L + c, cy - B],
    [cx - L, cy - B + c],
    [cx - L, cy + T - c]
  ];
}

/** Seating tier between two matching rings with per-vertex heights. */
function tier(b: MeshBuilder, inner: V2[], outer: V2[], zIn: number[] | number, zOut: number[] | number, seats: string, wall?: string) {
  const zi = (i: number) => (Array.isArray(zIn) ? zIn[i] : zIn);
  const zo = (i: number) => (Array.isArray(zOut) ? zOut[i] : zOut);
  b.color(seats).ribbon(
    inner.map((p, i) => [p[0], p[1], zi(i)] as V3),
    outer.map((p, i) => [p[0], p[1], zo(i)] as V3),
    true
  );
  if (wall) b.color(wall).wallProfile(outer, 0, outer.map((_, i) => zo(i)), true);
}

/** Polygon with its own per-vertex heights (sloped decks given by inner/outer edges). */
function zPoly(b: MeshBuilder, ring: V3[]) {
  const tmp = new MeshBuilder();
  tmp.cap(ring.map(p => [p[0], p[1]] as V2), 0);
  const pos = tmp.build().positions.value;
  const zAt = (x: number, y: number) => {
    let best = ring[0][2];
    let bd = Infinity;
    for (const p of ring) {
      const d = (p[0] - x) ** 2 + (p[1] - y) ** 2;
      if (d < bd) {
        bd = d;
        best = p[2];
      }
    }
    return best;
  };
  for (let i = 0; i < pos.length; i += 9) {
    b.tri([pos[i], pos[i + 1], zAt(pos[i], pos[i + 1])], [pos[i + 3], pos[i + 4], zAt(pos[i + 3], pos[i + 4])], [pos[i + 6], pos[i + 7], zAt(pos[i + 6], pos[i + 7])]);
  }
}

// ---- Levi's Stadium (frame 151.8°: +v = south-south-east end, +u = west side with the suite tower)
const LEVIS: V2 = [-121.96973, 37.403165];
const LEVIS_OUTLINE: V2[] = [
  [99.6, -129.6], [108.9, -120.4], [90.8, -102.3], [97.1, -96.1], [114.7, -96.2], [114.8, 88.1], [97.2, 88.2], [90.9, 94.5], [109.0, 112.5], [99.8, 121.7],
  [93.6, 115.5], [85.3, 123.8], [91.5, 130.0], [82.3, 139.2], [64.2, 121.3], [57.9, 127.6], [57.9, 141.9], [52.5, 141.9], [52.5, 157.2], [-45.0, 157.9],
  [-45.0, 141.5], [-48.6, 141.5], [-65.7, 128.3], [-71.9, 135.9], [-88.1, 123.0], [-82.1, 115.6], [-99.7, 100.6], [-116.3, 46.8], [-116.6, -51.7],
  [-99.3, -109.3], [-94.9, -112.8], [-101.5, -121.2], [-86.5, -133.0], [-79.9, -124.5], [-65.6, -135.8], [-72.2, -144.2], [-57.2, -156.0], [-50.6, -147.5],
  [-47.1, -150.3], [57.7, -150.9], [57.7, -135.1], [64.0, -128.9], [82.0, -147.0], [91.3, -137.8], [85.2, -131.6], [93.4, -123.4]
];
const LEVIS_EAST_DECK: V3[][] = [
  [[-35.7, -120.2, 34.5], [-72.0, -91.7, 34.5], [-94.0, -105.8, 51], [-44.7, -144.6, 51]],
  [[-94.0, -105.8, 51], [-72.0, -91.7, 34.5], [-85.5, -47.6, 34.5], [-110.5, -51.8, 51]],
  [[-110.5, -51.8, 51], [-85.5, -47.6, 34.5], [-85.5, 40.4, 34.5], [-110.5, 45.0, 51]],
  [[-110.5, 45.0, 51], [-85.5, 40.4, 34.5], [-71.9, 84.4, 34.5], [-93.9, 98.8, 51]],
  [[-44.9, 136.7, 51], [-93.9, 98.8, 51], [-71.9, 84.4, 34.5], [-36.0, 112.1, 34.5]]
];
const LEVIS_TOWER: V2[] = [[94.1, 79.4], [92.7, 79.3], [91.4, 83.4], [71.6, 77.4], [85.2, 34.2], [84.4, -46.6], [71.9, -85.7], [92.7, -92.1], [94.5, -86.0], [95.7, -85.9]];

const levisStadium = landmark(
  'levis_stadium',
  "Levi's Stadium",
  'stadium',
  [2012.3, 2014.54],
  9999,
  LEVIS,
  b => {
    b.frame(0, 0, 0, 151.8, () => {
      const RED = '#A9383B';
      const CONC = '#BCB7AE';
      // podium / concourses (OSM: 11 m) and the field
      b.color(CONC).prism(LEVIS_OUTLINE, 0, 11, {top: false});
      b.color('#4D8B3B').cap(rect(5.5, -4.5, 79, 129), 0.3);
      // lower bowl, field edge → 11 m
      const lowIn = oct8(5.5, -4.5, 39.5, 39.5, 64.5, 64.5, 6);
      const lowOut = oct8(5.5, -4.5, 70.5, 70, 96.2, 96.7, 30);
      tier(b, lowIn, lowOut, 0.8, 11, RED);
      // club / mid tier: 16 → 28 m round the bowl, 14 → 20 m on the suite-tower (west) side
      const midIn = oct8(5.5, -4.5, 59.5, 59.5, 75.7, 77.5, 22);
      const midOut = oct8(5.5, -4.5, 86, 79.7, 111.3, 111.8, 32);
      const west = (z: number, zw: number) => lowIn.map((_, i) => (i === 2 || i === 3 ? zw : z));
      b.color(CONC).wallProfile(midIn, 11, west(16, 14), true);
      tier(b, midIn, midOut, west(16, 14), west(28, 20), RED);
      b.color(CONC).wallProfile(midOut, west(28, 20), west(33, 22), true);
      // the great east upper deck (34.5 → 51 m), open to the sky
      b.color(RED);
      for (const d of LEVIS_EAST_DECK) zPoly(b, d);
      b.color(CONC);
      b.wallProfile([[-44.7, -144.6], [-94.0, -105.8], [-110.5, -51.8], [-110.5, 45.0], [-93.9, 98.8], [-44.9, 136.7]], 0, 51);
      b.wallProfile([[-35.7, -120.2], [-72.0, -91.7], [-85.5, -47.6], [-85.5, 40.4], [-71.9, 84.4], [-36.0, 112.1]], 29, 34.5);
      b.color('#8E9398').wallProfile([[-44.7, -144.6], [-94.0, -105.8], [-110.5, -51.8], [-110.5, 45.0], [-93.9, 98.8], [-44.9, 136.7]], 51, 52.5);
      // end-zone buildings and the two 200-ft video boards (OSM: 37 → 54 m)
      b.color(CONC);
      boxR(b, [-44.7, 55.6, -145.2, -120.2], 0, 33);
      boxR(b, [-35.6, 46.7, 112, 136.7], 0, 33);
      b.color('#9EA3A8');
      boxR(b, [-35.9, 44.4, -145.1, -130.6], 33, 37);
      boxR(b, [-35.6, 44.7, 120.2, 136.7], 33, 37);
      b.color('#25292D');
      boxR(b, [-6.8, 52.2, -141.9, -138.3], 37, 54);
      boxR(b, [-6.5, 52.5, 128.1, 131.8], 37, 54);
      // SAP suite tower on the west side (OSM: 44 m, 7 floors) with its green roof; solar canopy beyond it
      b.color('#C6CACD').prism(LEVIS_TOWER, 0, 44, {top: false});
      b.color('#6F8D50').cap(LEVIS_TOWER, 44);
      b.color('#7D8C96');
      for (const z of [17, 23.5, 30, 36.5]) b.wallProfile(LEVIS_TOWER.slice(3, 8), z, z + 3.2);
      b.color('#9EA3A8');
      for (let v = -84; v <= 79; v += 20.4) boxR(b, [100, 101.2, v - 0.6, v + 0.6], 0, 50.5);
      b.color('#3E4651');
      boxR(b, [94.1, 107.8, -85.7, 79.7], 50.5, 52);
    });
  },
  {
    Built: 'groundbreaking Apr 19, 2012; opened Jul 17, 2014 (San Francisco 49ers)',
    Capacity: '68,500, expandable to about 75,000; 174 suites',
    Architect: 'HNTB',
    Features: 'seven-storey SAP suite tower on the west side with a 27,000 sq ft green roof; solar canopies; two 200-ft video boards',
    Model:
      'outline, bowl tiers, east upper deck, suite tower and video boards from the OpenStreetMap 3D parts (© OSM contributors, ODbL) and the orthophoto; tier edges simplified to chamfered rectangles'
  },
  [WIKI + "Levi's_Stadium"],
  [rotPoly(rect(-1, 3, 235, 316), 151.8)]
);

// ---- SAP Center (San José Arena): square roof on a round drum, frame 176.5°
const SAP: V2 = [-121.901274, 37.332798];
const sapCenter = landmark(
  'sap_center',
  'SAP Center (San Jose Arena)',
  'stadium',
  [1990.49, 1993.68],
  9999,
  SAP,
  b => {
    b.frame(0, 0, 0, 176.5, () => {
      // elliptical bowl enclosure: glass and stainless steel (orthophoto: 142.6 × 135 m)
      const drum = ellipse(-0.5, 2, 71.3, 67.5, 40);
      b.color('#B7C2CA').prism(drum, 0, 21, {top: false});
      b.color('#8EA2B0');
      for (const z of [5.5, 12.5]) b.prism(drum.map(([x, y]) => [x * 1.003, (y - 2) * 1.003 + 2] as V2), z, z + 2.2, {top: false});
      // square space-frame roof, 132 × 131 m, white trusses round its edge (OSM height 28.7 m)
      const sq = rect(-0.5, 5, 132, 131);
      b.color('#E9ECEC').prism(sq, 22, 28.7);
      b.color('#D3D7D8').walls(sq, 21, 22);
      // raised diagonal skylight band, north-west corner → south-east corner
      b.color('#C8D2D6');
      b.frame(-0.5, 5, 0, 135, () => b.box(0, 0, 28.7, 13, 175, 1.4));
      // glass corner atria (north-west and south-east), ≈ 17 m legs
      b.color('#A9C4CF');
      for (const [cx, cy, sx, sy] of [[-66.5, 70.5, 1, -1], [65.5, -60.5, -1, 1]] as [number, number, number, number][]) {
        const a: V2 = [cx, cy];
        const c1: V2 = [cx + 17 * sx, cy];
        const c2: V2 = [cx, cy + 17 * sy];
        b.prism([a, c1, c2], 0, 28.7);
      }
    });
  },
  {
    Built: 'groundbreaking Jun 28, 1990; opened Sep 7, 1993 (San Jose Sharks)',
    Architect: 'Sink Combs Dethlefs (Charles Sink); Prodis Associates',
    Capacity: '17,435 (hockey) – 19,190 (concerts)',
    Model:
      'square roof (132 × 131 m), drum, diagonal skylight and corner glass atria measured on the orthophoto; height from OpenStreetMap (28.7 m, © OSM contributors, ODbL); facade bands estimated'
  },
  [WIKI + 'SAP_Center'],
  [rotPoly(rect(1.8, -6, 152, 162), 176.5)]
);

// ---- PayPal Park (Earthquakes Stadium): stands and canopies on three sides, bar behind the north-east goal
const PAYPAL: V2 = [-121.924806, 37.350928];
const paypalPark = landmark(
  'paypal_park',
  'PayPal Park',
  'stadium',
  [2012.8, 2015.16],
  9999,
  PAYPAL,
  b => {
    b.frame(0, 0, 0, 32.6, () => {
      const SEAT = '#2F4A68';
      const CONC = '#B9B5AD';
      b.color('#4C8A3B').cap(rect(0, 25, 74, 110), 0.3);
      // steep stands: west and east sides, south end (orthophoto: canopies 20 m deep)
      const side = (s: number) => {
        const x0 = 40 * s;
        const x1 = 68 * s;
        b.color(SEAT).quad([x0, -36, 1], [x0, 81, 1], [x1, 81, 17], [x1, -36, 17]);
        b.color(CONC).quad([x1, -36, 0], [x1, 81, 0], [x1, 81, 17], [x1, -36, 17]);
        b.quad([x0, 81, 0], [x1, 81, 0], [x1, 81, 17], [x0, 81, 1]);
        boxR(b, s > 0 ? [68, 72, -68, 81] : [-72, -68, -68, 81], 0, 23.8);
      };
      side(-1);
      side(1);
      b.color(SEAT).quad([-40, -33, 1], [40, -33, 1], [68, -64, 17], [-68, -64, 17]);
      b.quad([-40, -33, 1], [-68, -64, 17], [-68, -36, 17], [-40, -36, 1]);
      b.quad([40, -33, 1], [68, -64, 17], [68, -36, 17], [40, -36, 1]);
      b.color(CONC);
      boxR(b, [-72, 72, -68, -64], 0, 23.8);
      // white canopy roofs (OSM height 23.8 m)
      b.color('#EEF0EF');
      boxR(b, [-72, -50, -68, 81], 22.6, 23.8);
      boxR(b, [50, 72, -68, 81], 22.6, 23.8);
      boxR(b, [-50, 50, -68, -48], 22.6, 23.8);
      b.color('#9EA3A8');
      for (let v = -60; v <= 80; v += 20) for (const u of [-51, 51]) b.box(u, v, 17, 0.6, 0.6, 5.6);
    });
  },
  {
    Built: 'groundbreaking Oct 21, 2012; opened Feb 27, 2015 (San Jose Earthquakes) as Avaya Stadium; renamed PayPal Park in 2021',
    Capacity: '18,000; some of the steepest stands in Major League Soccer; field 105 × 68 m',
    Architect: 'HOK (360 Architecture)',
    Features: 'the largest outdoor bar in North America behind the north-east goal; canopy roofs over three sides',
    Model:
      'canopies and stands measured on the orthophoto (open north-east end); outline and height from OpenStreetMap (23.8 m, © OSM contributors, ODbL); rake estimated'
  },
  [WIKI + 'PayPal_Park'],
  [rotPoly(rect(0, 5, 152, 152), 32.6)]
);

// =================================================================== SANTA CLARA VALLEY: MISSIONS, HOUSES, AVIATION

// ---- Mission Santa Clara de Asís (frame 65.6°: +v = the facade, facing the Mission Gardens; bell tower on the +u side)
const MISSION_SC: V2 = [-121.94158, 37.349245];
const ADOBE = '#EFE7D6';

function missionSantaClara(b: MeshBuilder, variant: '1825' | '1861' | '1928') {
  b.frame(0, 0, 0, 65.6, () => {
    // nave 20 m wide (OSM), narrower sanctuary behind the altar
    b.color(ADOBE);
    boxR(b, [-8.5, 11.5, -25, 22.6], 0, 9);
    boxR(b, [-6, 5.7, -36.3, -25], 0, 8);
    b.color(TILE).gable(1.5, -1.2, 21, 48.4, 9, 4.6, true);
    b.gable(-0.15, -30.7, 12.5, 11.8, 8, 3.4, true);
    // low wing west of the facade (the 1822–25 adobe cloister wall)
    b.color(ADOBE);
    boxR(b, [-34.5, -12.6, 25.1, 28], 0, 3.6);
    b.color(TILE).gable(-23.5, 26.5, 22, 3.6, 3.6, 0.8, false);
    if (variant === '1861') {
      // 1861: wooden facade with two bell towers built over the adobe front
      b.color('#E8E2D5');
      boxR(b, [-12.6, 13.1, 22.6, 28], 0, 14);
      b.tri([-5, 28, 14], [5.5, 28, 14], [0.25, 28, 18]).tri([-5, 22.6, 14], [5.5, 22.6, 14], [0.25, 22.6, 18]);
      for (const x of [-9.2, 9.7]) {
        b.box(x, 25.3, 14, 5.4, 5.4, 6);
        b.box(x, 25.3, 20, 4.4, 4.4, 3.5);
        b.color('#8E8A84').pyramid(rect(x, 25.3, 4.6, 4.6), 23.5, [x, 25.3, 29]).color('#E8E2D5');
      }
      return;
    }
    // adobe-style facade: scalloped parapet, painted niches and pilasters (the 1928 church replicates the 1825 front)
    b.color(ADOBE);
    boxR(b, [-12.6, 8, 22.6, 27.2], 0, 12.5);
    const top: V2[] = [[-12.6, 12.5], [-10, 13.2], [-7.5, 14.5], [-5, 14.8], [-3, 16.3], [-1.2, 17], [1, 16.3], [3, 14.8], [5.5, 14.5], [8, 13]];
    for (let i = 0; i < top.length - 1; i++) {
      const [x0, z0] = top[i];
      const [x1, z1] = top[i + 1];
      for (const y of [22.6, 27.2]) b.quad([x0, y, 12.5], [x1, y, 12.5], [x1, y, z1], [x0, y, z0]);
      b.quad([x0, 22.6, z0], [x1, 22.6, z1], [x1, 27.2, z1], [x0, 27.2, z0]);
    }
    b.color('#B98E6A');
    for (const x of [-9.5, -5.2, 3.2]) b.box(x, 27.3, 2, 1.0, 0.2, 9.5); // painted pilasters
    b.color('#6E5A4A').box(-1.2, 27.3, 0, 3.2, 0.2, 5.5); // door
    if (variant === '1928') {
      // bell tower (left of the facade): two stages, tiled pyramid roof and a small lantern (photo estimate ≈ 22 m)
      b.color(ADOBE);
      boxR(b, [8, 13.1, 22.6, 28], 0, 13);
      boxR(b, [8.5, 12.6, 23.1, 27.5], 13, 17.5);
      b.color('#5A5048');
      b.box(10.55, 25.3, 14, 4.2, 1.6, 2.6).box(10.55, 25.3, 14, 1.6, 4.2, 2.6);
      b.color(TILE).pyramid(rect(10.55, 25.3, 4.6, 4.6), 17.5, [10.55, 25.3, 20]);
      b.color(ADOBE).cylinder(10.55, 25.3, 0.7, 19.6, 21, 8);
      b.color(TILE).dome(10.55, 25.3, 0.8, 21, 0.8, 8, 2);
    }
  });
}

const missionSC1825 = landmark(
  'mission_santa_clara_1825',
  'Mission Santa Clara de Asís (adobe church)',
  'building',
  [1822.5, 1825.6],
  1861.0,
  MISSION_SC,
  b => missionSantaClara(b, '1825'),
  {
    Built: '1822–1825: the fifth mission church, of adobe, on today\'s site (the mission had moved twice since 1777 after floods and earthquakes)',
    Model: 'nave and sanctuary on the footprint of the 1928 replica (same site and plan); adobe front after the 1928 replica of it; heights estimated (LOW CONFIDENCE)'
  },
  [WIKI + 'Mission_Santa_Clara_de_As%C3%ADs']
);
const missionSC1861 = landmark(
  'mission_santa_clara_1861',
  'Mission Santa Clara de Asís (1861 facade)',
  'building',
  [1861.0, 1861.5],
  1926.82,
  MISSION_SC,
  b => missionSantaClara(b, '1861'),
  {
    '1861': 'a wooden facade with two bell towers was built over the old adobe front; in 1885 the adobe nave walls were removed to widen the church',
    Fate: 'destroyed by fire on Oct 25, 1926',
    Model: 'facade and tower heights estimated from photographs (LOW CONFIDENCE); nave on the 1928 footprint'
  },
  [WIKI + 'Mission_Santa_Clara_de_As%C3%ADs']
);
const missionSC1928 = landmark(
  'mission_santa_clara_1928',
  'Mission Santa Clara de Asís',
  'building',
  [1927.3, 1928.95],
  9999,
  MISSION_SC,
  b => missionSantaClara(b, '1928'),
  {
    Built: 'rebuilt 1927–28 after the fire of 1926 as an enlarged replica of the 1825 church; consecrated 1929; chapel of Santa Clara University',
    Model:
      'outline from OpenStreetMap (© OSM contributors, ODbL); bell tower position from the orthophoto; scalloped parapet, wall and tower heights estimated from photographs'
  },
  [WIKI + 'Mission_Santa_Clara_de_As%C3%ADs'],
  [rotPoly(rect(-10.7, -4.2, 50, 66), 65.6)]
);

// ---- Winchester Mystery House (frame 0°; outline = OSM house limited to the historic house)
const WINCHESTER: V2 = [-121.951149, 37.318349];
const WINCH_PLAN: {o: V2[]; h: V2[][]}[] = [{"o":[[3.8,13.6],[4.8,13.6],[4.9,10.1],[9.6,10.2],[9.6,12.3],[14.8,12.3],[15.8,13.4],[15.6,15.3],[17.2,15.4],[18.1,16.1],[17.9,17.3],[18.6,17.7],[19.6,17.1],[21.8,19.6],[26.3,15.2],[28.7,17.4],[30.0,16.9],[30.0,-21.6],[24.3,-21.6],[24.3,-23.7],[20.0,-23.7],[19.5,-16.2],[12.8,-16.9],[13.2,-25.6],[18.3,-25.6],[18.2,-32.6],[23.2,-32.7],[23.1,-38.5],[19.7,-38.4],[19.6,-40.0],[13.0,-40.0],[13.0,-38.4],[9.3,-38.3],[9.4,-30.2],[4.0,-30.2],[4.0,-31.8],[-3.3,-31.1],[-3.3,-26.2],[-2.5,-26.2],[-2.5,-25.1],[1.0,-25.1],[1.7,-28.4],[9.7,-28.4],[9.8,-18.4],[7.6,-18.4],[8.3,-10.9],[1.6,-10.9],[1.8,-12.6],[0.7,-12.6],[0.6,-13.5],[-3.8,-13.4],[-3.8,-14.2],[-10.0,-13.4],[-10.0,-14.6],[-20.3,-14.5],[-17.6,-15.0],[-17.6,-22.9],[-16.6,-24.0],[-17.6,-25.3],[-17.7,-37.0],[-26.8,-36.9],[-27.3,-28.6],[-28.1,-28.6],[-28.0,-22.8],[-30.1,-22.8],[-30.8,-9.6],[-26.8,-9.7],[-26.7,-5.0],[-25.0,-5.0],[-25.0,-3.1],[-23.5,-3.1],[-23.5,-2.5],[-17.8,-2.5],[-17.8,0.6],[-26.8,0.2],[-26.8,2.7],[-29.2,2.7],[-29.2,8.7],[-22.7,8.7],[-22.7,6.7],[-22.2,6.7],[-22.1,8.4],[-18.0,8.3],[-18.0,6.6],[-15.6,6.6],[-15.6,4.5],[-11.6,4.5],[-11.6,11.7],[-7.6,11.7],[-7.6,15.5],[-9.4,15.6],[-9.4,20.0],[3.7,20.0]],"h":[[[-17.8,-8.2],[-14.6,-8.3],[-14.6,-7.0],[-12.3,-7.1],[-11.7,-6.0],[-17.8,-5.9]]]}];
const WINCH_RECTS: [number, number, number, number][] = [[-11.6,30.0,-10.8,10.0],[16.0,30.0,-16.4,15.2],[-7.6,3.6,-10.8,20.0],[-26.8,-20.0,-36.8,-5.2],[9.6,12.8,-38.4,12.4],[-30.0,-20.0,-22.8,-9.6],[-30.4,0.8,-13.6,-9.6],[9.6,18.4,-38.4,-25.6],[9.2,23.2,-38.4,-32.8],[-26.8,-18.0,0.4,6.8],[-29.2,-15.6,2.8,6.8],[-29.2,-22.8,2.8,8.8],[8.0,12.8,-18.4,-12.0],[-2.4,1.2,-31.2,-25.2],[-0.4,4.0,-31.6,-28.4]];

function winchesterHouse(b: MeshBuilder) {
  b.color('#E2D2A6');
  for (const p of WINCH_PLAN) b.prism(p.o, 0, 8.5, {holes: p.h});
  // roofscape: steep hipped roofs over every wing, broken into ≤ 10 m bays (many small gables and peaks)
  b.color('#8F4E3E');
  const pitch = Math.tan((40 * Math.PI) / 180);
  for (const [u0, u1, v0, v1] of WINCH_RECTS) {
    const nu = Math.max(1, Math.round((u1 - u0) / 10));
    const nv = Math.max(1, Math.round((v1 - v0) / 10));
    const du = (u1 - u0) / nu;
    const dv = (v1 - v0) / nv;
    for (let i = 0; i < nu; i++) {
      for (let j = 0; j < nv; j++) {
        b.hip(u0 + du * (i + 0.5), v0 + dv * (j + 0.5), du + 0.6, dv + 0.6, 8.5, (Math.min(du, dv) / 2 + 0.3) * pitch);
      }
    }
  }
  // round towers with conical roofs (orthophoto)
  b.color('#E2D2A6').cylinder(31.5, -16.5, 3.8, 0, 12, 12);
  b.color('#8F4E3E').pyramid(circle(31.5, -16.5, 4.1, 12), 12, [31.5, -16.5, 17.5]);
  b.color('#E2D2A6').cylinder(30, 16.5, 3, 0, 11, 10);
  b.color('#B0683F').dome(30, 16.5, 3.2, 11, 3, 10, 3);
}

const winchester = landmark(
  'winchester_mystery_house',
  'Winchester Mystery House',
  'building',
  [1886.5, 1906.25],
  9999,
  WINCHESTER,
  b => winchesterHouse(b),
  {
    Built: 'Sarah Winchester bought the farmhouse in 1886 and kept building until the 1906 earthquake (the house was under construction for two decades); 160 rooms at her death in 1922; opened to the public in 1923',
    Style: 'Victorian, with Gothic and Romanesque features; up to five levels in places',
    Model:
      'outline from OpenStreetMap (© OSM contributors, ODbL), limited to the historic house; turret positions from the orthophoto; wall height, roof pitch and colours estimated — the many small roofs are a simplified roofscape'
  },
  [WIKI + 'Winchester_Mystery_House'],
  [rect(0, -10, 66, 60)]
);

const winchesterTower = landmark(
  'winchester_tower_1906',
  'Winchester House seven-storey tower',
  'tower',
  [1895.0, 1900.0],
  1906.3,
  WINCHESTER,
  b => {
    b.color('#E2D2A6').box(10, 0, 0, 6, 6, 24);
    b.color('#8F4E3E').pyramid(rect(10, 0, 6.6, 6.6), 24, [10, 0, 31]);
  },
  {
    Fate: 'the seven-storey tower collapsed in the earthquake of Apr 18, 1906 and was not rebuilt',
    Model: 'height from the seven storeys (≈ 3.4 m each); position on the house and build years ESTIMATED (LOW CONFIDENCE)'
  },
  [WIKI + 'Winchester_Mystery_House']
);

// ---- Hangar One, Moffett Field (frame 157.8°): 1,133 × 308 ft, 198 ft high, elongated catenary section
const HANGAR_ONE: V2 = [-122.053965, 37.412951];

function hangarProfile(): [number, number][] {
  // catenary z = H − a(cosh(x/a) − 1) through (±46.5, 0), H = 60.4 m
  const H = 198 * FT;
  const W = 46.5;
  let a = 24;
  for (let i = 0; i < 40; i++) {
    const f = a * (Math.cosh(W / a) - 1) - H;
    a += f > 0 ? 0.25 : -0.25;
    if (Math.abs(f) < 0.3) break;
  }
  const out: [number, number][] = [];
  for (let i = 0; i <= 10; i++) {
    const x = W * (1 - i / 10);
    out.push([x, Math.max(0, H - a * (Math.cosh(x / a) - 1))]);
  }
  return out;
}

function hangarOne(b: MeshBuilder, skin: string) {
  b.frame(0, 0, 0, 157.8, () => {
    const prof = hangarProfile();
    const L = 134.5; // straight body ±134.5 m; rounded "orange-peel" door ends to ±173.5 m (OSM)
    b.color(skin);
    for (const s of [-1, 1]) {
      for (let i = 0; i < prof.length - 1; i++) {
        const [x0, z0] = prof[i];
        const [x1, z1] = prof[i + 1];
        b.quad([s * x0, -L, z0], [s * x0, L, z0], [s * x1, L, z1], [s * x1, -L, z1]);
      }
    }
    // ends: the section swept round half an ellipse (39 m deep)
    for (const e of [-1, 1]) {
      const n = 8;
      for (let k = 0; k < n; k++) {
        const t0 = (Math.PI * k) / n;
        const t1 = (Math.PI * (k + 1)) / n;
        for (let i = 0; i < prof.length - 1; i++) {
          const P = (t: number, j: number): V3 => {
            const [x, z] = prof[j];
            return [x * Math.cos(t), e * (L + Math.sin(t) * x * (39 / 46.5)), z];
          };
          b.quad(P(t0, i), P(t1, i), P(t1, i + 1), P(t0, i + 1));
        }
      }
    }
    // concrete apron strip and the door rails along the sides
    b.color('#9C9A94').box(0, 0, 0, 97, 2, 0.4);
  });
}

const hangarOne1933 = landmark(
  'hangar_one_1933',
  'Hangar One, Moffett Field',
  'building',
  [1931.8, 1933.6],
  2011.3,
  HANGAR_ONE,
  b => hangarOne(b, '#B9BDBF'),
  {
    Built: 'built 1931–33 for the US Navy airship USS Macon (moved in Oct 15, 1933)',
    Size: '1,133 × 308 ft (345 × 94 m), 198 ft (60 m) high; 8 acres of floor',
    Design: 'Karl Arnstein with Wilbur Watson Associates: steel girders sheathed in galvanized steel, inward-curving walls forming an elongated catenary, "orange-peel" doors at both ends',
    Fate: 'the toxic siding was stripped from Apr 2011 to mid-2012, leaving the bare frame',
    Model: 'outline from OpenStreetMap (© OSM contributors, ODbL); section a catenary through the documented width and height; end doors as half-ellipses'
  },
  [WIKI + 'Hangar_One_(Mountain_View,_California)'],
  [rotPoly(rect(0, 0, 95, 349), 157.8)]
);

const hangarOne2025 = landmark(
  'hangar_one',
  'Hangar One, Moffett Field (restored)',
  'building',
  [2010.5, 2025.95],
  9999,
  HANGAR_ONE,
  b => hangarOne(b, '#C3C7C9'),
  {
    'Bare frame': '2011–2025 the skeleton stood without its skin (shown as a frame)',
    Restored: 're-skinned and restored by Planetary Ventures (Google) under a NASA lease; reported complete Dec 2025, celebrated Mar 2026',
    Model: 'same geometry as the 1933 hangar; the frame phase stands for the stripped skeleton'
  },
  [WIKI + 'Hangar_One_(Mountain_View,_California)'],
  [rotPoly(rect(0, 0, 95, 349), 157.8)]
);

// ---- Lick Observatory, Mount Hamilton (frame 14.5°, anchor = OSM "Main Building")
const LICK: V2 = [-121.642845, 37.341418];
const lickObservatory = landmark(
  'lick_observatory',
  'Lick Observatory',
  'building',
  [1880.0, 1888.0],
  9999,
  LICK,
  b => {
    // the summit was levelled for the observatory; the terrain grid rounds it off, so the
    // buildings stand on a pad at the highest ground under them
    let lo = 0;
    let hi = 0;
    for (const [u, v] of [[-16, -50], [6, -50], [-14, 0], [1, 0], [-17, 37], [34, 34], [34, 22]] as V2[]) {
      const dz = groundDz(LICK, 14.5, u, v);
      lo = Math.min(lo, dz);
      hi = Math.max(hi, dz);
    }
    b.color('#B9AD94').frame(0, 0, 0, 14.5, () => b.prism(rect(8.5, -7.5, 56, 90), lo - 1, hi));
    b.frame(0, 0, hi, 14.5, () => {
      const WALL = '#E8E3D6';
      const DOME = '#E3E7E9';
      // long hall joining the two domes, with the central entrance block (OSM outline)
      b.color(WALL);
      boxR(b, [-11.4, 0.8, -29, 27.6], 0, 7.9);
      boxR(b, [-14, 3.5, -3.7, 4.9], 0, 9.5);
      b.color('#B7AFA2').gable(-5.3, -0.7, 12.4, 56.6, 7.9, 2.2, true);
      // north wing (brick, red roof) and the 12-inch refractor dome (r ≈ 5 m)
      b.color('#D9CFC0');
      boxR(b, [0.9, 34.4, 22.3, 34.6], 0, 6.5);
      b.color('#9E4C38').gable(17.6, 28.4, 34, 12.8, 6.5, 2.4, false);
      b.color(WALL).cylinder(-12.7, 32.5, 4.8, 0, 9, 16);
      b.color(DOME).dome(-12.7, 32.5, 5.0, 9, 5, 16, 4);
      // great dome of the 36-inch refractor: 75 ft (22.9 m) across
      b.color(WALL).cylinder(-5.2, -39, 11.3, 0, 12, 24);
      b.color(DOME).dome(-5.2, -39, 11.5, 12, 11.2, 24, 6);
      b.color('#9DA4A8').box(-5.2, -39, 18, 2.6, 22.6, 5.6);
    });
  },
  {
    Built: '1876–1887 with the $700,000 bequest of James Lick (buried under the great telescope in 1887); 36-inch refractor first light Jan 3, 1888; given to the University of California in May 1888',
    Site: 'summit of Mount Hamilton, 4,209 ft (1,283 m)',
    Domes: 'great dome 75 ft (22.9 m) across for the 36-inch refractor (then the largest in the world); 12-inch refractor dome at the north end',
    Model:
      'outline and dome positions from OpenStreetMap (© OSM contributors, ODbL) and the orthophoto; wall and drum heights estimated from photographs'
  },
  [WIKI + 'Lick_Observatory'],
  [rotPoly(rect(8.5, -7.5, 55, 88), 14.5)]
);

const SHANE: V2 = [-121.637167, 37.342971];
const shaneDome = landmark(
  'lick_shane_dome',
  'Lick Observatory — Shane 120-inch telescope dome',
  'building',
  [1950.5, 1959.3],
  9999,
  SHANE,
  b => {
    b.frame(0, 0, 0, 24.1, () => {
      b.color('#E6E8E8').cylinder(-1.3, 3, 15.2, 0, 17, 24);
      b.color('#E1E5E7').dome(-1.3, 3, 15.4, 17, 15.2, 24, 6);
      b.color('#9DA4A8').box(-1.3, 3, 24, 4, 30.6, 8.2);
      b.color('#DCD8CF').prism([[3.4, -22], [7.2, -20.2], [9.6, -25.5], [14.1, -23.5], [11.6, -18.2], [12.9, -17.6], [8.9, -8.5], [-0.7, -12.3]], 0, 7);
    });
  },
  {
    Built: 'funded by the California legislature in 1950; the 120-inch (3 m) C. Donald Shane reflector was completed in 1959 — then the second-largest telescope in the world',
    Model: 'outline and height (32.2 m) from OpenStreetMap (© OSM contributors, ODbL); drum height estimated'
  },
  [WIKI + 'Lick_Observatory'],
  [rotPoly(circle(-1.3, 3, 17, 12), 24.1)]
);

// =================================================================== DOWNTOWN SAN JOSÉ (street grid ≈ 149°/59°)

// ---- Electric light tower over Market & Santa Clara Sts (1881–1915)
const SJ_LIGHT_TOWER: V2 = [-121.892074, 37.335488];
const sjLightTower = landmark(
  'san_jose_electric_light_tower',
  'San Jose Electric Light Tower',
  'tower',
  [1881.61, 1881.95],
  1915.92,
  SJ_LIGHT_TOWER,
  b => {
    b.frame(0, 0, 0, 149, () => {
      const IRON = '#5F6164';
      const H = 207 * FT;
      // four legs of iron pipe from a 75 ft square base, braced by hoops (flared like a tapering truss)
      const half = (z: number) => 11.43 * Math.pow(1 - z / (H + 6), 1.6) + 0.9;
      const levels = [0, 6, 13, 21, 30, 40, 51, H];
      b.color(IRON);
      for (const [sx, sy] of [[1, 1], [1, -1], [-1, -1], [-1, 1]] as V2[]) {
        for (let i = 0; i < levels.length - 1; i++) {
          const z0 = levels[i];
          const z1 = levels[i + 1];
          b.beam([sx * half(z0), sy * half(z0), z0], [sx * half(z1), sy * half(z1), z1], 0.45);
        }
      }
      for (const z of levels.slice(1)) {
        const h = half(z);
        const ring: V3[] = [[h, h, z], [h, -h, z], [-h, -h, z], [-h, h, z], [h, h, z]];
        b.polyline(ring, 0.25);
      }
      // diagonal stays in the lower stages
      for (let i = 0; i < 4; i++) {
        const z0 = levels[i];
        const z1 = levels[i + 1];
        const a = half(z0);
        const c = half(z1);
        b.beam([a, a, z0], [-c, c, z1], 0.18).beam([a, -a, z0], [c, c, z1], 0.18).beam([-a, -a, z0], [c, -c, z1], 0.18).beam([-a, a, z0], [-c, -c, z1], 0.18);
      }
      // lamp platform with six arc lamps, and the 30 ft flagpole
      b.box(0, 0, H, 4.2, 4.2, 0.4);
      b.color('#E9E1C2');
      for (let k = 0; k < 6; k++) {
        const a = (k * Math.PI) / 3;
        b.box(Math.cos(a) * 1.8, Math.sin(a) * 1.8, H + 0.4, 0.5, 0.5, 0.9);
      }
      b.color(IRON).beam([0, 0, H], [0, 0, H + 30 * FT], 0.2);
    });
  },
  {
    Built: 'groundbreaking Aug 11, 1881; dedicated Dec 13, 1881 — J. J. Owen\'s tower to light downtown San José',
    Height: '207 ft (63 m) to the lamp platform, 237 ft (72 m) with the flagpole; base 75 ft (23 m) square over the intersection',
    Fate: 'brought down by 56 mph winds on Dec 3, 1915 (a half-size replica stands in History Park)',
    Model: 'hollow-iron-pipe legs and hoops after photographs; bracing stage heights estimated; aligned with the street grid'
  },
  [WIKI + 'San_Jose_Electric_Light_Tower']
);

// ---- Hotel De Anza (OSM 3D parts, frame 149°)
const DE_ANZA: V2 = [-121.895071, 37.334402];
const hotelDeAnza = landmark(
  'hotel_de_anza',
  'Hotel De Anza',
  'building',
  [1931.16, 1931.9],
  9999,
  DE_ANZA,
  b => {
    b.frame(0, 0, 0, 149, () => {
      const WALL = '#EBCBC0'; // pale pink stucco over a salmon-red ground storey (photo)
      b.color(WALL);
      b.prism([[16.1, 3.5], [16.1, 18.8], [6.6, 18.9], [6.6, 8.5], [2.7, 8.5], [2.7, 3.6]], 0, 30.9);
      b.prism([[-8.5, 3.7], [2.7, 3.6], [2.7, 8.5], [6.6, 8.5], [6.6, 18.9], [-5.6, 19.0], [-5.6, 14.3], [-8.5, 14.3]], 0, 36.3);
      b.prism([[-8.5, 3.7], [-8.5, 14.3], [-5.6, 14.3], [-5.6, 19.0], [-15.3, 19.0], [-15.3, 3.7]], 0, 31.2);
      b.prism([[5.2, -14.4], [18.5, -14.5], [18.5, 3.5], [-6.6, 3.7], [-6.6, -6.8], [5.2, -6.9]], 0, 9);
      b.prism([[-6.6, -9.7], [-6.6, 3.7], [-15.3, 3.7], [-15.3, -9.6]], 0, 15.1);
      b.prism([[-6.6, -6.8], [-6.6, -9.7], [-15.6, -9.6], [-15.6, -22.4], [5.2, -22.5], [5.2, -6.9]], 0, 8.3);
      boxR(b, [-5.6, 6.6, 18.9, 22.2], 0, 4.5);
      b.color('#C77662');
      boxR(b, [-15.8, 16.6, 3.2, 19.4], 0, 5.2, false);
      // Zig Zag Moderne crown: stepped piers with teal accents and the lattice rooftop sign
      b.color('#5E9C9A');
      boxR(b, [-8.9, 7, 3.3, 19.3], 35.5, 36.6);
      b.color(WALL);
      boxR(b, [-5, 3, 8, 15], 36.3, 39.2);
      b.color('#B5483D');
      boxR(b, [-4.5, 2.5, 18.6, 19.2], 39.2, 44);
    });
  },
  {
    Built: 'groundbreaking Feb 27, 1931 (W. H. Weeks, architect; Carl Swenson, contractor); restored and reopened 1990',
    Style: 'Zig Zag Moderne (Art Deco) with Mission Revival touches: a ten-storey centre between nine-storey wings',
    Model: 'massing from the OpenStreetMap 3D parts (© OSM contributors, ODbL; 36.3 / 30.9 / 31.2 m); crown, sign and colours from a photograph (pale pink over a salmon ground storey, teal accents); crown heights estimated'
  },
  [WIKI + 'Hotel_De_Anza'],
  [rotPoly(rect(-0.5, 0, 38, 45), 149)]
);

// ---- San José City Hall (2005) — Richard Meier; OSM 3D parts, frame 149.3°
const SJ_CITY_HALL: V2 = [-121.885877, 37.337635];
const sjCityHall = landmark(
  'san_jose_city_hall',
  'San José City Hall',
  'building',
  [2002.3, 2005.79],
  9999,
  SJ_CITY_HALL,
  b => {
    b.frame(0, 0, 0, 149.3, () => {
      const WHITE_M = '#E6E8E7';
      const GL = '#9DB5C0';
      // 18-storey tower, 285 ft (87 m), 21 × 78 m
      b.color(GL);
      boxR(b, [-70.9, -49.5, -58, 19], 0, 76);
      b.color(WHITE_M);
      for (let z = 4; z < 76; z += 4.2) boxR(b, [-71.6, -48.8, -58.7, 19.7], z, z + 0.5, false);
      boxR(b, [-71.6, -48.8, -58.7, 19.7], 75.5, 76.2);
      boxR(b, [-67.7, -54.3, -12.3, 8.7], 76, 80.2);
      boxR(b, [-77.4, -52.2, 17.3, 27.8], 0, 82.5, false);
      boxR(b, [-46.8, -34.8, -52.3, -40], 0, 85.7);
      boxR(b, [-58.9, -46.7, -56.9, -54.9], 0, 86.9);
      // low wing west of the tower and the council wing round the plaza
      boxR(b, [-88.9, -70.9, -40.3, 19.1], 0, 14.2);
      b.prism([[70.9, -2.8], [78.6, -11.0], [85.6, -11.1], [85.6, -18.9], [101.8, -18.9], [101.7, 36.3], [47.9, 36.0], [47.9, 39.1], [7.0, 39.3], [7.0, 36.7], [4.0, 36.6], [4.1, 7.8], [6.9, 7.2], [6.7, 22.0], [21.4, 20.8], [36.4, 17.2], [48.7, 12.2], [61.4, 4.8]], 0, 14.4);
      b.color(GL);
      b.prism([[6.7, 17.3], [28.1, 14.8], [51.4, 5.9], [59.6, 0.7], [68.4, -7.1], [77.4, -17.7], [81.9, -27.0], [83.7, -26.6], [80.6, -19.5], [75.6, -12.4], [78.6, -11.0], [77.5, -9.3], [66.1, 1.2], [53.9, 9.4], [39.2, 16.2], [21.4, 20.8], [6.7, 22.0]], 0, 12.3);
      b.color(WHITE_M);
      boxR(b, [52.6, 85.9, 25.5, 34.4], 0, 19.3);
      // Janet Gray Hayes Rotunda: glass, 100 ft across, 110 ft high
      b.color(GL).cylinder(5.7, -8.6, 15.2, 0, 22, 24, {top: false});
      b.color('#B7CAD2').dome(5.7, -8.6, 15.4, 22, 11.5, 24, 5);
      b.color(WHITE_M).cylinder(5.7, -8.6, 15.6, 21.4, 22.2, 24, {top: false});
    });
  },
  {
    Built: 'groundbreaking 2002; staff moved in Aug 2005; opened Oct 15, 2005',
    Architect: 'Richard Meier & Partners with Steinberg Architects',
    Height: 'tower 18 storeys, 285 ft (87 m), 68 × 255 ft; rotunda 100 ft (30 m) across and 110 ft (34 m) high',
    Previously: 'City Hall stood in Market Plaza 1889–1958 and on N. First St 1958–2005',
    Model: 'tower, wings and council chamber from the OpenStreetMap 3D parts (© OSM contributors, ODbL); rotunda position from the orthophoto, dimensions from Wikipedia; facade banding estimated'
  },
  [WIKI + 'San_Jose_City_Hall'],
  [rotPoly(rect(6, -10, 196, 104), 149.3)]
);

// ---- The Tech Interactive (1998) — Ricardo Legorreta: mango walls, blue IMAX dome
const TECH: V2 = [-121.890197, 37.331447];
const techInteractive = landmark(
  'tech_interactive',
  'The Tech Interactive',
  'building',
  [1996.6, 1998.83],
  9999,
  TECH,
  b => {
    b.frame(0, 0, 0, 147.2, () => {
      b.color('#E3823F');
      b.prism(
        [[-28.2, 28.9], [-30.2, -34.7], [30.2, -37.0], [31.2, -18.3], [27.3, -18.1], [27.7, 2.6], [16.8, 3.0], [17.7, 30.4], [10.3, 30.7], [10.4, 35.1], [-21.7, 36.4], [-21.8, 34.3], [-30.0, 34.0], [-30.2, 29.0]],
        0,
        13.7
      );
      b.color('#7D4C8E');
      b.prism([[28.3, 20.2], [23.5, 25.1], [24.1, 38.5], [18.2, 38.7], [19.0, 30.3], [17.7, 30.4], [16.8, 3.0], [27.7, 2.6]], 0, 17);
      b.color('#E3823F');
      boxR(b, [10.3, 19.2, 30.3, 35.1], 0, 21.8);
      // Hackworth IMAX Dome theater
      b.color('#2F6DB5').dome(-12.4, -17.8, 16.4, 13.7, 8.6, 24, 5);
    });
  },
  {
    Opened: 'Oct 31, 1998 as The Tech Museum of Innovation (132,000 sq ft)',
    Architect: 'Ricardo Legorreta',
    Model: 'outline and parts from OpenStreetMap (© OSM contributors, ODbL; walls 13.7 m, overall 22.3 m); dome rise and colours from photographs'
  },
  [WIKI + 'The_Tech_Interactive'],
  [rotPoly(rect(0, 3.5, 63, 83), 147.2)]
);

// =================================================================== MARIN COUNTY

// ---- Marin County Civic Center (Frank Lloyd Wright): two long wings meeting at 120° under a dome; frame 164.8°
const MARIN_CC: V2 = [-122.530834, 37.997966];
const MCC_BRG = 164.8;
const MCC_WALL = '#E6CDAE'; // "Big Pink": sand / golden-tan stucco
const MCC_ROOF = '#4E8FCB'; // bright blue roof (Olgivanna Lloyd Wright)

/**
 * One wing in the frame: centre line from (x0, y0) along `brg` (deg, frame-relative) for `len` m, `w` wide.
 * Barrel-vaulted roof over two office ranges and the skylit mall between them; the roof stays level
 * while the wing bridges the valley, its walls reach down to the lowest ground under it.
 */
function mccWing(b: MeshBuilder, x0: number, y0: number, brg: number, len: number, w: number, minEave: number): number {
  let lo = 0;
  let hi = 0;
  for (let t = 0; t <= len; t += len / 8) {
    const a = (brg * Math.PI) / 180;
    const dz = groundDz(MARIN_CC, MCC_BRG, x0 + Math.sin(a) * t, y0 + Math.cos(a) * t);
    lo = Math.min(lo, dz);
    hi = Math.max(hi, dz);
  }
  // level roof three storeys above the highest ground the wing crosses
  const eave = Math.max(minEave, hi + 12);
  b.frame(x0, y0, 0, brg, () => {
    const hw = w / 2;
    b.color(MCC_WALL);
    boxR(b, [-hw, hw, 0, len], lo, eave, false);
    // tiers of arches along both long fronts (wide at the bottom, smaller above)
    b.color('#A68E74');
    for (const [z, h] of [[eave - 13, 4], [eave - 8, 3], [eave - 4.2, 2]] as [number, number][]) {
      if (z < lo + 1) continue;
      for (const s of [-1, 1]) b.box(s * (hw + 0.05), len / 2, z, 0.12, len - 2, h);
    }
    // two blue barrel vaults and the glazed mall between them, rounded end
    const vault = (cx: number, vw: number) => {
      const n = 6;
      for (let i = 0; i < n; i++) {
        const a0 = (Math.PI * i) / n;
        const a1 = (Math.PI * (i + 1)) / n;
        const P = (a: number, y: number): V3 => [cx - Math.cos(a) * (vw / 2), y, eave + Math.sin(a) * 2.8];
        b.quad(P(a0, 0), P(a1, 0), P(a1, len), P(a0, len));
      }
    };
    b.color(MCC_ROOF);
    const vw = (w - 5) / 2;
    vault(-hw + vw / 2, vw);
    vault(hw - vw / 2, vw);
    b.color('#B8C9CF').box(0, len / 2, eave, 5.2, len, 1.4);
    b.color(MCC_ROOF).cap(arcPts(0, len, hw, 270, 450, 10), eave + 0.1);
    b.color(MCC_WALL).prism(arcPts(0, len, hw, 270, 450, 10), lo, eave, {top: false});
  });
  return eave;
}

const marinAdmin = landmark(
  'marin_civic_center_admin',
  'Marin County Civic Center — Administration Building',
  'building',
  [1960.12, 1962.78],
  9999,
  MARIN_CC,
  b => {
    b.frame(0, 0, 0, MCC_BRG, () => {
      const eave = mccWing(b, -40, 52, 26.9, 155, 34.4, 15);
      // library dome over the junction, and the 172 ft gold-anodised spire beside it
      b.color(MCC_WALL).cylinder(-29.5, 58, 19, Math.min(0, groundDz(MARIN_CC, MCC_BRG, -29.5, 58)), eave, 20);
      b.color(MCC_ROOF).dome(-29.5, 58, 19.5, eave, 7, 20, 4);
      b.color('#D7B24A');
      b.pyramid([[-58.4, 57], [-53.7, 52], [-55.4, 58]], 0, [-55.8, 55.7, 172 * FT]);
    });
  },
  {
    Built: 'groundbreaking Feb 15, 1960; dedicated Oct 13, 1962 — Frank Lloyd Wright\'s last major commission (completed by Aaron Green and William Wesley Peters)',
    Size: '580 ft (177 m) long; a barrel-vaulted roof bridging between hills; dome over the library rotunda (80 ft)',
    Spire: '172 ft (52 m), gold-anodised aluminium',
    Colours: 'sand / pink stucco ("Big Pink") under a bright blue roof',
    Model:
      'wing positions and widths from the OpenStreetMap outlines (© OSM contributors, ODbL) and the orthophoto; storey heights, vault rise and arcade bands estimated; roof kept level across the valley'
  },
  [WIKI + 'Marin_County_Civic_Center'],
  [rotPoly([[-58, 30], [-8, 50], [55, 205], [10, 210], [-45, 95]], MCC_BRG)]
);

const marinHallOfJustice = landmark(
  'marin_civic_center_hall_of_justice',
  'Marin County Civic Center — Hall of Justice',
  'building',
  [1966.4, 1969.95],
  9999,
  MARIN_CC,
  b => b.frame(0, 0, 0, MCC_BRG, () => mccWing(b, -27.6, 38, 165, 246, 40.8, 15)),
  {
    Built: 'cornerstone May 25, 1966; structurally complete Mar 1969; dedicated Dec 13, 1969',
    Size: '880 ft (268 m) long; courts, jail and county offices; meets the Administration Building at 120°',
    Model: 'as the Administration Building (outline from OpenStreetMap, © OSM contributors, ODbL; heights estimated)'
  },
  [WIKI + 'Marin_County_Civic_Center'],
  [rotPoly([[-47, 40], [18, -212], [52, -170], [-8, 52]], MCC_BRG)]
);

// ---- Mission San Rafael Arcángel (replica chapel, 1949), frame 7°
const MISSION_SR: V2 = [-122.527917, 37.974333];
const missionSanRafael = landmark(
  'mission_san_rafael',
  'Mission San Rafael Arcángel (replica chapel)',
  'building',
  [1948.6, 1949.5],
  9999,
  MISSION_SR,
  b => {
    b.frame(0, 0, 0, 7, () => {
      b.color(ADOBE);
      boxR(b, [1.9, 13.7, 3.9, 22.6], 0, 6.8);
      boxR(b, [-5.7, 16.4, -6.9, 3.9], 0, 5);
      b.color(TILE).gable(7.8, 13.25, 12.6, 19.5, 6.8, 3, true);
      b.gable(5.35, -1.5, 22.9, 11.6, 5, 2.4, false);
      // stepped front gable with the star window, and the bell wall
      b.color(ADOBE);
      b.quad([1.9, 3.85, 6.8], [13.7, 3.85, 6.8], [11, 3.85, 9.6], [4.6, 3.85, 9.6]);
      b.color('#5A4A3E').cap(circle(7.8, 3.8, 0.9, 8).map(([x, y]) => [x, y] as V2), 0).box(7.8, 3.8, 7.6, 1.6, 0.1, 1.6);
      b.color(ADOBE).box(-3.6, -6.9, 5, 4, 0.8, 3.2);
      b.color('#5A4A3E');
      for (const x of [-4.6, -2.6]) b.box(x, -7, 6, 0.9, 0.2, 1.4);
    });
  },
  {
    Founded: 'Dec 14, 1817 as an asistencia (hospital) of Mission San Francisco de Asís; full mission 1822; ruins removed 1870',
    Built: 'the replica chapel was built in 1949 on the site of the mission hospital, beside St. Raphael\'s Church',
    Model: 'outline from OpenStreetMap (© OSM contributors, ODbL); wall and roof heights, star window and bell openings estimated from photographs'
  },
  [WIKI + 'Mission_San_Rafael_Arc%C3%A1ngel'],
  [rotPoly(rect(5.35, 7.8, 23, 30.5), 7)]
);

// ---- Point Bonita Lighthouse (lens of 1855, tower on the present ledge since 1877)
const POINT_BONITA: V2 = [-122.529538, 37.815595];
const pointBonita = landmark(
  'point_bonita_lighthouse',
  'Point Bonita Lighthouse',
  'tower',
  [1877.0, 1877.5],
  9999,
  POINT_BONITA,
  b => {
    b.frame(0, 0, 0, 59.9, () => {
      // 33 ft tower with the second-order Fresnel lens, attached to the fog-signal / workroom building (OSM 12 × 4 m)
      b.color('#F1F0EA').box(0, -2.5, 0, 4, 7, 3.6);
      b.color('#B33A2E').gable(0, -2.5, 4.2, 7.2, 3.6, 1.2, true);
      b.color('#F1F0EA').prism(octagon(0, 3.2, 2.1), 0, 7.4);
      b.color('#2B2D2F').prism(octagon(0, 3.2, 2.5), 7.4, 7.8).cylinder(0, 3.2, 1.6, 7.8, 9.2, 10);
      b.dome(0, 3.2, 1.7, 9.2, 0.9, 10, 2);
    });
  },
  {
    Built: 'first lit 1855 on higher ground (306 ft), often hidden by fog; moved in 1877 to its ledge at 124 ft, reached through a 118 ft tunnel hand-carved through the rock',
    Tower: '33 ft (10 m), white with a black lantern; second-order Fresnel lens; focal height 124 ft',
    Bridge: 'suspension footbridge of 1954, replaced in 2012 (not modelled)',
    Model: 'footprint from OpenStreetMap (© OSM contributors, ODbL); octagonal tower and lantern proportions from photographs (estimated)'
  },
  [WIKI + 'Point_Bonita_Lighthouse']
);

// ---- Point Reyes Lighthouse (1870): sixteen-sided cast-iron tower, 37 ft
const POINT_REYES: V2 = [-123.023151, 37.995618];
const pointReyes = landmark(
  'point_reyes_lighthouse',
  'Point Reyes Lighthouse',
  'tower',
  [1870.3, 1870.92],
  9999,
  POINT_REYES,
  b => {
    b.color('#EEEDE8').frustum(0, 0, 2.7, 2.2, 0, 6.2, 16);
    b.color('#2C2E30').cylinder(0, 0, 2.6, 6.2, 6.6, 16);
    b.color('#C9D2D4').cylinder(0, 0, 1.7, 6.6, 9.2, 16);
    b.color('#B73A32').dome(0, 0, 1.9, 9.2, 1.3, 16, 2);
    b.color('#B73A32').cylinder(0, 0, 0.12, 10.5, 11.3, 4);
  },
  {
    Built: 'first lit Dec 1, 1870; sixteen-sided cast-iron tower 37 ft (11 m) with a first-order Fresnel lens, on a ledge some 300 steps below the headland',
    Model: 'footprint and height from OpenStreetMap (© OSM contributors, ODbL; 10.7 m); white tower, black gallery, red lantern roof from a photograph; proportions estimated; the adjoining red-roofed equipment building is not modelled; stands on the smoothed terrain grid, not its true ledge'
  },
  [WIKI + 'Point_Reyes_Lighthouse']
);

// =================================================================== PENINSULA (San Mateo County) AND THE STANFORD HILLS

// ---- Filoli (Woodside), frame 52°: Georgian Revival brick house round a forecourt (OSM outline)
const FILOLI: V2 = [-122.310847, 37.470369];
const filoli = landmark(
  'filoli',
  'Filoli',
  'building',
  [1915.3, 1917.5],
  9999,
  FILOLI,
  b => {
    b.frame(0, 0, 0, 52, () => {
      const BRICK = '#A85B46'; // red brick, white trim (photo)
      const ROOF = '#6F6058'; // grey-brown tiles (photo)
      const wings: [number, number, number, number][] = [
        [-28.4, 28.1, -20.4, -5.4],
        [-25.6, -12.2, -5.4, 30.1],
        [13.2, 26.3, -5.4, 29.6],
        [-15, 15, -5.4, 2.6]
      ];
      b.color(BRICK);
      for (const w of wings) boxR(b, w, 0, 9.5, false);
      b.color(ROOF);
      for (const w of wings.slice(0, 3)) hipR(b, [w[0] - 0.5, w[1] + 0.5, w[2] - 0.5, w[3] + 0.5], 9.5, (Math.min(w[1] - w[0], w[3] - w[2]) / 2 + 0.5) * Math.tan((32 * Math.PI) / 180));
      b.cap(rect(0, -1.4, 30, 8), 9.5);
      // tall chimneys and the white entrance portico
      b.color('#9A5240');
      for (const [x, y] of [[-20, -12.9], [-6, -12.9], [8, -12.9], [21, -12.9], [-19, 14], [19.7, 14]] as V2[]) b.box(x, y, 9.5, 1.4, 2.6, 5.6);
      b.color('#EDEAE2').box(0, -21.6, 0, 7, 2.4, 6.5);
    });
  },
  {
    Built: '1915–1917 for William Bowers Bourn II (gold-mine owner, president of the Spring Valley Water Company) and Agnes Moody Bourn; architect Willis Polk',
    Size: '54,256 sq ft, 56 rooms; 16 acres of formal gardens in a 654-acre estate; National Trust since 1975',
    Model: 'outline from OpenStreetMap (© OSM contributors, ODbL); wall height (9.5 m), roof pitch, chimneys and portico estimated from photographs'
  },
  [WIKI + 'Filoli'],
  [rotPoly(rect(0, 4.8, 58, 52), 52)]
);

// ---- Pigeon Point Lighthouse (1872): tower base located on the orthophoto (its shadow)
const PIGEON_POINT: V2 = [-122.393858, 37.181692];
const pigeonPoint = landmark(
  'pigeon_point_lighthouse',
  'Pigeon Point Lighthouse',
  'tower',
  [1871.3, 1872.87],
  9999,
  PIGEON_POINT,
  b => {
    const H = 115 * FT;
    b.color('#F2F1EC').frustum(0, 0, 4.3, 2.9, 0, H - 4.4, 16);
    b.color('#2C2E30').cylinder(0, 0, 3.7, H - 4.4, H - 4.0, 16);
    b.color('#C9D2D4').cylinder(0, 0, 2.0, H - 4.0, H - 1.4, 12);
    b.color('#2C2E30').dome(0, 0, 2.2, H - 1.4, 1.4, 12, 2);
    b.color('#F2F1EC').box(0, -6, 0, 6, 5, 4.5);
  },
  {
    Built: 'built 1871; first lit at sunset on Nov 15, 1872 — at 115 ft (35 m) one of the tallest lighthouses in the United States',
    Tower: 'tapered brick cylinder, white with black trim; first-order Fresnel lens (1,008 prisms), focal height 148 ft',
    Status: 'closed to visitors since Dec 2001 after the brickwork carrying the iron walkways failed; $16 million rehabilitation announced Dec 2023',
    Model: 'base position from the tower\'s shadow on the orthophoto; diameters estimated from photographs'
  },
  [WIKI + 'Pigeon_Point_Lighthouse']
);

// ---- Stanford Dish (1961): 150 ft radio telescope, shown stowed at zenith
const STANFORD_DISH: V2 = [-122.179577, 37.408572];
const stanfordDish = landmark(
  'stanford_dish',
  'Stanford Dish',
  'tower',
  [1960.6, 1961.8],
  9999,
  STANFORD_DISH,
  b => {
    const R = 150 * FT * 0.5; // 22.9 m
    const f = 0.4 * 2 * R;
    const z0 = 26;
    // concrete base and the steel alt-azimuth yoke
    b.color('#BDB9B1').cylinder(0, 0, 8, 0, 6, 16);
    b.color('#9EA3A6');
    for (const s of [-1, 1]) {
      b.beam([s * 9, -4, 6], [s * 9, 0, z0], 1.2).beam([s * 9, 4, 6], [s * 9, 0, z0], 1.2);
    }
    b.box(0, 0, 6, 20, 3, 2);
    // paraboloid reflector (mesh surface over a radial truss)
    const prof: [number, number][] = [];
    for (let i = 0; i <= 5; i++) {
      const r = (R * i) / 5;
      prof.push([r, z0 + (r * r) / (4 * f)]);
    }
    b.color('#D8DBDB');
    revolve(b, 0, 0, prof, 0, 360, 15);
    // feed legs to the focus
    b.color('#9EA3A6');
    for (let k = 0; k < 4; k++) {
      const a = (k * Math.PI) / 2 + Math.PI / 4;
      b.beam([Math.cos(a) * R * 0.8, Math.sin(a) * R * 0.8, z0 + (R * R * 0.64) / (4 * f)], [0, 0, z0 + f], 0.35);
    }
    b.box(0, 0, z0 + f - 1, 1.8, 1.8, 2);
  },
  {
    Built: '1961 by the Stanford Research Institute (SRI) for the US Air Force, $4.5 million; steerable 150 ft (46 m) dish',
    Model: 'position from the orthophoto; mount, yoke height and focal ratio estimated from photographs; shown pointing at the zenith'
  },
  [WIKI + 'Stanford_Dish'],
  [circle(0, 0, 10, 8)]
);

// ---- SLAC: the two-mile klystron gallery over the linear accelerator (frame 81.4°, +v = east)
const SLAC: V2 = [-122.222146, 37.414389];
const slacGallery = landmark(
  'slac_klystron_gallery',
  'SLAC — two-mile linear accelerator (klystron gallery)',
  'building',
  [1962.5, 1966.4],
  9999,
  SLAC,
  b => {
    b.frame(0, 0, 0, 81.4, () => {
      // 3,074 m long sheet-steel shed (17 × 30 ft) above the buried accelerator; stepped with the ground
      for (let v = -1527; v < 1542; v += 96) {
        const v1 = Math.min(v + 96, 1542.3);
        const dz = groundDz(SLAC, 81.4, -1.2, (v + v1) / 2);
        b.color('#C9CCCB');
        boxR(b, [-5.75, 3.35, v, v1], dz - 2, dz + 5.2);
        b.color('#9FA6A9');
        boxR(b, [-5.9, 3.5, v, v1], dz + 5.2, dz + 5.5);
      }
    });
  },
  {
    Built: 'laboratory founded 1962; the 2-mile (3.2 km) linac first ran in 1966; from 1966 to 1999 the longest building in the world',
    Gallery: '3,073.7 m long; the klystrons feed the accelerator in a 10 × 11 ft tunnel under 25 ft of compacted earth',
    Model: 'outline from OpenStreetMap (© OSM contributors, ODbL); section 17 ft × 30 ft (SLAC); drawn in ~100 m steps following the ground'
  },
  [WIKI + 'SLAC_National_Accelerator_Laboratory', 'https://ahro.slac.stanford.edu/resources/slac-history/history-bits'],
  [rotPoly(rect(-1.2, 7.7, 16, 3070), 81.4)]
);

// ---- NASA Ames: National Full-Scale Aerodynamics Complex (frame 0°, anchor = OSM 40 × 80 ft tunnel centroid)
const NFAC: V2 = [-122.062854, 37.415067];
const NFAC_40X80: V2[] = [
  [-47.4, 141.8], [-49.8, 63.0], [-52.7, 63.1], [-54.4, 31.6], [-57.2, 31.7], [-57.7, 23.1], [-50.7, 22.8], [-56.4, -67.8], [-56.9, -123.6], [66.7, -123.1],
  [67.1, -54.1], [54.7, -33.3], [52.0, -10.6], [27.7, -10.5], [23.5, -31.4], [12.3, -53.4], [12.5, -68.6], [-2.4, -68.5], [-7.3, 21.9], [-3.3, 22.4],
  [-6.2, 62.8], [-9.7, 62.3], [-11.5, 106.2], [22.7, 106.1], [24.7, 29.5], [52.7, 29.8], [57.7, 105.4], [56.9, 142.5]
];
const nfac40x80 = landmark(
  'nasa_ames_40x80_wind_tunnel',
  'NASA Ames 40 × 80 ft wind tunnel',
  'building',
  [1941.6, 1944.45],
  9999,
  NFAC,
  b => {
    // closed-circuit tunnel: two legs, turning vanes at both ends, drive fans in the south end
    b.color('#C4C6C3').prism(NFAC_40X80, 0, 30);
    b.color('#B3B6B4');
    boxR(b, [-56.9, 66.7, -123.4, -68.6], 30, 36);
    b.color('#8E9396');
    for (let k = 0; k < 6; k++) b.box(-48 + k * 20, -125, 4, 14, 1.2, 22);
  },
  {
    Built: 'built 1941–44 at the NACA Ames Aeronautical Laboratory; the largest wind tunnel in the world, 40 × 80 ft test section, six 40 ft fans; upgraded 1982–87 into the National Full-Scale Aerodynamics Complex',
    Model: 'outline from OpenStreetMap (© OSM contributors, ODbL); the circuit\'s heights (30–36 m; OSM gives 54.9 m for the complex) and fan housings estimated (LOW CONFIDENCE)'
  },
  [WIKI + 'Ames_Research_Center'],
  [rect(5, 9.5, 126, 268)]
);
const nfac80x120 = landmark(
  'nasa_ames_80x120_wind_tunnel',
  'NASA Ames 80 × 120 ft wind tunnel',
  'building',
  [1982.5, 1987.9],
  9999,
  NFAC,
  b => {
    // open-circuit leg: the great inlet (screened face, open to the north-west) and the diffuser into the 40 × 80 circuit
    b.color('#BFC2BF').prism(
      [[-49.2, 78.7], [-47.7, 133.3], [-63.7, 147.7], [-60.2, 151.5], [-111.5, 203.4], [-117.5, 215.4], [-139.6, 165.5], [-94.3, 117.7], [-90.9, 120.7]],
      0,
      40
    );
    b.color('#D6D8D3');
    const front: V2[] = [[-123.4, 268.5], [-211.4, 181.0]];
    const back: V2[] = [[-114.2, 256.2], [-158.3, 174.8]];
    b.quad([front[0][0], front[0][1], 0], [front[1][0], front[1][1], 0], [back[1][0], back[1][1], 54.9], [back[0][0], back[0][1], 54.9]);
    b.color('#A9ACA9');
    b.quad([back[0][0], back[0][1], 0], [back[1][0], back[1][1], 0], [back[1][0], back[1][1], 54.9], [back[0][0], back[0][1], 54.9]);
    b.prism([[-118.7, 227.5], [-114.2, 256.2], [-158.3, 174.8], [-139.6, 165.5], [-117.5, 215.4]], 0, 54.9);
    b.walls([[-211.4, 181.0], [-158.3, 174.8]], 0, 54.9);
    b.color('#8E9396');
    for (let t = 0.1; t < 1; t += 0.2) {
      const x0 = front[0][0] + (front[1][0] - front[0][0]) * t;
      const y0 = front[0][1] + (front[1][1] - front[0][1]) * t;
      const x1 = back[0][0] + (back[1][0] - back[0][0]) * t;
      const y1 = back[0][1] + (back[1][1] - back[0][1]) * t;
      b.beam([x0, y0, 0], [x1, y1, 54.9], 0.8);
    }
  },
  {
    Built: '1982–87: an open-circuit 80 × 120 ft test section added to the 40 × 80 ft tunnel — the largest wind tunnel in the world (National Full-Scale Aerodynamics Complex)',
    Model: 'outline and height (54.9 m) from OpenStreetMap (© OSM contributors, ODbL); the sloping screened inlet face from the orthophoto; diffuser height estimated (LOW CONFIDENCE)'
  },
  [WIKI + 'Ames_Research_Center'],
  [[[-49.2, 78.7], [-47.7, 133.3], [-112.5, 261.2], [-123.4, 268.5], [-211.4, 181.0], [-90.9, 120.7]]]
);

// =================================================================== MOUNTAIN VIEW, SANTA CLARA AND SAN JOSÉ: AMPHITHEATRE, CAMPUSES AND MALLS

/** Even–odd point-in-polygon test. */
function inPoly(x: number, y: number, poly: V2[]) {
  let inside = false;
  for (let i = 0, j = poly.length - 1; i < poly.length; j = i++) {
    const [xi, yi] = poly[i];
    const [xj, yj] = poly[j];
    if (yi > y !== yj > y && x < ((xj - xi) * (y - yi)) / (yj - yi) + xi) inside = !inside;
  }
  return inside;
}

/** Extruded footprints / building parts (massing from OSM outlines and heights). */
function massing(b: MeshBuilder, parts: {o: V2[]; h: number; z0?: number}[], wall: string, roof: string) {
  for (const p of parts) {
    b.color(wall).prism(p.o, p.z0 ?? 0, p.h, {top: false});
    b.color(roof).cap(p.o, p.h);
  }
}

/**
 * Tented "dragonscale" roof: glazed walls to `eave`, then a lattice of four-sided tents (grid `s` m, turned 45°)
 * peaking at `peak` wherever a whole tent fits inside the outline; the rest of the roof is flat at the eave.
 */
function tentRoof(b: MeshBuilder, ring: V2[], eave: number, peak: number, s: number, skin: string) {
  b.color('#9FB2BC').prism(ring, 0, eave, {top: false});
  b.color('#B9BEC0').cap(ring, eave);
  const xs = ring.map(p => p[0]);
  const ys = ring.map(p => p[1]);
  const R = Math.max(...xs.map(Math.abs), ...ys.map(Math.abs)) + s;
  const c = Math.SQRT1_2;
  b.color(skin);
  for (let i = -R; i <= R; i += s) {
    for (let j = -R; j <= R; j += s) {
      const cx = (i - j) * c;
      const cy = (i + j) * c;
      const h = s * c;
      const corners: V2[] = [[cx + h, cy], [cx, cy + h], [cx - h, cy], [cx, cy - h]];
      if (!corners.every(([x, y]) => inPoly(x, y, ring)) || !inPoly(cx, cy, ring)) continue;
      b.pyramid(corners, eave + 0.05, [cx, cy, peak]);
    }
  }
}

// ---- Shoreline Amphitheatre (1986): tensile canopy over the stage and reserved seats (OSM outline, 4-pointed)
const SHORELINE: V2 = [-122.080733, 37.426788];
const SHORELINE_CANOPY: V2[] = [[-56.9, -23.7], [-75.2, -32.4], [-55.4, -31.4], [-45.6, -32.4], [-23.5, -37.9], [-9.7, -47.2], [1.5, -57.5], [6.2, -63.0], [7.5, -46.0], [11.2, -29.5], [20.5, -13.8], [31.8, 0.7], [38.5, 5.8], [53.8, 14.6], [62.0, 17.9], [54.5, 19.6], [47.4, 22.7], [39.8, 26.8], [26.6, 36.2], [20.0, 44.1], [13.7, 53.8], [8.9, 63.4], [2.8, 82.0], [1.6, 62.8], [-3.9, 38.9], [-7.5, 27.9], [-17.2, 11.8], [-28.7, -2.9], [-38.2, -11.3]];
const shorelineAmphitheatre = landmark(
  'shoreline_amphitheatre',
  'Shoreline Amphitheatre',
  'stadium',
  [1985.5, 1986.45],
  9999,
  SHORELINE,
  b => {
    // reserved seats (red, photo) in a fan facing the stage, north-west of it; the lawn bowl is the terrain
    const st: V2 = [9, -12];
    b.color('#A9473E');
    const inner: V3[] = [];
    const outer: V3[] = [];
    for (let a = 262; a <= 368; a += 6) {
      const r = (a * Math.PI) / 180;
      inner.push([st[0] + Math.sin(r) * 20, st[1] + Math.cos(r) * 20, 0.8]);
      outer.push([st[0] + Math.sin(r) * 72, st[1] + Math.cos(r) * 72, 9]);
    }
    b.ribbon(inner, outer);
    b.color('#8F8A80').wallProfile(outer.map(p => [p[0], p[1]] as V2), 0, 9);
    // stage
    b.color('#4A4744').prism(
      [[st[0] - 14, st[1] + 6], [st[0] + 6, st[1] + 14], [st[0] + 16, st[1] - 6], [st[0] - 4, st[1] - 14]],
      0,
      2
    );
    // canopy: fabric anchored at the four points (4 m, OSM min height) and lifted by two masts to 18 m (OSM height)
    const masts: V2[] = [[-6, 6], [10, -10]];
    const tips: V2[] = [[-75.2, -32.4], [6.2, -63.0], [62.0, 17.9], [2.8, 82.0]];
    const zb = (p: V2) => 4 + Math.min(6, Math.min(...tips.map(t => Math.hypot(p[0] - t[0], p[1] - t[1]))) * 0.12);
    const ring = SHORELINE_CANOPY;
    const near = (p: V2) => (Math.hypot(p[0] - masts[0][0], p[1] - masts[0][1]) < Math.hypot(p[0] - masts[1][0], p[1] - masts[1][1]) ? 0 : 1);
    b.color('#F2F2EE');
    for (let i = 0; i < ring.length; i++) {
      const p = ring[i];
      const q = ring[(i + 1) % ring.length];
      const m = near([(p[0] + q[0]) / 2, (p[1] + q[1]) / 2]);
      const M: V3 = [masts[m][0], masts[m][1], 18];
      b.tri([p[0], p[1], zb(p)], [q[0], q[1], zb(q)], M);
      const mq = near(q);
      if (mq !== m) b.tri([q[0], q[1], zb(q)], M, [masts[mq][0], masts[mq][1], 18]);
    }
    b.color('#8E9396');
    for (const [x, y] of masts) b.beam([x, y, 0], [x, y, 19.5], 0.6);
  },
  {
    Built: '1985–86 by the city of Mountain View with promoter Bill Graham as part of Shoreline Park, on the city landfill; opened summer 1986',
    Capacity: '22,500: 6,500 reserved seats under and beside the canopy, 16,000 on the lawn',
    Canopy: '85,000 sq ft (7,900 m²) tensile fabric tent; Graham shaped the amphitheatre after the Grateful Dead\'s "steal your face" logo seen from above',
    Model:
      'canopy outline and heights from OpenStreetMap (© OSM contributors, ODbL: 4 m at the anchor points, 18 m overall); mast positions, seat fan and stage estimated from the orthophoto'
  },
  [WIKI + 'Shoreline_Amphitheatre'],
  [circle(0, 0, 30, 12)]
);

// ---- Googleplex: the Silicon Graphics campus at 1600 Amphitheatre Parkway (Buildings 40–43)
const GOOGLEPLEX: V2 = [-122.0848, 37.422];
const GOOGLEPLEX_SGI: {o: V2[]; h: number}[] = [
  {o: [[-0.8,13.3],[19.6,15.6],[17.6,23.2],[26.2,25.4],[28.8,15.6],[39.3,18.3],[36.8,28.2],[48.8,31.3],[49.7,24.3],[44.0,17.4],[47.8,14.6],[52.5,19.5],[52.3,17.2],[72.6,15.5],[72.8,17.9],[88.2,16.7],[90.7,7.1],[122.9,15.4],[124.7,8.6],[134.4,11.3],[136.2,15.2],[151.7,18.4],[151.6,15.3],[155.5,16.4],[174.1,25.6],[180.5,31.0],[180.1,32.2],[159.9,25.5],[167.6,34.3],[167.1,41.3],[130.0,31.8],[127.9,39.5],[130.6,42.0],[113.6,54.1],[95.1,63.6],[65.3,72.8],[34.2,75.5],[13.5,73.7],[-7.9,69.1],[-13.1,42.1],[-13.3,15.9]], h: 18.0},
  {o: [[-31.0,59.1],[-73.9,94.1],[-104.9,56.4],[-82.2,38.5],[-87.8,41.5],[-93.0,38.6],[-96.8,32.2],[-94.5,31.3],[-97.6,24.3],[-88.2,16.8],[-73.8,12.4],[-72.1,16.1],[-63.6,17.7],[-65.4,23.1],[-61.6,21.1],[-55.0,28.7],[-53.6,22.5],[-38.7,21.9],[-38.4,27.0],[-41.7,27.1],[-42.5,31.7],[-49.5,36.7]], h: 18.0},
  {o: [[-64.6,-4.4],[-73.1,-6.3],[-74.2,-5.1],[-80.4,-10.4],[-103.9,-8.8],[-105.7,-29.7],[-101.7,-30.0],[-98.5,-48.4],[-100.0,-48.5],[-99.6,-56.6],[-96.2,-56.5],[-94.8,-62.1],[-88.6,-62.4],[-88.5,-57.9],[-77.4,-58.5],[-77.6,-63.5],[-47.0,-65.8],[-45.5,-40.0],[-49.1,-40.1],[-48.6,-30.7],[-47.1,-30.2],[-49.0,-22.6],[-51.9,-22.3],[-57.3,-5.1]], h: 18.0},
  {o: [[108.1,-31.6],[108.4,-33.0],[106.5,-33.6],[105.5,-29.4],[82.6,-35.2],[81.1,-29.4],[71.8,-33.4],[71.2,-31.1],[60.5,-33.7],[62.1,-39.9],[57.6,-39.8],[58.9,-22.2],[48.1,-21.4],[30.6,-28.4],[27.1,-13.7],[-20.7,-26.5],[-22.7,-65.0],[-9.1,-67.5],[-9.2,-69.0],[48.6,-72.9],[49.3,-61.9],[60.6,-62.5],[70.2,-63.5],[76.3,-72.0],[84.3,-75.1],[84.9,-72.2],[86.2,-72.5],[85.9,-76.3],[130.7,-79.7],[131.3,-67.6],[153.6,-69.2],[156.6,-73.4],[162.8,-67.6],[170.0,-55.5],[170.7,-53.1],[162.5,-51.0],[163.3,-48.0],[170.5,-46.0],[168.6,-38.5],[164.8,-39.3],[166.9,-31.0],[151.7,-27.1],[133.1,-26.9],[132.9,-25.6]], h: 18.0}
];
const googleplexSGI = landmark(
  'googleplex_sgi_campus',
  'Googleplex (Buildings 40–43, the former Silicon Graphics campus)',
  'building',
  [1994.5, 1997.5],
  9999,
  GOOGLEPLEX,
  b => massing(b, GOOGLEPLEX_SGI, '#B9C3CA', '#8D979E'),
  {
    Built: '1994–97 for Silicon Graphics (SGI) on a 26-acre site with Charleston Park (landscape: SWA Group); county roll: 1997',
    Google: 'leased by Google from 2003 (interiors by Clive Wilkinson Architects, 2005); bought in June 2006 for $319 million',
    Model: 'massing from the OpenStreetMap outlines and heights (© OSM contributors, ODbL; 18 m, 3 storeys); facades not detailed; the campus\'s other buildings are left to the generic footprints'
  },
  [WIKI + 'Googleplex'],
  GOOGLEPLEX_SGI.map(p => p.o)
);

// ---- Google Bay View (2022): BIG + Heatherwick, two buildings under tented "dragonscale" solar roofs
const BAY_VIEW_A: V2 = [-122.0668, 37.4228];
const BAY_VIEW: {o: V2[]; h: number}[] = [
  {o: [[-68.1,113.5],[-63.3,62.5],[-50.7,11.3],[-39.2,-20.2],[-8.5,-20.2],[29.5,-15.8],[71.4,-8.0],[105.9,2.5],[123.5,-4.5],[133.5,23.0],[120.2,26.7],[114.7,91.0],[103.7,138.6],[91.1,166.6],[60.7,168.8],[9.3,164.4],[-39.2,151.1],[-67.1,138.1]], h: 41.3},
  {o: [[-68.7,-118.6],[-67.9,-153.4],[-38.4,-168.8],[2.9,-178.9],[36.3,-179.6],[51.5,-150.8],[63.1,-105.9],[62.8,-75.6],[34.3,-57.8],[-7.5,-46.8],[-40.6,-48.5],[-58.3,-76.3]], h: 10.7}
];
const googleBayView = landmark(
  'google_bay_view',
  'Google Bay View',
  'building',
  [2019.0, 2022.37],
  9999,
  BAY_VIEW_A,
  b => {
    tentRoof(b, BAY_VIEW[0].o, 10, 19, 32, '#8C99A6');
    tentRoof(b, BAY_VIEW[1].o, 10, 19, 32, '#8C99A6');
  },
  {
    Opened: 'May 2022 on 42 acres leased from NASA Ames beside Moffett Field; two office buildings, an events centre and 240 short-stay units; 1.1 million sq ft',
    Architects: 'BIG (Bjarke Ingels Group) and Heatherwick Studio',
    Roof: '"dragonscale" solar skin of some 50,000 silver panels (≈ 7 MW) over tented canopies with clerestories',
    Model:
      'outlines from OpenStreetMap (© OSM contributors, ODbL) and the orthophoto (diamond lattice of tents); eave (two storeys, 10 m), tent peaks (19 m) and tent spacing estimated; construction start from the county roll (2019); the events centre is not modelled'
  },
  [WIKI + 'Googleplex', 'https://www.dezeen.com/2022/05/18/google-bay-view-campus-big-heatherwick-studio/'],
  BAY_VIEW.map(p => p.o)
);

// ---- Google Charleston East / Gradient Canopy (2023)
const CHARLESTON_EAST_A: V2 = [-122.079598, 37.421968];
const CHARLESTON_EAST: {o: V2[]; h: number}[] = [
  {o: [[-93.6,-45.8],[-65.4,-108.6],[3.5,-103.9],[46.1,-93.1],[109.0,-65.1],[104.1,3.6],[93.6,45.9],[65.5,108.8],[-3.5,104.1],[-46.0,93.5],[-109.0,65.3],[-104.2,-3.5]], h: 13.2}
];
const googleCharlestonEast = landmark(
  'google_charleston_east',
  'Google Charleston East (Gradient Canopy)',
  'building',
  [2019.0, 2023.78],
  9999,
  CHARLESTON_EAST_A,
  b => tentRoof(b, CHARLESTON_EAST[0].o, 7, 13.2, 26, '#8C99A6'),
  {
    Built: 'opened Oct 12, 2023 with the Google Visitor Experience; county roll year 2023 (construction start estimated)',
    Design: 'BIG and Heatherwick Studio; a single large building under a tented canopy roof',
    Model:
      'outline and height from OpenStreetMap (© OSM contributors, ODbL; 13.2 m); eave height and tent lattice estimated after Bay View'
  },
  [WIKI + 'Googleplex'],
  CHARLESTON_EAST.map(p => p.o)
);

// ---- Westfield Valley Fair (1986 enclosed mall; 2020 expansion)
const VALLEY_FAIR: V2 = [-121.9451, 37.3251];
const VALLEY_FAIR_1986: {o: V2[]; h: number}[] = [
  {o: [[-201.3,45.6],[-199.6,14.2],[-217.0,-3.4],[-219.2,-0.4],[-288.8,-1.0],[-288.5,-24.1],[-312.1,-23.8],[-311.4,-109.5],[-197.5,-109.4],[-196.6,-58.0],[-200.5,-58.0],[-200.5,-53.6],[-195.9,-48.9],[-197.5,-47.3],[-149.8,0.8],[-103.3,1.0],[-103.3,3.1],[-75.8,3.3],[-75.9,5.4],[-13.0,5.7],[-13.0,3.6],[14.4,3.8],[14.5,1.6],[64.5,1.8],[99.9,-33.3],[97.4,-35.8],[152.7,-89.0],[171.2,-70.5],[174.4,-68.5],[175.9,-70.0],[182.6,-63.4],[181.1,-61.9],[183.0,-58.8],[224.4,-16.6],[226.2,-18.4],[232.2,-12.4],[234.1,-14.3],[238.9,-11.4],[245.9,-4.6],[245.3,-1.5],[258.7,11.9],[135.0,135.3],[135.4,142.4],[129.5,142.8],[129.7,145.0],[123.0,147.2],[120.5,140.0],[117.4,140.2],[117.2,138.5],[76.3,142.8],[76.7,147.4],[60.1,148.7],[59.9,146.5],[54.7,146.9],[54.9,149.2],[45.2,150.0],[45.0,147.4],[35.6,148.1],[35.3,145.1],[22.1,146.1],[21.7,141.2],[10.0,140.3],[-8.1,142.1],[-7.9,144.9],[-17.8,143.4],[-59.1,149.7],[-69.1,152.0],[-69.1,157.1],[-78.4,157.1],[-78.4,154.5],[-84.3,154.5],[-84.3,158.9],[-179.5,158.7],[-178.7,93.0],[-189.0,93.0],[-192.5,89.6],[-183.5,77.6],[-180.2,83.2],[-177.5,82.7],[-177.5,62.3],[-192.0,48.0],[-195.4,51.5]], h: 14.1},
  {o: [[-194.0,-48.3],[-194.0,-83.0],[-185.0,-83.3],[-169.1,-61.3],[-153.9,-64.4],[-153.9,-74.3],[-140.3,-79.2],[-118.2,-79.2],[-76.0,-71.9],[-68.2,-74.3],[-66.0,-68.2],[-51.3,-71.2],[-54.6,-79.2],[-40.8,-84.7],[-40.6,-58.0],[41.5,-56.6],[42.0,-78.3],[46.1,-78.3],[46.1,-66.5],[52.9,-66.5],[53.2,-64.1],[66.9,-64.1],[69.8,-58.3],[114.7,-58.5],[118.7,-55.2],[97.4,-35.8],[99.9,-33.3],[64.5,1.8],[14.5,1.6],[14.4,3.8],[-13.0,3.6],[-13.0,5.7],[-75.9,5.4],[-75.8,3.3],[-103.3,3.1],[-103.3,1.0],[-149.8,0.8],[-193.3,-43.0],[-190.4,-45.8]], h: 20.6}
];
const VALLEY_FAIR_2020: {o: V2[]; h: number}[] = [
  {o: [[52.9,-66.5],[46.1,-66.5],[46.3,-114.9],[63.2,-131.4],[63.6,-164.9],[132.2,-164.1],[132.0,-132.1],[157.2,-131.6],[157.2,-112.7],[152.2,-93.9],[114.7,-58.5],[69.8,-58.3],[66.9,-64.1],[53.2,-64.1]], h: 19.5},
  {o: [[231.6,196.8],[215.6,196.9],[151.1,131.6],[174.5,108.7],[170.5,105.0],[183.5,91.6],[185.1,92.8],[192.5,85.4],[195.1,88.6],[265.9,19.0],[323.5,77.5],[322.6,106.5],[318.7,110.7],[324.0,116.0],[320.3,119.6],[329.1,127.9],[328.0,168.8],[298.7,197.2],[261.7,197.4],[251.9,186.6],[247.9,190.4],[242.7,185.7]], h: 10.5}
];
const valleyFair1986 = landmark(
  'valley_fair_1986',
  'Valley Fair (enclosed mall)',
  'building',
  [1985.0, 1986.7],
  9999,
  VALLEY_FAIR,
  b => massing(b, VALLEY_FAIR_1986, '#E2DACB', '#BDB6A8'),
  {
    Built: 'the open-air Valley Fair (opened 1958, Macy\'s) on the San José side and Stevens Creek Plaza (Emporium, I. Magnin) on the Santa Clara side were merged by the Hahn Company into one two-level enclosed mall in 1986; county roll: 1985',
    Later: '2001–02 expansion (dining terrace, 80 stores, three garages, Nordstrom relocated); remodel from 2013',
    Model:
      'massing from the OpenStreetMap outlines and heights (© OSM contributors, ODbL; 14.1 / 20.6 m) — today\'s outline, so the 2002 additions inside it stand from 1986; the 1958 open-air centre is not modelled (no plan found)'
  },
  [WIKI + 'Westfield_Valley_Fair'],
  VALLEY_FAIR_1986.map(p => p.o)
);
const valleyFair2020 = landmark(
  'valley_fair_2020',
  'Westfield Valley Fair — 2020 expansion (Bloomingdale\'s)',
  'building',
  [2017.5, 2020.18],
  9999,
  VALLEY_FAIR,
  b => massing(b, VALLEY_FAIR_2020, '#E6E1D8', '#B5B1A9'),
  {
    Opened: 'grand opening Mar 5, 2020 with Bloomingdale\'s; county roll: 2020',
    Model: 'massing from the OpenStreetMap outlines and heights (© OSM contributors, ODbL; the garage at 3 floors ≈ 10.5 m); construction start estimated'
  },
  [WIKI + 'Westfield_Valley_Fair'],
  VALLEY_FAIR_2020.map(p => p.o)
);

// ---- Santana Row (2002): Hotel Valencia and the mixed-use blocks along the row
const SANTANA_ROW: V2 = [-121.9479, 37.3204];
const SANTANA_ROW_PARTS: {o: V2[]; h: number; z0: number}[] = [
  {o: [[-66.1,41.3],[-73.6,41.3],[-77.8,39.3],[-80.3,35.3],[-80.3,30.7],[-75.8,25.5],[-66.0,24.8]], h: 10.7, z0: 0},
  {o: [[-54.1,41.6],[-54.1,35.3],[-44.8,35.3],[-44.8,41.6]], h: 31.0, z0: 0},
  {o: [[-44.8,39.8],[-44.8,35.3],[-54.1,35.3],[-54.1,39.7],[-59.7,39.7],[-59.7,29.4],[-27.8,29.5],[-27.8,39.9]], h: 25.7, z0: 0},
  {o: [[-22.0,72.3],[-22.0,69.6],[-24.2,69.6],[-24.1,46.1],[-13.1,46.1],[-11.5,61.9],[-13.4,67.7],[-13.5,72.4]], h: 18.2, z0: 0},
  {o: [[-22.0,72.3],[-43.8,72.2],[-43.7,46.0],[-24.1,46.1],[-24.2,69.6],[-22.0,69.6]], h: 13.7, z0: 0},
  {o: [[-26.9,46.8],[-27.0,71.1],[-42.6,71.0],[-42.4,46.7]], h: 9.3, z0: 0},
  {o: [[-13.4,67.7],[-16.1,67.0],[-14.8,61.2],[-15.9,51.8],[-12.7,51.2],[-11.5,61.9]], h: 18.3, z0: 0},
  {o: [[-43.8,72.2],[-11.5,72.4],[-11.6,94.7],[-66.4,94.4],[-65.5,68.4],[-57.9,68.4],[-57.2,72.1],[-57.1,65.9],[-61.2,65.9],[-61.1,51.9],[-57.1,52.0],[-57.0,45.7],[-57.8,49.5],[-65.4,49.4],[-66.0,23.4],[-11.2,23.7],[-11.4,46.1],[-43.7,46.0]], h: 27.1, z0: 0},
  {o: [[-64.4,68.4],[-64.3,49.4],[-57.8,49.5],[-57.0,45.7],[-57.1,52.0],[-61.1,51.9],[-61.2,65.9],[-57.1,65.9],[-57.2,72.1],[-57.9,68.4]], h: 23.0, z0: 0},
  {o: [[-65.5,71.0],[-67.1,71.0],[-66.8,51.9],[-70.6,41.3],[-66.1,41.3],[-65.4,49.4],[-64.3,49.4],[-64.4,68.4],[-65.5,68.4]], h: 19.9, z0: 0},
  {o: [[-54.2,79.3],[-54.1,73.6],[-47.7,73.7],[-47.7,77.4],[-49.6,77.3],[-49.7,79.3]], h: 30.9, z0: 0},
  {o: [[-54.2,78.4],[-54.2,79.3],[-49.7,79.3],[-49.6,78.4],[-28.0,78.5],[-28.1,88.5],[-60.0,88.4],[-59.9,78.3]], h: 26.8, z0: 0},
  {o: [[13.1,31.4],[15.5,32.6],[15.4,49.1],[13.1,49.1]], h: 10.2, z0: 0},
  {o: [[27.4,29.6],[29.9,30.3],[29.9,37.0],[36.6,37.0],[36.6,42.4],[48.8,42.4],[48.8,44.7],[37.8,44.7],[37.8,57.5],[44.3,57.5],[44.3,61.4],[37.8,61.4],[37.8,73.8],[48.8,74.5],[48.8,76.4],[36.6,76.4],[36.6,81.8],[29.9,81.7],[29.5,88.8],[27.4,88.8],[27.4,81.0],[30.8,81.0],[29.6,50.6],[30.8,50.6],[30.8,37.9],[27.4,37.9]], h: 9.9, z0: 0},
  {o: [[12.0,89.2],[15.4,86.2],[15.4,69.7],[11.9,69.7],[12.0,49.1],[15.4,49.1],[15.5,32.6],[13.1,31.4],[12.0,28.8],[13.2,25.4],[16.5,24.1],[34.0,24.4],[34.0,27.8],[55.5,27.8],[55.9,42.4],[51.8,42.4],[51.8,43.5],[55.5,43.5],[55.5,45.4],[52.4,45.4],[52.4,56.8],[56.1,56.8],[55.5,73.4],[51.8,73.4],[51.8,76.4],[55.9,76.4],[55.5,91.1],[34.0,91.1],[34.0,94.4],[15.9,94.7],[12.7,92.9]], h: 21.0, z0: 0},
  {o: [[13.0,87.6],[13.0,69.7],[15.4,69.7],[15.4,86.2]], h: 10.5, z0: 0},
  {o: [[55.3,94.0],[34.0,94.0],[34.0,91.1],[55.3,91.1]], h: 9.9, z0: 0},
  {o: [[55.3,24.9],[55.3,27.8],[34.0,27.8],[34.0,24.9]], h: 10.1, z0: 0},
  {o: [[34.1,6.5],[35.2,-76.1],[34.0,-81.6],[34.0,-98.2],[35.3,-98.2],[36.1,-108.9],[33.9,-108.9],[34.2,-116.6],[34.6,-122.1],[40.7,-122.1],[40.7,-110.2],[63.5,-110.1],[63.3,-61.6],[50.3,-61.6],[50.3,-63.4],[40.5,-63.4],[40.5,-52.4],[50.3,-52.4],[50.3,-54.4],[63.3,-54.3],[63.1,-5.7],[53.6,-6.4],[53.6,-4.4],[45.6,-6.5],[40.3,-5.7],[40.3,6.5]], h: 8.7, z0: 0},
  {o: [[50.3,-63.4],[50.3,-52.4],[40.5,-52.4],[40.5,-63.4]], h: 12.7, z0: 0},
  {o: [[34.6,-122.1],[33.9,-108.9],[36.1,-108.9],[35.3,-98.2],[34.0,-98.2],[34.0,-81.6],[35.2,-76.1],[34.1,6.5],[20.4,6.8],[21.6,-44.8],[20.6,-64.1],[21.7,-68.1],[20.8,-122.7]], h: 17.4, z0: 0},
  {o: [[53.9,-110.7],[55.4,-110.7],[55.4,-122.8],[63.8,-122.7],[63.8,-110.1],[53.9,-109.5]], h: 17.0, z0: 0},
  {o: [[40.7,-122.1],[49.6,-122.6],[49.5,-110.7],[51.3,-110.7],[51.3,-109.8],[40.7,-110.2]], h: 16.5, z0: 0},
  {o: [[55.4,-110.7],[49.5,-110.7],[49.6,-123.1],[55.4,-123.1]], h: 20.5, z0: 0},
  {o: [[49.1,7.0],[49.1,-4.4],[55.0,-4.5],[54.9,7.2]], h: 21.8, z0: 0},
  {o: [[40.3,6.9],[40.3,-5.7],[50.9,-5.8],[50.9,-4.4],[49.1,-4.4],[49.1,7.0]], h: 16.5, z0: 0},
  {o: [[54.9,7.0],[55.0,-4.5],[53.6,-4.5],[53.6,-6.4],[63.4,-5.7],[63.6,7.0]], h: 17.5, z0: 0}
];
const santanaRow = landmark(
  'santana_row',
  'Santana Row (Hotel Valencia and the row)',
  'building',
  [2001.0, 2002.85],
  9999,
  SANTANA_ROW,
  b => massing(b, SANTANA_ROW_PARTS, '#E7D8BC', '#B4664C'),
  {
    Built: '2001–02 by Federal Realty Investment Trust on the site of the Town and Country Village shopping centre — a $450 million "village within a city" (SB Architects, BAR Architects, Steinberg Architects; landscape SWA Group)',
    Fire: 'Aug 19, 2002: Building 7 ("Santana Heights"), the largest on the site, burned while under construction — San José\'s largest structure fire',
    Model:
      'massing from the OpenStreetMap outlines and 3D parts (© OSM contributors, ODbL) of Hotel Valencia (county roll 2003) and the two blocks opposite (roll 2002); later buildings on the row (2006, 2013, 2016) are left to the generic footprints; colours (stucco, clay tile) estimated'
  },
  [WIKI + 'Santana_Row'],
  SANTANA_ROW_PARTS.map(p => p.o)
);

// ---- Stanford Shopping Center: the dated anchor stores
const STANFORD_SC_MACYS: {o: V2[]; h: number; z0: number}[] = [
  {o: [[60.8,-2.8],[-8.0,59.4],[-17.5,47.4],[-59.7,3.6],[-56.9,0.7],[-58.8,-0.8],[-33.7,-24.2],[-32.0,-22.7],[6.6,-59.8]], h: 15.8, z0: 0}
];
const STANFORD_SC_NEIMAN: {o: V2[]; h: number; z0: number}[] = [
  {o: [[12.5,35.3],[-13.9,34.5],[-35.7,11.9],[-34.7,-14.7],[-27.5,-21.3],[-26.2,-19.9],[-18.3,-27.8],[-20.2,-29.3],[-12.7,-35.4],[14.3,-34.4],[27.3,-18.2],[28.6,-19.5],[35.9,-11.9],[34.8,14.0],[18.3,27.0],[19.6,28.6]], h: 12.0, z0: 0}
];
const STANFORD_SC_BLOOMINGDALES: {o: V2[]; h: number; z0: number}[] = [
  {o: [[-6.9,44.3],[-43.9,2.9],[5.0,-43.3],[43.9,-2.8]], h: 10.0, z0: 0}
];
const SSC_FACT =
  'Stanford Shopping Center opened in Sep 1955 (Roos Brothers) and was completed Oct 22, 1956, an open-air centre on Stanford land anchored by the Emporium and I. Magnin';
const SSC_MODEL =
  'massing from the OpenStreetMap outline and height (© OSM contributors, ODbL); the open-air store blocks are left to the generic footprints because their individual build and rebuild years are not documented';
const stanfordSCMacys = landmark(
  'stanford_shopping_center_macys',
  "Stanford Shopping Center — Macy's",
  'building',
  [1960.3, 1961.5],
  9999,
  [-122.171653, 37.442198],
  b => massing(b, STANFORD_SC_MACYS, '#E4DED2', '#B8B1A5'),
  {Center: SSC_FACT, Store: "Macy's joined in 1961 (Macy's California)", Model: SSC_MODEL + '; construction start estimated'},
  [WIKI + 'Stanford_Shopping_Center'],
  STANFORD_SC_MACYS.map(p => p.o)
);
const stanfordSCNeiman = landmark(
  'stanford_shopping_center_neiman_marcus',
  'Stanford Shopping Center — Neiman Marcus',
  'building',
  [1984.4, 1985.6],
  9999,
  [-122.172657, 37.441209],
  b => massing(b, STANFORD_SC_NEIMAN, '#E8E4DC', '#BDB8AE'),
  {Center: SSC_FACT, Store: 'Neiman Marcus became the sixth anchor in Aug 1985', Model: SSC_MODEL + '; construction start estimated'},
  [WIKI + 'Stanford_Shopping_Center'],
  STANFORD_SC_NEIMAN.map(p => p.o)
);
const stanfordSCBloomingdales = landmark(
  'stanford_shopping_center_bloomingdales',
  "Stanford Shopping Center — Bloomingdale's (2014)",
  'building',
  [2012.9, 2014.6],
  9999,
  [-122.169617, 37.443859],
  b => massing(b, STANFORD_SC_BLOOMINGDALES, '#E9E6E0', '#BBB7B0'),
  {
    Center: SSC_FACT,
    Store: "the Emporium store was rebranded Bloomingdale's in Nov 1996; this new three-level, 120,000 sq ft store opened in 2014 (the old building was demolished for the 2016 wing)",
    Model: SSC_MODEL + '; construction start estimated'
  },
  [WIKI + 'Stanford_Shopping_Center'],
  STANFORD_SC_BLOOMINGDALES.map(p => p.o)
);

// =================================================================== MILL VALLEY

// ---- Our Lady of Mount Carmel (1968): twelve-sided church under a steep pyramidal roof, copper spire and gold cross
const MT_CARMEL: V2 = [-122.546361, 37.907618];
const mountCarmel = landmark(
  'mill_valley_mount_carmel',
  'Our Lady of Mount Carmel Church, Mill Valley',
  'building',
  [1966.8, 1968.38],
  9999,
  MT_CARMEL,
  b => {
    // dodecagon from the OSM outline (r ≈ 21.7 m, a vertex at bearing ≈ 173°)
    const ring = arcPts(0, 0, 21.7, 173, 173 + 330, 11);
    b.color('#5F5650').prism(ring, 0, 5.5, {top: false}); // lava-rock walls, redwood doors
    b.color('#8A5A3C').box(0, -21.4, 0, 6, 0.6, 4.2);
    b.color('#BDBAB3').pyramid(ring.map(([x, y]) => [x * 1.04, y * 1.04] as V2), 5.5, [0, 0, 29]);
    // copper spire and the 18 ft gold-leaf cross, 140 ft above the sidewalk
    b.color('#6E9C88').pyramid(arcPts(0, 0, 1.6, 173, 173 + 330, 11), 26.5, [0, 0, 37]);
    b.color('#D4AF37').beam([0, 0, 37], [0, 0, 42.7], 0.4).beam([-1.6, 0, 40.7], [1.6, 0, 40.7], 0.35);
  },
  {
    Built: 'unveiled May 1968 after a fund drive by parishioners and residents; architect Fred Houweling',
    Form: 'twelve-sided (dodecagon) church; copper-covered spire carrying an 18-ft gold-leaf cross that rises 140 ft (42.7 m) above the sidewalk; entrance of lava rock round massive redwood doors',
    Model:
      'dodecagon outline from OpenStreetMap (© OSM contributors, ODbL); the twelve-faceted pyramid roof seen on the orthophoto; wall height (5.5 m) and the split between roof and spire estimated; the cross top set at 140 ft above the anchor ground'
  },
  ['https://enjoymillvalley.com/?p=3689'],
  [circle(0, 0, 23, 12)]
);

// ---- Mill Valley Public Library (1966): Wurster, Bernardi & Emmons, redwood among the redwoods on Throckmorton Ave
const MV_LIBRARY: V2 = [-122.554221, 37.906002];
const millValleyLibrary = landmark(
  'mill_valley_library',
  'Mill Valley Public Library',
  'building',
  [1965.49, 1966.7],
  9999,
  MV_LIBRARY,
  b => {
    const REDWOOD = '#8B5A3E';
    b.color(REDWOOD).prism(
      [[18.2, -22.8], [29.1, -5.7], [-18.2, 23.9], [-27.1, 10.0], [-16.9, 3.7], [-21.6, -3.7], [-9.5, -11.2], [-5.3, -8.0]],
      0,
      4.5,
      {top: false}
    );
    b.color('#6E6258');
    b.frame(0.5, 0.6, 0, 302, () => b.gable(0, 0, 20.8, 56.5, 4.5, 3.6, true));
    b.cap([[-16.9, 3.7], [-21.6, -3.7], [-9.5, -11.2], [-5.3, -8.0], [-10, 0]], 4.5);
    // glazed reading-room front toward the redwoods
    b.color('#8FA7AE').frame(0.5, 0.6, 0, 302, () => b.box(-10.45, 0, 0.6, 0.2, 40, 3.4));
  },
  {
    Built: 'groundbreaking Jun 29, 1965; opened 1966 at 375 Throckmorton Ave, replacing the 1911 Carnegie library',
    Architects: 'Wurster, Bernardi & Emmons (Donn Emmons); AIA Honor Award 1969, ALA/AIA Library Building Award 1968',
    Later: 'a later expansion keeps the mid-century character (≈ 27,000 sq ft today); its extent is not separated in the model',
    Model:
      'outline from OpenStreetMap (© OSM contributors, ODbL; today\'s building, incl. the later expansion); low gable roof, eave height and glazing estimated — the roof is hidden by redwoods on the orthophoto'
  },
  ['https://calisphere.org/item/d7603a5e413d0418ed1d6cb108616e2f', 'https://pcad.lib.washington.edu/building/7977', 'https://www.mvhistory.org/vignette-carnegie-library/'],
  [rotPoly(rect(0, 0, 22, 58), 302, 0.5, 0.6)]
);

// =================================================================== CALIFORNIA'S GREAT AMERICA (Santa Clara, 1976)

/** Park frame: local metres from GA (track centrelines from OpenStreetMap, ordered along the direction of travel). */
const GA: V2 = [-121.972, 37.397];
// ---- generated (scratch tool coasters.py) from the OSM roller_coaster=track ways, resampled every ~5 m: [x, y, z]…
// z is SCHEMATIC: the lift (OSM lift_hill tag, else the longest straight run) climbs to the documented height, the
// first drop falls over 1.1 × that height, and the rest of the circuit is drawn as four decaying hills (PROCEDURAL).
const GA_TRACKS: Record<string, number[]> = {
  demon: [-210.0,-310.1,2.0,-207.2,-314.9,3.2,-204.3,-319.7,4.5,-201.5,-324.5,5.7,-198.6,-329.3,6.9,-196.0,-333.7,8.1,-193.4,-338.1,9.2,-190.8,-342.5,10.3,-188.2,-346.8,11.4,-185.6,-351.2,12.6,-183.0,-355.6,13.7,-180.4,-360.0,14.8,-177.8,-364.4,15.9,-175.2,-368.8,17.1,-172.6,-373.2,18.2,-169.9,-377.8,19.4,-167.2,-382.4,20.5,-164.5,-386.9,21.7,-161.8,-391.5,22.9,-159.1,-396.1,24.1,-156.4,-400.7,25.2,-153.7,-405.3,26.4,-151.0,-409.9,27.6,-148.3,-414.4,28.8,-145.6,-419.0,29.9,-142.9,-423.6,31.1,-139.7,-428.2,26.5,-136.5,-432.8,21.9,-133.2,-436.5,17.8,-129.4,-439.1,14.0,-124.8,-440.2,10.2,-119.7,-440.0,6.0,-115.9,-438.8,3.0,-112.0,-436.1,3.3,-109.3,-432.0,4.1,-108.6,-427.2,5.3,-109.4,-422.8,6.7,-111.8,-419.2,8.3,-116.5,-415.7,10.7,-121.8,-412.9,13.3,-127.2,-410.0,15.7,-131.0,-407.9,17.3,-136.8,-404.8,19.2,-140.0,-402.8,19.9,-141.1,-401.7,20.2,-142.0,-400.5,20.4,-143.3,-398.2,20.6,-144.3,-395.2,20.7,-144.1,-393.3,20.7,-143.5,-391.4,20.6,-140.9,-387.6,20.1,-139.1,-384.9,19.5,-138.4,-383.5,19.1,-138.0,-381.6,18.6,-138.1,-379.6,18.1,-138.9,-378.1,17.5,-140.7,-376.0,16.6,-143.9,-373.4,15.1,-145.5,-371.9,14.3,-146.9,-370.3,13.5,-147.5,-368.5,12.7,-147.6,-366.8,12.0,-147.1,-365.3,11.4,-142.4,-357.8,7.9,-141.5,-356.1,7.3,-141.1,-354.3,6.7,-141.5,-352.0,6.0,-143.5,-349.9,5.1,-149.3,-344.3,3.6,-151.1,-341.8,3.2,-152.5,-337.8,3.0,-153.1,-333.8,3.1,-152.9,-329.8,3.4,-151.7,-326.1,4.0,-149.7,-323.2,4.7,-146.9,-320.9,5.5,-142.8,-319.4,6.7,-139.2,-319.3,7.7,-135.6,-320.2,8.8,-133.0,-321.7,9.8,-130.7,-324.2,10.8,-129.3,-327.2,11.7,-128.8,-330.6,12.7,-129.6,-333.7,13.5,-130.8,-335.9,14.0,-132.9,-338.1,14.6,-135.9,-340.5,15.1,-141.2,-344.1,15.6,-146.4,-347.6,15.6,-151.7,-351.2,15.0,-156.1,-353.2,14.2,-159.4,-353.2,13.5,-162.7,-352.2,12.7,-164.4,-350.7,12.1,-166.6,-347.5,11.1,-168.2,-343.3,9.8,-169.6,-338.2,8.3,-171.1,-333.0,6.8,-172.6,-327.8,5.5,-174.0,-322.7,4.4,-175.5,-317.5,3.6,-176.9,-312.4,3.2,-178.4,-307.2,3.0,-180.0,-301.6,3.2,-181.5,-296.1,3.7,-183.5,-288.8,4.7,-184.8,-285.6,5.3,-186.2,-281.3,6.2,-186.7,-278.3,6.8,-188.0,-275.2,7.4,-190.5,-272.0,8.2,-194.7,-268.2,9.1,-198.8,-264.4,9.8,-203.2,-260.3,10.4,-207.6,-256.2,10.6,-211.4,-252.5,10.6,-215.3,-248.9,10.3,-219.2,-245.3,9.9,-223.1,-241.6,9.2,-226.9,-238.0,8.4,-230.8,-234.3,7.5,-234.7,-230.7,6.6,-238.6,-227.0,5.7,-242.4,-223.4,4.9,-245.1,-222.2,4.5,-248.0,-221.9,4.2,-251.1,-222.5,3.8,-253.5,-223.6,3.6,-255.4,-226.1,3.4,-256.3,-228.4,3.2,-257.0,-231.5,3.1,-256.6,-234.0,3.0,-253.9,-240.1,3.0,-251.2,-244.3,3.2,-248.5,-248.6,3.5,-245.8,-252.8,3.8,-243.1,-257.0,4.2,-240.4,-261.2,4.5,-237.7,-265.5,4.9,-235.0,-269.7,5.2,-230.4,-276.9,5.6,-226.7,-283.0,5.7,-223.0,-289.0,5.7,-226.4,-284.7,5.5,-229.8,-280.5,5.3,-227.1,-285.1,5.0,-224.4,-289.8,4.7,-221.6,-294.5,4.3,-218.9,-299.2,4.0,-216.2,-303.8,3.7,-213.5,-308.5,3.4,-210.8,-313.2,3.3,-208.1,-317.8,3.1,-205.4,-322.5,3.0,-207.7,-316.3,3.0,-210.0,-310.1,3.0],
  grizzly: [-21.5,-429.2,2.0,-16.0,-430.5,3.5,-10.4,-431.8,5.0,-4.9,-433.1,6.5,3.8,-435.2,8.8,9.0,-436.5,10.2,14.2,-437.7,11.6,19.4,-439.0,13.0,24.6,-440.2,14.4,29.8,-441.5,15.8,35.0,-442.8,17.2,40.2,-444.0,18.6,45.4,-445.3,20.1,50.8,-446.6,21.5,56.1,-447.9,23.0,61.6,-449.2,24.4,67.1,-450.5,25.9,73.6,-452.4,27.7,76.3,-453.9,25.2,78.1,-456.2,22.9,79.1,-458.8,20.6,79.4,-461.5,18.4,78.6,-464.5,15.9,77.2,-467.1,13.5,74.8,-468.9,11.0,72.0,-469.8,8.6,69.2,-469.9,6.4,66.8,-469.1,4.4,64.4,-467.5,3.0,28.3,-450.7,8.7,33.8,-452.1,10.0,39.2,-453.5,11.3,45.0,-455.1,12.8,48.8,-456.6,13.7,53.9,-459.3,15.0,49.7,-456.0,16.0,45.4,-452.7,16.9,41.2,-449.4,17.7,38.2,-447.4,18.1,34.7,-445.7,18.4,30.9,-444.5,18.6,24.7,-442.9,18.8,19.8,-441.7,18.7,14.9,-440.5,18.4,10.0,-439.3,18.0,5.2,-438.1,17.4,0.3,-436.9,16.7,-4.6,-435.7,15.8,-9.4,-434.5,14.9,-14.3,-433.3,13.8,-19.2,-432.1,12.7,-24.1,-430.9,11.6,-28.9,-429.7,10.4,-33.8,-428.5,9.3,-38.7,-427.3,8.2,-43.6,-426.1,7.1,-48.4,-424.9,6.2,-53.3,-423.7,5.3,-58.3,-422.1,4.5,-63.4,-420.5,3.9,-68.8,-418.1,3.4,-74.0,-414.9,3.1,-79.5,-410.4,3.0,-83.2,-406.8,3.1,-86.9,-403.2,3.4,-90.7,-399.5,3.9,-94.4,-395.9,4.4,-98.1,-392.3,5.1,-101.9,-388.7,5.8,-105.6,-385.0,6.7,-109.3,-381.4,7.6,-113.1,-377.8,8.5,-117.0,-373.7,9.5,-120.9,-369.6,10.4,-123.3,-365.2,11.2,-124.1,-361.5,11.8,-124.2,-357.7,12.3,-123.4,-354.3,12.7,-121.5,-350.9,13.2,-118.7,-347.8,13.6,-115.0,-345.6,13.9,-110.4,-344.7,14.1,-105.7,-345.2,14.3,-101.7,-346.8,14.3,-98.5,-349.7,14.2,-95.0,-353.8,14.0,-90.9,-358.6,13.6,-86.8,-363.4,13.0,-82.8,-368.1,12.3,-79.0,-372.7,11.4,-75.1,-377.2,10.6,-71.3,-381.7,9.6,-67.4,-386.2,8.7,-63.6,-390.7,7.7,-60.0,-395.0,6.8,-56.4,-399.2,6.0,-52.8,-403.4,5.3,-49.2,-407.6,4.6,-45.1,-412.0,4.0,-41.2,-415.6,3.6,-36.8,-418.9,3.3,-29.2,-423.1,3.0,-23.8,-425.3,3.0,-18.3,-427.1,3.2,-12.4,-428.7,3.4,-3.1,-430.9,4.1,2.5,-432.2,4.6,8.0,-433.6,5.2,13.6,-434.9,5.8,19.2,-436.3,6.4,24.6,-437.5,7.0,28.6,-437.4,7.4,32.5,-436.4,7.8,35.9,-434.4,8.2,38.8,-431.0,8.6,40.9,-426.6,9.0,41.7,-422.7,9.2,41.2,-418.8,9.4,38.7,-413.8,9.7,34.7,-410.0,9.8,30.0,-408.0,9.8,26.1,-407.5,9.8,22.0,-408.1,9.7,17.8,-409.4,9.6,13.0,-410.8,9.4,8.2,-412.3,9.1,3.4,-413.7,8.7,-2.8,-415.5,8.2,-9.1,-417.4,7.6,-14.0,-418.8,7.1,-18.9,-420.3,6.6,-23.1,-421.3,6.2,-28.4,-421.9,5.7,-33.5,-422.3,5.2,-40.4,-422.3,4.7,-48.3,-421.4,4.1,-57.2,-419.4,3.5,-65.6,-416.2,3.2,-72.8,-412.7,3.0,-77.7,-409.1,3.0,-81.4,-405.4,3.0,-85.1,-401.8,3.1,-88.7,-398.1,3.2,-92.4,-394.5,3.4,-96.0,-390.8,3.6,-99.7,-387.2,3.8,-103.3,-383.6,4.0,-107.0,-379.9,4.2,-110.6,-376.3,4.5,-114.3,-372.6,4.7,-117.9,-369.0,4.9,-120.2,-365.9,5.0,-121.4,-363.1,5.1,-122.0,-360.7,5.2,-121.9,-357.8,5.2,-121.1,-354.5,5.3,-119.5,-351.8,5.4,-117.1,-349.4,5.4,-114.3,-347.8,5.4,-110.8,-347.0,5.4,-106.6,-347.4,5.4,-103.1,-348.7,5.4,-100.2,-351.2,5.4,-96.7,-355.3,5.3,-93.4,-359.3,5.2,-90.2,-363.2,5.0,-86.9,-367.1,4.9,-83.6,-371.1,4.7,-80.3,-375.0,4.5,-77.1,-378.9,4.3,-73.8,-382.9,4.2,-70.5,-386.8,4.0,-67.2,-390.7,3.8,-64.0,-394.7,3.7,-60.7,-398.6,3.5,-57.4,-402.5,3.4,-54.1,-406.5,3.3,-50.4,-410.8,3.2,-45.2,-416.0,3.1,-39.2,-420.7,3.0,-32.0,-424.8,3.0,-26.7,-427.0,3.0,-21.5,-429.2,3.0],
  flight_deck: [30.9,115.4,2.0,35.5,112.7,4.8,40.1,110.1,7.6,44.6,107.4,10.4,49.2,104.8,13.1,54.1,102.0,16.1,59.0,99.1,19.1,63.9,96.3,22.1,68.9,93.4,25.1,73.8,90.6,28.1,78.7,87.8,31.1,82.7,86.7,27.7,87.1,86.4,24.1,91.4,87.3,20.5,94.3,89.4,17.5,96.1,91.9,15.0,97.3,95.5,11.9,97.8,100.1,8.1,96.9,106.2,3.0,95.4,112.7,3.5,100.6,114.0,4.7,105.6,116.2,6.5,108.7,118.7,8.0,110.7,121.7,9.6,112.2,126.1,11.6,112.0,131.1,13.9,109.9,135.8,16.1,106.1,138.9,17.9,100.9,140.6,19.4,95.0,141.1,20.4,89.8,139.8,20.7,86.2,136.5,20.4,83.8,132.4,19.7,82.9,127.9,18.5,82.7,120.9,16.1,79.3,121.2,14.8,77.1,122.2,13.8,75.6,124.8,12.5,74.0,129.1,10.5,72.1,133.1,8.7,69.3,135.4,7.3,64.8,136.4,5.7,54.9,137.0,3.5,49.7,137.0,3.0,44.6,137.0,3.1,39.4,137.0,3.6,34.3,137.0,4.6,29.1,137.0,5.8,23.9,144.5,8.7,20.7,142.3,9.9,19.3,147.6,11.7,17.9,152.9,13.2,16.5,158.2,14.4,15.1,163.5,15.3,13.7,168.8,15.7,12.3,174.1,15.6,10.9,179.4,15.0,9.5,184.7,14.0,8.1,190.0,12.7,6.7,195.3,11.2,7.6,197.4,10.5,6.7,199.4,9.9,5.6,200.0,9.4,8.1,204.0,8.0,7.3,208.5,6.7,2.1,208.3,5.4,-3.0,208.0,4.3,-8.1,207.7,3.6,-13.2,207.4,3.1,-18.3,207.2,3.0,-23.4,206.9,3.2,-28.5,206.6,3.7,-33.6,206.3,4.5,-38.8,206.1,5.4,-43.9,205.8,6.4,-48.9,198.6,8.1,-52.6,199.3,8.8,-59.5,200.5,9.9,-63.9,201.3,10.3,-70.5,199.6,10.7,-77.1,198.0,10.5,-76.4,192.9,10.2,-75.6,187.8,9.6,-74.9,182.7,8.8,-71.1,175.7,7.4,-64.3,178.3,6.1,-57.5,180.9,4.9,-57.6,175.2,4.1,-57.7,169.5,3.5,-57.9,163.8,3.2,-57.6,158.0,3.0,-56.8,151.8,3.1,-52.7,144.9,3.5,-48.6,140.1,3.9,-44.8,134.0,4.5,-42.8,128.0,5.0,-36.7,122.4,5.5,-31.7,116.2,5.7,-24.7,111.0,5.7,-16.5,108.8,5.4,-8.6,109.7,4.9,-0.7,114.0,4.3,3.2,114.4,4.0,6.5,112.0,3.8,13.1,108.2,3.4,17.5,115.5,3.1,22.8,112.6,3.0,28.0,109.7,3.0,30.9,115.4,3.0],
  patriot: [-86.5,-61.0,2.0,-87.1,-56.0,3.8,-87.7,-50.9,5.6,-88.3,-45.9,7.4,-88.8,-40.1,9.5,-89.4,-34.3,11.5,-89.9,-28.6,13.6,-90.6,-23.3,15.5,-91.3,-17.9,17.4,-91.9,-12.6,19.3,-92.6,-7.3,21.2,-93.5,-1.3,23.4,-94.3,4.8,25.5,-95.2,10.8,27.7,-95.3,17.3,22.5,-95.3,23.7,17.3,-95.3,30.1,12.1,-88.1,34.3,5.3,-85.6,33.8,3.3,-80.7,37.5,3.6,-75.8,41.2,5.3,-69.9,44.0,8.0,-64.0,46.9,11.2,-58.1,49.7,14.3,-53.1,53.8,16.8,-48.0,57.8,18.4,-47.6,59.5,18.6,-48.1,61.4,18.8,-51.5,66.3,18.5,-54.9,71.3,17.1,-58.3,76.3,15.0,-61.5,80.7,12.6,-64.7,85.1,10.0,-66.6,86.6,8.9,-71.1,82.9,6.4,-75.7,79.2,4.5,-80.2,75.5,3.3,-84.8,71.8,3.0,-89.4,68.7,3.5,-94.1,65.6,4.7,-93.3,60.6,6.2,-93.8,55.7,7.9,-95.2,51.6,9.5,-98.8,48.5,11.1,-103.6,44.1,12.9,-108.5,39.8,14.0,-113.3,35.4,14.3,-117.7,32.7,13.8,-122.1,30.0,12.8,-126.5,27.3,11.5,-130.9,24.7,9.8,-135.3,22.0,8.1,-139.8,19.3,6.4,-144.2,16.6,5.0,-148.6,14.0,3.9,-152.9,9.6,3.1,-157.3,5.2,3.0,-162.2,3.5,3.4,-164.1,1.2,3.8,-165.4,-0.7,4.2,-166.5,-2.9,4.7,-167.4,-5.2,5.2,-167.3,-7.0,5.6,-167.0,-9.4,6.1,-166.0,-12.1,6.7,-163.5,-15.2,7.6,-160.5,-19.3,8.6,-157.1,-16.7,9.2,-156.5,-17.6,9.3,-151.6,-14.2,9.8,-147.4,-11.1,9.8,-143.2,-7.9,9.4,-144.6,-4.4,9.0,-138.1,1.5,7.5,-129.7,2.2,5.8,-126.7,3.3,5.2,-122.1,5.4,4.3,-117.5,7.5,3.7,-112.3,10.8,3.2,-112.2,5.0,3.0,-112.0,-0.8,3.1,-111.9,-6.6,3.5,-111.8,-12.4,4.0,-117.6,-15.3,4.5,-123.4,-18.2,5.0,-129.2,-21.1,5.4,-126.2,-26.8,5.4,-123.3,-32.4,5.3,-120.3,-38.1,5.0,-118.8,-37.3,4.9,-116.3,-42.1,4.5,-113.8,-46.9,4.1,-111.3,-51.6,3.7,-107.1,-55.0,3.4,-102.8,-58.4,3.2,-98.5,-61.8,3.1,-92.5,-61.4,3.0,-86.5,-61.0,3.0],
  gold_striker: [-266.0,-28.1,2.0,-268.4,-23.7,5.4,-270.8,-19.3,8.9,-273.2,-14.9,12.3,-275.5,-10.5,15.8,-277.9,-6.1,19.2,-280.3,-1.7,22.7,-282.7,2.7,26.1,-285.1,7.1,29.6,-287.4,11.5,33.0,-290.5,16.9,27.8,-293.6,22.4,22.6,-296.7,27.9,17.4,-298.7,32.1,13.6,-299.5,36.1,10.2,-299.5,40.2,6.7,-298.2,44.1,3.3,-296.0,46.6,3.0,-293.8,48.1,3.1,-291.6,49.2,3.3,-289.0,50.0,3.5,-285.6,50.4,3.9,-281.8,50.2,4.4,-278.2,49.5,5.0,-274.8,48.2,5.7,-271.4,46.2,6.5,-268.0,43.4,7.5,-265.5,40.5,8.5,-263.2,36.6,9.7,-261.6,32.4,10.9,-261.1,29.1,11.9,-261.1,24.5,13.1,-261.8,19.9,14.4,-263.5,14.2,16.0,-265.4,7.9,17.6,-267.2,1.7,19.0,-268.5,-4.6,20.1,-269.1,-10.3,20.9,-268.3,-16.3,21.5,-266.4,-21.7,21.8,-263.7,-26.5,21.8,-261.1,-31.4,21.6,-258.4,-36.2,21.1,-255.7,-41.0,20.4,-253.1,-45.8,19.6,-250.4,-50.6,18.5,-247.8,-55.5,17.3,-244.4,-61.9,15.5,-241.1,-68.4,13.7,-236.6,-76.5,11.2,-235.0,-79.5,10.3,-233.6,-82.2,9.5,-233.0,-84.8,8.9,-233.3,-87.6,8.2,-234.3,-90.4,7.5,-236.0,-93.1,6.8,-238.6,-95.1,6.1,-242.0,-96.4,5.5,-244.0,-96.6,5.1,-246.9,-96.2,4.7,-251.4,-94.3,4.0,-255.3,-92.1,3.6,-259.2,-90.1,3.2,-262.7,-88.5,3.1,-266.1,-87.6,3.0,-270.5,-87.1,3.0,-274.7,-87.4,3.2,-279.3,-88.5,3.5,-283.8,-90.6,4.0,-285.9,-92.2,4.3,-293.0,-97.2,5.5,-297.2,-100.1,6.4,-299.7,-101.8,6.9,-302.5,-104.1,7.6,-305.0,-107.0,8.4,-307.2,-110.9,9.3,-308.6,-114.8,10.1,-309.3,-119.5,11.1,-308.9,-123.7,11.9,-307.5,-127.2,12.6,-305.3,-129.8,13.2,-302.5,-131.7,13.8,-299.0,-132.6,14.3,-294.7,-132.1,14.9,-291.8,-130.5,15.3,-289.4,-128.2,15.6,-288.0,-124.8,16.0,-286.5,-117.2,16.4,-285.7,-112.5,16.5,-284.4,-108.8,16.4,-282.2,-105.8,16.3,-279.9,-103.7,16.2,-277.1,-102.1,16.0,-272.0,-100.4,15.5,-263.7,-98.3,14.5,-260.3,-97.3,14.0,-257.9,-96.3,13.6,-255.9,-94.9,13.2,-255.1,-94.4,13.0,-251.8,-90.3,12.1,-250.1,-87.0,11.4,-249.0,-83.6,10.8,-247.7,-79.5,10.0,-245.5,-72.3,8.6,-243.7,-66.9,7.5,-242.3,-62.0,6.7,-240.9,-57.2,5.9,-239.3,-53.2,5.2,-237.0,-48.7,4.6,-233.9,-45.8,4.1,-230.7,-44.1,3.8,-225.0,-42.3,3.4,-221.8,-41.1,3.2,-218.9,-39.8,3.1,-216.7,-37.6,3.0,-215.1,-34.7,3.0,-214.5,-31.7,3.0,-215.0,-28.1,3.1,-216.7,-25.0,3.2,-219.5,-22.7,3.4,-223.1,-21.3,3.7,-226.7,-21.0,4.0,-230.7,-21.7,4.4,-234.3,-23.4,4.8,-237.6,-26.2,5.2,-240.3,-30.3,5.8,-241.7,-34.7,6.4,-242.1,-38.8,6.9,-241.8,-47.8,8.0,-242.1,-52.1,8.5,-242.7,-55.1,8.9,-244.4,-60.4,9.5,-246.0,-65.8,10.0,-247.7,-71.1,10.4,-248.9,-73.6,10.6,-251.5,-76.0,10.8,-254.8,-78.3,11.0,-258.6,-79.9,11.1,-263.2,-80.6,11.1,-268.5,-80.3,11.1,-273.8,-79.9,11.0,-277.5,-78.9,10.8,-280.7,-77.2,10.6,-285.8,-73.2,10.2,-288.5,-71.4,10.0,-291.2,-70.6,9.7,-294.1,-70.5,9.5,-297.1,-71.4,9.2,-299.6,-73.3,8.8,-301.4,-76.0,8.5,-302.4,-79.3,8.1,-302.2,-82.4,7.8,-301.4,-85.2,7.4,-300.0,-87.6,7.1,-298.0,-89.5,6.8,-295.3,-90.5,6.5,-291.9,-90.9,6.1,-289.0,-90.2,5.8,-286.1,-88.8,5.5,-282.1,-85.9,5.0,-279.1,-84.2,4.7,-275.8,-83.0,4.4,-272.4,-82.8,4.1,-269.0,-83.2,3.9,-264.7,-84.8,3.6,-259.3,-87.6,3.3,-254.0,-90.3,3.1,-248.6,-93.0,3.0,-245.5,-94.2,3.0,-242.5,-94.2,3.0,-239.6,-93.2,3.0,-237.9,-92.0,3.1,-235.8,-89.2,3.1,-235.0,-86.4,3.2,-235.1,-83.7,3.3,-236.1,-81.2,3.4,-237.4,-79.1,3.4,-239.7,-77.6,3.6,-244.5,-75.7,3.8,-249.8,-73.7,4.1,-255.2,-71.7,4.3,-260.5,-69.7,4.6,-265.8,-67.7,4.9,-267.9,-66.6,5.0,-269.1,-65.2,5.1,-270.0,-63.8,5.2,-270.7,-62.0,5.3,-271.3,-59.0,5.4,-272.0,-53.8,5.6,-272.6,-48.6,5.7,-273.3,-43.5,5.8,-273.9,-38.5,5.9,-274.5,-33.5,5.9,-275.1,-28.4,5.9,-275.1,-26.0,5.9,-274.4,-24.3,5.9,-273.2,-22.9,5.8,-266.3,-19.2,5.7,-264.5,-19.0,5.7,-262.8,-19.5,5.6,-261.2,-20.4,5.5,-260.1,-21.8,5.5,-258.2,-25.4,5.4,-255.3,-30.8,5.1,-252.3,-36.2,4.9,-249.4,-41.6,4.6,-246.4,-46.8,4.4,-245.6,-48.7,4.3,-245.3,-50.7,4.2,-245.3,-52.4,4.1,-245.7,-54.4,4.1,-247.8,-61.4,3.8,-249.1,-65.3,3.7,-250.4,-66.8,3.6,-252.5,-67.7,3.5,-254.5,-67.9,3.5,-256.6,-67.3,3.4,-258.1,-66.3,3.4,-259.1,-64.8,3.3,-259.4,-63.1,3.3,-259.1,-61.1,3.3,-258.2,-59.5,3.2,-254.8,-56.1,3.2,-254.0,-54.8,3.1,-253.5,-53.2,3.1,-253.6,-51.4,3.1,-254.0,-49.9,3.1,-257.5,-43.9,3.0,-260.4,-38.6,3.0,-263.2,-33.4,3.0,-266.0,-28.1,3.0],
  railblazer: [-137.5,-234.2,2.0,-139.4,-228.6,5.0,-141.2,-223.1,8.1,-142.9,-218.0,10.8,-144.6,-213.0,13.6,-147.4,-204.7,18.1,-149.2,-199.7,20.9,-151.0,-194.6,23.6,-153.0,-189.0,26.7,-155.0,-183.4,29.8,-156.5,-178.9,32.3,-157.2,-177.6,31.1,-158.6,-176.6,29.6,-160.5,-176.2,28.0,-162.4,-176.9,26.4,-163.9,-178.2,24.8,-164.7,-179.6,23.4,-164.9,-181.4,21.9,-164.5,-183.1,20.5,-164.2,-183.6,20.0,-163.5,-185.3,18.4,-162.2,-188.1,16.0,-159.3,-194.3,10.3,-158.5,-195.8,8.9,-156.1,-200.8,4.3,-153.9,-205.8,3.3,-151.7,-210.8,4.9,-148.1,-219.0,9.5,-145.4,-225.1,13.6,-142.7,-231.1,17.4,-141.7,-233.1,18.5,-140.7,-234.5,19.3,-138.9,-236.3,20.2,-138.8,-236.7,20.3,-139.1,-236.6,20.4,-141.2,-234.5,21.1,-144.4,-231.1,21.4,-148.8,-226.5,20.5,-151.1,-224.1,19.4,-152.5,-222.3,18.5,-153.4,-221.2,17.8,-154.1,-219.9,17.1,-154.6,-218.4,16.2,-155.1,-216.4,15.1,-155.1,-214.0,13.7,-154.8,-212.0,12.5,-154.0,-208.4,10.3,-152.9,-205.7,8.7,-151.6,-203.3,7.2,-149.9,-200.7,5.8,-147.3,-197.8,4.4,-146.8,-197.0,4.1,-146.2,-196.2,3.9,-145.6,-194.6,3.5,-145.4,-193.1,3.2,-145.6,-191.3,3.1,-146.1,-189.7,3.0,-147.0,-188.2,3.0,-148.1,-186.8,3.2,-150.1,-184.9,3.6,-152.1,-183.9,4.1,-154.0,-183.2,4.7,-156.6,-182.6,5.6,-159.9,-182.3,6.9,-164.0,-181.6,8.8,-166.9,-180.7,10.1,-168.8,-179.5,11.1,-170.1,-177.8,12.0,-170.7,-176.4,12.7,-170.9,-174.8,13.3,-170.5,-173.4,13.8,-169.6,-172.1,14.3,-168.1,-171.2,14.8,-166.9,-170.9,15.2,-165.1,-170.9,15.5,-163.7,-171.6,15.8,-162.4,-172.7,16.0,-161.5,-174.2,16.1,-161.2,-175.6,16.2,-161.2,-177.4,16.1,-162.0,-179.4,16.0,-163.4,-181.1,15.7,-166.3,-184.5,14.7,-167.1,-185.8,14.2,-167.6,-187.3,13.7,-167.6,-188.8,13.2,-167.2,-190.4,12.6,-166.4,-191.8,12.0,-165.3,-192.7,11.4,-163.7,-193.6,10.6,-156.4,-197.3,7.2,-150.6,-200.3,4.9,-142.4,-204.3,3.2,-139.4,-206.0,3.0,-137.4,-207.7,3.1,-135.8,-209.8,3.3,-135.1,-211.6,3.5,-134.7,-213.3,3.8,-134.6,-215.2,4.1,-135.2,-217.0,4.6,-138.3,-222.0,6.1,-141.4,-226.9,7.7,-142.7,-228.5,8.3,-143.9,-229.4,8.7,-146.0,-230.0,9.2,-148.1,-230.1,9.6,-150.4,-229.5,10.1,-153.1,-228.2,10.5,-156.1,-225.7,10.9,-158.0,-223.4,11.0,-158.9,-221.5,10.9,-159.3,-219.7,10.8,-159.4,-217.7,10.6,-159.1,-215.5,10.4,-156.0,-207.8,8.8,-153.3,-200.9,7.0,-152.6,-198.5,6.4,-152.4,-196.4,5.9,-152.5,-194.3,5.4,-153.4,-191.0,4.6,-154.8,-188.0,4.1,-156.8,-185.9,3.6,-159.6,-184.3,3.3,-162.2,-184.1,3.1,-164.3,-184.6,3.0,-166.3,-185.8,3.0,-168.3,-188.7,3.1,-168.8,-190.7,3.2,-168.5,-193.0,3.3,-167.8,-194.8,3.5,-166.4,-196.8,3.7,-164.2,-198.3,4.0,-161.1,-200.1,4.4,-156.7,-202.8,5.0,-152.4,-205.5,5.4,-148.0,-208.2,5.7,-143.7,-210.9,5.9,-138.0,-214.4,5.7,-132.4,-217.9,5.3,-131.7,-218.6,5.2,-131.1,-219.7,5.1,-129.2,-225.3,4.5,-127.2,-231.0,4.0,-125.3,-236.6,3.5,-125.0,-238.3,3.4,-125.2,-239.8,3.4,-126.0,-241.2,3.3,-127.4,-242.3,3.2,-129.3,-242.9,3.1,-131.5,-242.9,3.1,-133.6,-242.0,3.0,-134.8,-240.9,3.0,-135.7,-239.4,3.0,-137.5,-234.2,3.0],
};


function coaster(b: MeshBuilder, key: string, track: string, support: string, wooden: boolean) {
  const t = GA_TRACKS[key];
  const P: V3[] = [];
  for (let i = 0; i < t.length; i += 3) P.push([t[i], t[i + 1], t[i + 2]]);
  b.color(track);
  for (let i = 0; i < P.length - 1; i++) {
    const [a, c] = [P[i], P[i + 1]];
    const dx = c[0] - a[0];
    const dy = c[1] - a[1];
    const L = Math.hypot(dx, dy) || 1;
    const nx = (-dy / L) * 0.7;
    const ny = (dx / L) * 0.7;
    b.quad([a[0] - nx, a[1] - ny, a[2]], [a[0] + nx, a[1] + ny, a[2]], [c[0] + nx, c[1] + ny, c[2]], [c[0] - nx, c[1] - ny, c[2]]);
    b.quad([a[0], a[1], a[2] - 0.6], [a[0], a[1], a[2]], [c[0], c[1], c[2]], [c[0], c[1], c[2] - 0.6]);
  }
  b.color(support);
  const every = wooden ? 2 : 4;
  for (let i = 0; i < P.length - 1; i += every) {
    const [x, y, z] = P[i];
    if (z < 1.5) continue;
    if (!wooden) {
      b.beam([x, y, 0], [x, y, z - 0.5], 0.7);
      continue;
    }
    const c = P[i + 1];
    const dx = c[0] - x;
    const dy = c[1] - y;
    const L = Math.hypot(dx, dy) || 1;
    const w = 1.2 + z * 0.08; // bents widen toward the ground
    const nx = -dy / L;
    const ny = dx / L;
    b.beam([x - nx * w, y - ny * w, 0], [x - nx * 0.7, y - ny * 0.7, z - 0.5], 0.35);
    b.beam([x + nx * w, y + ny * w, 0], [x + nx * 0.7, y + ny * 0.7, z - 0.5], 0.35);
    b.beam([x - nx * w, y - ny * w, 0], [x + nx * 0.7, y + ny * 0.7, z - 0.5], 0.2);
  }
}

const GA_SRC = WIKI + 'California%27s_Great_America';
const GA_MODEL =
  'track centreline from OpenStreetMap (© OSM contributors, ODbL); only the documented maximum height is real: lift and first drop to it, the rest of the circuit a schematic of decaying hills (PROCEDURAL; loops, inversions and banking not modelled); supports simplified; track colours not checked';
const PARK =
  "the park opened Mar 20, 1976 as Marriott's Great America on a former pear orchard (Santa Clara 1985, Kings 1989, Paramount 1993, Cedar Fair 2006, Six Flags 2024); on Nov 6, 2026 Six Flags announced it will close on Sep 6, 2027";

function gaCoaster(id: string, name: string, built: [number, number], key: string, track: string, support: string, wooden: boolean, facts: Record<string, string>, src: string[]) {
  return landmark(id, name, 'park', built, 9999, GA, b => coaster(b, key, track, support, wooden), {...facts, Model: GA_MODEL}, [GA_SRC, ...src]);
}

const gaDemon = gaCoaster('great_america_demon', 'Demon (Great America)', [1975.6, 1976.38], 'demon', '#B23A33', '#C9CBCB', false, {
  Opened: 'May 20, 1976 as Turn of the Century (Arrow Dynamics); after 1979 its two airtime hills were replaced by two vertical loops and it reopened in 1980 as Demon',
  Size: '102 ft (31 m) high, 2,130 ft (650 m) long'
}, [WIKI + 'Demon_(Six_Flags_Great_America)']);
const gaGrizzly = gaCoaster('great_america_grizzly', 'The Grizzly (Great America)', [1985.6, 1986.38], 'grizzly', '#8E6B4C', '#A88660', true, {
  Opened: '1986; wooden out-and-back coaster (Curtis D. Summers)',
  Size: '91 ft (27.7 m) high (RCDB); ≈ 3,250 ft of track (OSM centreline 971 m)'
}, [WIKI + 'The_Grizzly', 'https://rcdb.com/77.htm']);
const gaFlightDeck = gaCoaster('great_america_flight_deck', 'Flight Deck (Top Gun), Great America', [1992.6, 1993.21], 'flight_deck', '#3F5E8C', '#C9CBCB', false, {
  Opened: 'Mar 20, 1993 as Top Gun (Bolliger & Mabillard inverted coaster); renamed Flight Deck in 2007',
  Size: '102 ft (31 m) high, 2,260 ft (690 m) long'
}, [WIKI + 'Flight_Deck_(California%27s_Great_America)']);
const gaPatriot = gaCoaster('great_america_vortex_patriot', 'Vortex / Patriot (Great America)', [1990.6, 1991.38], 'patriot', '#2F4F8F', '#D9DADB', false, {
  Opened: '1991 as Vortex (Bolliger & Mabillard stand-up); converted to the floorless Patriot for 2017',
  Size: '91 ft (28 m) drop, 1,920 ft (590 m) of track'
}, []);
const gaGoldStriker = gaCoaster('great_america_gold_striker', 'Gold Striker (Great America)', [2012.6, 2013.4], 'gold_striker', '#9B7A52', '#B9946A', true, {
  Opened: '2013; wooden coaster by Great Coasters International beside the park entrance',
  Size: '108.2 ft (33 m) high — the tallest and fastest wooden coaster in Northern California (53.7 mph)'
}, [WIKI + 'Gold_Striker', 'https://www.sixflags.com/cagreatamerica/attractions/gold-striker']);
const gaRailBlazer = gaCoaster('great_america_railblazer', 'RailBlazer (Great America)', [2017.6, 2018.45], 'railblazer', '#2E6FA8', '#E0B13A', false, {
  Opened: '2018; Rocky Mountain Construction single-rail coaster on the site of Invertigo (Vekoma, 1998–2011)',
  Size: '106 ft (32 m) high, 1,800 ft (549 m) of track'
}, ['https://www.undercovertourist.com/san-francisco/californias-great-america/railblazer/']);

// towers and the carousel (OSM positions)
const gaDropTower = landmark(
  'great_america_drop_tower',
  'Drop Tower (Great America)',
  'tower',
  [1995.8, 1996.4],
  9999,
  GA,
  b => {
    const [x, y] = [28, -382];
    b.color('#C9CBCB').box(x, y, 0, 4.5, 4.5, 64);
    b.color('#B23A33').box(x, y, 64, 6, 6, 5.2);
    b.color('#2F3236').prism(rect(x, y, 8, 8), 6, 8.5);
  },
  {Opened: '1996 as Drop Zone: Stunt Tower (Intamin); Drop Tower since 2008', Height: '227 ft (69 m)', Model: 'position from OpenStreetMap (© OSM contributors, ODbL); column and gondola ring proportions estimated'},
  [GA_SRC]
);
const gaStarTower = landmark(
  'great_america_star_tower',
  'Star Tower (Great America)',
  'tower',
  [1978.8, 1979.4],
  9999,
  GA,
  b => {
    const [x, y] = [-285, 32];
    b.color('#D9DADB').cylinder(x, y, 1.6, 0, 61, 10);
    b.color('#B23A33').cylinder(x, y, 2.2, 56, 61, 10);
    b.color('#8FA7AE').cylinder(x, y, 5.5, 2, 5, 16);
  },
  {Opened: '1979; Intamin gyro tower with a rotating observation cabin', Height: '200 ft (61 m)', Model: 'position from OpenStreetMap (© OSM contributors, ODbL); column diameter and cabin estimated'},
  [GA_SRC]
);
const gaCarousel = landmark(
  'great_america_carousel_columbia',
  'Carousel Columbia (Great America)',
  'park',
  [1975.6, 1976.22],
  9999,
  GA,
  b => {
    const [x, y] = [-213.8, 36.9];
    b.color('#E9E3D3').cylinder(x, y, 11, 0, 4.5, 24, {top: false});
    b.color('#C8443A').frustum(x, y, 11.6, 10.5, 4.5, 6.5, 24);
    b.color('#E9E3D3').cylinder(x, y, 9.8, 6.5, 10.5, 24, {top: false});
    b.color('#C8443A').frustum(x, y, 10.4, 6, 10.5, 15.5, 24, false);
    b.color('#E5C35A').dome(x, y, 6, 15.5, 6, 16, 3);
    b.color('#E9E3D3').cylinder(x, y, 1.2, 21.5, 27, 8);
    b.color('#E5C35A').dome(x, y, 1.6, 27, 2, 8, 2);
    b.beam([x, y, 29], [x, y, 31], 0.3);
  },
  {
    Opened: '1976 with the park (Chance Rides): Carousel Columbia, a double-decker carousel 101 ft (31 m) high in the entrance plaza (Carousel Plaza by 1988, Celebration Plaza from 2000) beside the reflecting pool',
    Park: PARK,
    Model: 'building outline from OpenStreetMap (© OSM contributors, ODbL; r ≈ 11 m); deck and crown proportions estimated; the plaza\'s other buildings are left to the generic footprints'
  },
  [GA_SRC],
  [circle(-213.8, 36.9, 12, 12)]
);

// =================================================================== PACIFICA

// ---- Taco Bell Cantina, Linda Mar (Pacifica State Beach): the 1972 A&W, a Taco Bell since 1985 (frame 27.8°, −u = the surf)
const PACIFICA_TB: V2 = [-122.503752, 37.597196];
const PACIFICA_TB_OUTLINE: V2[] = [
  [-8.6, -10.7], [-8.6, -4.4], [-6.7, 10.0], [-4.0, 10.0], [-4.0, 14.0], [7.0, 14.2], [7.1, 12.4], [7.1, -11.8], [5.5, -11.9], [5.6, -15.1], [0.7, -15.2], [0.7, -12.0], [-4.2, -11.9], [-4.2, -10.7]
];
const pacificaTacoBell = landmark(
  'pacifica_taco_bell',
  'Taco Bell Cantina, Linda Mar (Pacifica)',
  'building',
  [1971.6, 1972.3],
  9999,
  PACIFICA_TB,
  b => {
    b.frame(0, 0, 0, 27.8, () => {
      const WOOD = '#5B3F2E'; // dark brown wood siding (KQED, 2026)
      // the restaurant on the landward part of the lot, dark wood-clad, with a low roof (light membrane on the orthophoto)
      b.color(WOOD);
      b.prism([[-4, -14.5], [6.8, -14.5], [6.8, 13.8], [-4, 13.8]], 0, 4.2, {top: false});
      b.color('#CFCBC2').cap([[-4.4, -14.9], [7.2, -14.9], [7.2, 14.2], [-4.4, 14.2]], 4.4);
      b.color('#4A3426').walls([[-4.4, -14.9], [7.2, -14.9], [7.2, 14.2], [-4.4, 14.2]], 3.9, 4.6);
      // walk-up window toward the beach, purple Taco Bell sign
      b.color('#2C2A30').box(-4.05, -2, 1.0, 0.1, 3.2, 1.3);
      b.color('#5B2C83').box(-4.1, 6, 3.0, 0.15, 4.5, 0.9);
      // deck facing the surf (the A&W-era patio on stilts), railing and fire pits
      b.color('#8A6A4E').prism([[-8.6, -10.7], [-4, -10.7], [-4, 10], [-6.7, 10], [-8.6, -4.4]], 0, 1.0);
      b.color('#4A3426').wallProfile([[-4, -10.7], [-8.6, -10.7], [-8.6, -4.4], [-6.7, 10], [-4, 10]], 1.0, 2.0);
      b.color('#3A3633');
      for (const v of [-6, 3]) b.cylinder(-6.4, v, 0.7, 1.0, 1.5, 8);
    });
  },
  {
    Opened: 'spring 1972 (grand opening late Apr 1972) as an A&W franchise on Bud Wiechers\' beachfront lot — approved just before Proposition 20 (1972) created the Coastal Commission; a restaurant like it could not be built there today',
    'Taco Bell': 'A&W closed in 1985 and the building became a Taco Bell that year (Pacifica Tribune, Jul 31, 1985)',
    Cantina: 'renovated for about two months and reopened Jul 13, 2019 as a Taco Bell Cantina serving alcohol; the walk-up take-out window and surfboard rack kept; new fireplace and lounge seating inside',
    Exterior: 'dark brown wood siding in the A&W years and today, deck over the beach — the 2019 remodel was mainly inside, so one model covers 1972 to today',
    Model:
      'outline from OpenStreetMap (© OSM contributors, ODbL; building and deck); split between restaurant and deck, wall and roof heights, window, sign and fire-pit positions estimated from the (blurred) orthophoto and descriptions — no photograph was examined'
  },
  ['https://www.kqed.org/news/12080794/its-the-most-beautiful-taco-bell-in-the-world-heres-why-it-could-never-be-built-today', 'https://abc7news.com/post/restaurant-some-call-taco-bell-heaven-re-opens-at-pacifica-beach/5392123/', 'https://www.atlasobscura.com/places/linda-mar-taco-bell'],
  [rotPoly(PACIFICA_TB_OUTLINE, 27.8)]
);

// =================================================================== SAN FRANCISCO CIVIC CENTER

// ---- San Francisco Main Library (1996): Pei Cobb Freed & Partners with Simon Martin-Vegue Winkelstein Moris.
// OSM outline 106.2 × 56.9 m on the civic-centre grid (frame −9°: +u east from Larkin to Hyde, +v north to Fulton).
const SF_MAIN_LIBRARY: V2 = [-122.415771, 37.779128];
const sfMainLibrary = landmark(
  'sf_main_library',
  'San Francisco Main Library',
  'building',
  [1992.8, 1996.29],
  9999,
  SF_MAIN_LIBRARY,
  b => {
    b.frame(0, 0, 0, -9, () => {
      const GRANITE = '#D8D2C4';
      const MODERN = '#C9CCCB';
      // granite Beaux-Arts fronts on Fulton St (north, facing the 1917 library) and Larkin St (west), cornice line of the old library
      b.color(GRANITE);
      boxR(b, [-53.2, 53.2, -28.4, 28.4], 0, 30, false);
      b.color('#B8B0A0');
      boxR(b, [-53.6, 53.6, -28.8, 28.8], 27.5, 30.5, false);
      b.color('#6F7478');
      for (const u of [-44, -33, -22, -11, 0, 11, 22, 33, 44]) b.box(u, 28.45, 4, 6.5, 0.15, 18);
      for (const v of [-18, -6, 6, 18]) b.box(-53.25, v, 4, 0.15, 7, 18);
      // modern Hyde / Grove sides: a set-back upper block to the OSM height (46 m) and glazed planes
      b.color(MODERN);
      boxR(b, [-12, 53.2, -28.4, 14], 30, 46);
      b.color('#8FA7B2');
      boxR(b, [53.25, 53.35, -26, 26], 3, 44, false);
      boxR(b, [-50, 50, -28.5, -28.45], 3, 28, false);
      b.color('#BEB8AA').cap(rect(0, 0, 106.4, 56.8), 30);
      // five-storey skylit atrium (OSM part, 22 m) with its glazed roof
      b.color('#A9C0C9').pyramid([[-31.3, 4.7], [-19.2, -13.5], [-6.9, -5.4], [-19.0, 12.7]], 30, [-19.1, -0.4, 34]);
    });
  },
  {
    Opened: 'completed 1995, opened Apr 18, 1996 (construction start estimated), replacing the 1917 Main Library across Fulton St (now the Asian Art Museum); built on Marshall Square, part of the block of the old City Hall (1872–1906)',
    Architects: 'Pei Cobb Freed & Partners (James Ingo Freed) with Simon Martin-Vegue Winkelstein Moris (Cathy Simon)',
    Design: 'Beaux-Arts granite fronts toward the Civic Center (Fulton and Larkin Sts) and modern planar sides toward Hyde and Grove Sts; a central five-storey skylit atrium; seven storeys',
    Model:
      'outline, overall height (46 m) and the atrium square from OpenStreetMap (© OSM contributors, ODbL); cornice height, the set-back modern upper block and window bays estimated from photographs'
  },
  [WIKI + 'San_Francisco_Public_Library'],
  [rotPoly(rect(0, 0, 108, 59), -9)]
);

export const SOUTHBAY: Landmark[] = [
  appleRing,
  steveJobsTheater,
  appleVisitorCenter,
  innerQuad,
  outerQuad,
  memorialArch,
  memChu1903,
  memChu1913,
  hooverTower,
  greenLibrary,
  stanfordStadium1921,
  stanfordStadium1925,
  stanfordStadium1927,
  stanfordStadium2006,
  levisStadium,
  sapCenter,
  paypalPark,
  missionSC1825,
  missionSC1861,
  missionSC1928,
  winchester,
  winchesterTower,
  hangarOne1933,
  hangarOne2025,
  lickObservatory,
  shaneDome,
  sjLightTower,
  hotelDeAnza,
  sjCityHall,
  techInteractive,
  marinAdmin,
  marinHallOfJustice,
  missionSanRafael,
  pointBonita,
  pointReyes,
  filoli,
  pigeonPoint,
  stanfordDish,
  slacGallery,
  nfac40x80,
  nfac80x120,
  shorelineAmphitheatre,
  googleplexSGI,
  googleBayView,
  googleCharlestonEast,
  valleyFair1986,
  valleyFair2020,
  santanaRow,
  stanfordSCMacys,
  stanfordSCNeiman,
  stanfordSCBloomingdales,
  mountCarmel,
  millValleyLibrary,
  gaCarousel,
  gaDemon,
  gaStarTower,
  gaGrizzly,
  gaPatriot,
  gaFlightDeck,
  gaDropTower,
  gaGoldStriker,
  gaRailBlazer,
  pacificaTacoBell,
  sfMainLibrary
];
