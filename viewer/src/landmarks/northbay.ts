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
// shore, as HAER says); the 1927 bridge 61 m west of it. Six OSM pier outlines on the 1958 line
// lie 6, 157, 489, 535, 868 and 1,021 m from the north end — the HAER stations 0, 152, 488, 533,
// 869 and 1,021 m.
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
    Built: '1923–27 by the American Toll Bridge Company (Robinson & Steinman, designers; Charles Derleth Jr., chief engineer); dedicated May 21, 1927 — the first major crossing of San Francisco Bay’s waters, on the direct road to Sacramento',
    Form: 'double cantilever through truss, 3,350 ft: two 1,100 ft main spans, a 150 ft tower span, two 500 ft anchor arms; trusses 42 ft apart; 135 ft clear; peaks 168 ft above the roadway (HAER CA-297)',
    Later: 'westbound only after the 1958 bridge opened; once the Zampa bridge was open it carried eastbound traffic for a time while the 1958 span was retrofitted',
    Removed: 'replaced by the Alfred Zampa Memorial Bridge (Nov 2003) and dismantled span by span; completed Sep 4, 2007',
    Model: 'placed 200 ft (61 m) west of the 1958 bridge (HAER); truss depth at the abutments estimated; the curved Crockett approach viaduct (four deck trusses and three girder spans on steel towers) is not modelled; one end date for all spans'
  },
  sources: CQ_SRC
};

// eastbound viaduct from pier 5 up the Crockett hillside (Overture bridge segment; 3DEP ground 3 m at the shore, 50 m at the far end)
const CQ58_PIERS: V2[] = [[-122.225577, 38.065485], [-122.22546, 38.064124], [-122.225183, 38.061125], [-122.225148, 38.060707], [-122.224888, 38.057691], [-122.22477, 38.056308]];
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
  // the piers are generic footprints in the building data: hide them
  replaces: CQ58_PIERS.map(p => {
    const l = lngLatToLocal(CQ58_N, p);
    return rect(l[0], l[1], 40, 30);
  }),
  facts: {
    Opened: 'Nov 25, 1958, 200 ft upstream (east) of the 1927 bridge; four lanes, eastbound since the ramps were finished',
    Form: 'cantilever through truss with the same span lengths, pier locations and superstructure height as the 1927 bridge (HAER CA-297): 500 + 1,100 + 150 + 1,100 + 500 ft; 3,300 ft, 52 ft wide, 140 ft clear (Wikipedia)',
    Retrofit: 'seismic retrofit, deck and superstructure rehabilitation after the Zampa bridge opened in 2003',
    Model: 'alignment from OpenStreetMap, whose pier outlines fall within 5 m of the HAER span lengths; truss spacing (17 m), the south viaduct’s columns and the construction start are estimated'
  },
  sources: CQ_SRC
};

// ------------------------------------------------------------ Alfred Zampa Memorial Bridge (2003)
// Wikipedia: suspension bridge, 3,465 ft long, 84 ft wide, main span 2,387 ft, towers 410 ft,
// 148 ft clear; "consists of the south anchorage, a transition pier, the South and North
// towers, and the north anchorage. It has spans of 147 m, 728 m, and 181 m"; dedicated Nov 8,
// opened Nov 11, 2003. Overture's westbound bridge segment is 1,078 m (38.056220 → 38.065951);
// the two towers are OSM outlines (337 and 363 m², 724.8 m apart — the 728 m main span), 170 m
// and 895 m along it, so the 181 m north side span ends exactly at the segment's north end and
// the south anchorage stands 21 m inside its south end (3DEP: water from 50 m to 950 m).
const ZAMPA_S: V2 = [-122.225941, 38.05622];
const ZAMPA_N: V2 = [-122.226682, 38.065951];
const ZAMPA_TOWERS: V2[] = [[-122.226138, 38.057753], [-122.226599, 38.064298]];
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
    const yT1 = 168.35; // towers at their OSM outlines: 169.8 m and 894.9 m along the segment
    const y0 = yT1 - 147;
    const yT2 = yT1 + 728;
    const yEnd = y0 + 1056;
    const zd = (y: number) => lerpAt([[0, 44.5], [yT1 + 364, 49.0], [a.length, 48.7]], y);
    const grey = '#C4C8C9';
    const TOP = 410 * FT;
    // the structure's centre line runs ≈6 m west of the traffic lanes' (the path is on the west side): OSM tower outlines
    const br = (a.bearing * Math.PI) / 180;
    b.frame(-6 * Math.cos(br), 6 * Math.sin(br), 0, a.bearing, () => {
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
  // the towers are generic footprints in the building data (120 m prisms): hide them
  replaces: ZAMPA_TOWERS.map(p => {
    const l = lngLatToLocal(ZAMPA_S, p);
    return rect(l[0], l[1], 40, 40);
  }),
  facts: {
    Opened: 'dedicated Nov 8, opened Nov 11, 2003 (westbound I-80 and a bicycle / pedestrian path), replacing the 1927 cantilever',
    Form: 'suspension bridge with concrete towers and an orthotropic steel box deck: spans 147 + 728 + 181 m (main span 2,387 ft); 3,465 ft long, 84 ft wide',
    Towers: '410 ft (125 m); 148 ft clear above the strait',
    Namesake: 'Al Zampa, an ironworker on the 1927 Carquinez Bridge and the Golden Gate Bridge',
    Model: 'alignment and tower positions from OpenStreetMap (towers 725 m apart); tower sections, anchorage blocks, cable sag and deck heights estimated; construction start from the Jan 2000 contract award'
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
// the I-780 connector that leaves the 2007 span over the Benicia shore (Overture motorway segment; 3DEP ground 46 m at its west end)
const BM07_BRANCH: V2[] = [[-122.126179, 38.04858], [-122.126352, 38.048719], [-122.126691, 38.049142], [-122.127368, 38.049894], [-122.127764, 38.050343], [-122.127974, 38.050554], [-122.128193, 38.050733], [-122.128398, 38.050868], [-122.128686, 38.05103], [-122.128895, 38.051126], [-122.129159, 38.051221], [-122.129433, 38.051302], [-122.129726, 38.051363], [-122.130008, 38.051396]];
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
    viaduct(b, BM07_PATH[0], BM07_BRANCH, zd(d[13]) - 0.3, 46.7, 12, conc, 60);
  },
  facts: {
    Opened: 'Aug 25, 2007 (construction from late 2001; US$1.3 billion), east of the railroad bridge; named for Congressman George Miller',
    Form: '1.7 mi lightweight-concrete segmental box girder — the largest of its kind in California — carrying five northbound lanes',
    Model: 'LOW CONFIDENCE — alignment from OpenStreetMap (with the I-780 connector at the Benicia end); pier spacing (160 m), girder depths and deck heights estimated'
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
const FR_SRC = [NRHP('66000239', true), NRHP('70000150'), WIKI + 'Fort_Ross,_California', 'https://www.parks.ca.gov/?page_id=449'];

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
    Founded: '1812 by Ivan Kuskov of the Russian-American Company, who brought 25 Russians and 80 Alaskans to build houses and a stockade at Metini, in Kashaya Pomo country',
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
    Fire: 'its roof was damaged in the fires of 1970; opened as a house museum in 2010',
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
    Later: 'sold in 1881 (hay barn, winery, blacksmith shop); bought by the California Historic Landmarks League in 1903 and restored by the State in 1911–13',
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
  // chapel and convento are one OSM footprint whose centroid lies in the convento
  replaces: [rotRing(rect(0, 0, 13.5, 39.5), 93.9, 21.2, -18.8)],
  facts: {
    Built: 'the padres’ quarters: three adobe buildings ready for roofing at the end of 1824 melted in the rains; the rebuilt convento had 27 rooms by 1832',
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
          b.tri([-3.2, 0.26, 10.0], [3.2, 0.26, 10.0], [0, 0.26, 11.4]).tri([-3.2, -0.26, 10.0], [3.2, -0.26, 10.0], [0, -0.26, 11.4]);
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
    Form: 'Mission Revival in local basalt: two storeys, four identical fronts each with an arched doorway, a bell cupola and tile roofs; the fire department’s horse-drawn wagons once left by any side',
    Model: OSM_NOTE + '; heights scaled from a photograph (eaves ≈8.8 m, cupola ≈13.9 m)'
  },
  sources: [WIKI + 'Sonoma_City_Hall', PLAZA_SRC]
};

// ------------------------------------------------------------ Rancho Petaluma Adobe
// National Register form (70000151): "the two-story house is built in [adobe] … form three sides of
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
  // the three wings, not the courtyard (the U-shaped footprint's centroid lies in the main wing)
  replaces: [rotRing(rect(0, 3.7, 16, 61.4), 26.0), rotRing(rect(16.45, 27.2, 18.9, 14.6), 26.0), rotRing(rect(16.4, -10.9, 18.9, 14), 26.0)],
  facts: {
    Built: '1836–46 for Mariano Vallejo as the headquarters of Rancho Petaluma — the largest privately owned adobe building in California',
    Form: 'two storeys of adobe on redwood framing around a courtyard about 200 × 145 ft, walls 20 ft high, with broad two-storey verandas and a low shingled roof',
    Remains: 'the standing half: Vallejo sold it about 1857 and the south-east half decayed; the Native Sons of the Golden West bought the rest in 1910; now a state historic park',
    Model: OSM_NOTE + ' (main wing 60 × 15 m); the lost south-east half is not modelled (no plan or date of loss found); roof and veranda details from photographs'
  },
  sources: [WIKI + 'Rancho_Petaluma_Adobe', NRHP('70000151')]
};

// =================================================================== BENICIA AND MARE ISLAND

// ------------------------------------------------------------ Benicia Capitol
// NRHP 71000204: "a two-story structure of red brick … 'Greek Revival' style with white
// painted fluted columns supporting a triangular pediment, severe decorative cornice, brick
// masonry bearing walls … broad granite exterior stairs; classical entrance with a general
// temple appearance". Wikipedia: built 1852 as Benicia's city hall; the Legislature sat here
// from Feb 3, 1853 to Feb 24, 1854. OSM outline 28.3 × 15.2 m (stairs and cornice included),
// LiDAR height 9.3 m; West G Street lies 28 m to the south-south-west, so the portico faces it.
const beniciaCapitol: Landmark = {
  id: 'benicia_capitol',
  name: 'Benicia Capitol',
  kind: 'building',
  built: [1852.0, 1852.95],
  end: 9999,
  anchor: [-122.158789, 38.05015],
  build: b =>
    b.frame(0, 0, 0, 209.9, () => {
      // +y = the portico front on West G Street
      const brick = '#9A4B3A';
      const white = '#EEE9DD';
      b.color(brick).box(0, -3.5, -1, 13.6, 21.3, 10.3, {top: false});
      for (const sx of [-1, 1]) b.box(sx * 5.9, 8.65, -1, 1.8, 3, 9.4);
      b.color('#40342C').box(0, 7.2, 1.2, 10, 0.1, 7.2);
      b.color(white);
      for (const sx of [-1, 1]) b.cylinder(sx * 1.9, 9.6, 0.55, 1.2, 8.4, 10);
      b.box(0, 8.65, 8.4, 13.9, 3.2, 0.9);
      b.color('#8E8B84').gable(0, -2.0, 15.0, 25.3, 9.3, 2.6, true);
      b.color(white).tri([-7.5, 10.7, 9.3], [7.5, 10.7, 9.3], [0, 10.7, 11.9]);
      b.color('#BFB8AA').box(0, 12.2, -1, 9, 4, 2.2);
      b.color(brick).box(-4.5, -9, 10.2, 0.9, 0.9, 2.2).box(4.5, -9, 10.2, 0.9, 0.9, 2.2);
    }),
  replaces: [rotRing(rect(0, 0, 16.2, 29.3), 209.9)],
  facts: {
    Built: '1852 as Benicia’s city hall; California’s third capitol — the Legislature met here Feb 3, 1853 – Feb 24, 1854, then moved to Sacramento',
    Form: 'two-storey red-brick temple front: two fluted white columns between brick piers under a pediment, granite stairs (National Register)',
    Today: 'the only pre-Sacramento capitol that remains; restored as a state historic park',
    Model: OSM_NOTE + ' (28.3 × 15.2 m with stairs and cornice); cornice height from the LiDAR-derived OSM height (9.3 m); pediment and portico proportions from a photograph'
  },
  sources: [WIKI + 'Benicia_Capitol_State_Historic_Park', NRHP('71000204')]
};

// ------------------------------------------------------------ Benicia Arsenal: the Camel Barns
// NRHP 76000534: "Camel Barn (Building #7) — This two story sandstone structure was built in
// 1854. Its walls are 2′6″ thick and the gabled roof is of corrugated iron. The building
// measures 40.6′ × 100′ … Seven large arched double doors led to ground-floor stables on the
// northwest side … originally constructed as a storehouse but was converted in 1863 to stable
// a herd of camels"; Building 9 the same; a smaller building stands "between the two Camel
// Barns". OSM: 31.0 × 14.2 m and 31.4 × 13.5 m on a 22° axis, 64 m apart.
const camelBarns: Landmark = {
  id: 'benicia_arsenal_camel_barns',
  name: 'Benicia Arsenal — Camel Barns',
  kind: 'building',
  built: [1853.5, 1855.0],
  end: 9999,
  anchor: [-122.134222, 38.053092],
  build: b => {
    const stone = '#C5AE88';
    const barn = (cx: number, cy: number, brg: number) =>
      b.frame(cx, cy, 0, brg, () => {
        b.color(stone).box(0, 0, -1.5, 40.6 * FT, 100 * FT, 9, {top: false});
        b.color('#8A8D8E').gable(0, 0, 40.6 * FT + 0.8, 100 * FT + 0.6, 7.5, 3.0, true);
        b.color(stone).tri([-6.19, 15.25, 7.5], [6.19, 15.25, 7.5], [0, 15.25, 10.5]).tri([-6.19, -15.25, 7.5], [6.19, -15.25, 7.5], [0, -15.25, 10.5]);
        b.color('#4B4038');
        for (let y = -12.6; y <= 12.7; y += 4.2) b.box(-6.22, y, 0, 0.1, 2.4, 3.1);
      });
    barn(0, 0, 22.2);
    barn(26.7, 64.0, 22.6);
    b.frame(13.7, 34.8, 0, 21.9, () => {
      b.color(stone).box(0, 0, -1, 11.0, 11.6, 5.2, {top: false});
      b.color('#8A8D8E').hip(0, 0, 11.6, 12.2, 4.2, 2.0);
    });
  },
  replaces: [rotRing(rect(0, 0, 15, 32), 22.2), rotRing(rect(0, 0, 15, 32.4), 22.6, 26.7, 64.0), rotRing(rect(0, 0, 12, 12.6), 21.9, 13.7, 34.8)],
  facts: {
    Built: 'two sandstone storehouses of the Benicia Arsenal (Buildings 7 and 9), 1853–55; the National Register form dates Building 7 to 1854',
    Camels: 'the Army’s experimental camel herd was stabled here in 1863–64 before it was auctioned off',
    Form: 'two storeys, 40.6 × 100 ft, walls 2 ft 6 in thick, gabled roofs; seven arched double doors on the north-west side',
    Today: 'the Museum of History Benicia',
    Model: OSM_NOTE + '; eaves and ridge heights estimated (7.5 / 10.5 m); the small building between the barns from its OSM outline'
  },
  sources: [NRHP('76000534'), WIKI + 'Benicia_Arsenal']
};

// ------------------------------------------------------------ St. Peter's Chapel, Mare Island
// Wikipedia: Albert Sutton's plan of 1900, "a wood-framed, one-story, Shingled Gothic-style,
// cruciform church building, with a steep front gabled roof over a rectangular nave, a
// cross-gabled chancel, and a rectangular sanctuary"; first service Oct 6, dedicated Oct 13,
// 1901. OSM outline in a 95.5° frame (front on Walnut Avenue, east): nave 10.4 × 15.4 m,
// chancel 16 × 8 m, sanctuary 3.8 × 3.9 m, the tower and porch at the north-east corner.
const stPetersChapel: Landmark = {
  id: 'st_peters_chapel_mare_island',
  name: 'St. Peter’s Chapel, Mare Island',
  kind: 'building',
  built: [1900.95, 1901.78],
  end: 9999,
  anchor: [-122.270431, 38.094272],
  build: b =>
    b.frame(0, 0, 0, 95.5, () => {
      // +y = east (the front), +x = south
      const shingle = '#6B4A37';
      const roof = '#5C4838';
      b.color(shingle).box(1.8, 5.6, -1, 10.4, 15.4, 4.4, {top: false});
      b.color(roof).gable(1.8, 5.6, 11.2, 16.0, 3.4, 5.6, true);
      b.color(shingle).tri([-3.4, 13.32, 3.4], [7.0, 13.32, 3.4], [1.8, 13.32, 9.0]);
      b.color('#E9E4D8').box(1.8, 13.36, 3.0, 2.6, 0.1, 3.0);
      b.color(shingle).box(1.0, -6, -1, 16, 8, 4.4, {top: false});
      b.color(roof).gable(1.0, -6, 16.6, 8.6, 3.4, 4.6, false);
      b.color(shingle).box(1.1, -11.7, -1, 3.8, 3.9, 4.2, {top: false});
      b.color(roof).gable(1.1, -11.7, 4.4, 4.3, 3.2, 2.0, true);
      // corner tower with a flared spire, gabled porch in front of it
      b.color(shingle).box(-5.1, 10.6, -1, 4.0, 4.0, 8.5, {top: false});
      b.color('#E9E4D8').box(-5.1, 10.6, 5.6, 4.1, 4.1, 1.2);
      b.color(roof).pyramid(rect(-5.1, 10.6, 5.2, 5.2), 7.5, [-5.1, 10.6, 10.5]);
      b.pyramid(rect(-5.1, 10.6, 2.6, 2.6), 9.2, [-5.1, 10.6, 14.0]);
      b.color(shingle).box(-5.1, 13.4, -0.5, 3.4, 1.8, 3.3, {top: false});
      b.color(roof).gable(-5.1, 13.4, 3.8, 2.2, 2.8, 1.6, true);
    }),
  replaces: [rotRing(rect(1.0, 0.1, 17, 28.5), 95.5)],
  facts: {
    Built: 'designed by Albert Sutton (1900); first service Oct 6, dedicated Oct 13, 1901 — the oldest Navy chapel in the United States still standing and the first interdenominational chapel in the armed services',
    Form: 'brown-shingle Gothic: steep nave roof, cross-gabled chancel, corner tower with a flared spire; one of the largest collections of Tiffany windows under one roof',
    Model: OSM_NOTE + '; wall, ridge and spire heights scaled from a photograph (tower ≈4 m wide, spire ≈14 m)'
  },
  sources: [WIKI + 'St._Peter%27s_Chapel,_Mare_Island', NRHP('75002103', true)]
};

// =================================================================== NAPA VALLEY

// ------------------------------------------------------------ Greystone Cellars
// NRHP 78000725 (quoting the 1891 description): "The building is 400 feet long and
// seventy-eight feet in width, with a front projection of 50 x 20 feet, in which is the main
// entrance … a stone tower twenty feet square, extending one story above the [roof]"; three
// storeys of tufa, floors on 24 ft spans; 13 tunnels into the hillside behind. Built for
// William Bourn and Everett Wise, Percy & Hamilton architects, 1889 (Wikipedia).
// OSM outline: 123.5 × 25.4 m on a 324.1° axis, the 17 × 6.2 m entrance block centred on the
// north-east front.
const greystone: Landmark = {
  id: 'greystone_cellars',
  name: 'Greystone Cellars (Culinary Institute of America)',
  kind: 'building',
  built: [1888.0, 1889.6],
  end: 9999,
  anchor: [-122.484672, 38.514364],
  build: b =>
    b.frame(-15.2, 21.0, 0, 324.1, () => {
      // +y = north-west along the building, +x = north-east (the front, toward the highway)
      const tufa = '#9C9484';
      const tufaDk = '#8D8575';
      const slate = '#666B6F';
      b.color(tufa).box(0, 0, -4, 25.4, 123.5, 16, {top: false});
      b.color(slate).hip(0, 0, 26.4, 124.5, 12, 4.5);
      // stone cross-gables on the front, entrance block and the tower
      for (const y of [-34, 34]) {
        b.color(tufaDk).box(12.5, y, -4, 1.4, 10, 17.5, {top: false});
        b.color(slate).gable(11.0, y, 5.6, 10.6, 13.5, 2.6, false);
        b.color(tufaDk).tri([13.22, y - 5, 13.5], [13.22, y + 5, 13.5], [13.22, y, 16.1]);
      }
      b.color(tufa).box(15.6, 0, -4, 6.2, 17, 16.5, {top: false});
      b.color(slate).hip(15.6, 0, 7.0, 17.8, 12.5, 2.2);
      b.color(tufaDk).box(15.6, 0, -4, 20 * FT, 20 * FT, 22, {top: false});
      b.color(slate).pyramid(rect(15.6, 0, 20 * FT + 1, 20 * FT + 1), 18, [15.6, 0, 20.6]);
      b.color(tufaDk).box(12.0, 3.9, 12, 1.3, 1.3, 8.5);
      b.color('#3C3632').box(18.72, 0, 0, 0.1, 3.4, 4.6);
    }),
  replaces: [rotRing(rect(3, 0, 33, 125.5), 324.1, -15.2, 21.0)],
  facts: {
    Built: '1888–89 for William Bourn II and Everett Wise as a cooperative wine cellar (Percy & Hamilton, architects); George Percy called it the largest wine cellar in California, if not the world',
    Size: '400 × 78 ft, three storeys of local tufa, with a 50 × 20 ft entrance block and a tower 20 ft square rising a storey above the roof; thirteen tunnels run into the hill behind (National Register)',
    Owners: 'leased by the Christian Brothers in 1940, bought in 1945 and used for sparkling wine 1950–89; sold to the Culinary Institute of America in 1993',
    Model: OSM_NOTE + ' (123.5 × 25.4 m); eaves, ridge and tower heights estimated from a photograph (12 / 16.5 / 20.6 m); construction start estimated'
  },
  sources: [NRHP('78000725'), WIKI + 'The_Culinary_Institute_of_America_at_Greystone']
};

// ------------------------------------------------------------ Inglenook château
// Wikipedia (Inglenook): Gustave Niebaum's winery by Hamden McIntyre. OSM outline: 66.3 ×
// 19.5 m on a 324.2° axis with a 13 × 8 m wing behind. No published heights: massing above
// the eaves (roof, entrance gable, cupola) from a photograph.
const inglenook: Landmark = {
  id: 'inglenook_chateau',
  name: 'Inglenook château',
  kind: 'building',
  built: [1883.0, 1887.5],
  end: 9999,
  anchor: [-122.431269, 38.454461],
  build: b =>
    b.frame(1.25, 1.7, 0, 324.2, () => {
      // +x = north-east (the front)
      const stone = '#8F8F78';
      const roof = '#A04A3A';
      b.color(stone).box(0, 0, -1.5, 19.5, 66.3, 10.5, {top: false});
      b.color(roof).hip(0, 0, 20.5, 67.3, 9, 3.6);
      b.color(stone).box(9.2, 0, -1.5, 3.4, 9, 13, {top: false});
      b.color(roof).gable(7.0, 0, 7.8, 9.6, 11.5, 2.5, false);
      b.color('#E9DFB8').tri([10.92, -4.5, 11.5], [10.92, 4.5, 11.5], [10.92, 0, 14.0]);
      for (const y of [-27, 27]) {
        b.color(stone).box(9.4, y, -1.5, 1.6, 8, 12, {top: false});
        b.color(roof).gable(8.0, y, 4.4, 8.6, 10.5, 2.4, false);
      }
      // cupola
      b.color('#E9DFB8').box(4.5, 0, 12.0, 2.6, 2.6, 3.6);
      b.color(roof).pyramid(rect(4.5, 0, 3.4, 3.4), 15.6, [4.5, 0, 18.0]);
      b.color('#6E6E64').beam([4.5, 0, 18.0], [4.5, 0, 19.2], 0.12);
      b.color(stone).box(-13.8, 1.25, -1.5, 8, 13, 8.5, {top: false});
      b.color(roof).hip(-13.8, 1.25, 8.8, 13.8, 7, 2.5);
      b.color('#3C3632').box(10.95, 0, 0, 0.1, 3.0, 3.6);
    }),
  replaces: [rotRing(rect(-4, 0, 29, 67.5), 324.2, 1.25, 1.7)],
  facts: {
    Built: 'the stone winery of Gustave Niebaum’s Inglenook estate at Rutherford, designed by his winemaker Hamden McIntyre as a gravity-flow cellar',
    Later: 'sold to Allied Grape Growers in 1964; Francis Ford Coppola bought much of the estate in 1975 and later reunited it with the château',
    Model: OSM_NOTE + ' (66.3 × 19.5 m); LOW CONFIDENCE construction years (commonly given as 1883–87, not confirmed in the sources used); heights and roof forms estimated from a photograph'
  },
  sources: [WIKI + 'Inglenook_(winery)']
};

// ------------------------------------------------------------ Rhine House (Beringer)
// NRHP 72000242: "Approximately 45′ × 60′. Ceilings 12′ high. 2½ stories high … Constructed
// of white oak imported from Germany and stone, hand cut from Napa County quarry …
// Pennsylvania slate roof"; Wikipedia: built 1883–84, Albert Schroepfer. OSM
// outline: main block 27.1 × 13.4 m on a 328.6° axis (front toward Main Street, north-east)
// and a 15.3 × 9.8 m wing behind.
const rhineHouse: Landmark = {
  id: 'beringer_rhine_house',
  name: 'Rhine House (Beringer Vineyards)',
  kind: 'building',
  built: [1883.0, 1884.5],
  end: 9999,
  anchor: [-122.479908, 38.510165],
  build: b =>
    b.frame(0.4, -0.7, 0, 328.6, () => {
      // +x = north-east (the front)
      const stone = '#B8A98C';
      const timber = '#D9CBA8';
      const slate = '#5F6468';
      b.color(stone).box(0, 0, -1, 13.4, 27.1, 5.5, {top: false});
      b.color(timber).box(0, 0, 4.5, 13.4, 27.1, 4.0, {top: false});
      b.color(slate).hip(0, 0, 14.4, 28.1, 8.5, 5.0);
      // central tower bay with a steep pyramid roof, a gabled bay either side
      b.color(stone).box(6.9, 0, -1, 2.6, 4.6, 13, {top: false});
      b.color(slate).pyramid(rect(6.9, 0, 3.4, 5.4), 12, [6.9, 0, 17.5]);
      for (const y of [-8, 8]) {
        b.color(timber).box(6.4, y, 4.5, 1.2, 5, 5.5, {top: false});
        b.color(slate).gable(5.0, y, 4.4, 5.6, 10, 2.6, false);
      }
      b.color(stone).box(-11.0, -11.3, -1, 9.8, 15.3, 7, {top: false});
      b.color(slate).hip(-11.0, -11.3, 10.6, 16.1, 6, 3.0);
    }),
  replaces: [rotRing(rect(-4, -3.8, 26, 34.5), 328.6, 0.4, -0.7)],
  facts: {
    Built: '1883–84 for Frederick Beringer (Albert Schroepfer, architect)',
    Form: 'about 45 × 60 ft, 2½ storeys: Napa stone below, half-timbered upper walls, Pennsylvania slate roofs (National Register)',
    Model: 'LOW CONFIDENCE massing — ' + OSM_NOTE + ' (main block 27 × 13 m with later additions); towers, gables and all heights simplified from a photograph'
  },
  sources: [NRHP('72000242'), WIKI + 'Beringer_Vineyards']
};

// ------------------------------------------------------------ Bale Grist Mill
// Wikipedia / State Parks: built 1846 for Dr. Edward Bale, 36 ft overshot wheel (the 1972
// National Register form says 45 ft; a 2011 photograph shows the wheel reaching the eaves of
// the three-storey mill, i.e. ≈11 m). OSM outlines on a 79.7° axis: mill 12.9 × 7.4 m with a
// bay on its north side, granary 20.6 × 8 m to the south, its false front toward the highway.
const baleMill: Landmark = {
  id: 'bale_grist_mill',
  name: 'Bale Grist Mill',
  kind: 'building',
  built: [1846.0, 1846.9],
  end: 9999,
  anchor: [-122.50925, 38.541165],
  build: b =>
    b.frame(-0.03, 0.15, 0, 79.7, () => {
      // +y = east-north-east (toward the highway), +x = south
      const wood = '#7A6A58';
      const roof = '#5F564B';
      b.color(wood).box(0, 0, -1.5, 7.4, 12.9, 11, {top: false});
      b.color(roof).gable(0, 0, 8.0, 13.5, 9.5, 2.3, true);
      b.color(wood).tri([-3.7, 6.47, 9.5], [3.7, 6.47, 9.5], [0, 6.47, 11.8]).tri([-3.7, -6.47, 9.5], [3.7, -6.47, 9.5], [0, -6.47, 11.8]);
      b.box(-5.8, -1.3, -1.5, 3.6, 6.0, 8);
      b.box(5.5, 3.0, -1, 3.6, 6, 8);
      b.box(11.25, 4.6, -1, 8.0, 20.6, 8.5, {top: false});
      b.color(roof).gable(11.25, 4.6, 8.6, 20.6, 7.5, 2.3, true);
      b.color(wood).box(11.25, 14.95, 0, 8.6, 0.3, 10.3);
      // overshot wheel, 36 ft, on the north side; flume on trestles from the mill pond
      const R = 18 * FT;
      const cx = -9.4;
      const cz = R + 0.3;
      b.color('#5A4A3C');
      for (let i = 0; i < 16; i++) {
        const a0 = ((i + 0.5) / 16) * Math.PI * 2;
        const a1 = ((i + 1.5) / 16) * Math.PI * 2;
        b.beam([cx + Math.cos(a0) * R, 2.4, cz + Math.sin(a0) * R], [cx + Math.cos(a1) * R, 2.4, cz + Math.sin(a1) * R], 0.9, 0.3);
        if (i % 2 === 0) b.beam([cx, 2.4, cz], [cx + Math.cos(a0) * R, 2.4, cz + Math.sin(a0) * R], 0.2);
      }
      b.beam([cx, 0.6, cz], [cx, 3.2, cz], 0.5);
      b.color(wood).beam([cx, 2.4, 2 * R + 0.9], [cx - 18, -21.6, 2 * R + 1.6], 1.0, 0.6);
      for (let t = 0.15; t < 1; t += 0.2) b.beam([cx - 18 * t, 2.4 - 24 * t, -1], [cx - 18 * t, 2.4 - 24 * t, 2 * R + 0.8], 0.3);
    }),
  replaces: [rotRing(rect(0, 0, 9, 14.5), 79.7, -0.03, 0.15), rotRing(rect(11.25, 4.6, 9.2, 21.8), 79.7, -0.03, 0.15), rotRing(rect(-5.8, -1.3, 5, 7), 79.7, -0.03, 0.15)],
  facts: {
    Built: '1846 for Dr. Edward Turner Bale on his Rancho Carne Humana; mill and granary of local Douglas fir and redwood',
    Wheel: '36 ft overshot wheel fed by a wooden flume from Mill Creek — one of only two water-driven mills left west of the Mississippi',
    Park: 'deeded to the Native Sons of the Golden West, who restored it in the late 1960s and early 1970s; now a state historic park',
    Model: OSM_NOTE + '; building heights from a photograph; the wheel’s exact place on the north side and the flume’s line are approximate. The 1972 National Register form gives the wheel as 45 ft'
  },
  sources: [WIKI + 'Bale_Grist_Mill_State_Historic_Park', NRHP('72000240')]
};

// ------------------------------------------------------------ Napa County Courthouse
// NRHP 92000778: "High Victorian Italianate style two-story rectangular building (86 feet x
// 95 feet) constructed of brick and stucco … hipped roof … A Moorish Gothic and Classic motif
// tower rose from the front, or eastern end, of the Courthouse and was twenty feet square at
// its base. A bulb-shaped cupola rested on top"; "removing the tower and adding a pediment in
// 1931"; the addition behind it was built in 1978 (before it, the 1878 jail). OSM: one
// footprint 57 × 31 m on a 58.3° axis, 11.9 m high: the 1878 block is its north-east 26 m.
const NAPA_CH: V2 = [-122.285709, 38.297629];
const napaCourthouse: Landmark = {
  id: 'napa_county_courthouse',
  name: 'Napa County Courthouse (1878)',
  kind: 'building',
  built: [1877.6, 1878.9],
  end: 9999,
  anchor: NAPA_CH,
  build: b =>
    b.frame(2.7, 1.6, 0, 58.3, () => {
      // +y = north-east (the front on Brown Street)
      const stucco = '#DCD5BF';
      b.color(stucco).box(0, 15.4, -1, 95 * FT, 86 * FT, 12.5, {top: false});
      b.color('#9B4D3E').hip(0, 15.4, 95 * FT + 1.6, 86 * FT + 1.6, 11.5, 3.0);
      b.color(stucco).box(0, 28.9, 0, 9.4, 0.9, 11.5);
      b.tri([-4.7, 29.36, 11.5], [4.7, 29.36, 11.5], [0, 29.36, 13.8]);
      b.color('#BDB6A4').box(0, 30.6, -0.5, 8, 2.6, 2.0);
    }),
  replaces: [rotRing(rect(0, 0, 33, 59), 58.3, 2.7, 1.6)],
  facts: {
    Built: '1878 (Samuel and Joseph Newsom with Ira Gilchrist, architects), replacing the 1856 courthouse',
    Form: 'High Victorian Italianate, two storeys of brick and stucco, 86 × 95 ft, under a hipped roof (National Register)',
    Tower: 'a tower 20 ft square with a bulb-shaped cupola rose over the east front until 1931, when it was taken down and the pediment added — not modelled (no height found)',
    Later: 'addition of 1978 behind; damaged by the South Napa earthquake of 2014',
    Model: OSM_NOTE + ' (the north-east 26 m of the block); wall height from the OSM height (11.9 m); roof and pediment from a photograph; construction start estimated'
  },
  sources: [NRHP('92000778'), WIKI + 'Napa_County_Courthouse_Plaza']
};
const napaCourthouseAnnex: Landmark = {
  id: 'napa_county_courthouse_annex',
  name: 'Napa County Courthouse — 1978 addition',
  kind: 'building',
  built: [1977.0, 1978.5],
  end: 9999,
  anchor: NAPA_CH,
  build: b => b.frame(2.7, 1.6, 0, 58.3, () => b.color('#D3CCB8').box(0, -13.1, -1, 31, 30.8, 10.5)),
  facts: {
    Built: 'the 1978 addition on the site of the 1878 jail (National Register form)',
    Model: 'LOW CONFIDENCE — plain block on the south-west 31 m of the OSM footprint; height estimated; construction start estimated'
  },
  sources: [NRHP('92000778')]
};

// ------------------------------------------------------------ Napa Valley Opera House
// NRHP 73000414: "a two-story brick building with a frontage of 60 feet and a depth of 100
// feet. The second story contains the Napa Opera House". OSM outline 37.3 × 20.2 m on a
// 57.8° axis (Main Street lies to the south-west); cornice height scaled from the frontage in
// a 2010 photograph (≈12.3 m).
const napaOperaHouse: Landmark = {
  id: 'napa_valley_opera_house',
  name: 'Napa Valley Opera House',
  kind: 'building',
  built: [1879.7, 1880.12],
  end: 9999,
  anchor: [-122.285516, 38.299678],
  build: b =>
    b.frame(0, 0, 0, 237.8, () => {
      // +y = south-west (Main Street)
      const wall = '#B9A7A3';
      b.color(wall).box(0, 3.4, -0.5, 20.2, 100 * FT, 12.8);
      b.color('#A3938F').box(0, -15.25, -0.5, 20.2, 6.8, 10);
      b.color('#4A5750').box(0, 18.68, 0.2, 17.6, 0.12, 3.9);
      b.color('#D2C6C2').box(0, 18.9, 11.5, 20.6, 0.6, 0.8);
      b.tri([-3.4, 19.0, 12.3], [3.4, 19.0, 12.3], [0, 19.0, 13.3]);
      for (const x of [-9.6, -3.4, 3.4, 9.6]) b.beam([x, 18.9, 12.3], [x, 18.9, 14.2], 0.25);
    }),
  replaces: [rotRing(rect(0, 0, 21.2, 38.3), 237.8)],
  facts: {
    Built: 'late 1879 (Samuel and Joseph Newsom, architects); opened Feb 13, 1880 with HMS Pinafore — the opera house is the upper floor',
    Form: 'two-storey Italianate brick, 60 ft on Main Street by 100 ft deep; auditorium 54½ × 76 ft (National Register)',
    Later: 'closed in 1914 (National Register form); since restored as a theatre',
    Model: OSM_NOTE + ' (37.3 × 20.2 m with the rear addition); cornice height scaled from a photograph; construction months estimated'
  },
  sources: [NRHP('73000414'), WIKI + 'Napa_Valley_Opera_House']
};

// ------------------------------------------------------------ Monticello Dam
// Wikipedia: concrete arch dam, 304 ft high, crest 1,023 ft long, 100 ft thick at the base,
// built 1953–57 (topped out Nov 7, 1957); the Glory Hole spillway is "72 ft in diameter at
// lake level and narrows down to about 28 ft", its lip at 440 ft. The crest line is fitted to
// the USGS 3DEP surface (a 5 m grid of samples shows the crest at ≈139–140 m as an arc of
// radius ≈151 m, convex upstream, centred 115 m east and 8 m north of the anchor), and agrees
// with the OSM dam line (38.5122–38.5146 N). The spillway is the OSM outline "Morning Glory
// Spillway Opening" (22.6 m across at 38.512258 N, 122.104901 W, ≈70 m from the dam).
const DAM: V2 = [-122.1042, 38.5133];
const monticelloDam: Landmark = {
  id: 'monticello_dam',
  name: 'Monticello Dam and the Glory Hole',
  kind: 'monument',
  built: [1953.5, 1957.85],
  end: 9999,
  anchor: DAM,
  build: b => {
    // absolute heights: the crest stands at 139 m whatever the coarse lookup returns here
    const base = elevationAt(DAM[0], DAM[1]) - 0.5;
    const zc = 139.0 - base;
    const H = 304 * FT;
    const C: V2 = [115.4, 8];
    const R = 151.4;
    const half = (1023 * FT) / 2 / R;
    const n = 24;
    const arc = (r: number): V2[] => Array.from({length: n + 1}, (_, i) => [C[0] - r * Math.cos(-half + (2 * half * i) / n), C[1] + r * Math.sin(-half + (2 * half * i) / n)] as V2);
    const up = arc(R + 1.83);
    const dnTop = arc(R - 1.83);
    const dnBase = arc(R + 1.83 - 100 * FT);
    b.color('#BEB9AD').wallProfile(up, zc - H, zc);
    b.ribbon(dnBase.map(p => [p[0], p[1], zc - H] as V3), dnTop.map(p => [p[0], p[1], zc] as V3));
    b.color('#A9A49A').ribbon(up.map(p => [p[0], p[1], zc] as V3), dnTop.map(p => [p[0], p[1], zc] as V3));
    b.color('#BEB9AD');
    for (const i of [0, n]) b.quad([up[i][0], up[i][1], zc - H], [dnBase[i][0], dnBase[i][1], zc - H], [dnTop[i][0], dnTop[i][1], zc], [up[i][0], up[i][1], zc]);
    // Glory Hole: 72 ft lip at 440 ft, narrowing to 28 ft
    const lip = 440 * FT - base;
    b.frustum(-61.1, -115.2, 36 * FT + 1.2, 36 * FT, lip - 45, lip, 20, false);
    b.color('#4E5357').loft([circle(-61.1, -115.2, 36 * FT, 20), circle(-61.1, -115.2, 14 * FT, 20)], [lip, lip - 18], {top: false});
  },
  facts: {
    Built: '1953–57 by the Bureau of Reclamation for the Solano Project, drowning the town of Monticello under Lake Berryessa; topped out Nov 7, 1957',
    Dam: 'concrete arch 304 ft high, crest 1,023 ft long, 100 ft thick at the base',
    'Glory Hole': 'morning-glory spillway 72 ft across at the lip (440 ft above sea level), narrowing to 28 ft; it last spilled in February 2025',
    Model: 'crest arc (radius ≈151 m) fitted to the USGS 3DEP surface and the OpenStreetMap dam line; spillway position from OpenStreetMap; crest thickness (12 ft) and the face profile are estimated, and the mesh keeps the crest’s full length at every depth, so the canyon walls of the coarse terrain hide or expose parts of it'
  },
  sources: [WIKI + 'Monticello_Dam']
};

// =================================================================== SANTA ROSA, PETALUMA, THE COAST

// ------------------------------------------------------------ Church of One Tree
// Wikipedia: built 1873/74 for the First Baptist Church from a single redwood felled near
// Guerneville (275 ft tall, 18 ft through, 78,000 board feet); it stood downtown on B Street
// and was moved to Juilliard Park. OSM outline at the park: body 18.5 × 13 m on a 343.4° axis
// with the tower projecting at the south-east corner. A c. 1918 postcard gives the form
// (gable with wall dormers, corner tower and spire) and the proportions: eaves ≈5.5 m, ridge
// ≈11.5 m, spire ≈21 m (the "70-foot steeple").
const churchOfOneTree: Landmark = {
  id: 'church_of_one_tree',
  name: 'Church of One Tree (at Juilliard Park)',
  kind: 'building',
  built: [1957.0, 1957.6],
  end: 9999,
  anchor: [-122.714054, 38.436015],
  build: b =>
    b.frame(-0.93, 2.98, 0, 343.4, () => {
      // +y = north-north-west (Sonoma Avenue), +x = east
      const white = '#EDEBE4';
      const roof = '#7A5548';
      b.color(white).box(0, 0, -1, 13, 18.5, 6.5, {top: false});
      b.color(roof).gable(0, 0, 13.8, 19.1, 5.5, 6.0, true);
      b.color(white).tri([-6.5, 9.27, 5.5], [6.5, 9.27, 5.5], [0, 9.27, 11.5]).tri([-6.5, -9.27, 5.5], [6.5, -9.27, 5.5], [0, -9.27, 11.5]);
      // four gabled wall dormers on each side
      for (const sx of [-1, 1]) {
        for (const y of [-6, -2, 2, 6]) {
          b.color(white).box(sx * 6.3, y, 5.2, 0.5, 1.4, 1.8);
          b.color(roof).gable(sx * 5.6, y, 2.0, 1.7, 7.0, 0.9, false);
        }
      }
      b.color(white).box(5.44, -10.57, -1, 4.6, 4.6, 11.5);
      b.color(roof).pyramid(ngon(5.44, -10.57, 2.6, 8), 10.5, [5.44, -10.57, 21.0]);
    }),
  replaces: [rotRing(rect(0.6, -1.2, 15.5, 22), 343.4, -0.93, 2.98)],
  facts: {
    Built: '1873–74 for the First Baptist Church of Santa Rosa on B Street, entirely of lumber from one redwood felled near Guerneville (275 ft tall, 18 ft in diameter, 78,000 board feet)',
    Moved: 'to Juilliard Park to save it from demolition (1957 — LOW CONFIDENCE year, not in the sources used); the Ripley Memorial Museum from 1970 to 1998 (Robert Ripley, a Santa Rosa native, featured it in “Believe It or Not!”)',
    Model: OSM_NOTE + ' at the park; heights scaled from a c. 1918 postcard. Only the present site is modelled — the 1873–1957 position on B Street was not located'
  },
  sources: [WIKI + 'Church_of_One_Tree']
};

// ------------------------------------------------------------ DeTurk Round Barn
// NRHP 04000334: "a two-story post and beam frame round barn clad in one-by-eight inch
// redwood beveled shiplap siding with a shingled, broad conical roof topped by a vented wood
// cupola and a copper weathervane punctuating its thin spire. The barn, excluding the spire,
// rises thirty-two feet above grade and is 76′ in diameter"; built 1891 for Isaac DeTurk's
// trotting horses. OSM: a 16-gon 24.2 m across.
const deTurkBarn: Landmark = {
  id: 'deturk_round_barn',
  name: 'DeTurk Round Barn',
  kind: 'building',
  built: [1890.6, 1891.6],
  end: 9999,
  anchor: [-122.725213, 38.440866],
  build: b => {
    const R = 38 * FT;
    b.color('#E7E2D2').cylinder(0, 0, R, -1, 6.3, 24, {top: false});
    b.color('#6B5F52').pyramid(circle(0, 0, R + 0.5, 24), 6.3, [0, 0, 9.4]);
    b.color('#C9A84C').cylinder(0, 0, 1.3, 8.6, 32 * FT - 0.6, 10, {top: false});
    b.dome(0, 0, 1.3, 32 * FT - 0.6, 0.6, 10, 2);
    b.color('#8C7A44').beam([0, 0, 32 * FT], [0, 0, 32 * FT + 3.6], 0.1);
  },
  replaces: [circle(0, 0, 13, 16)],
  facts: {
    Built: '1891 for the winemaker Isaac DeTurk’s trotting horses, across Donahue Street from the old Santa Rosa Winery',
    Form: 'truly round, 76 ft in diameter, two storeys of redwood shiplap under a broad conical roof; 32 ft high to the vented cupola, with a thin spire (National Register)',
    Later: 're-acquired by the city in 1996 and restored (National Register, 2004)',
    Model: 'diameter and height from the National Register form; wall height and spire length estimated; construction months estimated'
  },
  sources: [NRHP('04000334')]
};

// ------------------------------------------------------------ Free Public Library of Petaluma
// NRHP 88000925: "a 60′ by 60′ two-story building on high foundations, topped by a low
// pyramid roof. On three faces of the building the central elements — two-story pedimented
// and columned entrance and side bays — project from the basic square"; Brainerd Jones; built
// 1904, opened early 1906 (Wikipedia). OSM outline in a 25.8° frame: a 19.5 m square, side
// bays projecting 1.1 m, the portico 2.2 m toward Fourth Street.
const petalumaLibrary: Landmark = {
  id: 'petaluma_carnegie_library',
  name: 'Free Public Library of Petaluma (Carnegie library)',
  kind: 'building',
  built: [1904.4, 1906.1],
  end: 9999,
  anchor: [-122.640024, 38.232579],
  build: b =>
    b.frame(0, 0, 0, 25.8, () => {
      // +y = north-north-east (Fourth Street)
      const stone = '#CDBE9B';
      b.color(stone).box(0, 0, -1.5, 19.5, 19.5, 12, {top: false});
      for (const sx of [-1, 1]) b.box(sx * 10.3, 0, -1.5, 1.1, 9.8, 12);
      b.color('#857B6E').hip(0, 0, 20.5, 20.5, 10.5, 2.0);
      b.color('#E0D6BC');
      for (const x of [-3.5, -1.3, 1.3, 3.5]) b.cylinder(x, 11.3, 0.45, 1.6, 8.6, 8);
      b.box(0, 10.7, 8.6, 8.1, 2.3, 1.1);
      b.tri([-4.05, 11.86, 9.7], [4.05, 11.86, 9.7], [0, 11.86, 11.6]);
      b.color(stone).box(0, 10.7, -1.5, 8.1, 2.3, 3.1);
      b.color('#BDB39A').box(0, 12.6, -1, 6, 1.6, 2.2);
    }),
  replaces: [rotRing(rect(0, 1, 22.5, 22.8), 25.8)],
  facts: {
    Built: 'cornerstone 1904, opened early 1906 with a Carnegie grant; Brainerd Jones’s first major commission',
    Form: 'Neo-Classical Revival, 60 × 60 ft, two storeys on a high basement, faced in local stone and Alameda pressed brick, with a four-column pedimented portico',
    Today: 'a Carnegie library until 1976; since then the Petaluma Historical Library and Museum',
    Model: OSM_NOTE + ' (19.5 m square); cornice and roof heights estimated from a photograph'
  },
  sources: [NRHP('88000925'), WIKI + 'Free_Public_Library_of_Petaluma']
};

// ------------------------------------------------------------ St. Teresa of Avila, Bodega
// Wikipedia: "built by shipbuilders in 1860 on land donated by Jasper O'Farrell …
// Archbishop Alemany dedicated the church on June 2, 1861"; "white, wooden church with a
// steeple … on a hilltop overlooking Bodega Highway". OSM outline: nave 19.7 × 9.4 m on a
// 315.5° axis, a 3.5 × 1.3 m tower base on the north-west front (the engaged tower of the
// photographs) and a 6.3 × 4 m sanctuary behind. Heights scaled from a 2023 photograph.
const stTeresaBodega: Landmark = {
  id: 'st_teresa_of_avila_bodega',
  name: 'St. Teresa of Avila Church, Bodega',
  kind: 'building',
  built: [1860.0, 1861.42],
  end: 9999,
  anchor: [-122.972369, 38.346237],
  build: b =>
    b.frame(-0.05, -0.03, 0, 315.5, () => {
      // +y = north-west (the front)
      const white = '#F2F1EC';
      const roof = '#6E6E6C';
      b.color(white).box(0, 0, -1.5, 9.4, 19.7, 7.5, {top: false});
      b.color(roof).gable(0, 0, 10.0, 20.3, 6, 4, true);
      b.color(white).tri([-4.7, 9.87, 6], [4.7, 9.87, 6], [0, 9.87, 10]).tri([-4.7, -9.87, 6], [4.7, -9.87, 6], [0, -9.87, 10]);
      b.box(0, -11.85, -1.5, 6.3, 4, 6, {top: false});
      b.color(roof).gable(0, -11.85, 6.8, 4.3, 4.5, 2.5, true);
      // engaged tower: belfry, parapet with corner pinnacles, octagonal spire and cross
      b.color(white).box(0, 9.4, -1.5, 3.5, 3.5, 17);
      for (const sx of [-1, 1]) for (const sy of [-1, 1]) b.pyramid(rect(sx * 1.45, 9.4 + sy * 1.45, 0.6, 0.6), 15.5, [sx * 1.45, 9.4 + sy * 1.45, 16.9]);
      b.pyramid(ngon(0, 9.4, 1.55, 8), 15.5, [0, 9.4, 21.5]);
      b.color('#D8D5CC').beam([0, 9.4, 21.5], [0, 9.4, 22.7], 0.12).beam([-0.4, 9.4, 22.3], [0.4, 9.4, 22.3], 0.1);
      b.color('#5B4632').box(0, 11.17, 0, 1.4, 0.1, 2.6);
    }),
  replaces: [rotRing(rect(0, -1.5, 11, 26), 315.5, -0.05, -0.03)],
  facts: {
    Built: 'by ship’s carpenters in 1860 on land given by Jasper O’Farrell; dedicated by Archbishop Alemany on June 2, 1861 — the oldest church in continuous use in Sonoma County',
    Form: 'white redwood church with an engaged front tower, belfry and octagonal spire; photographed by Ansel Adams in 1953',
    Model: OSM_NOTE + ' (nave 19.7 × 9.4 m); heights scaled from a 2023 photograph (ridge ≈10 m, spire ≈21.5 m)'
  },
  sources: [WIKI + 'St._Teresa_of_Avila_Church_(Bodega,_California)']
};

// ------------------------------------------------------------ The Sea Ranch: Condominium One and the chapel
// NRHP 05000731 (Condominium 1): designed 1963–64 by Moore, Lyndon, Turnbull and Whitaker,
// built 1965; ten units, "each of the 24-foot square condominium units"; "its large, complex
// form rises from the cliff edge along the slope of an upward-rising hill, terminating in a
// pair of towers at the crest"; unstained redwood boards, shed roofs. OSM outline ≈50 × 48 m.
const CONDO1: V2[] = [[-12.0, -6.9], [5.8, -28.3], [26.7, -11.1], [21.7, -5.0], [24.4, -2.8], [20.4, 2.0], [14.3, -3.1], [18.5, -8.1], [6.7, -17.9], [-3.5, -5.7], [-1.7, -4.2], [-0.3, -5.9], [21.2, 11.8], [25.7, 6.4], [28.3, 8.5], [30.1, 6.3], [36.8, 11.9], [29.1, 21.2], [25.4, 18.2], [22.8, 21.3], [3.4, 5.4], [0.1, 9.4], [-0.9, 8.6], [-4.6, 13.1], [-1.9, 15.4], [-6.0, 20.4], [4.3, 28.8], [2.7, 30.7], [-5.7, 23.8], [-4.8, 22.7], [-13.8, 15.3], [-9.6, 10.2], [-7.9, 11.5], [-3.2, 5.9], [-8.4, 1.7], [-5.6, -1.6]];
const condominiumOne: Landmark = {
  id: 'sea_ranch_condominium_one',
  name: 'Condominium One, The Sea Ranch',
  kind: 'building',
  built: [1964.6, 1965.8],
  end: 9999,
  anchor: [-123.429091, 38.679078],
  build: b => {
    // one roof plane rising inland (north-east) from the cliff edge: 24 ft at the low edge
    const zf = (x: number, y: number) => 5.5 + 0.11 * (x * 0.766 + y * 0.643 + 13.75);
    b.color('#8B8478').wallProfile(CONDO1, -2, CONDO1.map(p => zf(p[0], p[1])), true);
    b.color('#77756F');
    slopedCap(b, CONDO1, zf);
  },
  replaces: [rect(9.5, 1.5, 52, 60)],
  facts: {
    Built: '1965 (designed 1963–64 by Charles Moore, Donlyn Lyndon, William Turnbull and Richard Whitaker — MLTW; Matthew Sylvia, builder): the first unit of the Sea Ranch development',
    Form: 'ten units, each a 24 ft cube framed in heavy fir timbers and clad in unstained redwood boards, gathered around two courts under shed roofs that climb the slope from the cliff edge (National Register, 2005)',
    Model: OSM_NOTE + '; LOW CONFIDENCE massing — the stepped shed roofs and the two towers at the crest are merged into one roof plane rising inland (≈5.5 → 11 m)'
  },
  sources: [NRHP('05000731'), WIKI + 'Condominium_1']
};
const SR_CHAPEL: V2[] = [[0.6, 4.0], [-3.2, 3.3], [-4.8, 1.2], [-4.8, -2.0], [-2.7, -4.6], [0.6, -5.5], [3.8, -4.3], [5.0, -1.1], [4.3, 2.1]];
const seaRanchChapel: Landmark = {
  id: 'sea_ranch_chapel',
  name: 'The Sea Ranch Chapel',
  kind: 'building',
  built: [1984.9, 1985.95],
  end: 9999,
  anchor: [-123.477267, 38.733513],
  build: b => {
    b.color('#8F8A80').prism(SR_CHAPEL, -1, 1.4, {top: false});
    b.color('#8A6F52').pyramid(SR_CHAPEL.map(p => [p[0] * 1.08, p[1] * 1.08] as V2), 1.4, [2.2, 1.2, 8.2]);
    b.color('#5E8F7E').beam([2.2, 1.2, 8.0], [3.6, 2.0, 11.0], 0.2);
  },
  replaces: [rect(0.1, -0.7, 11.5, 11.5)],
  facts: {
    Built: 'completed December 1985, the gift of Sea Ranch residents Robert and Betty Buffum in memory of Kirk Ditzler; non-denominational',
    Form: 'a hand-built sculptural shell of cedar shingles on a stone base, its roof sweeping up to a plume of bronze fins',
    Model: 'LOW CONFIDENCE — ' + OSM_NOTE + ' (≈10 m across); the free-form roof is reduced to a skewed cone and its height (≈8 m, fins to ≈11 m) is estimated from a photograph'
  },
  sources: [WIKI + 'Sea_Ranch,_California']
};

// =================================================================== MONTEZUMA HILLS WIND FARMS

// US Wind Turbine Database v9.1 (USGS / LBNL / ACP, public domain), Solano County: every
// turbine at its database position with the project's online year, hub height and rotor
// diameter; one landmark per project / model group. [id, project, year, model, kW, hub m,
// rotor m, tip m, anchor lon, anchor lat, turbine offsets in metres (x east, y north) …].
// prettier-ignore
const WIND: [string, string, number, string, number, number, number, number, number, number, number[]][] = [
  ["wind_anheuser_busch_fairfield_2011_ge1577_65m", "Anheuser-Busch Fairfield", 2011, "GE Wind GE1.5-77", 1500, 65, 77, 103.6, -122.089287, 38.232296, [0,0]],
  ["wind_anheuser_busch_fairfield_2014_ge185825_80m", "Anheuser-Busch Fairfield", 2014, "GE Wind GE1.85-82.5", 1850, 80, 82.5, 121.3, -122.092079, 38.233505, [0,0]],
  ["wind_high_winds_2003_v8018_60m", "High Winds", 2003, "Vestas V80-1.8", 1800, 60, 80, 100, -121.802868, 38.130889, [24,-231,-212,454,1742,-1785,-212,797,-693,-2576,209,-3128,-1351,2787,881,1677,1775,1007,217,-3007,-1783,-2354,1452,-3372,-2427,1438,-45,1405,900,1416,1672,1114,-185,642,1671,1923,-1487,2133,-1009,2533,-781,1128,1735,-1472,1154,1239,-886,1272,869,-3378,795,-1338,-230,1681,-4,-3518,-1543,2267,-1562,2394,740,1838,-2506,1703,1179,1082,-413,852,1067,332,827,-3232,-11,-2271,-2576,1836,-702,1018,-1831,-2616,-1464,-3257,1550,1668,-1588,2550,-1524,-2980,1652,-1618,-1091,2706,-34,-2633,-2664,2279,1058,189,1093,23,199,-2754,-72,-55,-2498,1593,-80,-2454,1714,34,-1548,-3157,1641,1261,-2637,2146,661,1998,-545,963,787,-1580,-1359,2942,1628,-3573,1002,-2985,1620,1792,1746,-320,-851,-2078,-396,1958,900,1283,-72,100,99,-3360,33,1251,1597,1551,970,-2034,1171,885,1135,532,-125,266,-1320,-3330,1600,2042,1660,735,-886,-1879,-1765,-2767,-2611,2002,-308,1848,-56,1547,1163,675,1723,379,1536,1426,189,-2893,-1096,1394]],
  ["wind_montezuma_2010_swt2393_80m", "Montezuma", 2010, "Siemens SWT-2.3-93", 2300, 80, 93, 126.5, -121.796987, 38.161701, [342,-587,-26,22,-26,-620,-315,508,376,596,368,-233,-412,-1195,-429,-885,-149,884,-26,420,-227,-421,359,-1051,-193,1182,368,1171,368,99,-376,110]],
  ["wind_montezuma_winds_ii_2012_swt2393_80m", "Montezuma Winds II", 2012, "Siemens SWT-2.3-93", 2300, 80, 93, 126.5, -121.821795, 38.118616, [2006,-643,290,1988,1805,-190,342,1457,999,53,1945,-367,1069,-190,272,905,-1760,-1374,-2399,-2004,-2093,-2048,-1313,-1340,552,1203,447,1833,-2478,-1639,789,750,754,131,-1585,-2015,1455,97,123,2154,1411,-522,-481,1822,-1707,-1771,-35,606,1560,-102,-157,1158,-2154,-1351,336,-246,316,53,-314,1656,-306,1291,1464,-798,-1252,-1584,97,1026]],
  ["wind_shiloh_ii_2009_mm92_68m", "Shiloh II", 2009, "REpower MM92", 2000, 68.5, 92.5, 114.6, -121.822679, 38.176615, [3482,-489,-4577,1469,-1576,-290,-788,285,2187,345,-4527,1194,4235,-3850,-1497,319,-3851,1601,-4280,1999,-4096,1800,-3527,1347,6291,-3839,3467,-762,883,362,3465,-212,-324,332,1767,352,-1200,-279,-3098,1004,2607,341,-1051,-24,6677,-3905,-631,-80,3441,-1040,25,362,-4324,2243,-1357,-644,-3317,1170,3447,-1816,-1521,22,428,362,3141,319]],
  ["wind_shiloh_ii_2009_mm92_80m", "Shiloh II", 2009, "REpower MM92", 2000, 80, 92.5, 126.2, -121.766713, 38.152928, [-593,2462,221,-1651,563,1202,-330,1953,46,372,-138,969,-611,981,-50,-1010,-575,-192,405,-833,-645,1445,37,1567,729,-1275,-269,428,563,-1795,711,-535,151,-2558,738,-855,799,-247,-505,-711,-287,1666,-383,2241,-120,52,624,361,203,1356,1324,-1684,-1468,2860,46,-313,186,-579,-1398,1224,-400,-977,-322,-2060,764,29,344,593,597,-2093,-611,-1707,239,-2226,-68,-1419,-488,-446,956,284,-698,1898,-287,1224]],
  ["wind_shiloh_iii_2011_mm92_68m", "Shiloh III", 2011, "REpower MM92", 2050, 68.5, 92.5, 114.6, -121.820686, 38.167396, [8490,-3605,-2608,796,-2713,1194,-3168,1614]],
  ["wind_shiloh_iii_2011_mm92_78m", "Shiloh III", 2011, "REpower MM92", 2050, 78.5, 92.5, 124.7, -121.756645, 38.164895, [2447,-2974,2753,-1271,-109,288,1887,55,-4738,929,-590,1051,1467,-586,1082,0,1563,11,-4616,1194,959,254,2412,-1338,1633,-840,-5072,1161,2246,-1625,548,1626,-5141,918,-1544,1636,434,1183,-5701,1216,-459,741,-152,741,1685,-1404,-9115,1891,-118,-697,2307,-1902,1843,-1117,2561,-2002,-345,1636,2184,-1061,-21,1150,-1045,1592,2587,-1039,408,630,154,752,-424,1382,-4879,663,2570,-3229,1545,-1172,2614,-2698,2701,-243,-713,1603,250,-221,1344,-840,268,1603,329,354]],
  ["wind_shiloh_iv_2012_mm92_68m", "Shiloh IV", 2012, "REpower MM92", 2050, 68.5, 92.5, 114.6, -121.860129, 38.160686, [450,2113,-1099,-1702,-968,-1923,1027,-180,590,1693]],
  ["wind_shiloh_iv_2012_mm92_78m", "Shiloh IV", 2012, "REpower MM92", 2050, 78.5, 92.5, 124.7, -121.849286, 38.132246, [-771,1222,-1366,-934,709,-2195,701,1819,-954,-271,-131,-559,289,403,893,-614,604,2195,-1523,-448,-491,-946,-219,1509,656,282,963,-857,-1384,989,-578,691,-1261,-658,-551,-426,-1296,1277,1234,-1432,105,746,-648,-1255,324,1553,447,680,157,1786,648,-1488,674,-459,-1182,835,341,2416,-788,-835,35,2073,-499,967,1419,-1598,-105,1244,1059,-2261,-1086,-1178,1488,-1841,368,-2604,1025,-205,858,-1908,-1296,569,1165,-2505,-709,437,464,2681,210,1100]],
  ["wind_shiloh_wind_project_2006_ge1577_65m", "Shiloh Wind Project", 2006, "GE Wind GE1.5-77", 1500, 65, 77, 103.6, -121.849826, 38.160557, [47,844,1124,137,951,905,-565,-1455,-653,-405,1071,303,1115,645,-758,-272,-1835,-936,174,361,-1266,-770,-277,-947,-1598,-250,1894,900,-925,-1367,-32,1022,-320,-792,-898,-1489,-478,1043,1036,778,1063,469,21,690,-855,-151,1964,734]],
  ["wind_shiloh_wind_project_2006_ge1577_80m", "Shiloh Wind Project", 2006, "GE Wind GE1.5-77", 1500, 80, 77, 118.6, -121.852509, 38.143623, [2383,1534,-742,1069,2270,1932,1013,-72,-1496,3900,369,-5211,-838,2264,1219,-5731,-156,-3121,1192,-5587,1166,-5233,3346,2053,-2283,-80,335,-3497,-1241,2795,-409,-3917,1175,-5410,326,-2248,3460,1921,2339,1722,-2152,3889,-2064,-633,-1881,2717,-1206,3590,-1662,1191,-2222,837,-716,-2956,3084,2463,2313,1257,-1942,2385,-1916,-766,-112,-3940,-1854,2186,3171,2330,484,-5742,-926,2452,431,-3088,1735,1302,90,-3320,-1767,1578,-1731,1401,1989,1247,-339,-3033,-2231,1058,-2336,1512,1307,-5985,-2082,-423,-1180,1302,-2668,52,-637,3137,-2125,3215,-1320,3745,1299,-410,-2283,4066,1377,-6118,396,-2878,-15,-3198,457,-5366,-2213,-224,1516,1832,1543,1645,-112,-4083,2182,2286,-2248,3403,-821,3281,3259,2164,2182,2076,2978,2573,-2055,1733,-462,3060,1247,-623,1033,194,1008,-256,-926,3436,-1172,2629,2611,2584,-2012,2960,448,-5576,151,-3453,-2283,1291,1299,-739,650,-2336]],
  ["wind_solano_iv_repower_2024_v15045_105m", "Solano IV Repower", 2024, "Vestas V150-4.5", 4500, 105, 150, 180.1, -121.796479, 38.100925, [-3314,-1689,3962,1240,-1432,-2615,-2781,-2166,2079,3144,-1861,-2889,-3046,-916,3730,1531,-2551,-1866,-2833,-2448,1837,2534,3016,2001,-1553,-2311,1924,2830,-1061,-3099,-2850,-1188,1869,3396,1924,2202,2942,2308]],
  ["wind_solano_phase_3_2012_v9018_80m", "Solano Phase 3", 2012, "Vestas V90-1.8", 1800, 80, 90, 125, -121.800732, 38.084885, [-1784,841,-14,-43,-22,-231,-1240,-297,766,-1459,1082,-972,328,532,1309,256,372,-707,959,-209,-1363,112,-1766,665,311,709,415,963,468,-883,302,-1127,-1722,477,942,-32,-285,189,530,-1270,-67,-408,-1371,-65,319,355,1125,-530,-548,764,-732,919,880,532,-1696,300,880,808,1029,-375,591,189]],
  ["wind_solano_phase_3_2012_v9030_80m", "Solano Phase 3", 2012, "Vestas V90-3.0", 3000, 80, 90, 125, -121.762986, 38.091516, [-1226,-489,1752,263,-1271,-1252,-1857,-1860,666,1501,745,1767,719,1955,-272,-898,1664,429,-1244,-887,-2059,-1395,-1831,-257,-324,-600,-1235,-1064,894,1270,1332,1546,1577,595,-1244,-677,-473,-1086,-1297,-1429,788,904,850,-334,1218,1126,2129,871]],
  ["wind_solano_phase_iia_2006_v9030_80m", "Solano Phase IIA", 2006, "Vestas V90-3.0", 3000, 80, 90, 125, -121.774748, 38.10142, [41,462,-4,86,41,273,41,639,-30,-91,-47,-633,-30,-456,-12,-279]],
  ["wind_solano_wind_project_2007_v9030_80m", "Solano Wind Project", 2007, "Vestas V90-3.0", 3000, 80, 90, 125, -121.766612, 38.101324, [397,251,405,-47,265,-667,-1618,682,1088,-1253,536,782,1062,-843,510,992,-1610,859,361,-468,-383,-987,-471,981,519,583,-471,1191,-366,-1175,-1601,506,1001,-667,-462,-832,966,-1042,-558,1423,431,-268]],
  ["wind_superior_farms_2012_mwt6210_55m", "Superior Farms", 2012, "Mitsubishi MWT62/1.0", 1000, 55, 61.4, 85.6, -121.81749, 38.420094, [0,0]],
];
const USWTDB = 'https://eerscmap.usgs.gov/uswtdb/';
/** Rotors face the prevailing west-south-west wind through the Carquinez gap (static). */
const WIND_FACING = 245;

function turbine(b: MeshBuilder, x: number, y: number, z0: number, hub: number, rotor: number, phase: number) {
  const s = rotor / 90;
  b.color('#E9EAE8').frustum(x, y, 2.0 * s + 0.4, 1.1 * s + 0.3, z0 - 8, z0 + hub - 1.6 * s, 6, false);
  b.frame(x, y, z0 + hub, WIND_FACING, () => {
    b.color('#DFE1DF').box(0, -2.4 * s, -1.8 * s, 3.6 * s, 9.6 * s, 3.6 * s);
    const yr = 3.3 * s;
    b.color('#F2F3F1').box(0, yr - 0.6 * s, -1.2 * s, 2.4 * s, 2.0 * s, 2.4 * s);
    const R = rotor / 2;
    for (let k = 0; k < 3; k++) {
      const a = phase + (k * 2 * Math.PI) / 3;
      const ux = Math.sin(a);
      const uz = Math.cos(a);
      const c0 = 1.0 * s;
      const c1 = 0.2 * s;
      const r0 = 1.2 * s;
      b.quad([ux * r0 - uz * c0, yr, uz * r0 + ux * c0], [ux * r0 + uz * c0, yr, uz * r0 - ux * c0], [ux * R + uz * c1, yr, uz * R - ux * c1], [ux * R - uz * c1, yr, uz * R + ux * c1]);
    }
  });
}

const windFarms: Landmark[] = WIND.map(([id, project, year, model, kw, hub, rotor, tip, lon, lat, pts]) => {
  const anchor: V2 = [lon, lat];
  const n = pts.length / 2;
  return {
    id,
    name: `${project} — ${n === 1 ? 'wind turbine' : n + ' wind turbines'} (${year})`,
    kind: 'tower',
    built: [year - 0.6, year + 0.4],
    end: 9999,
    anchor,
    build: b => {
      for (let i = 0; i < n; i++) {
        const x = pts[i * 2];
        const y = pts[i * 2 + 1];
        turbine(b, x, y, dzAt(anchor, x, y), hub, rotor, ((i * 2.399963) % 2.0944) + 0.3);
      }
    },
    facts: {
      Project: `${project}, online ${year} (US Wind Turbine Database project year; month not recorded)`,
      Turbines: `${n} × ${model}, ${(kw / 1000).toFixed(kw % 1000 ? 2 : 1)} MW each`,
      Size: `hub height ${hub} m, rotor diameter ${rotor} m, ${tip} m to the blade tip`,
      Model: 'each turbine at its database position on the terrain; rotors static, facing the prevailing west-south-west wind; tower and nacelle proportions generic'
    },
    sources: [USWTDB, WIKI + 'Shiloh_wind_power_plant']
  } as Landmark;
});

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
  petalumaAdobe,
  beniciaCapitol,
  camelBarns,
  stPetersChapel,
  greystone,
  inglenook,
  rhineHouse,
  baleMill,
  napaCourthouse,
  napaCourthouseAnnex,
  napaOperaHouse,
  monticelloDam,
  churchOfOneTree,
  deTurkBarn,
  petalumaLibrary,
  stTeresaBodega,
  condominiumOne,
  seaRanchChapel,
  ...windFarms
];
