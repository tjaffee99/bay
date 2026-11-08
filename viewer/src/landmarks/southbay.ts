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
import {MeshBuilder, circle, ellipse, lngLatToLocal, localToLngLat, rect, roundedRect, type V2, type V3} from './kit';
import type {Landmark} from './types';

const WIKI = 'https://en.wikipedia.org/wiki/';
const OSM = 'https://www.openstreetmap.org/';
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

/** Ring offset of a convex-ish polygon by scaling about its centroid. */
function grow(ring: V2[], d: number): V2[] {
  const cx = ring.reduce((s, p) => s + p[0], 0) / ring.length;
  const cy = ring.reduce((s, p) => s + p[1], 0) / ring.length;
  return ring.map(([x, y]) => {
    const L = Math.hypot(x - cx, y - cy) || 1;
    return [x + ((x - cx) / L) * d, y + ((y - cy) / L) * d] as V2;
  });
}

/** Local metres (in the frame of `anchor`) of another lon/lat point. */
function at(anchor: V2, p: V2): V2 {
  return lngLatToLocal(anchor, p);
}

/** Polygon in a rotated frame → anchor-local metres (for `replaces`). */
function rotPoly(ring: V2[], bearing: number, dx = 0, dy = 0): V2[] {
  const a = (bearing * Math.PI) / 180;
  const ex: V2 = [Math.cos(a), -Math.sin(a)];
  const ey: V2 = [Math.sin(a), Math.cos(a)];
  return ring.map(([u, v]) => [dx + u * ex[0] + v * ey[0], dy + u * ex[1] + v * ey[1]] as V2);
}

/** Lattice girder between two points: two chords with zig-zag diagonals (frames, towers, trusses). */
function lattice(b: MeshBuilder, a: V3, c: V3, off: V3, n: number, w: number) {
  const P = (t: number, s: number): V3 => [a[0] + (c[0] - a[0]) * t + off[0] * s, a[1] + (c[1] - a[1]) * t + off[1] * s, a[2] + (c[2] - a[2]) * t + off[2] * s];
  b.beam(P(0, 0), P(1, 0), w).beam(P(0, 1), P(1, 1), w);
  for (let i = 0; i < n; i++) b.beam(P(i / n, i % 2), P((i + 1) / n, (i + 1) % 2), w * 0.6);
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
    Built: 'groundbreaking Nov 2013 (demolition of the former HP Cupertino campus from Oct 2013); employees moved in from Apr 2017',
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

export const SOUTHBAY: Landmark[] = [appleRing, steveJobsTheater, appleVisitorCenter];
