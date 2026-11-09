/**
 * Second batch of reconstructions (data/research/landmarks.md "Priority 2" and
 * "Golden Gate Park"): Bay Bridge (three spans), Ferry Building, City Halls,
 * Coit Tower, Palace of Fine Arts, Sutro Tower, Alcatraz, Fort Point, Mission
 * Dolores, Cliff House / Sutro Baths, Embarcadero Freeway, Golden Gate Park
 * buildings. Dimensions are documented unless a fact says "estimated".
 */
import {MeshBuilder, circle, lngLatToLocal, parabola, rect, rotRect, roundedRect, type V2, type V3} from './kit';
import type {Landmark} from './types';

const WIKI = 'https://en.wikipedia.org/wiki/';

/** Helper: model a point-to-point structure in a frame whose +y runs from a to b. */
function along(anchor: V2, a: V2, b: V2) {
  const pa = lngLatToLocal(anchor, a);
  const pb = lngLatToLocal(anchor, b);
  const dx = pb[0] - pa[0];
  const dy = pb[1] - pa[1];
  return {origin: pa, bearing: (Math.atan2(dx, dy) * 180) / Math.PI, length: Math.hypot(dx, dy)};
}

/** Truss deck segment as a box beam from p to q (top of deck at z). */
function deck(b: MeshBuilder, p: V3, q: V3, width: number, depth: number, color: string, road = '#5A5753') {
  b.color(color).beam([p[0], p[1], p[2] - depth / 2], [q[0], q[1], q[2] - depth / 2], width, depth);
  b.color(road).beam([p[0], p[1], p[2] + 0.05], [q[0], q[1], q[2] + 0.05], width * 0.92, 0.1);
}

// =========================================================== Bay Bridge
const BB_ANCHOR: V2 = [-122.377877, 37.798119]; // centre anchorage W4
const BB_W = {
  sfAnch: [-122.3905, 37.7867] as V2,
  w1: [-122.388471, 37.78831] as V2,
  w2: [-122.385856, 37.790764] as V2,
  w3: [-122.380677, 37.7956] as V2,
  w4: [-122.377877, 37.798119] as V2,
  w5: [-122.375112, 37.8008] as V2,
  w6: [-122.369929, 37.805635] as V2,
  w7: [-122.367179, 37.808179] as V2
};
const STEEL_GREY = '#A9AEB2';
const BB_DECK = 58; // upper deck (estimate; towers 160 m)

function bbTower(b: MeshBuilder, p: V2, bearing: number) {
  b.frame(p[0], p[1], 0, bearing, () => {
    b.color('#BDB8AE').box(0, 0, 0, 34, 16, 10);
    b.color(STEEL_GREY);
    for (const x of [-12, 12]) {
      b.box(x, 0, 10, 6, 9, 70);
      b.box(x, 0, 80, 5, 7.5, 80);
    }
    // X-braced (not portal-strutted) between the legs
    for (const [z0, z1] of [
      [12, 46],
      [64, 100],
      [104, 140]
    ])
      b.beam([-12, 0, z0], [12, 0, z1], 1.6).beam([12, 0, z0], [-12, 0, z1], 1.6);
    b.box(0, 0, 155, 30, 7, 5);
  });
}

function bayBridgeWest(b: MeshBuilder) {
  const L = (p: V2) => lngLatToLocal(BB_ANCHOR, p);
  const pts = [BB_W.sfAnch, BB_W.w1, BB_W.w2, BB_W.w3, BB_W.w4, BB_W.w5, BB_W.w6, BB_W.w7].map(L);
  const a = along(BB_ANCHOR, BB_W.w2, BB_W.w6);
  for (const t of [pts[2], pts[3], pts[5], pts[6]]) bbTower(b, t, a.bearing);
  // centre anchorage ("Moran's Island")
  b.frame(pts[4][0], pts[4][1], 0, a.bearing, () => {
    b.color('#BDB8AE').box(0, 0, 0, 40, 69, 52);
    b.color(STEEL_GREY).box(0, 0, 52, 26, 30, 15);
  });
  // double-deck truss along the whole crossing (two levels ~ 10 m apart)
  for (let i = 0; i < pts.length - 1; i++) {
    const p = pts[i];
    const q = pts[i + 1];
    const z0 = i === 0 ? 40 : BB_DECK;
    deck(b, [p[0], p[1], z0], [q[0], q[1], BB_DECK], 20, 10, STEEL_GREY);
  }
  // cables: anchorage -> towers -> centre anchorage -> towers -> YBI
  b.color(STEEL_GREY);
  const top = 157;
  const off = (p: V2, s: number): V2 => {
    const r = ((a.bearing + 90) * Math.PI) / 180;
    return [p[0] + Math.sin(r) * s, p[1] + Math.cos(r) * s];
  };
  for (const s of [-10, 10]) {
    const c = (p: V2, z: number): V3 => {
      const o = off(p, s);
      return [o[0], o[1], z];
    };
    const spans: [V3, V3, number][] = [
      [c(pts[0], BB_DECK - 5), c(pts[2], top), BB_DECK + 25],
      [c(pts[2], top), c(pts[3], top), BB_DECK + 6],
      [c(pts[3], top), c(pts[4], 66), BB_DECK + 22],
      [c(pts[4], 66), c(pts[5], top), BB_DECK + 22],
      [c(pts[5], top), c(pts[6], top), BB_DECK + 6],
      [c(pts[6], top), c(pts[7], BB_DECK - 5), BB_DECK + 25]
    ];
    for (const [p, q, mid] of spans) {
      const curve = parabola(p, q, Math.min(mid, (p[2] + q[2]) / 2 - 2), 18);
      b.polyline(curve, 1.4);
      for (let i = 1; i < curve.length - 1; i += 1) {
        if (curve[i][2] - BB_DECK > 2) b.beam([curve[i][0], curve[i][1], BB_DECK], curve[i], 0.4);
      }
    }
  }
}

const bayBridgeWestSpan: Landmark = {
  id: 'bay_bridge_west_span',
  name: 'San Francisco–Oakland Bay Bridge (west span)',
  kind: 'bridge',
  built: [1933.52, 1936.87],
  end: 9999,
  anchor: BB_ANCHOR,
  build: bayBridgeWest,
  // generic footprints of the towers / centre anchorage (OSM building parts, split by the
  // 2023 LiDAR into 80-85 m prisms) stand inside the model: hide them
  replaces: [BB_W.w2, BB_W.w3, BB_W.w4, BB_W.w5, BB_W.w6].map(p => {
    const l = lngLatToLocal(BB_ANCHOR, p);
    return rect(l[0], l[1], 90, 90);
  }),
  facts: {
    Construction: 'Jul 9, 1933 – Nov 12, 1936',
    Form: 'two suspension bridges in series sharing a centre anchorage',
    'Main spans': '2 × 704 m (2,310 ft)',
    Towers: '160 m above water',
    Model: 'tower and anchorage positions from OSM; deck height estimated'
  },
  sources: [WIKI + 'San_Francisco%E2%80%93Oakland_Bay_Bridge']
};

// --- original east span (1936–2013), dismantled in stages Nov 2013 – Mar 2017 (steel) and to Nov 2017 (piers):
// cantilever gone by Jun 12, 2015 (Wikipedia); the five 504 ft trusses lowered Feb 4 – Aug 2016; the last of
// the fourteen 288 ft causeway trusses removed Mar 13, 2017 (ABC7 / KTVU)
const YBI_EAST: V2 = [-122.3607, 37.8152];
const OAK_MOLE: V2 = [-122.3277, 37.8238];
function eastOldPart(part: 'cantilever' | 'trusses' | 'causeway') {
  return (b: MeshBuilder) => {
    const a = along(YBI_EAST, YBI_EAST, OAK_MOLE);
    b.frame(0, 0, 0, a.bearing, () => {
      const grey = '#9A9FA3';
      const W = 20;
      if (part === 'cantilever') {
        // double balanced cantilever: main span 427 m between the main piers
        const y0 = 120;
        const y1 = y0 + 427;
        for (const yp of [y0, y1]) {
          b.color('#BDB8AE').box(0, yp, 0, 30, 20, 12);
        }
        deck(b, [0, 0, 50], [0, y1 + 150, 50], W, 9, grey);
        // deep truss over the piers, shallow at mid-span
        const prof: [number, number][] = [
          [0, 60],
          [y0, 92],
          [y0 + 110, 64],
          [(y0 + y1) / 2, 60],
          [y1 - 110, 64],
          [y1, 92],
          [y1 + 150, 60]
        ];
        for (const x of [-W / 2, W / 2]) {
          for (let i = 0; i < prof.length - 1; i++) b.beam([x, prof[i][0], prof[i][1]], [x, prof[i + 1][0], prof[i + 1][1]], 1.6);
          for (let y = 0; y <= y1 + 150; y += 25) {
            let zt = 60;
            for (let i = 0; i < prof.length - 1; i++) {
              if (y >= prof[i][0] && y <= prof[i + 1][0]) {
                const t = (y - prof[i][0]) / (prof[i + 1][0] - prof[i][0]);
                zt = prof[i][1] + (prof[i + 1][1] - prof[i][1]) * t;
              }
            }
            b.beam([x, y, 41], [x, y, zt], 0.8);
            b.beam([x, y, 41], [x, y + 25, zt], 0.6);
          }
        }
        for (const yp of [y0, y1]) for (const x of [-W / 2, W / 2]) b.beam([x, yp, 12], [x, yp, 41], 3);
      } else if (part === 'trusses') {
        // five 509 ft (155 m) through-truss spans
        const ys = 697;
        deck(b, [0, ys, 44], [0, ys + 5 * 155, 34], W, 9, grey);
        for (let k = 0; k <= 5; k++) {
          const y = ys + k * 155;
          const z = 44 - (10 * k) / 5;
          b.color('#BDB8AE').box(0, y, 0, 26, 12, z - 9);
          if (k < 5) {
            b.color(grey);
            for (const x of [-W / 2, W / 2]) {
              b.beam([x, y + 6, z + 18], [x, y + 149, z - 2 + 18], 1.4);
              for (let s = 0; s < 155; s += 31) b.beam([x, y + s, z], [x, y + s + 31, z + 18], 0.7).beam([x, y + s, z], [x, y + s, z + 18], 0.6);
            }
          }
        }
      } else {
        // deck-truss causeway descending to the Oakland mole
        const y0 = 697 + 775;
        const y1 = a.length;
        const n = 14;
        for (let k = 0; k < n; k++) {
          const ya = y0 + ((y1 - y0) * k) / n;
          const yb = y0 + ((y1 - y0) * (k + 1)) / n;
          const za = 34 - (28 * k) / n;
          const zb = 34 - (28 * (k + 1)) / n;
          deck(b, [0, ya, za], [0, yb, zb], W, 7, grey);
          b.color('#BDB8AE').box(0, yb, 0, 18, 6, Math.max(zb - 7, 0.5));
        }
      }
    });
  };
}
const eastFacts = {
  Opened: 'Nov 12, 1936',
  'Main span': '427 m (1,400 ft) double balanced cantilever, then five 504 ft (154 m) through-trusses and a causeway of fourteen 288 ft deck trusses',
  '1989': 'a 15 m section of upper deck collapsed in the Loma Prieta quake',
  Replaced: 'closed Aug 28, 2013; dismantled Nov 2013 – Nov 2017: cantilever gone by Jun 12, 2015, the five 504 ft trusses lowered Feb – Aug 2016, the last 288 ft truss removed Mar 2017, the piers imploded Nov 2015 – Nov 2017',
  Model: 'APPROXIMATE alignment (~100 m north of today’s skyway); truss heights estimated'
};
const eastSrc = [
  WIKI + 'Eastern_span_replacement_of_the_San_Francisco%E2%80%93Oakland_Bay_Bridge',
  'https://www.cbsnews.com/sanfrancisco/news/demolition-of-old-bay-bridge-to-take-years',
  'https://abc7news.com/demolition-of-old-span-bay-bridge-project/1799171/'
];
const bayBridgeEastOld: Landmark[] = [
  {id: 'bay_bridge_east_1936_cantilever', name: 'Bay Bridge east span (1936) — cantilever', kind: 'bridge', built: [1933.52, 1936.87], end: 2015.45, anchor: YBI_EAST, build: eastOldPart('cantilever'), facts: eastFacts, sources: eastSrc},
  {id: 'bay_bridge_east_1936_trusses', name: 'Bay Bridge east span (1936) — truss spans', kind: 'bridge', built: [1933.52, 1936.87], end: 2016.6, anchor: YBI_EAST, build: eastOldPart('trusses'), facts: eastFacts, sources: eastSrc},
  {id: 'bay_bridge_east_1936_causeway', name: 'Bay Bridge east span (1936) — causeway', kind: 'bridge', built: [1933.52, 1936.87], end: 2017.2, anchor: YBI_EAST, build: eastOldPart('causeway'), facts: eastFacts, sources: eastSrc}
];

// --- new east span (2013): skyway (2002–2007) + self-anchored suspension span (2009–2013)
const SAS_W: V2 = [-122.3602, 37.8143];
const SAS_E: V2 = [-122.3543, 37.8176];
const SAS_TOWER: V2 = [-122.358479, 37.815265];
const OAK_TOUCH: V2 = [-122.3277, 37.8222];
const sasSpan: Landmark = {
  id: 'bay_bridge_east_2013_sas',
  name: 'Bay Bridge east span (2013) — self-anchored suspension span',
  kind: 'bridge',
  built: [2009.0, 2013.67],
  end: 9999,
  anchor: SAS_TOWER,
  build: b => {
    const a = along(SAS_TOWER, SAS_W, SAS_E);
    const p0 = lngLatToLocal(SAS_TOWER, SAS_W);
    b.frame(p0[0], p0[1], 0, a.bearing, () => {
      const t = Math.hypot(...lngLatToLocal(SAS_TOWER, SAS_W)); // tower position along the span
      for (const x of [-20, 20]) deck(b, [x, 0, 50], [x, a.length, 48], 26, 5, '#C9CDD0');
      // single tower: four tapered legs joined by shear links, 160 m
      b.color('#F1F1EE');
      for (const x of [-4, 4]) for (const y of [-4, 4]) b.loft([rect(x * 1.6, t + y * 1.4, 5.5, 5.5), rect(x, t + y, 3, 3)], [0, 160], {top: true});
      for (let z = 30; z < 160; z += 22) b.box(0, t, z, 14, 2, 1.5);
      // one continuous cable from the west end over the tower, looping around the east end
      for (const x of [-7, 7]) {
        const w: V3 = [x * 3.4, 0, 52];
        const tt: V3 = [x, t, 158];
        const e: V3 = [x * 3.4, a.length, 50];
        const c1 = parabola(w, tt, 75, 10);
        const c2 = parabola(tt, e, 80, 16);
        b.polyline(c1, 1.4).polyline(c2, 1.4);
        for (const c of [...c1, ...c2]) if (c[2] > 56) b.beam([c[0], c[1], 50], c, 0.35);
      }
    });
  },
  // the tower's generic footprint (OSM part, a 53 m LiDAR prism) stands inside the model
  replaces: [rect(0, 0, 120, 120)],
  facts: {
    Opened: 'Sep 2, 2013',
    Form: 'single-tower self-anchored suspension span (world’s largest)',
    Tower: '160 m (525 ft), four legs with shear links',
    'Main span': '385 m'
  },
  sources: [WIKI + 'Eastern_span_replacement_of_the_San_Francisco%E2%80%93Oakland_Bay_Bridge']
};
const skyway: Landmark = {
  id: 'bay_bridge_east_2013_skyway',
  name: 'Bay Bridge east span (2013) — skyway',
  kind: 'bridge',
  built: [2002.08, 2007.5],
  end: 9999,
  anchor: SAS_E,
  build: b => {
    const a = along(SAS_E, SAS_E, OAK_TOUCH);
    b.frame(0, 0, 0, a.bearing, () => {
      const n = 16;
      for (let k = 0; k < n; k++) {
        const ya = (a.length * k) / n;
        const yb = (a.length * (k + 1)) / n;
        const za = 48 - (42 * k) / n;
        const zb = 48 - (42 * (k + 1)) / n;
        for (const x of [-20, 20]) {
          deck(b, [x, ya, za], [x, yb, zb], 26, 5, '#C9CDD0');
          b.color('#BDBAB3').box(x, yb, 0, 6, 6, Math.max(zb - 5, 0.5));
        }
      }
    });
  },
  facts: {Construction: '2002 – 2007 (opened with the SAS span, Sep 2013)', Form: 'twin concrete viaducts, ~2 km'},
  sources: [WIKI + 'Eastern_span_replacement_of_the_San_Francisco%E2%80%93Oakland_Bay_Bridge']
};

// =========================================================== Ferry Building
// Audit 2026-11: the earlier model was mirrored across its long axis (tower on
// the bay side, sheds standing in the Embarcadero). Geometry now from the OSM
// footprint + 3D tower parts in a frame whose +y runs NW along the Embarcadero
// (324°) and +x points NE to the bay: main block x −27…20.4 (47 m) × 201 m,
// projecting entrance pavilion on the Embarcadero side (x −36…−27, 43 m long),
// tower on that side at (−22, 2.9): 11.4 m shaft to 43.5 m, stepped stages to 60.5 m.
const ferryBuilding: Landmark = {
  id: 'ferry_building',
  name: 'Ferry Building',
  kind: 'building',
  built: [1896.0, 1898.53],
  end: 9999,
  anchor: [-122.393383, 37.795538],
  build: b => {
    const stone = '#D8D2C4';
    b.frame(0, 0, 0, 324, () => {
      b.color(stone).box(-3.3, 2.4, 0, 47.4, 200.8, 15);
      b.color('#8E9396').gable(-3.3, 2.4, 48.4, 201.8, 15, 6, true);
      b.color('#B9BDBF').box(-3.3, 2.4, 19, 8, 190, 2.5); // clerestory over the Great Nave
      // entrance pavilion under the tower (Embarcadero side)
      b.color(stone).box(-31.45, 3.15, 0, 8.9, 43.1, 16);
      b.color('#8E9396').box(-31.45, 3.15, 16, 9.4, 43.6, 1);
      // ground-floor arcade along the Embarcadero front
      b.color('#C9C2B2');
      for (let y = -94; y <= 100; y += 8) if (y < -19 || y > 25) b.box(-27.6, y, 0, 1.2, 2.2, 6.5);
      for (let y = -16; y <= 23; y += 6.5) b.box(-36.5, y, 0, 1.2, 2.2, 7);
      b.color(stone).box(-27.6, -57.5, 6.5, 1.4, 81, 1.4).box(-27.6, 63.3, 6.5, 1.4, 79, 1.4);
      // Giralda-style clock tower (OSM 3D parts), clock stage with 6.7 m dials, cupola to 75 m
      const tx = -22;
      const ty = 2.9;
      b.color(stone).box(tx, ty, 0, 11.4, 12.1, 40);
      b.color('#F4F2EC').box(tx, ty, 40, 12, 12.7, 5.5); // clock stage
      b.color(stone).box(tx, ty, 45.5, 10.3, 11.1, 5).box(tx, ty, 50.5, 8.3, 8.2, 3.7).box(tx, ty, 54.2, 6.4, 6.5, 6.3);
      b.color('#C9C2B2').box(tx, ty, 60.5, 4.6, 4.6, 6);
      b.color('#9BA1A3').dome(tx, ty, 2.6, 66.5, 5.5, 10, 3);
      b.color('#7E8487').cylinder(tx, ty, 0.25, 72, 75, 4);
    });
  },
  replaces: [rotRect(0, 0, 60, 205, 144)],
  facts: {
    Opened: 'Jul 13, 1898 (architect A. Page Brown)',
    'Clock tower': '75 m (245 ft), after the Giralda of Seville; four 6.7 m clock dials',
    Survived: '1906 earthquake and fire',
    Restored: '2002–2003',
    Model: 'footprint and tower stages from OSM; roof pitch and cupola estimated'
  },
  sources: [WIKI + 'San_Francisco_Ferry_Building']
};

// =========================================================== City Hall
// Audit 2026-11 (owner report "oriented the wrong way"): the earlier model ran
// its long axis E–W. The OSM/DataSF footprints and the orthophoto show the
// long axis N–S along Polk (E, main front) and Van Ness (W) on the −9° street
// grid: main block 87 × 126.6 m, centre pavilions projecting ~6 m on both long
// fronts, two light courts N and S of the rotunda wing (28 m deep, E–W), and the
// dome centred on the rotunda wing. Dome stages follow the OSM 3D parts
// (drum r ≈ 17 m to 46–52 m, dome r ≈ 14.5 m from 60 m) and the 93.7 m total.
function cityHallBuild(b: MeshBuilder) {
  const granite = '#DDD9CF';
  const shade = '#CFCAC0';
  const gold = '#C9A43A';
  b.frame(0, 0, 0, -9, () => {
    // local +x = east (Polk St front), +y = north (McAllister St)
    const outer = rect(0, 0.4, 87, 126.6);
    const courts = [rect(0, 29.9, 50, 31.4), rect(0, -29.6, 50, 30.8)];
    b.color(granite).prism(outer, 0, 26, {holes: courts});
    b.color('#D3CEC3').prism(rect(0, 0.4, 85.6, 125.2), 26, 30, {holes: courts, top: false});
    b.color('#9FB3AA').cap(rect(0, 0.4, 85.6, 125.2), 30, courts); // verdigris copper roofs (orthophoto)
    b.color('#A9BDB9');
    for (const c of courts) b.cap(c, 8); // glazed court roofs at the second floor
    // rotunda wing across the middle, rising above the ring
    b.color(granite).box(0, 0, 30, 86, 28.4, 5);
    b.color(granite).box(0, 0, 35, 39, 40, 2);
    // centre pavilions on Polk (E) and Van Ness (W): portico + pediment + six columns
    for (const sx of [-1, 1]) {
      b.color(granite).box(sx * 45.5, 0, 0, 5, 24.6, 27);
      b.color(shade).gable(sx * 45.5, 0, 5.6, 25.4, 27, 4.2, false);
      b.color('#E6E2D8');
      for (const y of [-8.5, -5.1, -1.7, 1.7, 5.1, 8.5]) b.cylinder(sx * 48.6, y, 0.85, 4, 24.5, 8);
      b.color(granite).box(sx * 48.4, 0, 0, 2.6, 26, 4); // steps / podium
      b.color(granite).box(sx * 48.6, 0, 24.5, 2.2, 22, 2.5); // entablature
      // giant order along the long fronts (2nd–3rd floors on a rusticated base)
      b.color('#E6E2D8');
      for (const sy of [-1, 1]) for (let y = 16; y <= 52; y += 4) b.cylinder(sx * 43.9, sy * y + 0.4, 0.7, 8, 24, 6);
      // end pavilions with small pediments
      for (const sy of [-1, 1]) {
        b.color(granite).box(sx * 44, sy * 56.5 + 0.4, 0, 2, 13, 27);
        b.color(shade).gable(sx * 44.6, sy * 56.5 + 0.4, 3, 13, 27, 2.6, false);
      }
    }
    // drum: colonnaded ring (r 17, 24 columns) on the rotunda base, attic, dome
    b.color(shade).cylinder(0, 0, 15.6, 37, 52, 24);
    b.color('#E6E2D8');
    for (let i = 0; i < 24; i++) {
      const a = (i / 24) * Math.PI * 2;
      b.cylinder(Math.cos(a) * 17, Math.sin(a) * 17, 0.65, 37, 51, 6);
    }
    b.color(granite).cylinder(0, 0, 17.8, 51, 53.5, 24).cylinder(0, 0, 15.6, 53.5, 60, 24);
    const R0 = 14.6;
    const H = 15;
    b.color('#6C7377').dome(0, 0, R0, 60, H, 24, 6);
    // gilded ribs following the dome profile
    const Rs = (R0 * R0 + H * H) / (2 * H);
    const zc = 60 + H - Rs;
    b.color(gold);
    for (let i = 0; i < 8; i++) {
      const a = (i / 8) * Math.PI * 2 + Math.PI / 8;
      const pts: V3[] = [];
      for (let k = 0; k <= 4; k++) {
        const z = 60 + (H - 2) * (k / 4);
        const r = Math.sqrt(Math.max(Rs * Rs - (z - zc) * (z - zc), 0)) + 0.2;
        pts.push([Math.cos(a) * r, Math.sin(a) * r, z]);
      }
      b.polyline(pts, 0.6);
    }
    // lantern, cupola and spire to 93.7 m
    b.color(granite).cylinder(0, 0, 3.6, 74, 84.5, 10);
    b.color(gold).dome(0, 0, 3.8, 84.5, 3.5, 10, 3).cylinder(0, 0, 0.5, 88, 93.7, 6);
  });
}

const cityHall: Landmark = {
  id: 'city_hall_1915',
  name: 'San Francisco City Hall',
  kind: 'building',
  built: [1913.26, 1915.95],
  end: 9999,
  anchor: [-122.419235, 37.779274], // rotunda centre (OSM 3D parts)
  build: cityHallBuild,
  replaces: [rotRect(0, 0, 104, 132, -9)],
  facts: {
    Construction: 'Apr 1913 – Dec 1915 (in time for the PPIE)',
    Architect: 'Bakewell & Brown (Arthur Brown Jr.)',
    Dome: '93.7 m (307.5 ft); gilding restored 1999',
    Footprint: '≈ 127 m (N–S, along Polk St) × 87 m, two light courts',
    Model: 'footprint and dome stages from OSM/DataSF; column counts and roof pitches estimated from photos'
  },
  sources: [WIKI + 'San_Francisco_City_Hall', 'https://www.openstreetmap.org/relation/7261820']
};

// =========================================================== Old City Hall (1872–1906)
// Triangular block south of McAllister St and east of Larkin St (Yerba Buena Park); frontages from the
// San Francisco News Letter of Aug 5, 1893: Larkin St 450 ft, McAllister St 600 ft, the main front on the diagonal
// (City Hall Ave / Park Ave). Frame: origin = Larkin & McAllister centreline crossing (Overture/OSM),
// +u east along McAllister (80.2°), +v north. Today's Main Library (Larkin–Hyde–Fulton–Grove) stands on its site;
// its ruins were found under Hyde St near Fulton St (CBS).
const OLD_CH: V2 = [-122.4169901, 37.7804986];
const OCH_BRG = -9.8;
const OCH_A: V2 = [10.5, -10.5]; // Larkin / McAllister property corner
const OCH_B: V2 = [10.5 + 600 * 0.3048, -10.5]; // 600 ft east on McAllister
const OCH_C: V2 = [10.5, -10.5 - 450 * 0.3048]; // 450 ft south on Larkin
const OCH_STONE = '#D9D3C4';
const OCH_ROOF = '#5E6266';

/** A wing along a property line p→q, `d` m deep toward `inward`, walls to `eave`, mansard roof above. */
function ochWing(b: MeshBuilder, p: V2, q: V2, d: number, eave: number, inward: 1 | -1) {
  const dx = q[0] - p[0];
  const dy = q[1] - p[1];
  const L = Math.hypot(dx, dy);
  const nx = (-dy / L) * inward;
  const ny = (dx / L) * inward;
  const ring: V2[] = [p, q, [q[0] + nx * d, q[1] + ny * d], [p[0] + nx * d, p[1] + ny * d]];
  b.color(OCH_STONE).prism(ring, 0, eave, {top: false});
  const inset = (k: number): V2[] => [
    [p[0] + nx * k + (dx / L) * k, p[1] + ny * k + (dy / L) * k],
    [q[0] + nx * k - (dx / L) * k, q[1] + ny * k - (dy / L) * k],
    [q[0] + nx * (d - k) - (dx / L) * k, q[1] + ny * (d - k) - (dy / L) * k],
    [p[0] + nx * (d - k) + (dx / L) * k, p[1] + ny * (d - k) + (dy / L) * k]
  ];
  b.color(OCH_ROOF).loft([ring, inset(3)], [eave, eave + 5]);
}

function oldCityHallWings(b: MeshBuilder) {
  b.frame(0, 0, 0, OCH_BRG, () => {
    ochWing(b, OCH_A, OCH_B, 20, 20, -1); // McAllister wing
    ochWing(b, OCH_C, OCH_A, 20, 20, -1); // Larkin wing
    ochWing(b, OCH_B, OCH_C, 24, 22, -1); // main front on the diagonal, facing south-east
    // Hall of Records: circular domed building at the eastern point of the block (position LOW CONFIDENCE)
    const hr: V2 = [OCH_B[0] - 32, OCH_B[1] - 14];
    b.color(OCH_STONE).cylinder(hr[0], hr[1], 14, 0, 20, 20);
    b.color(OCH_ROOF).dome(hr[0], hr[1], 14.5, 20, 9, 20, 4);
  });
}

/** Tower over the middle of the main front: square base, colonnaded drum, ribbed dome, lantern and statue (335 ft). */
function oldCityHallTower(b: MeshBuilder, ruin: boolean) {
  const m: V2 = [(OCH_B[0] + OCH_C[0]) / 2 - 8, (OCH_B[1] + OCH_C[1]) / 2 + 8];
  b.frame(0, 0, 0, OCH_BRG, () => {
    b.color(OCH_STONE).box(m[0], m[1], 0, 26, 26, ruin ? 30 : 38);
    if (!ruin) {
      b.cylinder(m[0], m[1], 13, 38, 46, 20);
      for (let k = 0; k < 16; k++) {
        const a = (k / 16) * Math.PI * 2;
        b.box(m[0] + Math.cos(a) * 12.4, m[1] + Math.sin(a) * 12.4, 46, 1.2, 1.2, 14);
      }
      b.cylinder(m[0], m[1], 11, 46, 60, 20).cylinder(m[0], m[1], 13.3, 60, 62.5, 20);
      b.color('#8C8F8E').dome(m[0], m[1], 12.5, 62.5, 20, 20, 6);
      b.color(OCH_STONE).cylinder(m[0], m[1], 3, 82.5, 92, 10);
      b.color('#B89B4A').dome(m[0], m[1], 3.2, 92, 2.5, 10, 2).beam([m[0], m[1], 94.5], [m[0], m[1], 335 * 0.3048], 1.0);
      return;
    }
    // 1906–1909: the steel skeleton of the dome stood on its drum over the gutted building
    b.color('#5E5A55').cylinder(m[0], m[1], 12.5, 30, 46, 16, {top: false});
    for (let k = 0; k < 16; k++) {
      const a0 = (k / 16) * Math.PI * 2;
      const pts: V3[] = [];
      for (let i = 0; i <= 6; i++) {
        const t = (i / 6) * (Math.PI / 2);
        pts.push([m[0] + Math.cos(a0) * 12.5 * Math.cos(t), m[1] + Math.sin(a0) * 12.5 * Math.cos(t), 62.5 + 20 * Math.sin(t)]);
      }
      b.beam([m[0] + Math.cos(a0) * 12.5, m[1] + Math.sin(a0) * 12.5, 46], pts[0], 0.6);
      b.polyline(pts, 0.5);
    }
    b.cylinder(m[0], m[1], 3, 82.5, 88, 8, {top: false});
  });
}

const OCH_SOURCES = [
  WIKI + 'San_Francisco_City_Hall',
  'https://sfmuseum.org/hist5/laver.html',
  'https://oac.cdlib.org/ark:/13030/hb096nb16b/',
  'https://www.cbsnews.com/sanfrancisco/news/construction-crew-unearths-ruins-of-old-san-francisco-city-hall-building-destroyed-in-06-quake'
];

const oldCityHall: Landmark = {
  id: 'city_hall_1899',
  name: 'Old San Francisco City Hall',
  kind: 'building',
  built: [1872.14, 1889.0],
  end: 1906.3,
  anchor: OLD_CH,
  build: oldCityHallWings,
  facts: {
    Built: 'cornerstone Feb 22, 1872; built in stages over 27 years (completed 1899) to Augustus Laver\'s Second Empire design — the wings and Hall of Records first, the tower last',
    Site: 'triangular block of Yerba Buena Park: 450 ft on Larkin St, 600 ft on McAllister St, the main front (≈ 1,100 ft of irregular walls) on the diagonal avenue — today\'s Main Library block and Fulton St east of Larkin',
    Destroyed: 'Apr 18, 1906 in the earthquake and fire',
    Model:
      'triangle from the documented frontages laid on today\'s Larkin / McAllister lines; wing depths (20–24 m), eave heights, mansards, the Hall of Records position and the split of the build years into wings (to 1889) and tower (1889–98) estimated — LOW CONFIDENCE in detail (no Sanborn sheet of the block was traced)'
  },
  sources: OCH_SOURCES
};

const oldCityHallDome: Landmark = {
  id: 'city_hall_1899_dome',
  name: 'Old San Francisco City Hall — tower and dome',
  kind: 'tower',
  built: [1889.0, 1898.9],
  end: 1906.3,
  anchor: OLD_CH,
  build: b => oldCityHallTower(b, false),
  facts: {
    Height: 'main dome 335 ft (102 m) (Bancroft Library photo record; other sources say about 300 ft); Laver\'s 1870s design had called for a 420 ft tower',
    Built: 'still unfinished in 1893 (News Letter); completed in the late 1890s, crowned by the Goddess of Progress (her head survives in today\'s City Hall)',
    Model: 'position at the middle of the diagonal front, stage heights and colonnade estimated from photographs; LOW CONFIDENCE'
  },
  sources: OCH_SOURCES
};

const oldCityHallRuin: Landmark = {
  id: 'city_hall_1906_ruin',
  name: 'Old City Hall ruins (dome skeleton)',
  kind: 'monument',
  built: [1906.3, 1906.32],
  end: 1909.5,
  anchor: OLD_CH,
  build: b => {
    oldCityHallTower(b, true);
    b.frame(0, 0, 0, OCH_BRG, () => {
      b.color('#77716A');
      for (const [p, q] of [[OCH_A, OCH_B], [OCH_C, OCH_A], [OCH_B, OCH_C]] as [V2, V2][]) b.wallProfile([p, q], 0, 7);
    });
  },
  facts: {
    Ruin: 'after the fire the bare steel frame of the dome stood over the gutted walls and was shown to visitors for years',
    Removed: 'pulled down c. 1909 (one account; others put the sale of the ruins later) — LOW CONFIDENCE end date',
    Model: 'dome ribs on the drum and low broken walls on the building lines, estimated from the 1906 photographs'
  },
  sources: OCH_SOURCES
};

// =========================================================== Coit Tower
const coitTower: Landmark = {
  id: 'coit_tower',
  name: 'Coit Tower',
  kind: 'tower',
  built: [1932.5, 1933.77],
  end: 9999,
  anchor: [-122.405842, 37.802373],
  build: b => {
    const conc = '#E2DED3';
    // base building rotated −14.5° (OSM footprint 22 m, axes 75.6°/165.6°)
    b.frame(0, 0, 0, -14.5, () => b.color(conc).prism(roundedRect(0, 0, 22, 22, 3, 2), 0, 8));
    // fluted shaft (24 flutes approximated by a 24-gon) tapering slightly to 55 m
    b.color('#E8E4DA').frustum(0, 0, 5.8, 5.4, 8, 55, 24, false);
    // arcaded crown
    b.color(conc).cylinder(0, 0, 5.6, 55, 57, 24);
    b.color('#D2CDBF');
    for (let i = 0; i < 16; i++) {
      const a = (i / 16) * Math.PI * 2;
      b.box(Math.cos(a) * 5.3, Math.sin(a) * 5.3, 57, 0.9, 0.9, 5);
    }
    b.color(conc).cylinder(0, 0, 5.6, 62, 63.2, 24).cylinder(0, 0, 4.8, 63.2, 64, 24);
  },
  replaces: [rect(0, 0, 26, 26)],
  facts: {
    Dedicated: 'Oct 8, 1933 (Lillie Hitchcock Coit bequest)',
    Height: '64 m (210 ft), on the summit of Telegraph Hill (≈ 84 m / 275 ft)',
    Murals: 'WPA / PWAP, 1934'
  },
  sources: [WIKI + 'Coit_Tower']
};

// =========================================================== Palace of Fine Arts
// Audit 2026-11: rebuilt from the OSM 3D geometry (the earlier hall arc was too
// small and the colonnades curved the wrong way). Local metres from the rotunda
// centre. Exhibition hall: OSM outline (≈ 270 m arc, 45 m deep) with its raised
// clerestory band; colonnade arms: centrelines of the OSM colonnade outlines
// with paired columns every 4.5 m and the planter boxes on top (OSM h 19–21 m);
// rotunda: 8 piers on r = 24.5 m at bearings 13.5° + 45°k, entablature ring to
// 33 m, drum r 17.9 m to 40 m, dome r 16.3 m to 49.4 m (162 ft); lagoon from
// the US Census TIGER area-water polygon.
const POFA_HALL: V2[] = [
  [-78.9, -61.2], [-61.1, -89.7], [-33.6, -116.1], [-10.0, -129.6], [6.6, -136.4], [10.8, -126.8], [8.7, -125.9], [16.5, -107.2],
  [18.1, -107.8], [22.6, -97.2], [3.7, -89.5], [-4.7, -84.1], [-26.4, -64.1], [-35.7, -51.5], [-44.6, -34.2], [-52.0, -7.0],
  [-53.4, 11.6], [-48.7, 43.4], [-41.7, 59.7], [-30.3, 78.7], [-17.3, 94.0], [-9.5, 99.7], [-16.9, 107.9], [-18.1, 106.8],
  [-30.9, 121.4], [-28.6, 123.5], [-36.4, 132.1], [-52.5, 117.1], [-68.2, 99.4], [-86.2, 65.9], [-92.5, 41.2], [-96.7, 10.6],
  [-94.7, -10.4], [-87.8, -42.5]
];
const POFA_CLERESTORY: V2[] = [
  [6.6, -110.9], [-3.1, -106.3], [-21.6, -93.9], [-31.4, -85.2], [-49.2, -64.2], [-63.4, -35.6], [-70.5, -7.2], [-71.5, 24.4],
  [-67.3, 42.3], [-52.6, 74.6], [-44.1, 88.4], [-27.5, 106.6], [-32.2, 111.9], [-50.4, 92.7], [-59.3, 78.9], [-68.5, 60.1],
  [-74.4, 43.3], [-77.9, 25.7], [-77.6, -7.8], [-69.9, -37.6], [-63.5, -53.7], [-56.4, -67.7], [-47.3, -80.5], [-15.7, -107.7],
  [3.7, -117.7]
];
const POFA_ARMS: V2[][] = [
  [[-35.9, 20.4], [-32.1, 28.6], [-30.1, 39.8], [-25.6, 48.4], [-21.5, 58.9], [-15.1, 66.4], [-8.2, 74.9], [0.4, 80.1], [6.8, 80.0], [16.3, 80.8], [17.0, 91.1], [13.7, 101.3], [12.1, 106.7]],
  [[-27.5, -30.2], [-22.1, -37.3], [-16.4, -46.9], [-10.1, -55.1], [-2.0, -62.6], [5.4, -69.3], [16.1, -73.6], [25.1, -74.4], [33.4, -74.8], [41.1, -72.2], [43.3, -76.0], [44.4, -87.2], [47.4, -97.2], [47.9, -104.2]]
];
const POFA_LAGOON: V2[] = [
  [-15.3, 41.2], [1.3, 60.7], [30.9, 73.0], [33.4, 80.6], [31.6, 97.4], [36.5, 102.8], [50.8, 107.0], [54.4, 131.7], [65.6, 131.5],
  [76.6, 123.4], [93.3, 99.8], [90.2, 73.0], [102.8, 54.5], [106.5, 39.3], [108.6, 11.3], [96.6, -4.4], [118.6, -33.7], [112.8, -46.0],
  [118.7, -62.3], [111.7, -71.5], [109.6, -80.4], [96.8, -90.3], [93.1, -103.4], [80.7, -107.5], [64.2, -95.2], [56.7, -70.5],
  [45.6, -59.6], [37.2, -56.6], [16.4, -60.7], [4.7, -51.2], [2.6, -44.2], [4.9, -42.8], [33.9, -39.1], [41.8, -31.1], [48.6, 9.0],
  [43.9, 20.5], [30.9, 35.4], [20.0, 42.7], [-9.0, 34.4], [-14.6, 35.9]
];

function pofaColonnade(b: MeshBuilder, path: V2[], stone: string) {
  let acc = 0;
  let next = 1;
  let k = 0;
  for (let i = 0; i < path.length - 1; i++) {
    const [ax, ay] = path[i];
    const [bx, by] = path[i + 1];
    const L = Math.hypot(bx - ax, by - ay);
    const ux = (bx - ax) / L;
    const uy = (by - ay) / L;
    b.color(stone).beam([ax, ay, 11.8], [bx, by, 11.8], 4.6, 1.6);
    while (next <= acc + L) {
      const t = next - acc;
      const x = ax + ux * t;
      const y = ay + uy * t;
      for (const o of [-1.6, 1.6]) b.cylinder(x - uy * o, y + ux * o, 0.45, 0, 11, 5, {top: false});
      if (k % 5 === 2) b.beam([x - ux * 2, y - uy * 2, 15.6], [x + ux * 2, y + uy * 2, 15.6], 4.4, 6); // planter box
      next += 4.5;
      k++;
    }
    acc += L;
  }
}

function palaceOfFineArts(stone: string, dome: string) {
  return (b: MeshBuilder) => {
    // lagoon (drawn just above the ground plane)
    b.color('#9FC2D0').cap(POFA_LAGOON, 0.15);
    // exhibition hall
    b.color(stone).prism(POFA_HALL, 0, 14, {top: false});
    b.color('#8E8A84').cap(POFA_HALL, 14).prism(POFA_CLERESTORY, 14, 18.5);
    // colonnade arms + their end pavilions (OSM blocks, 21 m)
    for (const arm of POFA_ARMS) pofaColonnade(b, arm, stone);
    b.color(stone).box(-3, 105.7, 0, 8.2, 8.2, 21).box(30.2, -101.4, 0, 8, 8, 21);
    b.box(15, 99, 0, 9, 13, 19).box(46.2, -99.5, 0, 8, 10, 19).box(31, -74.8, 0, 13, 8, 19);
    // rotunda: eight piers, entablature ring, drum and dome
    const R = 24.5;
    for (let i = 0; i < 8; i++) {
      const brg = 13.5 + 45 * i;
      const a = (brg * Math.PI) / 180;
      b.frame(Math.sin(a) * R, Math.cos(a) * R, 0, brg, () => {
        b.color(stone).box(0, 0, 0, 9.3, 5.4, 25);
        b.box(0, 0.4, 25, 6, 4, 11); // pier tops with the figure boxes
      });
    }
    const ring = (r: number) => circle(0, 0, r, 8).map(([x, y]) => {
      const a = (-9 * Math.PI) / 180; // align the octagon with the piers
      return [x * Math.cos(a) - y * Math.sin(a), x * Math.sin(a) + y * Math.cos(a)] as V2;
    });
    b.color(stone).prism(ring(28.6), 25, 33, {holes: [ring(22.6)]});
    b.color(stone).cylinder(0, 0, 17.9, 25, 40, 20);
    b.color(dome).dome(0, 0, 16.3, 40, 9.4, 20, 5);
  };
}
const pofa1915: Landmark = {
  id: 'palace_of_fine_arts_1915',
  name: 'Palace of Fine Arts (1915, plaster)',
  kind: 'monument',
  built: [1914.2, 1915.13],
  end: 1964.3,
  anchor: [-122.448402, 37.802919],
  build: palaceOfFineArts('#D9B48C', '#B4785A'),
  facts: {
    Built: '1914–15 for the Panama-Pacific Exposition (Bernard Maybeck), wood frame and plaster "staff"',
    Fate: 'the only PPIE building kept on site; decayed and demolished 1964',
    Rotunda: '49 m (162 ft)',
    Model: 'layout of the 1967 replica (OSM 3D) applied to the 1915 original; column count estimated'
  },
  sources: [WIKI + 'Palace_of_Fine_Arts']
};
const pofa1967: Landmark = {
  ...pofa1915,
  id: 'palace_of_fine_arts_1967',
  name: 'Palace of Fine Arts',
  built: [1964.5, 1967.5],
  end: 9999,
  build: palaceOfFineArts('#D7B98E', '#B07A52'),
  replaces: [rect(-30, -2, 150, 280)],
  facts: {
    Rebuilt: '1964–67 in steel and concrete to the 1915 design',
    Exploratorium: '1969–2013',
    Rotunda: '49 m (162 ft)',
    Model: 'hall, colonnades and rotunda from OSM 3D geometry; column count estimated'
  }
};

// =========================================================== Sutro Tower
const sutroTower: Landmark = {
  id: 'sutro_tower',
  name: 'Sutro Tower',
  kind: 'tower',
  built: [1971.0, 1973.5],
  end: 9999,
  anchor: [-122.452857, 37.755242],
  build: b => {
    // equilateral-triangle legs: side 45.7 m at the base, 18.3 m at the waist (~168 m),
    // 30.5 m at the antenna platform (235 m); trusses at 55, 114, 168, 198, 235 m
    const side = (z: number) => (z <= 168 ? 45.7 + ((18.3 - 45.7) * z) / 168 : 18.3 + ((30.5 - 18.3) * (z - 168)) / 67);
    const leg = (k: number, z: number): V3 => {
      const r = side(z) / Math.sqrt(3);
      // legs point W, SE and NE (OSM truss-level outlines; audit 2026-11: was rotated 90°, a leg pointing N)
      const a = (k / 3) * Math.PI * 2 + Math.PI;
      return [Math.cos(a) * r, Math.sin(a) * r, z];
    };
    const bands = (z: number) => (Math.floor(z / 30) % 2 === 0 ? '#BF4E3B' : '#F2F2F2');
    const zs = [0, 30, 60, 90, 120, 150, 168, 198, 235];
    for (let k = 0; k < 3; k++)
      for (let i = 0; i < zs.length - 1; i++) b.color(bands(zs[i])).beam(leg(k, zs[i]), leg(k, zs[i + 1]), 2.2);
    for (const z of [55, 114, 168, 198, 235]) {
      for (let k = 0; k < 3; k++) b.color(bands(z)).beam(leg(k, z), leg((k + 1) % 3, z), 1.4);
    }
    // antenna platform + three masts to 297.8 m
    b.color('#F2F2F2').prism([0, 1, 2].map(k => leg(k, 235).slice(0, 2) as V2), 235, 238);
    for (let k = 0; k < 3; k++) {
      const p = leg(k, 238);
      b.color('#BF4E3B').beam(p, [p[0] * 0.8, p[1] * 0.8, 270], 1.6);
      b.color('#F2F2F2').beam([p[0] * 0.8, p[1] * 0.8, 270], [p[0] * 0.7, p[1] * 0.7, 297.8], 1.1);
    }
  },
  replaces: [circle(0, 0, 35, 12)],
  facts: {
    Completed: 'Jul 4, 1973',
    Height: '297.8 m (977 ft), on a 254 m (834 ft) hill — its top is 552 m (1,811 ft) above the sea',
    'Tallest structure in SF': 'until 2018'
  },
  sources: [WIKI + 'Sutro_Tower', 'https://www.sutrotower.com/faq']
};

// =========================================================== Alcatraz
const ALC: V2 = [-122.42325, 37.82681];
const alcatrazCellhouse: Landmark = {
  id: 'alcatraz_cellhouse',
  name: 'Alcatraz Main Cellhouse',
  kind: 'building',
  built: [1909.5, 1912.0],
  end: 9999,
  anchor: ALC,
  build: b => {
    // OSM footprint centroids (audit 2026-11: the administration block was at the
    // wrong (NW) end; it closes the SE end, its long axis at 46°)
    const p = lngLatToLocal(ALC, [-122.422932, 37.82663]);
    b.frame(p[0], p[1], 0, 136, () => {
      b.color('#CFC8B8').box(0, 0, 0, 49, 65, 15);
      b.color('#9C968A').box(0, 0, 15, 49, 65, 1, {top: true});
    });
    const ad = lngLatToLocal(ALC, [-122.422557, 37.826417]);
    b.frame(ad[0], ad[1], 0, 46, () => b.color('#B9B2A3').box(0, 0, 0, 14.7, 34.9, 12)); // administration block
    const d = lngLatToLocal(ALC, [-122.423393, 37.826994]);
    b.frame(d[0], d[1], 0, 136, () => b.color('#CFC8B8').box(0, 0, 0, 20, 52, 9)); // dining hall
  },
  replaces: [
    circle(lngLatToLocal(ALC, [-122.422932, 37.82663])[0], lngLatToLocal(ALC, [-122.422932, 37.82663])[1], 45, 12),
    circle(lngLatToLocal(ALC, [-122.423393, 37.826994])[0], lngLatToLocal(ALC, [-122.423393, 37.826994])[1], 12, 8)
  ],
  facts: {
    Built: '1909–1912 (Army disciplinary barracks, incorporating the 1859 citadel)',
    'Federal penitentiary': '1934 – Mar 21, 1963',
    Occupation: 'Indians of All Tribes, Nov 1969 – Jun 1971',
    Model: 'footprints from OSM; heights estimated'
  },
  sources: [WIKI + 'Alcatraz_Federal_Penitentiary', WIKI + 'Alcatraz_Island']
};
const alcatrazLight1854: Landmark = {
  id: 'alcatraz_lighthouse_1854',
  name: 'Alcatraz Lighthouse (1854)',
  kind: 'tower',
  built: [1853.6, 1854.42],
  end: 1909.6,
  anchor: [-122.422296, 37.826254],
  build: b => {
    b.color('#EDE7D8').box(0, 0, 0, 10, 8, 7);
    b.color('#8C8F92').gable(0, 0, 10.5, 8.5, 7, 3, false);
    b.color('#F2F0EA').cylinder(0, 0, 1.6, 7, 13, 8);
    b.color('#3C4145').dome(0, 0, 1.8, 13, 1.6, 8, 2);
  },
  facts: {Lit: 'Jun 1, 1854 — first lighthouse on the US West Coast', Replaced: '1909 (damaged in 1906)', Model: 'Cape Cod-style keeper’s house with lantern; size estimated'},
  sources: [WIKI + 'Alcatraz_Island_Lighthouse']
};
const alcatrazLight1909: Landmark = {
  id: 'alcatraz_lighthouse_1909',
  name: 'Alcatraz Lighthouse',
  kind: 'tower',
  built: [1909.0, 1909.6],
  end: 9999,
  anchor: [-122.422296, 37.826254],
  build: b => {
    b.color('#EFEDE6').frustum(0, 0, 3.4, 2.4, 0, 21, 8, true);
    b.color('#2F3437').cylinder(0, 0, 2, 21, 24, 8);
    b.color('#2F3437').dome(0, 0, 2.2, 24, 2, 8, 2);
  },
  replaces: [circle(0, 0, 8, 8)],
  facts: {Built: '1909, reinforced concrete', Automated: '1963', Height: 'tower 84 ft (26 m); the light is 214 ft (65 m) above the water'},
  sources: [WIKI + 'Alcatraz_Island_Lighthouse']
};
const alcatrazWater: Landmark = {
  id: 'alcatraz_water_tower',
  name: 'Alcatraz Water Tower',
  kind: 'tower',
  built: [1940.3, 1941.3],
  end: 9999,
  anchor: [-122.423935, 37.827573],
  build: b => {
    b.color('#8E8F8C');
    for (const [x, y] of [
      [-5, -5],
      [5, -5],
      [5, 5],
      [-5, 5]
    ])
      b.beam([x * 1.2, y * 1.2, 0], [x, y, 20], 0.9);
    b.color('#E8E4DA').cylinder(0, 0, 6.5, 20, 28, 12);
    b.color('#9E5A44').frustum(0, 0, 6.6, 0.5, 28, 30.5, 12, false);
  },
  replaces: [circle(0, 0, 8, 8)],
  facts: {Built: '1940–41 (commonly cited)', 'Since 1970': '"Peace and Freedom … Indians Welcome" graffiti from the occupation'},
  sources: [WIKI + 'Alcatraz_Island']
};

// =========================================================== Fort Point
const fortPoint: Landmark = {
  id: 'fort_point',
  name: 'Fort Point',
  kind: 'monument',
  built: [1853.5, 1861.0],
  end: 9999,
  anchor: [-122.477092, 37.8106],
  build: b => {
    // OSM outline (relation 5504536) in a frame with +y at 68° (ENE) and +x at 158°
    // (SSE, the landward gorge wall); casemate faces: NNW (−x), ENE (+y), WSW (−y).
    // Audit 2026-11: the gun embrasures were on the landward face.
    b.frame(0, 0, 0, 68, () => {
      const outer: V2[] = [
        [-18.6, -39.6], [-14.3, -39.7], [-6.0, -32.6], [33.0, -45.3], [36.2, -42.5], [21.3, 27.6], [0.9, 34.2], [-1.3, 44.5],
        [-4.8, 46.7], [-12.4, 45.0], [-14.8, 41.5], [-12.7, 31.3], [-22.3, 22.7], [-23.5, 17.9], [-15.1, -22.1], [-23.3, -29.2], [-23.8, -33.8]
      ];
      const inner: V2[] = [
        [-8.2, -10.3], [-14.1, 17.2], [-5.6, 19.1], [-2.7, 17.5], [-0.6, 20.3], [8.1, 22.3], [10.9, 20.6], [21.4, -28.5],
        [18.7, -30.8], [6.1, -26.9], [0.5, -20.4], [0.9, -17.8], [-2.1, -17.4]
      ];
      b.color('#8C4A36').prism(outer, 0, 15, {holes: [inner]});
      b.color('#9A968C').prism(outer, 15, 16, {holes: [inner]});
      b.color('#B7A48C').cap(inner, 0.2);
      // three tiers of gun embrasures on the water faces
      b.color('#5E3224');
      const faces: [V2, V2][] = [
        [[-15.1, -22.1], [-23.5, 17.9]],
        [[-12.7, 31.3], [-22.3, 22.7]],
        [[21.3, 27.6], [0.9, 34.2]],
        [[-6.0, -32.6], [33.0, -45.3]]
      ];
      for (const [p0, p1] of faces) {
        const dx = p1[0] - p0[0];
        const dy = p1[1] - p0[1];
        const L = Math.hypot(dx, dy);
        const brg = (Math.atan2(dx, dy) * 180) / Math.PI;
        // outward normal = to the right of the walking direction when the ring is clockwise; test both, keep the one away from the parade
        const nx = dy / L;
        const ny = -dx / L;
        const mx = (p0[0] + p1[0]) / 2;
        const my = (p0[1] + p1[1]) / 2;
        const out = nx * (mx - 3) + ny * (my + 2) > 0 ? 1 : -1;
        for (let t = 3; t < L - 2; t += 6) {
          const x = p0[0] + (dx * t) / L + out * nx * 0.25;
          const y = p0[1] + (dy * t) / L + out * ny * 0.25;
          b.frame(x, y, 0, brg, () => {
            for (const z of [3, 7.5, 12]) b.box(0, 0, z, 0.5, 1.4, 1.4);
          });
        }
      }
    });
    b.color('#2F3437').cylinder(-14, 14, 1.2, 16, 22, 6);
  },
  replaces: [circle(0, 0, 55, 10)],
  facts: {
    Built: '1853–1861, US Army Corps of Engineers (brick and granite)',
    'Before': 'Spanish Castillo de San Joaquín, 1794–1835',
    'Rooftop lighthouse': '1864–1934',
    'Golden Gate Bridge': 'its Fort Point arch was built over the fort (1933–37)'
  },
  sources: [WIKI + 'Fort_Point,_San_Francisco']
};

// =========================================================== Mission Dolores
const missionAdobe: Landmark = {
  id: 'mission_dolores',
  name: 'Mission San Francisco de Asís (Mission Dolores)',
  kind: 'building',
  built: [1782.5, 1791.5],
  end: 9999,
  // OSM footprint centroid; audit 2026-11: was 6 m east, 17 m wide and on a 90° axis
  anchor: [-122.426799, 37.764182],
  build: b => {
    b.frame(0, 0, 0, 82, () => {
      // facade faces ENE (+y here) onto Dolores St; nave 11.5 × 46 m (OSM)
      b.color('#F1EEE6').box(0, 0, 0, 11.5, 46, 7.5);
      b.color('#A0523A').gable(0, 0, 13.4, 47.4, 7.5, 3.6, true);
      // facade: six engaged columns in two tiers and the bell balcony
      b.color('#E4DFD3');
      for (const x of [-4.6, -2.8, -1, 1, 2.8, 4.6]) b.box(x, 23.3, 0, 0.8, 0.7, 7.8);
      b.color('#F1EEE6').box(0, 23.4, 7.5, 11.5, 0.6, 2.6);
      b.color('#5E4A3A').box(0, 23.9, 5.4, 7, 1.2, 0.4);
    });
  },
  replaces: [rotRect(0, 0, 15, 50, 82)],
  facts: {
    Founded: 'Oct 9, 1776 (temporary structures nearby)',
    'Adobe church': 'built 1782–1791 — the oldest intact building in San Francisco',
    Size: '≈ 46 × 11.5 m (OSM)',
    Model: 'wall and ridge heights estimated from photos (≈ 7.5 / 11 m)'
  },
  sources: [WIKI + 'Mission_San_Francisco_de_As%C3%ADs']
};
// Basilica: cruciform church in a frame with +y at 85° (east, towards Dolores St)
// and +x at 175° (south, towards the adobe); plan from the OSM footprint:
// nave 20.7 m wide, transept 27.7 m, crossing dome, twin-towered front 25 m wide.
// Audit 2026-11: the earlier 33 × 59 m box overlapped the adobe church.
const missionBasilica: Landmark = {
  id: 'mission_dolores_basilica',
  name: 'Mission Dolores Basilica',
  kind: 'building',
  built: [1913.5, 1918.98],
  end: 9999,
  anchor: [-122.427016, 37.76434],
  build: b => {
    const cream = '#E8DCC6';
    const tile = '#B5654A';
    b.frame(0, 0, 0, 85, () => {
      // nave (y 14.5–28.2) and transept/crossing (y −10.9–14.5)
      b.color(cream).box(-3.15, 21.35, 0, 20.7, 13.7, 14);
      b.color(tile).gable(-3.15, 21.35, 21.5, 14.2, 14, 4.5, true);
      b.color(cream).box(-3.25, 1.8, 0, 27.7, 25.4, 14);
      b.color(tile).gable(-3.25, 1.8, 28.5, 25.9, 14, 4.5, false);
      // sanctuary block and the apse to the west, sacristy on the south
      b.color(cream).box(-3.5, -15.95, 0, 27, 10.1, 12);
      b.color(tile).box(-3.5, -15.95, 12, 27.4, 10.5, 1);
      b.color(cream).cylinder(-3.6, -21, 5.9, 0, 11, 10);
      b.color(cream).box(13, -16, 0, 6, 10, 9);
      // crossing dome on a drum (estimated from photos)
      b.color(cream).cylinder(-3.4, 1.8, 8.5, 14, 18, 16);
      b.color(tile).dome(-3.4, 1.8, 8.5, 18, 6, 16, 4);
      b.color('#6FA58E').cylinder(-3.4, 1.8, 1.4, 24, 26, 6);
      // Churrigueresque front and twin bell towers (≈ 28 m, estimated from photo)
      b.color(cream).box(-2.95, 31.55, 0, 24.9, 6.7, 17);
      for (const x of [-12.2, 6.3]) {
        b.color(cream).box(x, 31.5, 17, 6.4, 6.4, 2.5).box(x, 31.5, 19.5, 5.2, 5.2, 5);
        b.color('#6FA58E').dome(x, 31.5, 2.5, 24.5, 3, 8, 2);
        b.color('#C9A43A').cylinder(x, 31.5, 0.2, 27.5, 28.8, 4);
      }
    });
  },
  replaces: [rotRect(-0.3, -3, 36, 62, 85)],
  facts: {
    Cornerstone: '1913',
    Dedicated: 'Christmas 1918; Churrigueresque remodel 1926; basilica since 1952',
    Replaced: 'the 1876 Gothic parish church destroyed in 1906',
    Model: 'plan from OSM; tower, dome and roof heights estimated from photos'
  },
  sources: [WIKI + 'Mission_San_Francisco_de_As%C3%ADs']
};

// =========================================================== Cliff House & Sutro Baths
const CLIFF: V2 = [-122.514044, 37.778557];
const cliff1863: Landmark = {
  id: 'cliff_house_1863',
  name: 'Cliff House (1863)',
  kind: 'building',
  built: [1863.0, 1863.6],
  end: 1894.98,
  anchor: CLIFF,
  build: b => {
    b.frame(0, 0, 0, 155, () => {
      b.color('#E9E2D1').box(0, 0, 0, 14, 30, 7);
      b.color('#7E6F62').gable(0, 0, 15, 31, 7, 3, true);
    });
  },
  facts: {Built: '1863, modest wooden roadhouse', Fate: 'burned Dec 25, 1894', Model: 'size estimated'},
  sources: [WIKI + 'Cliff_House,_San_Francisco']
};
const cliff1896: Landmark = {
  id: 'cliff_house_1896',
  name: 'Cliff House (Sutro’s "Gingerbread Palace", 1896)',
  kind: 'building',
  built: [1895.6, 1896.2],
  end: 1907.68,
  anchor: CLIFF,
  build: b => {
    b.frame(0, 0, 0, 155, () => {
      b.color('#EFE9DC').box(0, 0, 0, 30, 60, 18);
      b.color('#6E6A66').hip(0, 0, 31, 61, 18, 8);
      for (const y of [-26, 26]) {
        b.color('#EFE9DC').cylinder(0, y, 5, 0, 26, 8);
        b.color('#6E6A66').frustum(0, y, 5.4, 0.3, 26, 34, 8, false);
      }
      b.color('#EFE9DC').prism(circle(0, 0, 6, 8), 18, 34);
      b.color('#6E6A66').frustum(0, 0, 6.5, 0.4, 34, 44, 8, false);
    });
  },
  facts: {Built: '1896 by Adolph Sutro — a seven-storey Victorian château', 'Survived 1906': 'but burned Sep 7, 1907', Model: 'massing estimated (~60 m wide, central tower ~40 m)'},
  sources: [WIKI + 'Cliff_House,_San_Francisco']
};
const cliff1909: Landmark = {
  id: 'cliff_house_1909',
  name: 'Cliff House (1909)',
  kind: 'building',
  built: [1908.5, 1909.5],
  end: 9999,
  anchor: CLIFF,
  build: b => {
    // the 1909 block only: south part of today's OSM footprint (frame +y at 335°, +x at 65°);
    // the 2004 Sutro wing to the north is a separate landmark (batch3)
    b.frame(0, 0, 0, 335, () => {
      b.color('#F1EFEA').box(-0.9, -16.9, 0, 22.2, 26.6, 12);
      b.color('#E4E0D6').box(-0.9, -16.9, 12, 21.4, 25.8, 0.8);
      b.color('#F1EFEA').box(7, -33.85, 0, 13.2, 7.3, 4); // south terrace wing
    });
  },
  replaces: [rotRect(0, 0, 36, 75, 155)],
  facts: {
    Built: '1909 (Reid & Reid), neoclassical concrete',
    Restored: '2003–04 toward its 1909 look',
    Restaurant: 'closed Dec 2020',
    Model: 'block from the OSM footprint (audit 2026-11: was a 32 × 71 m box over the cliff edge); height from photo'
  },
  sources: [WIKI + 'Cliff_House,_San_Francisco']
};
const sutroBaths: Landmark = {
  id: 'sutro_baths',
  name: 'Sutro Baths',
  kind: 'building',
  built: [1894.3, 1896.2],
  end: 1966.45,
  anchor: [-122.514124, 37.780156],
  build: b => {
    // audit 2026-11: the hall stood east of the surviving seawall (the anchor
    // lies on it), long axis ≈ N–S along the cove — not on a 160° axis
    // straddling the rocks. Ruins traced on the orthophoto.
    b.frame(38, 0, 0, -2, () => {
      b.color('#D8D4CA').box(0, 0, 0, 75, 150, 4);
      // parallel gabled glass roofs over the pools
      for (let x = -30; x <= 30; x += 15) {
        b.color('#F2F1EC').box(x, 0, 4, 1.2, 150, 9);
        if (x < 30) b.color('#B9CBD4').gable(x + 7.5, 0, 15, 150, 13, 5, true);
      }
    });
    // Greek-temple entrance pavilion up the slope on Point Lobos Ave (position estimated)
    b.frame(90, -70, 0, 270, () => {
      b.color('#EDE9DF').box(0, 0, 0, 22, 14, 10);
      b.color('#B5B0A5').gable(0, 0, 23, 15, 10, 3, false);
    });
  },
  facts: {
    Opened: 'Mar 14, 1896 — the world’s largest indoor swimming establishment (7 pools)',
    Fate: 'burned June 1966; ruins remain',
    Model: 'hall ≈ 152 × 77 m (499.5 × 254 ft, commonly cited) placed on the ruins; roof form from photos; entrance position estimated'
  },
  sources: [WIKI + 'Sutro_Baths']
};

// =========================================================== Embarcadero Freeway (1959–1991)
const EMB: V2[] = [
  [-122.3935, 37.7885],
  [-122.3918, 37.7899],
  [-122.39065, 37.79145],
  [-122.3911, 37.79244],
  [-122.3925, 37.79377],
  [-122.39326, 37.79423],
  [-122.39541, 37.79668],
  [-122.39767, 37.79923]
];
const embarcaderoFreeway: Landmark = {
  id: 'embarcadero_freeway',
  name: 'Embarcadero Freeway (SR 480)',
  kind: 'bridge',
  built: [1957.5, 1959.1],
  end: 1991.3,
  anchor: EMB[3],
  build: b => {
    const pts = EMB.map(p => lngLatToLocal(EMB[3], p));
    const grey = '#B9B7B0';
    for (let i = 0; i < pts.length - 1; i++) {
      const p = pts[i];
      const q = pts[i + 1];
      deck(b, [p[0], p[1], 10], [q[0], q[1], 10], 20, 1.6, grey, '#6A6863');
      deck(b, [p[0], p[1], 19], [q[0], q[1], 19], 20, 1.6, grey, '#6A6863');
      const L = Math.hypot(q[0] - p[0], q[1] - p[1]);
      for (let s = 0; s < L; s += 30) {
        const t = s / L;
        const x = p[0] + (q[0] - p[0]) * t;
        const y = p[1] + (q[1] - p[1]) * t;
        b.color(grey).box(x, y, 0, 2.2, 2.2, 19);
      }
    }
  },
  facts: {
    Opened: 'Feb 5, 1959 (double-deck viaduct)',
    Closed: 'after the Oct 17, 1989 Loma Prieta earthquake',
    Demolished: '1991 — reopening the waterfront and the Ferry Building',
    Model: 'APPROXIMATE route along the Embarcadero centerline; deck heights estimated'
  },
  sources: [WIKI + 'California_State_Route_480', 'https://www.aaroads.com/guides/i-480-ca']
};

// =========================================================== Golden Gate Park buildings
const conservatory: Landmark = {
  id: 'conservatory_of_flowers',
  name: 'Conservatory of Flowers',
  kind: 'building',
  built: [1878.5, 1879.3],
  end: 9999,
  anchor: [-122.460184, 37.77259],
  build: b => {
    // plan from the OSM footprint in a −6° frame centred on the dome (audit 2026-11):
    // the end pavilions are N–S wings 11.4 × 24.3 m projecting south, not small boxes
    const white = '#F6F5F0';
    b.frame(-3.87, 2.41, 0, -6, () => {
      b.color(white).prism(circle(0, 0, 9, 12), 0, 7);
      b.color('#E9EEF0').dome(0, 0, 9, 7, 11, 16, 5);
      b.color(white).cylinder(0, 0, 1.8, 18, 21, 8);
      for (const sx of [-1, 1]) {
        // barrel-vaulted wing
        b.color(white).box(sx * 17.4, 0.2, 0, 17, 11, 5);
        const n = 8;
        for (let i = 0; i < n; i++) {
          const a0 = (i / n) * Math.PI;
          const a1 = ((i + 1) / n) * Math.PI;
          const y0 = 0.2 - Math.cos(a0) * 5.5;
          const y1 = 0.2 - Math.cos(a1) * 5.5;
          const z0 = 5 + Math.sin(a0) * 4;
          const z1 = 5 + Math.sin(a1) * 4;
          b.color('#E6ECEE').quad([sx * 8.9, y0, z0], [sx * 25.9, y0, z0], [sx * 25.9, y1, z1], [sx * 8.9, y1, z1]);
        }
        // end pavilion
        b.color(white).box(sx * 31.4, -3.55, 0, 11.4, 24.3, 7);
        b.color('#E6ECEE').hip(sx * 31.4, -3.55, 11.4, 24.3, 7, 4.5);
      }
      // entrance vestibule on the south side of the dome
      b.color(white).box(0.2, -12.8, 0, 7.8, 8.6, 6);
      b.color('#E6ECEE').gable(0.2, -12.8, 8.2, 9, 6, 2.5, true);
    });
  },
  replaces: [rect(0, 0, 76, 36)],
  facts: {
    Opened: 'Apr 1879 — oldest building in Golden Gate Park',
    Dome: 'burned 1883 and rebuilt taller',
    Restored: 'reopened 2003',
    Size: '74 m long (OSM), dome ≈ 18 m',
    Model: 'plan from OSM; vault and roof heights estimated from photos'
  },
  sources: [WIKI + 'Conservatory_of_Flowers']
};

function windmill(b: MeshBuilder, galleryColor: string) {
  b.color('#9C8F80').prism(circle(0, 0, 5.5, 8), 0, 7);
  b.color(galleryColor).prism(circle(0, 0, 8, 8), 6, 6.8, {holes: [circle(0, 0, 5.3, 8)]});
  b.color('#8D8A82').frustum(0, 0, 5, 3.2, 7, 19, 8, false);
  b.color('#7C776E').dome(0, 0, 3.6, 19, 3.5, 8, 3);
  // four lattice sails, ~30 m span, on the west (ocean) face
  b.color('#E8E2D2');
  const hub: V3 = [0, -4.2, 19.5];
  for (let k = 0; k < 4; k++) {
    const a = (k / 4) * Math.PI * 2 + 0.35;
    const tip: V3 = [Math.cos(a) * 15, -4.4, 19.5 + Math.sin(a) * 15];
    b.beam(hub, tip, 0.5);
    const mid: V3 = [Math.cos(a) * 8.5, -4.4, 19.5 + Math.sin(a) * 8.5];
    const off: V3 = [Math.cos(a + Math.PI / 2) * 1.2, 0, Math.sin(a + Math.PI / 2) * 1.2];
    b.quad([mid[0] - off[0] * 0, mid[1], mid[2]], tip, [tip[0] + off[0], tip[1], tip[2] + off[2]], [mid[0] + off[0], mid[1], mid[2] + off[2]]);
  }
}
const dutchWindmill: Landmark = {
  id: 'dutch_windmill',
  name: 'Dutch Windmill (Golden Gate Park)',
  kind: 'building',
  built: [1902.5, 1903.5],
  end: 9999,
  anchor: [-122.509406, 37.770441], // OSM footprint centroid (audit 2026-11: was 32 m north)
  build: b => b.frame(0, 0, 0, 90, () => windmill(b, '#7A5A44')),
  replaces: [circle(0, 0, 10, 8)],
  facts: {Completed: '1903 — pumped groundwater to irrigate the park', Restored: '1981', Model: 'height estimated from photos (~22 m to cap, ~30 m sail tip)'},
  sources: [WIKI + 'Dutch_Windmill_(Golden_Gate_Park)']
};
const murphyWindmill: Landmark = {
  id: 'murphy_windmill',
  name: 'Murphy Windmill',
  kind: 'building',
  built: [1907.5, 1908.5],
  end: 9999,
  anchor: [-122.508711, 37.765002],
  build: b => b.frame(0, 0, 0, 90, () => windmill(b, '#8C4F3A')),
  replaces: [circle(0, 0, 12, 8)],
  facts: {Completed: '1908', Restored: '2002–2012', Model: 'height estimated from photos'},
  sources: [WIKI + 'Murphy_Windmill']
};
const templeOfMusic: Landmark = {
  id: 'spreckels_temple_of_music',
  name: 'Spreckels Temple of Music',
  kind: 'monument',
  built: [1899.3, 1900.69],
  end: 9999,
  anchor: [-122.4686, 37.769872],
  build: b => {
    // faces NE (48°) across the Music Concourse; +y = toward the audience. Plan from
    // the OSM footprint: shell block 18 m wide (x −9…9, y −11.6…8.5), colonnade
    // wings to ±27 m. Audit 2026-11: the earlier frame (228°) faced it backwards.
    b.frame(0, 0, 0, 48, () =>
      b.frame(2.25, 0, 0, 0, () => {
        b.color('#D9CDB4').box(0, -6.3, 0, 18, 10.6, 21);
        b.color('#CBBE9F');
        b.loft([circle(0, -1, 8.6, 10).filter(([, y]) => y >= -1).concat([[-8.6, -1]]), circle(0, -1, 2, 10).filter(([, y]) => y >= -1).concat([[-2, -1]])], [4, 19], {top: false});
        for (const sx of [-1, 1]) {
          b.color('#D9CDB4').box(sx * 18.2, 2.3, 0, 18.6, 6.6, 9);
          for (let x = 10.5; x <= 27; x += 3.3) b.cylinder(sx * x, 6, 0.5, 0, 8, 6);
        }
      })
    );
  },
  replaces: [rect(0, 0, 50, 30)],
  facts: {Dedicated: 'Sep 9, 1900 (Claus Spreckels)', Shell: '21 m (70 ft), Colusa sandstone'},
  sources: [WIKI + 'Spreckels_Temple_of_Music']
};
const deYoung2005: Landmark = {
  id: 'de_young_museum_2005',
  name: 'de Young Museum',
  kind: 'building',
  built: [2002.5, 2005.79],
  end: 9999,
  anchor: [-122.468612, 37.77155],
  build: b => {
    const copper = '#6E4B33';
    b.frame(0, 0, 0, 48, () => {
      for (const [x, skew] of [
        [-22, -2],
        [0, 0],
        [22, 2]
      ] as [number, number][])
        b.frame(x, 0, 0, skew, () => b.color(copper).box(0, 0, 0, 20, 140, 13));
      b.color('#5F4230').box(0, 0, 13, 76, 154, 1.2);
      // Hamon tower over the NW side of the NE end (OSM, audit 2026-11: was on the SE side).
      // Floor plates ≈ 30 × 10 m, long axis across the museum (138°) at the roof,
      // turning clockwise ~1.3°/m (OSM plates at 18/23/28 m) to ≈ 180° at the top.
      const tw: V2[][] = [];
      const zs: number[] = [];
      for (let k = 0; k <= 4; k++) {
        const a = ((-(k / 4) * 42) * Math.PI) / 180;
        const r = rect(0, 0, 30, 10).map(([x, y]) => [x * Math.cos(a) - y * Math.sin(a) - 23, x * Math.sin(a) + y * Math.cos(a) + 54] as V2);
        tw.push(r);
        zs.push(13 + (k / 4) * 30.9);
      }
      b.color('#704D36').loft(tw, zs, {top: true});
      b.color('#2E3438').loft([tw[4], tw[4]], [41, 41.6], {top: false}); // glazed observation floor band
    });
  },
  replaces: [rotRect(0, 0, 80, 160, 48)],
  facts: {
    Opened: 'Oct 15, 2005 (Herzog & de Meuron)',
    'Hamon tower': '43.9 m (144 ft), twisting to align with the street grid',
    Cladding: 'perforated copper',
    Model: 'tower position and lower floor plates from OSM; total twist (≈ 42°) extrapolated'
  },
  sources: [WIKI + 'De_Young_Museum']
};
const deYoung1919: Landmark = {
  id: 'de_young_museum_1919',
  name: 'de Young Museum (Mullgardt building)',
  kind: 'building',
  built: [1917.5, 1919.5],
  end: 2001.5,
  anchor: [-122.468612, 37.77155],
  build: b => {
    b.frame(0, 0, 0, 48, () => {
      b.color('#D9CBA9').box(0, 0, 0, 60, 120, 14).box(0, 40, 0, 14, 14, 30);
      b.color('#B98C5C').pyramid(rect(0, 40, 14, 14), 30, [0, 40, 36]);
    });
  },
  facts: {Built: '1919–1921 (Louis Christian Mullgardt), Spanish-Plateresque, cast stone', Fate: 'damaged 1989; demolished c. 2001', Model: 'massing estimated'},
  sources: [WIKI + 'De_Young_Museum']
};
const calAcademy: Landmark = {
  id: 'california_academy_of_sciences_2008',
  name: 'California Academy of Sciences',
  kind: 'building',
  built: [2005.7, 2008.74],
  end: 9999,
  anchor: [-122.466126, 37.769853],
  build: b => {
    b.frame(0, 0, 0, 48, () => {
      b.color('#A9C1C9').box(0, 0, 0, 100, 158, 11, {top: false});
      b.color('#F2F2EE').box(0, 0, 11, 103, 161, 0.6, {top: false});
      b.color('#7FA35A').cap(rect(0, 0, 103, 161), 11.6);
      // living roof hills: planetarium (W) and rainforest (E) domes + smaller hills
      b.color('#7FA35A').dome(0, -38, 15, 11.6, 10, 16, 4).dome(0, 38, 15, 11.6, 10, 16, 4);
      for (const [x, y, r] of [
        [-32, -60, 9],
        [32, -60, 9],
        [-32, 60, 9],
        [32, 60, 9],
        [-36, 0, 8]
      ])
        b.dome(x, y, r, 11.6, 5, 12, 3);
      b.color('#C9DDE3').cylinder(0, 0, 6, 11.6, 12.2, 12); // piazza skylight
    });
  },
  replaces: [rotRect(0, 0, 108, 165, 48)],
  facts: {Opened: 'Sep 27, 2008 (Renzo Piano)', Roof: '2.5-acre living roof, ~1.7 million plants', Model: 'roof-hill heights estimated'},
  sources: [WIKI + 'California_Academy_of_Sciences']
};

export const CITY_LANDMARKS: Landmark[] = [
  bayBridgeWestSpan,
  ...bayBridgeEastOld,
  sasSpan,
  skyway,
  ferryBuilding,
  cityHall,
  oldCityHall,
  oldCityHallDome,
  oldCityHallRuin,
  coitTower,
  pofa1915,
  pofa1967,
  sutroTower,
  alcatrazCellhouse,
  alcatrazLight1854,
  alcatrazLight1909,
  alcatrazWater,
  fortPoint,
  missionAdobe,
  missionBasilica,
  cliff1863,
  cliff1896,
  cliff1909,
  sutroBaths,
  embarcaderoFreeway,
  conservatory,
  dutchWindmill,
  murphyWindmill,
  templeOfMusic,
  deYoung1919,
  deYoung2005,
  calAcademy
];
