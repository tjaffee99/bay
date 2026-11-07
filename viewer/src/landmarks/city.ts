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
  facts: {
    Construction: 'Jul 9, 1933 – Nov 12, 1936',
    Form: 'two suspension bridges in series sharing a centre anchorage',
    'Main spans': '2 × 704 m (2,310 ft)',
    Towers: '160 m above water',
    Model: 'tower and anchorage positions from OSM; deck height estimated'
  },
  sources: [WIKI + 'San_Francisco%E2%80%93Oakland_Bay_Bridge']
};

// --- original east span (1936–2013), demolished in stages 2013–2017
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
  'Main span': '427 m (1,400 ft) double balanced cantilever, then five 155 m through-trusses and a causeway',
  '1989': 'a 15 m section of upper deck collapsed in the Loma Prieta quake',
  Replaced: 'closed Aug 28, 2013; demolished 2013–2017',
  Model: 'APPROXIMATE alignment (~100 m north of today’s skyway); truss heights estimated'
};
const eastSrc = [WIKI + 'Eastern_span_replacement_of_the_San_Francisco%E2%80%93Oakland_Bay_Bridge', 'https://www.cbsnews.com/sanfrancisco/news/demolition-of-old-bay-bridge-to-take-years'];
const bayBridgeEastOld: Landmark[] = [
  {id: 'bay_bridge_east_1936_cantilever', name: 'Bay Bridge east span (1936) — cantilever', kind: 'bridge', built: [1933.52, 1936.87], end: 2014.6, anchor: YBI_EAST, build: eastOldPart('cantilever'), facts: eastFacts, sources: eastSrc},
  {id: 'bay_bridge_east_1936_trusses', name: 'Bay Bridge east span (1936) — truss spans', kind: 'bridge', built: [1933.52, 1936.87], end: 2015.9, anchor: YBI_EAST, build: eastOldPart('trusses'), facts: eastFacts, sources: eastSrc},
  {id: 'bay_bridge_east_1936_causeway', name: 'Bay Bridge east span (1936) — causeway', kind: 'bridge', built: [1933.52, 1936.87], end: 2016.8, anchor: YBI_EAST, build: eastOldPart('causeway'), facts: eastFacts, sources: eastSrc}
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
  replaces: [],
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
const ferryBuilding: Landmark = {
  id: 'ferry_building',
  name: 'Ferry Building',
  kind: 'building',
  built: [1896.0, 1898.53],
  end: 9999,
  anchor: [-122.393383, 37.795538],
  build: b => {
    const stone = '#D8D2C4';
    b.frame(0, 0, 0, 144, () => {
      // local +y along the Embarcadero (144°), +x toward the bay (NE side)
      b.color(stone).box(0, 0, 0, 40, 201, 15);
      b.color('#8E9396').gable(0, 0, 41, 202, 15, 6, true);
      b.color('#B9BDBF').box(0, 0, 19, 8, 190, 2.5); // clerestory
      // arcade on the Embarcadero (SW) side
      b.color('#C9C2B2');
      for (let y = -96; y <= 96; y += 8) b.box(-20.6, y, 0, 1.2, 2.2, 6.5);
      b.color(stone).box(-20.6, 0, 6.5, 1.4, 200, 1.4);
      // ferry sheds / piers behind
      b.color('#B5B3AC').box(28, -60, 0, 16, 70, 8).box(28, 60, 0, 16, 70, 8);
      // Giralda-style clock tower on the Market St axis
      b.color(stone).box(-6, 0, 0, 13, 13, 52);
      b.color('#F4F2EC').box(-6, 0, 44, 13.6, 13.6, 7); // clock stage
      b.color(stone).box(-6, 0, 51, 10.5, 10.5, 9).box(-6, 0, 60, 8, 8, 6).box(-6, 0, 66, 5.5, 5.5, 4);
      b.color('#9BA1A3').dome(-6, 0, 2.6, 70, 5, 10, 3);
    });
  },
  replaces: [rotRect(0, 0, 60, 205, 144)],
  facts: {Opened: 'Jul 13, 1898 (architect A. Page Brown)', 'Clock tower': '75 m (245 ft), after the Giralda of Seville', Survived: '1906 earthquake and fire', Restored: '2002–2003'},
  sources: [WIKI + 'San_Francisco_Ferry_Building']
};

// =========================================================== City Hall
const cityHall: Landmark = {
  id: 'city_hall_1915',
  name: 'San Francisco City Hall',
  kind: 'building',
  built: [1913.26, 1915.95],
  end: 9999,
  anchor: [-122.419284, 37.779322],
  build: b => {
    const granite = '#DDD9CF';
    // 119 m (E–W) × 83 m (N–S) block, two light courts
    const outer = rect(0, 0, 119, 83);
    const courts = [rect(-30, 0, 30, 45), rect(30, 0, 30, 45)];
    b.color(granite).prism(outer, 0, 30, {holes: courts});
    b.color('#C9C4B8').box(0, 0, 30, 121, 85, 1.2, {top: false}).cap(outer, 31.2, courts);
    // Doric colonnaded centre pavilions on Polk (E) and Van Ness (W)
    for (const sx of [-1, 1]) {
      b.color(granite).box(sx * 61, 0, 0, 4, 40, 27);
      b.color('#CFCAC0');
      for (let y = -16; y <= 16; y += 4) b.cylinder(sx * 64, y, 0.9, 4, 24, 8);
      b.color(granite).box(sx * 64, 0, 24, 3, 38, 4);
    }
    // rotunda: colonnaded drum, ribbed dome, lantern (dome to 93.7 m)
    b.color(granite).cylinder(0, 0, 17, 31, 46, 24);
    b.color('#CFCAC0');
    for (let i = 0; i < 24; i++) {
      const a = (i / 24) * Math.PI * 2;
      b.cylinder(Math.cos(a) * 17.6, Math.sin(a) * 17.6, 0.7, 34, 46, 6);
    }
    b.color(granite).cylinder(0, 0, 18.2, 46, 49, 24);
    b.color('#6C7377').dome(0, 0, 15.5, 49, 25, 24, 6);
    b.color('#C9A43A');
    for (let i = 0; i < 12; i++) {
      const a = (i / 12) * Math.PI * 2;
      b.beam([Math.cos(a) * 15.5, Math.sin(a) * 15.5, 49], [Math.cos(a) * 3, Math.sin(a) * 3, 73.5], 0.6);
    }
    b.color('#C9C4B8').cylinder(0, 0, 3.4, 73, 85, 10);
    b.color('#C9A43A').dome(0, 0, 3.6, 85, 4, 10, 3).cylinder(0, 0, 0.5, 89, 93.7, 6);
  },
  replaces: [rect(0, 0, 135, 95)],
  facts: {
    Construction: 'Apr 1913 – Dec 1915 (in time for the PPIE)',
    Architect: 'Bakewell & Brown (Arthur Brown Jr.)',
    Dome: '93.7 m (307.5 ft); gilding restored 1999',
    Footprint: '119 × 83 m'
  },
  sources: [WIKI + 'San_Francisco_City_Hall']
};

const oldCityHall: Landmark = {
  id: 'city_hall_1899',
  name: 'Old San Francisco City Hall',
  kind: 'building',
  built: [1871.0, 1899.0],
  end: 1906.3,
  anchor: [-122.415, 37.7795],
  build: b => {
    const stone = '#D6CFBF';
    // long multi-wing classical building on a triangular block (massing approximate)
    b.color(stone).box(0, 0, 0, 160, 30, 22).box(-55, 35, 0, 30, 70, 22).box(55, 30, 0, 30, 60, 22);
    b.color('#8C8F92').hip(0, 0, 160, 30, 22, 4);
    // domed tower at the Larkin/McAllister side, dome to ≈ 102 m
    b.color(stone).cylinder(-40, -5, 11, 22, 62, 20);
    b.color('#7E8487').dome(-40, -5, 11, 62, 22, 20, 5);
    b.color(stone).cylinder(-40, -5, 2.5, 84, 98, 8);
    b.color('#B89B4A').dome(-40, -5, 2.6, 98, 4, 8, 2);
  },
  facts: {
    Built: '1871/72 – 1899 (27 years, seven architects)',
    Destroyed: 'Apr 18, 1906 earthquake and fire; the bare dome skeleton stood over the ruins',
    Dome: '≈ 102 m (335 ft)',
    Model: 'LOW CONFIDENCE: massing and exact position approximate'
  },
  sources: [WIKI + 'San_Francisco_City_Hall', 'https://calisphere.org/item/ark:/13030/hb096nb16b/']
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
    b.color(conc).prism(roundedRect(0, 0, 22, 22, 3, 2), 0, 8);
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
    Height: '64 m (210 ft) — stands on Telegraph Hill (≈ 89 m), not modelled: the map is flat',
    Murals: 'WPA / PWAP, 1934'
  },
  sources: [WIKI + 'Coit_Tower']
};

// =========================================================== Palace of Fine Arts
function palaceOfFineArts(stone: string, dome: string) {
  return (b: MeshBuilder) => {
    // octagonal open rotunda, 49 m
    const R = 17;
    b.color(stone);
    for (let i = 0; i < 8; i++) {
      const a = (i / 8) * Math.PI * 2 + Math.PI / 8;
      b.box(Math.cos(a) * R, Math.sin(a) * R, 0, 4, 4, 24);
    }
    b.prism(circle(0, 0, R + 2.2, 8), 24, 30, {holes: [circle(0, 0, R - 2.2, 8)]});
    b.color(dome).loft([circle(0, 0, R + 1, 8), circle(0, 0, R - 2, 8), circle(0, 0, 10, 8), circle(0, 0, 2, 8)], [30, 38, 45, 49], {top: true});
    // curving peristyle colonnades embracing the lagoon (arc centred east of the rotunda)
    const cx = 75;
    const rr = 75;
    for (const sgn of [-1, 1]) {
      for (let k = 1; k <= 14; k++) {
        const t = (sgn * (k * 4.2) * Math.PI) / 180;
        const x = cx - Math.cos(t) * rr;
        const y = Math.sin(t) * rr;
        if (k % 4 === 0) b.color(stone).box(x, y, 0, 4, 4, 17).box(x, y, 17, 5, 5, 1.5);
        else b.color(stone).cylinder(x, y, 0.8, 0, 12, 8);
      }
      const arc: V3[] = [];
      const arcO: V3[] = [];
      for (let k = 0; k <= 14; k++) {
        const t = (sgn * (k * 4.2) * Math.PI) / 180;
        arc.push([cx - Math.cos(t) * (rr - 1.5), Math.sin(t) * (rr - 1.5), 12]);
        arcO.push([cx - Math.cos(t) * (rr + 1.5), Math.sin(t) * (rr + 1.5), 12]);
      }
      b.color(stone).ribbon(arc, arcO);
    }
    // long curved windowless exhibition hall behind (west)
    const hallIn: V2[] = [];
    const hallOut: V2[] = [];
    for (let k = 0; k <= 20; k++) {
      const a = ((200 + (140 * k) / 20) * Math.PI) / 180;
      hallIn.push([Math.sin(a) * 60, Math.cos(a) * 60]);
      hallOut.push([Math.sin(a) * 88, Math.cos(a) * 88]);
    }
    b.color(stone).prism([...hallIn, ...hallOut.slice().reverse()], 0, 20);
    // lagoon edge (water is the ground plane colour here: a low rim only)
    b.color('#9FC2D0').cap(roundedRect(85, 0, 70, 140, 30, 6), 0.3);
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
    Model: 'hall arc length and peristyle radius estimated'
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
  replaces: [rect(-20, 0, 190, 200)],
  facts: {Rebuilt: '1964–67 in steel and concrete to the 1915 design', Exploratorium: '1969–2013', Rotunda: '49 m (162 ft)'}
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
      const a = (k / 3) * Math.PI * 2 + Math.PI / 2;
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
    Height: '297.8 m (977 ft) — on a 254 m hill (not modelled: the map is flat)',
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
    const p = lngLatToLocal(ALC, [-122.423015, 37.826659]);
    b.frame(p[0], p[1], 0, 136, () => {
      b.color('#CFC8B8').box(0, 0, 0, 49, 65, 15);
      b.color('#9C968A').box(0, 0, 15, 49, 65, 1, {top: true});
      b.color('#B9B2A3').box(0, -38, 0, 15, 35, 12); // administration block
    });
    const d = lngLatToLocal(ALC, [-122.423454, 37.82703]);
    b.frame(d[0], d[1], 0, 136, () => b.color('#CFC8B8').box(0, 0, 0, 20, 52, 9));
  },
  replaces: [circle(lngLatToLocal(ALC, [-122.423015, 37.826659])[0], lngLatToLocal(ALC, [-122.423015, 37.826659])[1], 45, 12)],
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
  facts: {Built: '1909, reinforced concrete', Automated: '1963', Height: '≈ 26 m (OSM); 95 ft above mean sea level'},
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
    b.frame(0, 0, 0, 68, () => {
      const outer: V2[] = [
        [-30, -46],
        [30, -46],
        [30, 40],
        [0, 48],
        [-30, 40]
      ];
      const inner: V2[] = [
        [-18, -30],
        [18, -30],
        [18, 30],
        [-18, 30]
      ];
      b.color('#8C4A36').prism(outer, 0, 15, {holes: [inner]});
      b.color('#9A968C').prism(outer, 15, 16, {holes: [inner]});
      b.color('#B7A48C').cap(inner, 0.2);
      // gun embrasure tiers on the bay faces
      b.color('#5E3224');
      for (const z of [3, 7.5, 12]) for (let y = -40; y <= 34; y += 6) b.box(30.2, y, z, 0.4, 1.2, 1.4);
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
  anchor: [-122.426736, 37.764151],
  build: b => {
    b.frame(0, 0, 0, 90, () => {
      // facade faces east (+y here) onto Dolores St
      b.color('#F1EEE6').box(0, 0, 0, 17, 46, 9);
      b.color('#A0523A').gable(0, 0, 18, 47, 9, 3.2, true);
      // facade: six engaged columns in two tiers and a bell balcony
      b.color('#E4DFD3');
      for (const x of [-6, -3.5, -1.2, 1.2, 3.5, 6]) b.box(x, 23.3, 0, 0.8, 0.7, 10.5);
      b.color('#F1EEE6').box(0, 23.4, 10, 17, 0.6, 2.4);
      b.color('#5E4A3A').box(0, 23.9, 6, 7, 1.2, 0.4);
    });
  },
  replaces: [rotRect(0, 0, 20, 50, 90)],
  facts: {
    Founded: 'Oct 9, 1776 (temporary structures nearby)',
    'Adobe church': 'built 1782–1791 — the oldest intact building in San Francisco',
    Size: '≈ 46 × 17 m'
  },
  sources: [WIKI + 'Mission_San_Francisco_de_As%C3%ADs']
};
const missionBasilica: Landmark = {
  id: 'mission_dolores_basilica',
  name: 'Mission Dolores Basilica',
  kind: 'building',
  built: [1913.5, 1918.98],
  end: 9999,
  anchor: [-122.427016, 37.76434],
  build: b => {
    b.frame(0, 0, 0, 90, () => {
      b.color('#E8DCC6').box(0, 0, 0, 33, 59, 14);
      b.color('#B5654A').gable(0, 0, 34, 60, 14, 5, true);
      for (const x of [-12, 12]) {
        b.color('#E8DCC6').box(x, 26, 0, 7, 7, 22);
        b.color('#E8DCC6').box(x, 26, 22, 5, 5, 4);
        b.color('#B5654A').dome(x, 26, 2.8, 26, 3, 8, 2);
      }
    });
  },
  replaces: [rotRect(0, 0, 36, 62, 90)],
  facts: {Cornerstone: '1913', Dedicated: 'Christmas 1918; Churrigueresque remodel 1926; basilica since 1952', Replaced: 'the 1876 Gothic parish church destroyed in 1906'},
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
    b.frame(0, 0, 0, 155, () => {
      b.color('#F1EFEA').box(0, 0, 0, 32, 71, 10);
      b.color('#DCD8CF').box(-4, -10, 10, 22, 30, 3);
    });
  },
  replaces: [rotRect(0, 0, 36, 75, 155)],
  facts: {Built: '1909 (Reid & Reid), neoclassical concrete', Restored: '2003–04 toward its 1909 look', Restaurant: 'closed Dec 2020'},
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
    b.frame(0, 0, 0, 160, () => {
      b.color('#D8D4CA').box(0, 0, 0, 75, 150, 4);
      // parallel gabled glass roofs over the pools
      for (let x = -30; x <= 30; x += 15) {
        b.color('#F2F1EC').box(x, 0, 4, 1.2, 150, 9);
        b.color('#B9CBD4').gable(x + 7.5, 0, 15, 150, 13, 5, true);
      }
      // Greek-temple entrance pavilion up the slope
      b.color('#EDE9DF').box(0, 92, 0, 22, 14, 10);
      b.color('#B5B0A5').gable(0, 92, 23, 15, 10, 3, false);
    });
  },
  facts: {Opened: 'Mar 14, 1896 — the world’s largest indoor swimming establishment (7 pools)', Fate: 'burned June 1966; ruins remain', Model: 'glass-hall size estimated (~150 × 75 m)'},
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
    const white = '#F6F5F0';
    // central domed pavilion + two barrel-vault wings ending in pavilions, 73 m long
    b.color(white).prism(circle(0, 0, 9, 12), 0, 7);
    b.color('#E9EEF0').dome(0, 0, 9, 7, 11, 16, 5);
    b.color(white).cylinder(0, 0, 1.8, 18, 21, 8);
    for (const sx of [-1, 1]) {
      b.color(white).box(sx * 20, 0, 0, 22, 12, 5);
      const n = 8;
      for (let i = 0; i < n; i++) {
        const a0 = (i / n) * Math.PI;
        const a1 = ((i + 1) / n) * Math.PI;
        const y0 = -Math.cos(a0) * 6;
        const y1 = -Math.cos(a1) * 6;
        const z0 = 5 + Math.sin(a0) * 4;
        const z1 = 5 + Math.sin(a1) * 4;
        b.color('#E6ECEE').quad([sx * 9, y0, z0], [sx * 31, y0, z0], [sx * 31, y1, z1], [sx * 9, y1, z1]);
      }
      b.color(white).box(sx * 34, 0, 0, 8, 14, 8);
      b.color('#E6ECEE').pyramid(rect(sx * 34, 0, 8, 14), 8, [sx * 34, 0, 11]);
    }
  },
  replaces: [rect(0, 0, 76, 36)],
  facts: {Opened: 'Apr 1879 — oldest building in Golden Gate Park', 'Dome': 'burned 1883 and rebuilt taller', Restored: 'reopened 2003', Size: '73 m long, dome ≈ 18 m'},
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
  anchor: [-122.509403, 37.770732],
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
    b.frame(0, 0, 0, 228, () => {
      // faces NE across the concourse; +y = toward the audience
      b.color('#D9CDB4').box(0, -6, 0, 26, 10, 21);
      b.color('#CBBE9F');
      b.loft([circle(0, -1, 9, 10).filter(([, y]) => y >= -1).concat([[-9, -1]]), circle(0, -1, 2, 10).filter(([, y]) => y >= -1).concat([[-2, -1]])], [4, 19], {top: false});
      for (const sx of [-1, 1]) {
        b.color('#D9CDB4').box(sx * 20, -4, 0, 14, 6, 9);
        for (let x = 14; x <= 26; x += 3) b.cylinder(sx * x, 0, 0.5, 0, 8, 6);
      }
    });
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
      // Hamon tower: twists as it rises to 43.9 m
      const tw: V2[][] = [];
      const zs: number[] = [];
      for (let k = 0; k <= 4; k++) {
        const a = ((k / 4) * 18 * Math.PI) / 180;
        const r = rect(0, 0, 16, 26).map(([x, y]) => [x * Math.cos(a) - y * Math.sin(a) + 26, x * Math.sin(a) + y * Math.cos(a) + 62] as V2);
        tw.push(r);
        zs.push(14 + (k / 4) * 29.9);
      }
      b.color('#704D36').loft(tw, zs, {top: true});
    });
  },
  replaces: [rotRect(0, 0, 80, 160, 48)],
  facts: {Opened: 'Oct 15, 2005 (Herzog & de Meuron)', 'Hamon tower': '43.9 m (144 ft), twisting to align with the street grid', Cladding: 'perforated copper', Model: 'tower twist angle estimated'},
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
