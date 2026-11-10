/**
 * North Bay reconstructions (Sonoma, Napa and Solano counties) —
 * data/research/landmarks_northbay.md.
 *
 * Buildings: footprints are the OpenStreetMap outlines of the standing buildings (via
 * Overture 2026-10-21.0, © OpenStreetMap contributors, ODbL), each model in a frame
 * aligned with the building (`b.frame(cx, cy, 0, bearing)`: local +y at `bearing`,
 * +x at `bearing + 90°`) around an anchor inside it. Documented dimensions come from
 * the National Register / National Historic Landmark nominations (NPGallery), HAER
 * CA-297 (Carquinez Bridge), Engineering News-Record 1931 (Martinez–Benicia railroad
 * bridge) and Wikipedia, as named in each model's facts; heights that no source gives
 * are scaled from the reference photographs listed in the research note and say so
 * ("Model: …"). Bridges are modelled from sea level along the real Overture / OSM
 * alignments; the Montezuma Hills wind turbines stand at their US Wind Turbine
 * Database positions with their recorded hub heights and rotor diameters.
 */
import {earcut} from '@math.gl/polygon';
import {MeshBuilder, circle, lngLatToLocal, localToLngLat, parabola, rect, type V2, type V3} from './kit';
import type {Landmark} from './types';
import {elevationAt} from '../layers/elevation';

const WIKI = 'https://en.wikipedia.org/wiki/';
/** National Register nomination text (NPGallery) by reference number. */
const NRHP = (ref: string, nhl = false) => `https://npgallery.nps.gov/NRHP/GetAsset/${nhl ? 'NHLS' : 'NRHP'}/${ref}_text`;
const OSM_NOTE = 'footprint from OpenStreetMap (© OSM contributors, ODbL)';
const FT = 0.3048;
const CONC = '#C4C0B6';

// ------------------------------------------------------------------ helpers

/** Regular n-gon ring (first vertex at angle `rot`, radians). */
function ngon(cx: number, cy: number, r: number, n: number, rot = Math.PI / n): V2[] {
  const out: V2[] = [];
  for (let i = 0; i < n; i++) out.push([cx + Math.cos(rot + (i * 2 * Math.PI) / n) * r, cy + Math.sin(rot + (i * 2 * Math.PI) / n) * r]);
  return out;
}

/** A local-frame ring (frame at (dx, dy), bearing `brg`) as anchor-frame polygon (for `replaces`). */
function rotRing(ring: V2[], brg: number, dx = 0, dy = 0): V2[] {
  const a = (-brg * Math.PI) / 180;
  const c = Math.cos(a);
  const s = Math.sin(a);
  return ring.map(([x, y]) => [dx + c * x - s * y, dy + s * x + c * y] as V2);
}

/** Frame of a point-to-point structure: origin at a, +y toward b. */
function along(anchor: V2, a: V2, b: V2) {
  const pa = lngLatToLocal(anchor, a);
  const pb = lngLatToLocal(anchor, b);
  const dx = pb[0] - pa[0];
  const dy = pb[1] - pa[1];
  return {origin: pa, bearing: (Math.atan2(dx, dy) * 180) / Math.PI, length: Math.hypot(dx, dy)};
}

/** Deck segment as a box beam from p to q (top of deck at z) with a road surface. */
function deck(b: MeshBuilder, p: V3, q: V3, width: number, depth: number, color: string, road = '#5A5753') {
  b.color(color).beam([p[0], p[1], p[2] - depth / 2], [q[0], q[1], q[2] - depth / 2], width, depth);
  b.color(road).beam([p[0], p[1], p[2] + 0.05], [q[0], q[1], q[2] + 0.05], width * 0.9, 0.1);
}

/** Piecewise-linear interpolation through (s, value) pairs sorted by s. */
function lerpAt(pts: [number, number][], s: number): number {
  if (s <= pts[0][0]) return pts[0][1];
  for (let i = 0; i < pts.length - 1; i++) {
    if (s <= pts[i + 1][0]) return pts[i][1] + ((pts[i + 1][1] - pts[i][1]) * (s - pts[i][0])) / (pts[i + 1][0] - pts[i][0] || 1);
  }
  return pts[pts.length - 1][1];
}

/** Ground height at a north-up local point relative to the anchor's ground. */
function dzAt(anchor: V2, x: number, y: number) {
  const p = localToLngLat(anchor, [x, y]);
  return elevationAt(p[0], p[1]) - elevationAt(anchor[0], anchor[1]);
}

/** Deck on round columns along a lon/lat path; deck height runs linearly from z0 to z1 (bridges: z = sea level). */
function viaduct(b: MeshBuilder, anchor: V2, path: V2[], z0: number, z1: number, width: number, color: string, every = 45) {
  const pts = path.map(p => lngLatToLocal(anchor, p));
  const d = [0];
  for (let i = 1; i < pts.length; i++) d.push(d[i - 1] + Math.hypot(pts[i][0] - pts[i - 1][0], pts[i][1] - pts[i - 1][1]));
  const L = d[d.length - 1];
  let next = every / 2;
  for (let i = 0; i < pts.length - 1; i++) {
    const za = z0 + ((z1 - z0) * d[i]) / L;
    const zb = z0 + ((z1 - z0) * d[i + 1]) / L;
    deck(b, [pts[i][0], pts[i][1], za], [pts[i + 1][0], pts[i + 1][1], zb], width, 2.2, color);
    while (next <= d[i + 1]) {
      const t = (next - d[i]) / (d[i + 1] - d[i] || 1);
      b.color(CONC).cylinder(pts[i][0] + (pts[i + 1][0] - pts[i][0]) * t, pts[i][1] + (pts[i + 1][1] - pts[i][1]) * t, 1.5, 0, za + (zb - za) * t - 2.2, 6, {top: false});
      next += every;
    }
  }
}

/** Polygon cap whose height is a function of position (sloping roofs over irregular outlines). */
function slopedCap(b: MeshBuilder, ring: V2[], zf: (x: number, y: number) => number) {
  const flat: number[] = [];
  for (const p of ring) flat.push(p[0], p[1]);
  const t = earcut(flat, undefined, 2);
  for (let i = 0; i < t.length; i += 3) {
    const v = (k: number): V3 => [ring[t[k]][0], ring[t[k]][1], zf(ring[t[k]][0], ring[t[k]][1])];
    b.tri(v(i), v(i + 1), v(i + 2));
  }
}

// =================================================================== CARQUINEZ STRAIT

// ------------------------------------------------------------ Carquinez Bridge: 1927 and 1958 cantilevers
// HAER CA-297 (Library of Congress): "a double cantilever, through-truss structure, 3350′ in
// length … two 500′ anchor arms, two main spans of 1100′ each, and a 150′ length of roadway
// over the large center pier. The width … from the center lines of the parallel trusses, is
// 42′. The total height of the superstructure is 168′ from the truss bottom chords to the
// tops of piers 2, 3, and 4 [the peaks above them]. The truss bottom chords have a minimum
// clearance of 135′ above mean high water … The bridge roadway slopes down from north to
// south on a grade of about 1 percent." Anchor arms 18 panels of 27′9″, cantilever arms 12;
// suspended spans 433′2″ long, 72′ deep at mid-span and 60′ at the hips. Piers are numbered
// from the north abutment (pier 1); pier 3 is the double tower in mid-strait; tower legs
// stand 83′ apart on circular pedestals 34′ across. "The second Carquinez Bridge was
// constructed 200′ upstream (east) of the original … with the same span lengths, pier
// locations, and superstructure height, and a nearly identical truss configuration."
// The 1958 bridge is placed on Overture's eastbound carriageway (bridge flag: 1,097 m from
// 38.065543 N to 38.055645 N; the 3DEP surface puts the north bluff at 51 m and open water
// from 75 m to 1,040 m along it, so pier 2 stands in the water and pier 5 on the Crockett
// shore, as HAER says); the 1927 bridge 61 m west of it.
const CQ58_N: V2 = [-122.225577, 38.065543];
const CQ58_S: V2 = [-122.224759, 38.056229];
const CQ_OFF = 61 / (111_320 * Math.cos((38.0609 * Math.PI) / 180));
const CQ27_N: V2 = [CQ58_N[0] - CQ_OFF, CQ58_N[1]];
const CQ27_S: V2 = [CQ58_S[0] - CQ_OFF, CQ58_S[1]];
const CQ_P = [0, 500, 1600, 1750, 2850, 3350].map(f => f * FT);
const CQ_ARM = 333 * FT;
/** Bottom chord: 51 m on the north bluff, ≈1 % down to the south, 135 ft clear at the south channel span. */
const cqChord = (s: number) => 51.0 - 0.010936 * s;

/** Panel points (station, truss depth) of the cantilever profile. */
function cqNodes(): [number, number][] {
  const out: [number, number][] = [];
  const H = 168 * FT;
  const HIP = 60 * FT;
  const MID = 72 * FT;
  const END = 12; // depth at the abutments (estimated)
  const seg = (s0: number, s1: number, n: number, f: (t: number) => number, last = false) => {
    for (let i = 0; i < n + (last ? 1 : 0); i++) out.push([s0 + ((s1 - s0) * i) / n, f(i / n)]);
  };
  const up = (a: number, c: number) => (t: number) => a + (c - a) * Math.pow(t, 1.5);
  const down = (a: number, c: number) => (t: number) => c + (a - c) * Math.pow(1 - t, 1.5);
  const susp = (t: number) => HIP + (MID - HIP) * (1 - (2 * t - 1) ** 2);
  seg(CQ_P[0], CQ_P[1], 9, up(END, H));
  seg(CQ_P[1], CQ_P[1] + CQ_ARM, 6, down(H, HIP));
  seg(CQ_P[1] + CQ_ARM, CQ_P[2] - CQ_ARM, 8, susp);
  seg(CQ_P[2] - CQ_ARM, CQ_P[2], 6, up(HIP, H));
  seg(CQ_P[2], CQ_P[3], 2, () => H);
  seg(CQ_P[3], CQ_P[3] + CQ_ARM, 6, down(H, HIP));
  seg(CQ_P[3] + CQ_ARM, CQ_P[4] - CQ_ARM, 8, susp);
  seg(CQ_P[4] - CQ_ARM, CQ_P[4], 6, up(HIP, H));
  seg(CQ_P[4], CQ_P[5], 9, down(H, END), true);
  return out;
}

/** The cantilever in a frame with the origin at pier 1 (north abutment) and +y running south. */
function carquinezCantilever(b: MeshBuilder, W: number, steel: string, encasedPier5: boolean) {
  const nodes = cqNodes();
  const zb = cqChord;
  const L = CQ_P[5];
  deck(b, [0, 0, zb(0) + 1.5], [0, L, zb(L) + 1.5], W - 1.2, 1.5, steel);
  b.color(steel);
  for (const x of [-W / 2, W / 2]) {
    b.beam([x, 0, zb(0)], [x, L, zb(L)], 1.1);
    for (let i = 0; i < nodes.length; i++) {
      const [s, h] = nodes[i];
      b.beam([x, s, zb(s)], [x, s, zb(s) + h], 0.8);
      if (i === nodes.length - 1) break;
      const [s1, h1] = nodes[i + 1];
      b.beam([x, s, zb(s) + h], [x, s1, zb(s1) + h1], 1.2);
      if (i % 2 === 0) b.beam([x, s, zb(s)], [x, s1, zb(s1) + h1], 0.6);
      else b.beam([x, s, zb(s) + h], [x, s1, zb(s1)], 0.6);
    }
  }
  for (let i = 0; i < nodes.length; i += 2) {
    const [s, h] = nodes[i];
    b.beam([-W / 2, s, zb(s) + h], [W / 2, s, zb(s) + h], 0.5);
  }
  // steel towers on the caisson pedestals (legs 83 ft apart at the base, converging to the trusses)
  const B = (83 * FT) / 2;
  const tower = (s: number, spread: number) => {
    for (const sx of [-1, 1]) {
      b.color(CONC).cylinder(sx * B, s, 5.2, -3, 3, 10);
      b.color(steel);
      for (const d of spread ? [-spread, spread] : [0]) b.beam([sx * B, s + d, 3], [(sx * W) / 2, s, zb(s)], 1.5);
    }
    for (const f of [0.25, 0.5, 0.75]) {
      const x = B + (W / 2 - B) * f;
      b.beam([-x, s, 3 + (zb(s) - 3) * f], [x, s, 3 + (zb(s) - 3) * f], 0.7);
    }
  };
  tower(CQ_P[1], 12 * FT);
  tower(CQ_P[4], 12 * FT);
  tower(CQ_P[2], 0);
  tower(CQ_P[3], 0);
  for (const sx of [-1, 1]) {
    b.beam([sx * B, CQ_P[2], 3], [(sx * W) / 2, CQ_P[3], zb(CQ_P[3])], 0.8);
    b.beam([sx * B, CQ_P[3], 3], [(sx * W) / 2, CQ_P[2], zb(CQ_P[2])], 0.8);
  }
  // pier 5 on the Crockett shore (two legs 64 ft apart; encased in concrete in 1958), pier 1 abutment
  b.color(encasedPier5 ? CONC : steel);
  for (const sx of [-1, 1]) b.beam([sx * 32 * FT, L, 0], [(sx * W) / 2, L, zb(L)], encasedPier5 ? 3 : 1.5);
  b.color(CONC).box(0, -2, zb(0) - 7.8, 60 * FT, 3.9, 7.8);
}

const CQ_SRC = ['https://www.loc.gov/pictures/item/ca3089/', WIKI + 'Carquinez_Bridge'];
const carquinez1927: Landmark = {
  id: 'carquinez_bridge_1927',
  name: 'Carquinez Bridge (1927 cantilever)',
  kind: 'bridge',
  built: [1923.3, 1927.39],
  end: 2007.68,
  anchor: CQ27_N,
  build: b => {
    const a = along(CQ27_N, CQ27_N, CQ27_S);
    b.frame(0, 0, 0, a.bearing, () => carquinezCantilever(b, 42 * FT, '#7E8A86', false));
  },
  facts: {
    Built: '1923–27 by the American Toll Bridge Company (Robinson & Steinman, designers; Charles Derleth Jr., chief engineer); dedicated May 21, 1927 — the first highway bridge across an arm of San Francisco Bay',
    Form: 'double cantilever through truss, 3,350 ft: two 1,100 ft main spans, a 150 ft tower span, two 500 ft anchor arms; trusses 42 ft apart; 135 ft clear; peaks 168 ft above the roadway (HAER CA-297)',
    Later: 'westbound only after the 1958 bridge opened; carried eastbound traffic 2003–06 while the 1958 span was retrofitted',
    Removed: 'replaced by the Alfred Zampa Memorial Bridge (Nov 2003) and dismantled span by span; completed Sep 4, 2007',
    Model: 'placed 200 ft (61 m) west of the 1958 bridge (HAER); truss depth at the abutments estimated; the curved Crockett approach viaduct (four deck trusses and three girder spans on steel towers) is not modelled; one end date for all spans'
  },
  sources: CQ_SRC
};

// eastbound viaduct from pier 5 up the Crockett hillside (Overture bridge segment; 3DEP ground 3 m at the shore, 50 m at the far end)
const CQ58_VIADUCT: V2[] = [[-122.224768, 38.056331], [-122.224759, 38.056229], [-122.224749, 38.055759], [-122.22476, 38.055646], [-122.224801, 38.055473], [-122.224857, 38.055223], [-122.224926, 38.055024], [-122.225005, 38.054839], [-122.225099, 38.054657], [-122.225246, 38.05441], [-122.22538, 38.05424], [-122.22552, 38.054072], [-122.225637, 38.053951], [-122.225816, 38.053788], [-122.226021, 38.053623], [-122.226367, 38.053378], [-122.228025, 38.052208], [-122.228057, 38.052184]];
const carquinez1958: Landmark = {
  id: 'carquinez_bridge_1958',
  name: 'Carquinez Bridge (1958 cantilever, eastbound I-80)',
  kind: 'bridge',
  built: [1956.0, 1958.9],
  end: 9999,
  anchor: CQ58_N,
  build: b => {
    const a = along(CQ58_N, CQ58_N, CQ58_S);
    b.frame(0, 0, 0, a.bearing, () => carquinezCantilever(b, 17, '#8D9895', true));
    viaduct(b, CQ58_N, CQ58_VIADUCT, cqChord(CQ_P[5]) + 1.5, 50.7, 17, '#B9B6AD');
  },
  facts: {
    Opened: 'Nov 25, 1958, 200 ft upstream (east) of the 1927 bridge; four lanes, eastbound since the ramps were finished',
    Form: 'cantilever through truss with the same span lengths, pier locations and superstructure height as the 1927 bridge (HAER CA-297): 500 + 1,100 + 150 + 1,100 + 500 ft; 3,300 ft, 52 ft wide, 140 ft clear (Wikipedia)',
    Retrofit: 'seismic retrofit and new deck after the Zampa bridge opened (2003–06)',
    Model: 'alignment from OpenStreetMap; truss spacing (17 m), the south viaduct’s columns and the construction start are estimated'
  },
  sources: CQ_SRC
};

// ------------------------------------------------------------ Alfred Zampa Memorial Bridge (2003)
// Wikipedia: suspension bridge, 3,465 ft long, 84 ft wide, main span 2,387 ft, towers 410 ft,
// 148 ft clear; "consists of the south anchorage, a transition pier, the South and North
// towers, and the north anchorage. It has spans of 147 m, 728 m, and 181 m"; dedicated Nov 8,
// opened Nov 11, 2003. Overture's westbound bridge segment is 1,078 m (38.056220 → 38.065951);
// the 1,056 m of spans are centred on it, which puts the south tower at the Crockett shore
// and the north tower in the water ≈90 m off the Vallejo bluff (3DEP: water from 50 m to 950 m).
const ZAMPA_S: V2 = [-122.225941, 38.05622];
const ZAMPA_N: V2 = [-122.226682, 38.065951];
const ZAMPA_VIADUCT: V2[] = [[-122.225941, 38.05622], [-122.225925, 38.055968], [-122.225926, 38.055688], [-122.225943, 38.055351], [-122.226011, 38.055005], [-122.226181, 38.054693], [-122.226292, 38.054447], [-122.226425, 38.054208], [-122.22667, 38.053862], [-122.226805, 38.0537], [-122.227016, 38.053488], [-122.227273, 38.05327], [-122.227633, 38.052997], [-122.228339, 38.052458], [-122.228386, 38.052422]];
const zampaBridge: Landmark = {
  id: 'alfred_zampa_memorial_bridge',
  name: 'Alfred Zampa Memorial Bridge (Carquinez, 2003)',
  kind: 'bridge',
  built: [2000.2, 2003.86],
  end: 9999,
  anchor: ZAMPA_S,
  build: b => {
    const a = along(ZAMPA_S, ZAMPA_S, ZAMPA_N);
    const y0 = (a.length - 1056) / 2;
    const yT1 = y0 + 147;
    const yT2 = yT1 + 728;
    const yEnd = y0 + 1056;
    const zd = (y: number) => lerpAt([[0, 44.5], [yT1 + 364, 49.0], [a.length, 48.7]], y);
    const grey = '#C4C8C9';
    const TOP = 410 * FT;
    b.frame(0, 0, 0, a.bearing, () => {
      // orthotropic steel box girder, 84 ft wide
      const n = 14;
      for (let i = 0; i < n; i++) {
        const ya = (a.length * i) / n;
        const yb = (a.length * (i + 1)) / n;
        deck(b, [0, ya, zd(ya)], [0, yb, zd(yb)], 84 * FT, 3, grey);
      }
      // concrete portal towers: two hollow legs, a strut under the deck and one below the saddles
      for (const yt of [yT1, yT2]) {
        b.color(CONC);
        for (const sx of [-1, 1]) {
          b.box(sx * 15.6, yt, -3, 13, 20, 7);
          b.loft([rect(sx * 15.6, yt, 5, 7.2), rect(sx * 14.8, yt, 3.6, 5)], [4, TOP], {top: true});
        }
        b.box(0, yt, zd(yt) - 9.5, 27, 5, 5.5);
        b.box(0, yt, TOP - 14, 27, 4.2, 6);
      }
      // anchorages (the south one rises from the Crockett flat, the north one is cut into the bluff)
      b.color(CONC).box(0, y0 - 9, 0, 34, 26, zd(y0) - 3);
      b.box(0, yEnd + 6, 30, 34, 16, zd(yEnd) - 33);
      // main cables and suspenders
      for (const sx of [-1, 1]) {
        const x = sx * 14.8;
        const spans: [V3, V3, number, number][] = [
          [[x, y0, zd(y0) + 0.5], [x, yT1, TOP - 0.5], (zd(y0) + TOP) / 2 - 5, 6],
          [[x, yT1, TOP - 0.5], [x, yT2, TOP - 0.5], zd(yT1 + 364) + 3.5, 30],
          [[x, yT2, TOP - 0.5], [x, yEnd, zd(yEnd) + 0.5], (zd(yEnd) + TOP) / 2 - 6, 8]
        ];
        for (const [p, q, mid, segs] of spans) {
          const curve = parabola(p, q, mid, segs);
          b.color('#B2553E').polyline(curve, 0.9);
          b.color('#9E4A36');
          for (let i = 1; i < curve.length - 1; i++) if (curve[i][2] - zd(curve[i][1]) > 3) b.beam([x, curve[i][1], zd(curve[i][1])], curve[i], 0.25);
        }
      }
    });
    viaduct(b, ZAMPA_S, ZAMPA_VIADUCT, 44.5, 49.7, 84 * FT, '#B9B6AD', 50);
  },
  facts: {
    Opened: 'dedicated Nov 8, opened Nov 11, 2003 (westbound I-80 and a bicycle / pedestrian path), replacing the 1927 cantilever',
    Form: 'suspension bridge with concrete towers and an orthotropic steel box deck: spans 147 + 728 + 181 m (main span 2,387 ft); 3,465 ft long, 84 ft wide',
    Towers: '410 ft (125 m); 148 ft clear above the strait',
    Namesake: 'Al Zampa (1905–2000), ironworker on the 1927 Carquinez Bridge, the Bay Bridge and the Golden Gate Bridge',
    Model: 'alignment from OpenStreetMap, the spans centred on the bridge segment; tower sections, anchorage blocks, cable sag and deck heights estimated; construction start from the Jan 2000 contract award'
  },
  sources: [WIKI + 'Carquinez_Bridge']
};

// ------------------------------------------------------------ Martinez–Benicia railroad bridge (1930)
// S. A. Roake, "Design and erection of the Martinez-Benicia bridge superstructure",
// Engineering News-Record, June 4, 1931, pp. 918–922, table "Principal data on superstructure"
// (distances from the south abutment): plate-girder viaduct to 560 ft; one deck Warren truss
// of 264 ft (40 ft deep, trusses 19.5 ft apart) to 826 ft; one through Warren truss of 526 ft
// (curved top chord, 80 ft deep at the centre, 33 ft apart) to 1,356 ft; the 328 ft lift span
// to 1,692 ft; six more 526 ft through trusses to 4,877 ft; one deck Warren truss of 504 ft
// (60 ft deep) to 5,383 ft; viaduct to 5,603 ft. "Erected at the 70-ft. clearance above mean
// higher high water"; the lift span rises 65 ft to give 135 ft. Formally opened Nov 1, 1930.
// Overture's two tracks give the line (1,680 m bridge flag, bearing 328.8°); the 1,708 m of
// the table are centred on it. Tower height is not in the article: estimated.
const RR_S: V2 = [-122.118156, 38.035172];
const RR_N: V2 = [-122.128093, 38.04816];
const RUST = '#6B4338';

/** Through truss with a curved top chord between y0 and y1 (low steel at zl). */
function throughTruss(b: MeshBuilder, y0: number, y1: number, zl: number, depth: number, w: number, n: number, color: string, flat = false) {
  const h = (i: number) => (i === 0 || i === n ? 0 : flat ? depth : depth * Math.pow(Math.sin((Math.PI * i) / n), 0.75));
  const y = (i: number) => y0 + ((y1 - y0) * i) / n;
  b.color(color);
  for (const x of [-w / 2, w / 2]) {
    b.beam([x, y0, zl], [x, y1, zl], 0.9);
    for (let i = 0; i < n; i++) {
      b.beam([x, y(i), zl + h(i)], [x, y(i + 1), zl + h(i + 1)], 0.9);
      if (i > 0) b.beam([x, y(i), zl], [x, y(i), zl + h(i)], 0.5);
      if (i > 0 && i < n - 1) {
        if (i % 2 === 1) b.beam([x, y(i), zl + h(i)], [x, y(i + 1), zl], 0.45);
        else b.beam([x, y(i), zl], [x, y(i + 1), zl + h(i + 1)], 0.45);
      }
    }
  }
  for (let i = 1; i < n; i++) b.beam([-w / 2, y(i), zl + h(i)], [w / 2, y(i), zl + h(i)], 0.4);
}

/** Deck truss hanging below the roadway / track between y0 and y1 (top chord at zt). */
function deckTruss(b: MeshBuilder, y0: number, y1: number, zt: number | ((y: number) => number), depth: (t: number) => number, w: number, n: number, color: string) {
  const top = (y: number) => (typeof zt === 'number' ? zt : zt(y));
  const y = (i: number) => y0 + ((y1 - y0) * i) / n;
  const bot = (i: number) => top(y(i)) - depth(i / n);
  b.color(color);
  for (const x of [-w / 2, w / 2]) {
    for (let i = 0; i < n; i++) {
      b.beam([x, y(i), top(y(i))], [x, y(i + 1), top(y(i + 1))], 0.8);
      b.beam([x, y(i), bot(i)], [x, y(i + 1), bot(i + 1)], 0.8);
      b.beam([x, y(i), top(y(i))], [x, y(i), bot(i)], 0.45);
      if (i % 2 === 0) b.beam([x, y(i), top(y(i))], [x, y(i + 1), bot(i + 1)], 0.45);
      else b.beam([x, y(i), bot(i)], [x, y(i + 1), top(y(i + 1))], 0.45);
    }
    b.beam([x, y1, top(y1)], [x, y1, bot(n)], 0.45);
  }
}

const beniciaRailBridge: Landmark = {
  id: 'martinez_benicia_railroad_bridge',
  name: 'Martinez–Benicia railroad bridge (1930)',
  kind: 'bridge',
  built: [1928.4, 1930.83],
  end: 9999,
  anchor: RR_S,
  build: b => {
    const a = along(RR_S, RR_S, RR_N);
    const off = (a.length - 5603 * FT) / 2;
    const Y = (ft: number) => off + ft * FT;
    const ZL = 70 * FT; // low steel above mean higher high water
    const ZR = ZL + 1.7; // base of rail (estimated floor depth)
    b.frame(0, 0, 0, a.bearing, () => {
      // double track on the whole crossing
      deck(b, [0, Y(0), ZR], [0, Y(5603), ZR], 9, 1.0, RUST, '#4A4744');
      // plate-girder viaducts on steel bents
      for (const [f0, f1, step] of [[0, 560, 80], [5383, 5603, 55]] as [number, number, number][]) {
        for (let f = f0 + step / 2; f < f1; f += step) b.color(RUST).box(0, Y(f), 0, 7, 1.2, ZR - 1);
      }
      deckTruss(b, Y(560), Y(826), ZR - 1, () => 40 * FT, 19.5 * FT, 6, RUST);
      throughTruss(b, Y(826), Y(1356), ZL, 80 * FT, 33 * FT, 10, RUST);
      throughTruss(b, Y(1356), Y(1692), ZL, 16.8, 33 * FT, 8, RUST, true);
      const c = (4877 - 1692) / 6;
      for (let k = 0; k < 6; k++) throughTruss(b, Y(1692 + k * c), Y(1692 + (k + 1) * c), ZL, 80 * FT, 33 * FT, 10, RUST);
      deckTruss(b, Y(4877), Y(5383), ZR - 1, () => 60 * FT, 33 * FT, 10, RUST);
      // concrete piers
      b.color(CONC);
      b.box(0, Y(560), -3, 9, 4, ZR - 40 * FT + 2);
      b.box(0, Y(826), -3, 15, 6.5, ZL + 2);
      b.box(0, Y(1356), -3, 17, 8, ZL + 2);
      for (let k = 0; k <= 6; k++) b.box(0, Y(1692 + k * c), -3, k === 0 ? 17 : 15, k === 0 ? 8 : 6.5, ZL + 2);
      b.box(0, Y(5383), -3, 13, 5, ZR - 60 * FT + 2);
      // lift towers at both ends of the 328 ft span, sheave houses and counterweights
      const TOP = 64;
      for (const [ft, out] of [[1356, -1], [1692, 1]] as [number, number][]) {
        const yt = Y(ft) + out * 3.2;
        b.color(RUST);
        for (const sx of [-1, 1]) {
          for (const sy of [-1, 1]) b.beam([sx * 6.2, yt + sy * 3.2, ZL], [sx * 6.2, yt + sy * 3.2, TOP], 1.1);
          for (let z = ZL; z < TOP - 9; z += 9.2) {
            b.beam([sx * 6.2, yt - 3.2, z], [sx * 6.2, yt + 3.2, z + 9.2], 0.4);
            b.beam([sx * 6.2, yt + 3.2, z], [sx * 6.2, yt - 3.2, z + 9.2], 0.4);
          }
        }
        b.box(0, yt, TOP - 1, 14.6, 8.6, 3.2);
        b.color('#8F8A80').box(0, yt + out * 2.4, ZL + 26, 10.5, 2, 9);
      }
      // operator's house on the lift span
      b.color('#8C8F8C').box(0, (Y(1356) + Y(1692)) / 2, ZL + 16.8, 6, 7, 3.4);
    });
  },
  facts: {
    Opened: 'Nov 1, 1930 (Southern Pacific; begun 1928), ending the train ferries Solano and Contra Costa between Port Costa and Benicia',
    Form: 'double track, 5,603 ft 6 in: seven 526 ft through Warren trusses with curved top chords (80 ft deep), a 328 ft vertical-lift span, deck trusses of 264 and 504 ft, plate-girder viaducts (Engineering News-Record, 1931)',
    Clearance: '70 ft with the span down, 135 ft raised (lift 65 ft); 291 ft horizontal',
    Today: 'Union Pacific’s Martinez Subdivision: Capitol Corridor, California Zephyr and Coast Starlight trains',
    Model: 'spans from the 1931 table, centred on the OpenStreetMap track; lift-tower height (64 m), lift-span truss depth, track level and pier sizes estimated'
  },
  sources: ['https://historicbridges.org/california/martinezrr/benicia.pdf', WIKI + 'Benicia%E2%80%93Martinez_Bridge']
};

// ------------------------------------------------------------ Benicia–Martinez Bridge: 1962 deck truss and 2007 segmental span
// Wikipedia: the 1962 span is "a 1.2 mi deck truss bridge … it has seven 528 ft spans and
// 138 ft of vertical clearance"; opened Sep 15, 1962 (routes.csv); the 2007 span is a 1.7 mi
// lightweight-concrete segmental bridge of five lanes, opened Aug 25, 2007, construction from
// late 2001. Alignments: Overture bridge segments. Where the seven truss spans sit on the
// 1,881 m crossing is not in the sources: they are centred on the water (3DEP: open water
// from 275 m to 1,775 m from the south end), which puts one span over the railroad lift span.
const BM62_N: V2 = [-122.128714, 38.047692];
const BM62_K: V2 = [-122.118131, 38.034584]; // south end of the straight
const BM62_CURVE: V2[] = [[-122.118131, 38.034584], [-122.117937, 38.034325], [-122.117755, 38.03404], [-122.117624, 38.033809], [-122.11751, 38.033572], [-122.117419, 38.033352], [-122.117382, 38.033245]];
const benicia1962: Landmark = {
  id: 'benicia_martinez_bridge_1962',
  name: 'Benicia–Martinez Bridge (1962 truss span, southbound I-680)',
  kind: 'bridge',
  built: [1960.0, 1962.71],
  end: 9999,
  anchor: BM62_N,
  build: b => {
    const a = along(BM62_N, BM62_N, BM62_K);
    const steel = '#8E9691';
    const W = 24;
    // deck heights along the straight, from the north end (3DEP ground 34 m) to the crest over the channel
    const zd = (s: number) => lerpAt([[0, 34.7], [590, 43], [1050, 49.5], [1180, 50], [1320, 49], [1881, 28.7]], s);
    const SPAN = 528 * FT;
    const s0 = 293;
    b.frame(0, 0, 0, a.bearing, () => {
      const n = 20;
      for (let i = 0; i < n; i++) {
        const sa = (a.length * i) / n;
        const sb = (a.length * (i + 1)) / n;
        deck(b, [0, sa, zd(sa)], [0, sb, zd(sb)], W, 1.8, '#B5B3AB');
      }
      // seven haunched deck trusses
      for (let k = 0; k < 7; k++) deckTruss(b, s0 + k * SPAN, s0 + (k + 1) * SPAN, y => zd(y) - 1.8, t => 8 + 8 * (2 * t - 1) ** 2, 11, 8, steel);
      b.color(CONC);
      for (let k = 0; k <= 7; k++) {
        const s = s0 + k * SPAN;
        for (const sx of [-1, 1]) b.box(sx * 5.5, s, -3, 3.4, 5, zd(s) - 14.8);
        b.box(0, s, zd(s) - 21.8, 14.4, 5, 4);
      }
      // girder approach spans
      for (let s = s0 - 49; s > 20; s -= 49) b.box(0, s, 0, 12, 2.4, zd(s) - 1.8);
      for (let s = s0 + 7 * SPAN + 46; s < a.length; s += 46) b.box(0, s, 0, 12, 2.4, zd(s) - 1.8);
    });
    // curve onto the Martinez shore
    const pts = BM62_CURVE.map(p => lngLatToLocal(BM62_N, p));
    let s = a.length;
    for (let i = 0; i < pts.length - 1; i++) {
      const d = Math.hypot(pts[i + 1][0] - pts[i][0], pts[i + 1][1] - pts[i][1]);
      deck(b, [pts[i][0], pts[i][1], zd(s)], [pts[i + 1][0], pts[i + 1][1], zd(s + d)], W, 1.8, '#B5B3AB');
      s += d;
    }
  },
  facts: {
    Opened: 'Sep 15, 1962, replacing the last automobile ferry on San Francisco Bay; named for George Miller Jr. in 1975',
    Form: 'deck truss, 1.2 mi: seven 528 ft spans, 138 ft of vertical clearance; four southbound lanes and a bicycle / pedestrian path since 2009',
    Model: 'LOW CONFIDENCE — alignment from OpenStreetMap; the position of the seven truss spans along the crossing (centred on the water), the deck heights (from the 138 ft clearance and the ground at both ends), truss depths, pier forms and the construction start are estimated'
  },
  sources: [WIKI + 'Benicia%E2%80%93Martinez_Bridge']
};

const BM07_PATH: V2[] = [[-122.116757, 38.031832], [-122.116714, 38.033654], [-122.11672, 38.034124], [-122.116754, 38.034549], [-122.116837, 38.035096], [-122.116992, 38.035767], [-122.117119, 38.036173], [-122.117224, 38.036447], [-122.11735, 38.036756], [-122.117609, 38.037292], [-122.117956, 38.037875], [-122.118378, 38.038467], [-122.121761, 38.042852], [-122.126179, 38.04858], [-122.126262, 38.048762], [-122.127196, 38.049967], [-122.127701, 38.050641], [-122.128484, 38.051649], [-122.128742, 38.052019], [-122.128859, 38.052205], [-122.128969, 38.052421], [-122.129069, 38.052615], [-122.129179, 38.05286], [-122.129291, 38.053198], [-122.129358, 38.053443]];
const benicia2007: Landmark = {
  id: 'benicia_martinez_bridge_2007',
  name: 'Benicia–Martinez Bridge (2007 span, northbound I-680)',
  kind: 'bridge',
  built: [2001.9, 2007.65],
  end: 9999,
  anchor: BM07_PATH[0],
  build: b => {
    const pts = BM07_PATH.map(p => lngLatToLocal(BM07_PATH[0], p));
    const d = [0];
    for (let i = 1; i < pts.length; i++) d.push(d[i - 1] + Math.hypot(pts[i][0] - pts[i - 1][0], pts[i][1] - pts[i - 1][1]));
    const L = d[d.length - 1];
    // 3DEP ground: 23 m at the south end, 30 m at the north end; crest beside the 1962 span's
    const zd = (s: number) => lerpAt([[0, 23.7], [430, 37], [860, 50.5], [1300, 49], [2071, 40], [L, 30.7]], s);
    const at = (s: number): V2 => {
      let i = 0;
      while (i < d.length - 2 && d[i + 1] < s) i++;
      const t = (s - d[i]) / (d[i + 1] - d[i] || 1);
      return [pts[i][0] + (pts[i + 1][0] - pts[i][0]) * t, pts[i][1] + (pts[i + 1][1] - pts[i][1]) * t];
    };
    const W = 25;
    const conc = '#CFCCC3';
    // haunched box girder: deep at the piers, slender at mid-span
    const SPAN = 160;
    const first = 110;
    for (let s = first; s < L - 40; s += SPAN) {
      const p = at(s);
      b.color(CONC).cylinder(p[0], p[1], 3.6, -3, zd(s) - 9, 8, {top: false});
    }
    const step = 20;
    for (let s = 0; s < L; s += step) {
      const e = Math.min(s + step, L);
      const m = (((s + e) / 2 - first) % SPAN + SPAN) % SPAN;
      const depth = 4.5 + 5.5 * Math.pow(Math.abs(m / SPAN - 0.5) * 2, 2);
      const p = at(s);
      const q = at(e);
      deck(b, [p[0], p[1], zd(s)], [q[0], q[1], zd(e)], W, depth, conc);
    }
  },
  facts: {
    Opened: 'Aug 25, 2007 (construction from late 2001; US$1.3 billion), east of the railroad bridge; named for Congressman George Miller',
    Form: '1.7 mi lightweight-concrete segmental box girder — the largest of its kind in California — carrying five northbound lanes',
    Model: 'LOW CONFIDENCE — alignment from OpenStreetMap; pier spacing (160 m), girder depths and deck heights estimated'
  },
  sources: [WIKI + 'Benicia%E2%80%93Martinez_Bridge']
};

// =================================================================== FORT ROSS

// Russian-American Company settlement, 1812–41. National Historic Landmark nominations
// (Fort Ross, 66000239; Commander's House, 70000150): "a quadrangular enclosure which
// measured about 276 by 312 feet. Hand-hewn redwood timbers were used for all construction,
// including the stockaded walls, which were 12 feet high. Two two-story blockhouses, one
// 7-sided and the other 8-sided, were located at diagonally opposite corners"; inside, "the
// commander's house, officers' quarters, a two-story barracks, a chapel, and 3 storehouses".
// "The Russian Orthodox chapel was built about 1825 … during the 1906 earthquake, its walls
// collapsed. The chapel was restored in 1916-17 and more authentically in 1955-56, only to
// be completely destroyed by fire in 1970" (Oct 5; rebuilt 1973). "The original blockhouses
// and some parts of the stockade remained standing until the 1906 earthquake."
// OSM outlines (local metres from the anchor): seven-sided blockhouse at the north corner
// (−6.6, 54.3), eight-sided at the south corner (27.8, −77.0), the chapel in the east corner,
// a stockade fragment giving the west corner (−45.5, −33.7): walls of 93, 86, 95 and 79 m
// (the nominations' 312 × 276 ft = 95 × 84 m). Rotchev House 17.5 × 10.5 m, Kuskov House
// 19.1 × 14.3 m, Officials' Quarters 22.4 × 7.4 m, Magazin 16.5 × 9.1 m. Heights other than
// the 12 ft stockade are scaled from photographs of the reconstructions.
const FR: V2 = [-123.2437, 38.51435];
const FR_N: V2 = [-8.0, 51.0];
const FR_S: V2 = [25.0, -70.0];
const FR_W: V2 = [-45.5, -33.7];
const REDWOOD = '#74685A';
const REDWOOD_DK = '#62584C';
const PLANK = '#877D6F';
const FR_SRC = [NRHP('66000239', true), NRHP('70000150'), WIKI + 'Fort_Ross,_California'];

function frStockade(b: MeshBuilder) {
  const wall = (p: V2, q: V2, t0 = 0, t1 = 1) =>
    b.beam([p[0] + (q[0] - p[0]) * t0, p[1] + (q[1] - p[1]) * t0, 1.33], [p[0] + (q[0] - p[0]) * t1, p[1] + (q[1] - p[1]) * t1, 1.33], 0.35, 4.66);
  b.color(REDWOOD);
  wall(FR_W, FR_N, 0, 0.97);
  wall(FR_N, [60.8, 18.1], 0.03, 0.47); // sally port in the north-east wall
  wall(FR_N, [60.8, 18.1], 0.53, 1);
  wall([65.9, 6.4], FR_S, 0, 0.95);
  wall(FR_S, FR_W, 0.05, 0.47); // main gate, south-west
  wall(FR_S, FR_W, 0.53, 1);
  for (const [c, sides, r] of [[[-6.6, 54.3], 7, 3.8], [[27.8, -77.0], 8, 4.4]] as [V2, number, number][]) {
    b.color(REDWOOD_DK).prism(ngon(c[0], c[1], r, sides), -1, 6.4, {top: false});
    b.color(PLANK).pyramid(ngon(c[0], c[1], r + 0.5, sides), 6.4, [c[0], c[1], 9.2]);
  }
}

/** Log building with a plank hip roof in its own frame. */
function frHouse(b: MeshBuilder, cx: number, cy: number, brg: number, sx: number, sy: number, wall: number, rise: number) {
  b.frame(cx, cy, 0, brg, () => {
    b.color(REDWOOD_DK).box(0, 0, -1, sx, sy, wall + 1, {top: false});
    b.color(PLANK).hip(0, 0, sx + 0.8, sy + 0.8, wall, rise);
  });
}

function frChapel(b: MeshBuilder) {
  // +y = west-north-west (the entrance and bell tower); the cupola stands over the altar in the stockade's east corner
  b.frame(63.3, 12.2, 0, 297.3, () => {
    b.color(REDWOOD).box(0, 0, -1, 8.1, 10, 4.3, {top: false});
    b.color(PLANK).hip(0, 0, 8.9, 10.8, 3.3, 2.0);
    const hex = ngon(0, 3.1, 1.55, 6);
    b.color(REDWOOD).prism(hex, 4.0, 7.7, {top: false});
    b.color(PLANK).pyramid(ngon(0, 3.1, 1.9, 6), 7.7, [0, 3.1, 9.7]);
    b.color(REDWOOD).cylinder(0, -2.7, 1.6, 4.0, 6.8, 8, {top: false});
    b.color(PLANK).pyramid(circle(0, -2.7, 1.9, 8), 6.8, [0, -2.7, 7.9]);
    b.color('#3F3A34');
    for (const y of [3.1, -2.7]) {
      const z = y > 0 ? 9.7 : 7.9;
      b.beam([0, y, z], [0, y, z + 1.0], 0.1).beam([-0.3, y, z + 0.7], [0.3, y, z + 0.7], 0.08);
    }
  });
}

const frStockade1812: Landmark = {
  id: 'fort_ross_stockade_1812',
  name: 'Fort Ross — Russian stockade and blockhouses (1812)',
  kind: 'building',
  built: [1812.2, 1812.7],
  end: 1906.3,
  anchor: FR,
  build: frStockade,
  facts: {
    Founded: '1812 by Ivan Kuskov and the Russian-American Company: 25 Russians and some 80 Alaska Natives built the stockaded fort on the Kashaya Pomo site of Metini',
    Stockade: 'about 276 × 312 ft of hand-hewn redwood timbers, 12 ft high, with three sally ports and a seven-sided and an eight-sided two-storey blockhouse at opposite corners (National Historic Landmark nomination)',
    After: 'sold to John Sutter in December 1841; a ranch until 1903. The original blockhouses and parts of the stockade stood until the 1906 earthquake',
    Model: 'corners and blockhouse outlines from the reconstructed fort in OpenStreetMap; blockhouse heights from photographs. LOW CONFIDENCE: how much of the wall still stood through the ranch years'
  },
  sources: FR_SRC
};
const frBuildings1812: Landmark = {
  id: 'fort_ross_russian_buildings',
  name: 'Fort Ross — Kuskov House, Officials’ Quarters and Magazin (Russian period)',
  kind: 'building',
  built: [1812.2, 1814.0],
  end: 1842.0,
  anchor: FR,
  build: b => {
    frHouse(b, 28.5, 22.5, 118.1, 14.3, 19.1, 5.6, 4.4); // Kuskov House, two storeys
    frHouse(b, -18.3, -38.6, 118.9, 7.4, 22.4, 3.0, 2.4); // Officials' Quarters
    frHouse(b, -13.9, 15.4, 24.4, 9.1, 16.5, 5.5, 3.2); // Magazin (fur warehouse), two storeys
  },
  replaces: [rotRing(rect(0, 0, 15.3, 20.1), 118.1, 28.5, 22.5), rotRing(rect(0, 0, 8.4, 23.4), 118.9, -18.3, -38.6), rotRing(rect(0, 0, 10.1, 17.5), 24.4, -13.9, 15.4)],
  facts: {
    Buildings: 'the first manager’s house (Kuskov House, the “old commandant’s house” of the 1841 inventory), the officials’ quarters and a two-storey warehouse (magazin) stood inside the stockade with barracks, storehouses and the well',
    Model: 'the State Park’s reconstructions on the excavated sites, as outlined in OpenStreetMap, stand in for the Russian buildings; heights from photographs. The model ends with the colony (the company left in January 1842): what became of each building afterwards, and the years of today’s reconstructions, were not researched — LOW CONFIDENCE end date'
  },
  sources: FR_SRC
};
const frRotchev: Landmark = {
  id: 'fort_ross_rotchev_house',
  name: 'Fort Ross — Rotchev House',
  kind: 'building',
  built: [1835.5, 1836.5],
  end: 9999,
  anchor: FR,
  build: b => frHouse(b, -29.0, -15.8, 25.6, 10.5, 17.5, 3.2, 4.6),
  replaces: [rotRing(rect(0, 0, 11.5, 18.5), 25.6, -29.0, -15.8)],
  facts: {
    Built: 'renovated about 1836 from an existing building for Alexander Rotchev, the last manager — the only original Russian building left at the fort (National Historic Landmark, 1970)',
    Form: 'one storey of hand-squared redwood timbers notched at the corners under a steep hip roof of split redwood planks up to 23 ft long; the nomination gives about 36 × 48 ft',
    Fire: 'its roof was damaged by the fires of 1970–71; opened as a house museum in 2010',
    Model: OSM_NOTE + ' (17.5 × 10.5 m); wall and roof heights from a photograph'
  },
  sources: [NRHP('70000150'), WIKI + 'Rotchev_House']
};
const chapelFacts = {
  Built: 'about 1825 — the first Russian Orthodox chapel in North America south of Alaska, standing in the stockade’s east corner',
  History: 'walls collapsed in the earthquake of Apr 18, 1906; re-erected 1916–17 from the original timbers and restored more authentically in 1955–56; burned Oct 5, 1970; rebuilt 1973',
  Model: 'one mesh for all three periods (the 1916–17 chapel kept ranch-era alterations); outline from OpenStreetMap (10.0 × 8.1 m), heights from a photograph of the 1973 chapel; construction months estimated'
};
const frChapel1825: Landmark = {id: 'fort_ross_chapel_1825', name: 'Fort Ross Chapel (c. 1825)', kind: 'building', built: [1824.5, 1825.5], end: 1906.3, anchor: FR, build: frChapel, facts: chapelFacts, sources: FR_SRC};
const frChapel1917: Landmark = {id: 'fort_ross_chapel_1917', name: 'Fort Ross Chapel (restored 1916–17)', kind: 'building', built: [1916.0, 1917.5], end: 1970.76, anchor: FR, build: frChapel, facts: chapelFacts, sources: FR_SRC};
const frChapel1973: Landmark = {
  id: 'fort_ross_chapel',
  name: 'Fort Ross Chapel (rebuilt 1973)',
  kind: 'building',
  built: [1972.5, 1973.9],
  end: 9999,
  anchor: FR,
  build: frChapel,
  replaces: [rotRing(rect(0, 0, 9.1, 11), 297.3, 63.3, 12.2)],
  facts: chapelFacts,
  sources: FR_SRC
};
const frStockadeToday: Landmark = {
  id: 'fort_ross_stockade',
  name: 'Fort Ross — reconstructed stockade and blockhouses',
  kind: 'building',
  built: [1955.0, 1957.0],
  end: 9999,
  anchor: FR,
  build: frStockade,
  replaces: [rect(-6.6, 54.3, 9, 9), rect(27.8, -77.0, 10, 10), rect(-32.2, -25.9, 5, 5)],
  facts: {
    Reconstruction: 'the State of California (owner since 1906) rebuilt the stockade and both blockhouses on the original lines “with a high degree of accuracy, using original materials to some extent” (National Historic Landmark nomination); the restored fort reopened in 1974 after the 1970–71 fires, and Highway 1, which ran through the compound, was moved out in the 1970s',
    Stockade: 'redwood timbers 12 ft high; seven-sided blockhouse at the north corner, eight-sided at the south corner',
    Model: 'LOW CONFIDENCE years — the sources only show the reconstruction standing by the 1961 landmark survey; it is dated here with the chapel’s 1955–56 restoration. Blockhouse heights from photographs'
  },
  sources: FR_SRC
};

// =================================================================== SONOMA AND PETALUMA

const ADOBE = '#EFEBE1';
const TILE = '#A9553B';
const SHINGLE = '#6B5F52';
const PLAZA_SRC = NRHP('75000489', true);

// ------------------------------------------------------------ Mission San Francisco Solano
// Sonoma Plaza NHL nomination: founded July 4, 1823; the first church was "a crude wood
// structure, 105 ft long, 34 ft wide … dedicated April 4, 1824"; the adobe mission church was
// destroyed after secularization (1834). "The present parish church is a small
// one-and-a-half story adobe structure with a tile roof … A one-story tile-roofed adobe
// convento … nearly 120 feet long, adjoins the chapel on the east side to give the two
// buildings an L-shaped ground plan … sold [1881] and utilized as a hay barn, winery, and
// blacksmith shop … restored by the State in 1911-13." Wikipedia: Vallejo's chapel, 1841, on
// the site of the first wooden chapel; 27 rooms in the convento by 1832.
// OSM outline: chapel 8.9 × 33 m with its facade on Spain Street, convento 37.8 × 10.5 m.
const MSFS: V2 = [-122.456102, 38.293892];
const sonomaMissionChapel: Landmark = {
  id: 'mission_san_francisco_solano_chapel',
  name: 'Mission San Francisco Solano — chapel (1841)',
  kind: 'building',
  built: [1840.0, 1841.5],
  end: 9999,
  anchor: MSFS,
  build: b =>
    b.frame(-0.6, -3.8, 0, 4.0, () => {
      b.color(ADOBE).box(0, 0, -1, 8.9, 33, 6.2, {top: false});
      b.color(TILE).gable(0, 0, 9.8, 33.6, 5.2, 2.8, true);
      b.color(ADOBE).tri([-4.45, -16.52, 5.2], [4.45, -16.52, 5.2], [0, -16.52, 8.0]);
      b.color('#4A3B2C').box(0, -16.55, 0, 1.8, 0.12, 2.9).box(0, -16.55, 4.1, 1.0, 0.12, 1.1);
      b.beam([0, -16.4, 8.0], [0, -16.4, 10.6], 0.22).beam([-0.9, -16.4, 9.8], [0.9, -16.4, 9.8], 0.2);
    }),
  replaces: [rotRing(rect(0, 0, 10, 34), 4.0, -0.6, -3.8)],
  facts: {
    Mission: 'founded July 4, 1823 by José Altimira — the 21st and last California mission, the only one founded under Mexican rule; secularized 1834',
    Chapel: 'built in 1841 by order of Mariano Vallejo as the parish church, on the site of the first wooden mission chapel (the large adobe mission church, at the convento’s east end, was already in ruins)',
    Later: 'sold in 1881 (hay barn, winery, blacksmith shop); bought by the Historic Landmarks League in 1903, damaged in 1906 and restored by the State 1911–13',
    Model: OSM_NOTE + ' (8.9 × 33 m); wall and ridge heights from a photograph; construction start estimated'
  },
  sources: [WIKI + 'Mission_San_Francisco_Solano', PLAZA_SRC]
};
const sonomaMissionConvento: Landmark = {
  id: 'mission_san_francisco_solano_convento',
  name: 'Mission San Francisco Solano — convento',
  kind: 'building',
  built: [1825.0, 1832.0],
  end: 9999,
  anchor: MSFS,
  build: b =>
    b.frame(21.2, -18.8, 0, 93.9, () => {
      // +y = east along Spain Street, +x = south (the corridor)
      b.color(ADOBE).box(-1.75, 0, -1, 7, 37.8, 4.3, {top: false});
      b.color(TILE).gable(-1.75, 0, 7.6, 38.4, 3.3, 2.0, true);
      b.quad([1.7, -18.9, 3.5], [1.7, 18.9, 3.5], [5.4, 18.9, 2.6], [5.4, -18.9, 2.6]);
      b.color('#5A4634');
      for (let y = -18; y <= 18; y += 3.6) b.box(5.0, y, 0, 0.3, 0.3, 2.6);
    }),
  replaces: [rotRing(rect(0, 0, 11.5, 38.8), 93.9, 21.2, -18.8)],
  facts: {
    Built: 'the padres’ quarters: adobe building began in 1825 after the first season’s walls melted in the rains; 27 rooms by 1832 — the oldest building in Sonoma',
    Form: 'one-storey tile-roofed adobe nearly 120 ft long with a corridor on wooden posts along the street; restored 1911–13',
    Model: OSM_NOTE + ' (37.8 × 10.5 m); heights from a photograph; LOW CONFIDENCE construction years (between the 1825 start and the 1832 inventory)'
  },
  sources: [WIKI + 'Mission_San_Francisco_Solano', PLAZA_SRC]
};

// ------------------------------------------------------------ Sonoma Barracks
// Wikipedia (after Stammerjohan): "Construction of the barracks was episodic: digging the
// foundation began in 1837, construction of the adobe walls in 1839 and the building was more
// or less completed in 1840 to '41" — "a two-story, wide-balconied, adobe building facing the
// central plaza". OSM outline 38.4 × ≈18 m along Spain Street (balconies included), 6.8 m high.
const sonomaBarracks: Landmark = {
  id: 'sonoma_barracks',
  name: 'Sonoma Barracks',
  kind: 'building',
  built: [1837.0, 1841.0],
  end: 9999,
  anchor: [-122.456624, 38.293759],
  build: b =>
    b.frame(-0.1, -0.6, 0, 97.7, () => {
      // +y = east along Spain Street, +x = south (the plaza front)
      b.color(ADOBE).box(0, 0, -1, 12, 38.4, 7.8, {top: false});
      b.color(SHINGLE).hip(0, 0, 18.8, 39.6, 6.8, 2.8);
      for (const sx of [-1, 1]) {
        b.color('#7A6A58').box(sx * 7.5, 0, 3.1, 3, 38.4, 0.25);
        b.color('#5A4A3A');
        for (let y = -18.9; y <= 18.9; y += 4.2) b.box(sx * 8.8, y, 0, 0.3, 0.3, 6.8);
      }
    }),
  replaces: [rotRing(rect(0, 0, 19.5, 39.6), 97.7, -0.1, -0.6)],
  facts: {
    Built: 'for Mariano Vallejo’s presidial company, moved from San Francisco in 1835: foundation 1837, adobe walls 1839, finished 1840–41',
    '1846': 'headquarters of the Bear Flag Party (June 14), then of U.S. forces',
    Later: 'sold in 1879 and given a Victorian front; restored by the State after 1957 to its 1840s appearance',
    Model: OSM_NOTE + '; two-storey balconies on both long sides and a hipped shingle roof; heights from the OSM height (6.8 m) and photographs'
  },
  sources: [WIKI + 'Sonoma_Barracks', PLAZA_SRC]
};

// ------------------------------------------------------------ Sonoma City Hall
// Wikipedia: cornerstone Feb 22, 1906; dedicated Sep 9, 1908; A. C. Lutgens; basalt, two
// stories, a tower and a tiled roof, "four identical sides, each with an arched doorway".
// OSM outline: a 20.8 m square turned 7.4°, four corner pavilions 7.2 × 7.5 m with the wall
// between them set back 3.9 m. Heights scaled from the Wikipedia photograph (front 20.8 m).
const sonomaCityHall: Landmark = {
  id: 'sonoma_city_hall',
  name: 'Sonoma City Hall',
  kind: 'building',
  built: [1906.15, 1908.69],
  end: 9999,
  anchor: [-122.457728, 38.292817],
  build: b =>
    b.frame(0.3, -0.1, 0, 7.4, () => {
      const stone = '#8C8375';
      b.color(stone).box(0, 0, -1, 13.3, 13.3, 9.8);
      for (const sx of [-1, 1]) {
        for (const sy of [-1, 1]) {
          b.color(stone).box(sx * 6.75, sy * 6.75, -1, 7.2, 7.5, 9.8, {top: false});
          b.color(TILE).hip(sx * 6.75, sy * 6.75, 8.2, 8.5, 8.8, 1.4);
        }
      }
      // curved parapet gable over each of the four entrances, arched doorways below
      for (const [nx, ny] of [[1, 0], [-1, 0], [0, 1], [0, -1]] as V2[]) {
        b.frame(nx * 6.7, ny * 6.7, 0, (Math.atan2(nx, ny) * 180) / Math.PI, () => {
          b.color(stone).box(0, 0, 8.8, 6.4, 0.5, 1.2);
          b.gable(0, 0, 4.4, 0.5, 10.0, 1.3, false);
          b.color('#3B3530').box(0, 0.27, 0, 2.2, 0.1, 3.6);
        });
      }
      b.color(TILE).hip(0, 0, 12.6, 12.6, 8.8, 1.2);
      // bell cupola
      b.color('#E6E0D2');
      for (const sx of [-1, 1]) for (const sy of [-1, 1]) b.box(sx * 1.0, sy * 1.0, 10.0, 0.35, 0.35, 2.7);
      b.box(0, 0, 9.6, 2.6, 2.6, 0.9);
      b.color(TILE).hip(0, 0, 3.4, 3.4, 12.7, 1.2);
      b.color('#B9B4A8').beam([0, 0, 13.9], [0, 0, 17.0], 0.1);
    }),
  replaces: [rotRing(rect(0, 0, 21.8, 21.8), 7.4, 0.3, -0.1)],
  facts: {
    Built: 'cornerstone Feb 22, 1906; dedicated Sep 9, 1908 (Adolph C. Lutgens, architect)',
    Form: 'Mission Revival in local basalt: two storeys, four identical fronts — so that no merchant on the Plaza faced its back — a bell cupola and tile roofs; the fire engines once left through its arched doors',
    Model: OSM_NOTE + '; heights scaled from a photograph (eaves ≈8.8 m, cupola ≈13.9 m)'
  },
  sources: [WIKI + 'Sonoma_City_Hall', PLAZA_SRC]
};

// ------------------------------------------------------------ Rancho Petaluma Adobe
// NHL nomination (70000151): "the two-story house is built in [adobe] … form three sides of
// a quadrangle measuring 200 by 145 feet … [walls] 20 feet high. A broad two-story veranda
// ran around"; Wikipedia: built 1836–46, "what remains of the Petaluma Adobe is only half
// its former size" (the south-east half decayed under the Bliss family; bought by the Native
// Sons in 1910). OSM outline in a 26° frame: main wing 60.3 × 15 m (the 200 ft front), two
// wings of ≈18 × 13 m toward the lost half.
const petalumaAdobe: Landmark = {
  id: 'rancho_petaluma_adobe',
  name: 'Rancho Petaluma Adobe',
  kind: 'building',
  built: [1836.0, 1846.0],
  end: 9999,
  anchor: [-122.584807, 38.255729],
  build: b =>
    b.frame(0, 0, 0, 26.0, () => {
      // +y = north-north-east along the main wing, +x = into the courtyard
      const wing = (cx: number, cy: number, sx: number, sy: number) => {
        const alongY = sy > sx;
        const cxs = alongY ? sx - 5.6 : sx;
        const cys = alongY ? sy : sy - 5.6;
        b.color(ADOBE).box(cx, cy, -1, cxs, cys, 7.1, {top: false});
        b.color('#7A6A58').box(cx, cy, 2.9, sx, sy, 0.25);
        b.color('#5A4A3A');
        if (alongY) for (const s of [-1, 1]) for (let y = cy - sy / 2 + 0.3; y <= cy + sy / 2; y += 3.3) b.box(cx + s * (sx / 2 - 0.3), y, 0, 0.3, 0.3, 6.1);
        else for (const s of [-1, 1]) for (let x = cx - sx / 2 + 0.3; x <= cx + sx / 2; x += 3.3) b.box(x, cy + s * (sy / 2 - 0.3), 0, 0.3, 0.3, 6.1);
        b.color(SHINGLE).hip(cx, cy, sx + 0.8, sy + 0.8, 6.1, 2.0);
      };
      wing(0, 3.7, 15, 60.35);
      wing(16.45, 27.2, 17.9, 13.6);
      wing(16.4, -10.9, 17.9, 13.0);
    }),
  replaces: [rotRing(rect(9, 3.7, 35, 62), 26.0)],
  facts: {
    Built: '1836–46 for Mariano Vallejo as the headquarters of the 66,000-acre Rancho Petaluma — the largest private adobe building in California; never quite finished',
    Form: 'two storeys of adobe on redwood framing around a courtyard about 200 × 145 ft, walls 20 ft high, with broad two-storey verandas and a low shingled roof',
    Remains: 'the standing half: Vallejo sold it about 1857 and the south-east half decayed; the Native Sons of the Golden West bought the rest in 1910; state historic park since 1951',
    Model: OSM_NOTE + ' (main wing 60 × 15 m); the lost south-east half is not modelled (no plan or date of loss found); roof and veranda details from photographs'
  },
  sources: [WIKI + 'Rancho_Petaluma_Adobe', NRHP('70000151', true)]
};

// @@NEXT@@

export const NORTHBAY: Landmark[] = [
  carquinez1927,
  carquinez1958,
  zampaBridge,
  beniciaRailBridge,
  benicia1962,
  benicia2007,
  frStockade1812,
  frBuildings1812,
  frRotchev,
  frChapel1825,
  frChapel1917,
  frChapel1973,
  frStockadeToday,
  sonomaMissionChapel,
  sonomaMissionConvento,
  sonomaBarracks,
  sonomaCityHall,
  petalumaAdobe
];
