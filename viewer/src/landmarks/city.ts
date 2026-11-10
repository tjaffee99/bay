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
// Rebuilt 2026-11 (owner: "fix the Bay Bridge shape") on surveyed geometry; numbers and sources in
// data/research/landmarks.md "San Francisco–Oakland Bay Bridge":
//  * plan: tower / anchorage centres are the centroids of the OSM footprints (Overture 2026-10-21); the
//    2013 east span and the island structures follow the OSM centrelines of the two roadways, curves
//    included; the 1936 east span follows the axis of the structure itself in the 2010 USGS lidar
//    (ARRA-CA_GoldenGate_2010, ARRA-CA_SanFranCoast_2010) and the three foundations kept for the 2020
//    observation pier (2021 lidar) — it ran SOUTH of today's span, 50 m off along the causeway and up to 200 m
//    at the through trusses;
//  * heights: NAVD88 metres read off the 2023 / 2021 / 2010 USGS 3DEP point clouds (the bay there is at
//    0): roadway profile, tower tops, cable low points, anchorages, truss chords.
// West-span stations are metres from tower W2 along the axis W2 -> W6 (bearing 40.4°); east-span (1936)
// stations are metres from the main pier E2 along its alignment.
const STEEL_GREY = '#A9AEB2';
const BB_CONC = '#BDB8AE';
const BB_ROAD = '#5A5753';
const BB_OLD = '#9A9FA3';
const BB_LIDAR = 'https://www.usgs.gov/3d-elevation-program (lidar point clouds CA_SanFrancisco_1_B23, CA_AlamedaCo_2_2021, ARRA-CA_GoldenGate_2010, ARRA-CA_SanFranCoast_2010)';
const BB_OSM = 'https://www.openstreetmap.org/copyright (I-80 centrelines, tower and anchorage footprints via Overture 2026-10-21)';
const BB_WIKI = WIKI + 'San_Francisco%E2%80%93Oakland_Bay_Bridge';
const BB_WIKI_EAST = WIKI + 'Eastern_span_replacement_of_the_San_Francisco%E2%80%93Oakland_Bay_Bridge';

type Tab = [number, number][];
/** Piecewise-linear table lookup. */
function tab(t: Tab, s: number): number {
  if (s <= t[0][0]) return t[0][1];
  for (let i = 1; i < t.length; i++) {
    if (s <= t[i][0]) return t[i - 1][1] + ((t[i][1] - t[i - 1][1]) * (s - t[i - 1][0])) / (t[i][0] - t[i - 1][0]);
  }
  return t[t.length - 1][1];
}

/** Polyline with stations (metres along it); `s0` = station of its first point. */
type BBPath = {pts: V2[]; cum: number[]; s0: number; s1: number};
function bbPath(pts: V2[], s0 = 0): BBPath {
  const cum = [0];
  for (let i = 1; i < pts.length; i++) cum.push(cum[i - 1] + Math.hypot(pts[i][0] - pts[i - 1][0], pts[i][1] - pts[i - 1][1]));
  return {pts, cum, s0, s1: s0 + cum[cum.length - 1]};
}
function bbPos(p: BBPath, s: number): V2 {
  const c = Math.min(Math.max(s - p.s0, 0), p.cum[p.cum.length - 1]);
  let i = 1;
  while (i < p.cum.length - 1 && p.cum[i] < c) i++;
  const t = (c - p.cum[i - 1]) / (p.cum[i] - p.cum[i - 1] || 1);
  return [p.pts[i - 1][0] + (p.pts[i][0] - p.pts[i - 1][0]) * t, p.pts[i - 1][1] + (p.pts[i][1] - p.pts[i - 1][1]) * t];
}
/** Unit tangent at s (the bisector at a vertex). */
function bbDir(p: BBPath, s: number): V2 {
  const a = bbPos(p, s - 0.5);
  const c = bbPos(p, s + 0.5);
  const l = Math.hypot(c[0] - a[0], c[1] - a[1]) || 1;
  return [(c[0] - a[0]) / l, (c[1] - a[1]) / l];
}
/** Point at station s, `off` metres to the right of the path. */
function bbAt(p: BBPath, s: number, off = 0): V2 {
  const q = bbPos(p, s);
  if (!off) return q;
  const d = bbDir(p, s);
  return [q[0] + d[1] * off, q[1] - d[0] * off];
}
/** Compass bearing of the path at s. */
function bbBearing(p: BBPath, s: number) {
  const d = bbDir(p, s);
  return (Math.atan2(d[0], d[1]) * 180) / Math.PI;
}
/** Stations between a and c: both ends, every `step`, the path's own vertices and `extra`. */
function bbStations(p: BBPath, a: number, c: number, step: number, extra: number[] = []): number[] {
  const all = [...extra];
  for (let s = a + step; s < c; s += step) all.push(s);
  for (const v of p.cum) all.push(p.s0 + v);
  const mid = all.filter(s => s > a + 1 && s < c - 1).sort((x, y) => x - y);
  const out = [a];
  for (const s of mid) if (s - out[out.length - 1] > 1) out.push(s);
  out.push(c);
  return out;
}
type Sweep = {half: number; off?: number; top: (s: number) => number; depth: number | ((s: number) => number); color: string; road?: string; step?: number; extra?: number[]; ends?: boolean};
/** Box section (deck slab, girder, chord) swept along a path between stations a and c. */
function bbSweep(b: MeshBuilder, p: BBPath, a: number, c: number, o: Sweep) {
  const off = o.off ?? 0;
  const sec = bbStations(p, a, c, o.step ?? 1e9, o.extra).map(s => {
    const l = bbAt(p, s, off - o.half);
    const r = bbAt(p, s, off + o.half);
    const zt = o.top(s);
    const zb = zt - (typeof o.depth === 'number' ? o.depth : o.depth(s));
    return {lt: [l[0], l[1], zt] as V3, rt: [r[0], r[1], zt] as V3, lb: [l[0], l[1], zb] as V3, rb: [r[0], r[1], zb] as V3};
  });
  for (let i = 0; i < sec.length - 1; i++) {
    const A = sec[i];
    const B = sec[i + 1];
    b.color(o.road ?? o.color).quad(A.lt, A.rt, B.rt, B.lt);
    b.color(o.color).quad(A.lb, A.rb, B.rb, B.lb).quad(A.lb, A.lt, B.lt, B.lb).quad(A.rb, A.rt, B.rt, B.rb);
  }
  if (o.ends) {
    const A = sec[0];
    const B = sec[sec.length - 1];
    b.color(o.color).quad(A.lb, A.rb, A.rt, A.lt).quad(B.lb, B.rb, B.rt, B.lt);
  }
}
/** Flat member (2 triangles) in the vertical plane through p -> q; `h` = that plane's horizontal
 *  direction when the member is vertical. Truss webs and suspenders: edge-on from above, like the real ones. */
function bbWeb(b: MeshBuilder, p: V3, q: V3, w: number, h: V2 = [0, 1]) {
  const hl = Math.hypot(q[0] - p[0], q[1] - p[1]);
  const ux = hl > 1e-6 ? (q[0] - p[0]) / hl : h[0];
  const uy = hl > 1e-6 ? (q[1] - p[1]) / hl : h[1];
  const dz = q[2] - p[2];
  const L = Math.hypot(hl, dz) || 1;
  const n: V3 = [((-dz * ux) / L) * (w / 2), ((-dz * uy) / L) * (w / 2), (hl / L) * (w / 2)];
  b.quad([p[0] - n[0], p[1] - n[1], p[2] - n[2]], [p[0] + n[0], p[1] + n[1], p[2] + n[2]], [q[0] + n[0], q[1] + n[1], q[2] + n[2]], [q[0] - n[0], q[1] - n[1], q[2] - n[2]]);
}
/** Slender member as two crossed flat strips (4 triangles): cables and chords, visible from every side. */
function bbRod(b: MeshBuilder, p: V3, q: V3, w: number) {
  bbWeb(b, p, q, w);
  const hl = Math.hypot(q[0] - p[0], q[1] - p[1]) || 1;
  const nx = (((q[1] - p[1]) / hl) * w) / 2;
  const ny = ((-(q[0] - p[0]) / hl) * w) / 2;
  b.quad([p[0] - nx, p[1] - ny, p[2]], [p[0] + nx, p[1] + ny, p[2]], [q[0] + nx, q[1] + ny, q[2]], [q[0] - nx, q[1] - ny, q[2]]);
}
/** Two truss planes at x = ±half in the current frame (+y along the bridge): top chord through the
 *  nodes, a vertical at every node, diagonals alternating between them, struts across the top. */
function bbTruss(b: MeshBuilder, half: number, nodes: {y: number; zb: number; zt: number}[], strutEvery = 2) {
  for (const x of [-half, half]) {
    for (let i = 0; i < nodes.length; i++) {
      const n = nodes[i];
      if (n.zt - n.zb > 3) bbWeb(b, [x, n.y, n.zb], [x, n.y, n.zt], 0.9);
      if (i === nodes.length - 1) break;
      const m = nodes[i + 1];
      bbRod(b, [x, n.y, n.zt], [x, m.y, m.zt], 1.5);
      if (n.zt - n.zb > 3 || m.zt - m.zb > 3) {
        if (i % 2 === 0) bbWeb(b, [x, n.y, n.zb], [x, m.y, m.zt], 0.9);
        else bbWeb(b, [x, n.y, n.zt], [x, m.y, m.zb], 0.9);
      }
    }
  }
  for (let i = 0; i < nodes.length; i += strutEvery) {
    const n = nodes[i];
    if (n.zt - n.zb > 12) b.beam([-half, n.y, n.zt], [half, n.y, n.zt], 1.2);
  }
}

// --------------------------------------------------------------- west span (1936)
const BB_ANCHOR: V2 = [-122.377877, 37.798119]; // frame origin (centre anchorage W4)
const BB_W2: V2 = [-122.385823, 37.790753];
const BB_W3: V2 = [-122.380648, 37.795588];
const BB_W4: V2 = [-122.37786, 37.79819];
const BB_W5: V2 = [-122.37508, 37.800787];
const BB_W6: V2 = [-122.3699, 37.805622];
/** Upper roadway (station from W2, m NAVD88), 2023 lidar: 2.9 % up from the San Francisco anchorage,
 *  level at 79.4 m across the centre anchorage, 2.8 % down to the island. */
const BB_WEST_Z: Tab = [
  [-789, 41.5], [-725, 43.4], [-665, 45], [-610, 46.4], [-510, 49.6], [-410, 52.6], [-357, 54], [-250, 57.4], [-150, 60.4], [-50, 63.1], [0, 64.8],
  [100, 67.9], [200, 70.6], [300, 72.9], [400, 74.9], [500, 76.5], [600, 77.5], [700, 78.3], [800, 78.9], [900, 79.2], [1000, 79.4], [1280, 79.4],
  [1350, 79.1], [1450, 78.4], [1550, 77.6], [1650, 76.6], [1750, 75.1], [1850, 73.1], [1950, 70.9], [2050, 68.1], [2165, 64.8], [2250, 62.4],
  [2350, 59.1], [2450, 56.1], [2530, 53.9], [2600, 53], [2656, 52.4]
];
const BB_DECKS = 7.9; // lower roadway below the upper one (lidar, island viaduct; elsewhere hidden — estimated)
const BB_TRUSS = 10; // stiffening truss, top of roadway to bottom chord (lidar; 30 ft trusses)
const BB_HALF = 10.3; // cable and truss planes: 20.6 m apart (lidar; 66 ft documented)
/** Stations of the structures on the axis (lidar). */
const BB_S = {anchW: -665, anchE: -610, bent: -490, w1: -357, w4a: 1055, w4b: 1112, ybi: 2520, portalW: 2656, portalE: 2826};

/** Frame of the west span: origin at tower W2, +y along the axis to W6, +x to the south-east. `k` turns
 *  surveyed metres along the axis into the frame's (the kit's local metres are ≈ 0.3 % long on this bearing,
 *  7 m at the island): W2 – W6 is 2,164.9 m in the survey. */
function bbWestFrame(b: MeshBuilder, fn: (st: (p: V2) => number, k: number) => void) {
  const a = along(BB_ANCHOR, BB_W2, BB_W6);
  const r = (a.bearing * Math.PI) / 180;
  const st = (p: V2) => {
    const l = lngLatToLocal(BB_ANCHOR, p);
    return (l[0] - a.origin[0]) * Math.sin(r) + (l[1] - a.origin[1]) * Math.cos(r);
  };
  b.frame(a.origin[0], a.origin[1], 0, a.bearing, () => fn(st, st(BB_W6) / 2164.9));
}

/** Steel tower on its concrete pier, in a frame at the tower centre (+y along the bridge). Lidar: fender
 *  skirt ~55 × 30 m, pier top 37 × 18 m at +12 m; legs 27 m apart at the pier and 20.5 m at the top;
 *  X-bracing in one bay below the roadway and three above; deep strut under the saddles. */
function bbTower(b: MeshBuilder, top: number, deck: number) {
  b.color(BB_CONC).prism(roundedRect(0, 0, 55, 30, 9, 2), 0, 5).box(0, 0, 5, 37, 18, 7);
  b.color(STEEL_GREY);
  const z0 = 12;
  const xc = (z: number) => 13.6 - (3.3 * (z - z0)) / (top - z0);
  for (const sx of [-1, 1]) {
    b.loft([rect(sx * xc(z0), 0, 5.2, 9.5), rect(sx * xc(top - 3), 0, 4, 6.5)], [z0, top - 3], {top: false});
    b.box(sx * xc(top), 0, top - 3, 5, 7.5, 3); // cable saddle
  }
  const a0 = deck + 8.5;
  const a1 = top - 9.5;
  const bays: [number, number][] = [[19, deck - 16]];
  for (let k = 0; k < 3; k++) bays.push([a0 + ((a1 - a0) * k) / 3, a0 + ((a1 - a0) * (k + 1)) / 3]);
  for (const [za, zb] of bays) {
    b.beam([-xc(za), 0, za], [xc(zb), 0, zb], 3, 1.3).beam([xc(za), 0, za], [-xc(zb), 0, zb], 3, 1.3);
    b.beam([-xc(za), 0, za], [xc(za), 0, za], 3, 1.5);
  }
  b.beam([-xc(deck - 16), 0, deck - 16], [xc(deck - 16), 0, deck - 16], 3, 1.5);
  b.box(0, 0, a1, 2 * xc(a1), 4, 7); // portal strut under the saddles
}

function bayBridgeWest(b: MeshBuilder) {
  bbWestFrame(b, (st, k) => {
    const [sW3, sW4, sW5, sW6] = [BB_W3, BB_W4, BB_W5, BB_W6].map(st);
    const S = Object.fromEntries(Object.entries(BB_S).map(([n, v]) => [n, v * k])) as typeof BB_S;
    const zU = (s: number) => tab(BB_WEST_Z, s / k);
    const sc = (pts: V2[]): V2[] => pts.map(([x, y]) => [x, y * k]);
    // centreline: straight from the San Francisco anchorage to the tunnel; west of the anchorage the
    // upper-deck viaduct swings west toward Fifth Street (OSM way, 2023 lidar)
    const curve = sc([[-23, -789], [-8.5, -725], [-1.5, -665], [0, -620]]);
    const path = bbPath([...curve, [0, S.portalW]]);
    path.s0 = -620 * k - path.cum[curve.length - 1];
    path.s1 = path.s0 + path.cum[path.cum.length - 1];
    // the lower deck comes off Rincon Hill on its own curve (OSM way) and is under the upper one from the anchorage
    const lowCurve = sc([[-14.9, -765.5], [-8.1, -739.9], [-3.6, -714.8], [-0.6, -690], [0, -660]]);
    const lowPath = bbPath([...lowCurve, [0, S.portalW]]);
    lowPath.s0 = -660 * k - lowPath.cum[lowCurve.length - 1];
    lowPath.s1 = lowPath.s0 + lowPath.cum[lowPath.cum.length - 1];
    const zNodes = BB_WEST_Z.map(r => r[0] * k);

    // --- double deck: upper roadway on the top chords, lower one on the bottom chords
    bbSweep(b, path, path.s0, S.portalW, {half: BB_HALF, top: zU, depth: 1.6, color: STEEL_GREY, road: BB_ROAD, extra: zNodes});
    bbSweep(b, lowPath, lowPath.s0, S.portalW, {half: BB_HALF, top: s => zU(s) - BB_DECKS, depth: BB_TRUSS - BB_DECKS, color: STEEL_GREY, road: BB_ROAD, extra: zNodes});
    // stiffening / deck trusses from the anchorage to the island (Warren webs, drawn every 15 m)
    b.color(STEEL_GREY);
    for (const x of [-BB_HALF, BB_HALF]) {
      let up = true;
      for (let y = S.anchE; y < S.ybi - 1; y += 15) {
        const y1 = Math.min(y + 15, S.ybi);
        const lo: V3 = [x, up ? y : y1, zU(up ? y : y1) - BB_DECKS];
        const hi: V3 = [x, up ? y1 : y, zU(up ? y1 : y) - 1.6];
        bbWeb(b, lo, hi, 0.8);
        up = !up;
      }
    }

    // --- towers: W2 / W6 146.5 m, W3 / W5 159.5 m above the bay (lidar; 526 ft documented)
    for (const [y, top] of [[0, 146.5], [sW3, 159.5], [sW5, 159.5], [sW6, 146.5]]) b.frame(0, y, 0, 0, () => bbTower(b, top, zU(y)));

    // --- centre anchorage W4 (lidar): 28 × 60 m at the water, 25.5 × 57 m above 30 m, up to the roadway,
    // which runs through it between cable housings 86 m high
    b.frame(0, sW4, 0, 0, () => {
      b.color(BB_CONC).prism(roundedRect(0, 0, 44, 70, 8, 2), 0, 6.5).box(0, 0, 6.5, 28, 60, 23.5).box(0, 0, 30, 25.5, 57, 48.4);
      for (const sx of [-1, 1]) b.box(sx * 11.4, 0, 78.4, 2.7, 57, 8);
      for (const sy of [-1, 1]) b.box(0, sy * 24, 86.4, 25.5, 4, 2.6);
    });

    // --- San Francisco end: anchorage on Rincon Hill (28 × 55 m block under the deck trusses), steel
    // bent, cable bent W1 (the side span ends there; the cables run on under the roadway)
    b.color(BB_CONC).box(0, (S.anchW + S.anchE) / 2, 0, 28, S.anchE - S.anchW, 37);
    b.box(-6, -716 * k, 0, 26, 100, zU(-716 * k) - BB_TRUSS);
    for (const y of [-745 * k, -772 * k]) {
      for (const o of [-7, 7]) {
        const c = bbAt(path, y, o);
        b.box(c[0], c[1], 18, 2.6, 2.6, zU(y) - 1.6 - 18, {top: false});
      }
    }
    b.box(0, S.w1, 0, 27, 9, zU(S.w1) - BB_TRUSS);
    for (const sx of [-1, 1]) b.box(sx * BB_HALF, S.w1, zU(S.w1) - BB_TRUSS, 3.2, 6, BB_TRUSS + 3);
    b.color(STEEL_GREY);
    const zBent = zU(S.bent) - BB_TRUSS;
    for (const sx of [-1, 1]) b.beam([sx * BB_HALF, S.bent, 4], [sx * BB_HALF, S.bent, zBent], 1.8);
    b.beam([-BB_HALF, S.bent, 6], [BB_HALF, S.bent, zBent - 2], 2, 1).beam([BB_HALF, S.bent, 6], [-BB_HALF, S.bent, zBent - 2], 2, 1);

    // --- island end: cable anchorage in the rock of Yerba Buena Island, 321 ft concrete viaduct to the tunnel
    b.color(BB_CONC).box(0, S.ybi + 13, 15, 28, 26, zU(S.ybi + 13) - 1.6 - 15);
    for (const y of [2575 * k, 2602 * k, 2629 * k]) for (const sx of [-1, 1]) b.box(sx * 7.5, y, 20, 3, 3, zU(y) - BB_TRUSS - 20, {top: false});

    // --- the two cables and their suspenders (drawn every ≈ 17 m)
    b.color(STEEL_GREY);
    const zs = 57.5; // at the cable bents
    const spans: [number, number, number, number, number, number, boolean][] = [
      // y0, z0, y1, z1, height at mid-span, segments, suspenders
      [S.anchE, 13.5, S.w1, zs, (13.5 + zs) / 2, 1, false],
      [S.w1, zs, 0, 143, 81.5, 7, true],
      [0, 143, sW3, 155.5, 77.5, 14, true],
      [sW3, 155.5, S.w4a, 84, 100.7, 7, true],
      [S.w4a, 84, S.w4b, 84, 84, 1, false],
      [S.w4b, 84, sW5, 155.5, 100.7, 7, true],
      [sW5, 155.5, sW6, 143, 78.2, 14, true],
      [sW6, 143, S.ybi, zs, 80.3, 7, true],
      [S.ybi, zs, S.ybi + 14, zs - 6, zs - 3, 1, false]
    ];
    for (const x of [-BB_HALF, BB_HALF]) {
      for (const [y0, z0, y1, z1, mid, n, hang] of spans) {
        const curve3 = parabola([x, y0, z0], [x, y1, z1], mid, n * 3);
        for (let i = 0; i < curve3.length - 1; i += 3) bbRod(b, curve3[i], curve3[i + 3], 1.5);
        if (!hang) continue;
        for (let i = 1; i < curve3.length - 1; i++) {
          const c = curve3[i];
          const zd = zU(c[1]);
          if (c[2] - zd > 4) bbWeb(b, [c[0], c[1], zd], c, 0.55);
        }
      }
    }
  });
}

const bayBridgeWestSpan: Landmark = {
  id: 'bay_bridge_west_span',
  name: 'San Francisco–Oakland Bay Bridge (west span)',
  kind: 'bridge',
  built: [1933.52, 1936.87],
  end: 9999,
  anchor: BB_ANCHOR,
  build: bayBridgeWest,
  // generic footprints of the towers / centre anchorage (OSM bridge structures, split by the
  // 2023 LiDAR into 80-85 m prisms) stand inside the model: hide them
  replaces: [BB_W2, BB_W3, BB_W4, BB_W5, BB_W6].map(p => {
    const l = lngLatToLocal(BB_ANCHOR, p);
    return rect(l[0], l[1], 90, 90);
  }),
  facts: {
    Construction: 'Jul 9, 1933 – Nov 12, 1936',
    Form: 'two suspension bridges in series sharing a centre anchorage; double deck',
    'Main spans': '2 × 704 m (2,310 ft); side spans 354 m (1,160 ft)',
    Towers: 'W3 and W5 160 m (526 ft) above the water, W2 and W6 146.5 m',
    Roadway: 'upper deck 46 m at the San Francisco anchorage, 79 m at the centre anchorage (67 m / 220 ft clear below), 52 m at the island',
    'Centre anchorage': 'concrete pier 28 × 60 m at the water, 86 m high; the roadway runs through it',
    Model: 'plan from the OSM tower and anchorage footprints; roadway profile, tower tops, cables and anchorages measured on the 2023 USGS lidar; lower deck height and member sizes estimated'
  },
  sources: [BB_WIKI, BB_LIDAR, BB_OSM]
};

// --------------------------------------------------------------- Yerba Buena Island tunnel (1936)
/** Portal ring in a frame whose +y points INTO the hill: bore 76 ft wide × 58 ft high outside,
 *  66 × 53 ft inside, lower roadway at z0. */
function bbPortal(b: MeshBuilder, z0: number) {
  const ring = (hw: number, zw: number, zc: number, zf: number): V2[] => {
    const out: V2[] = [[-hw, zf]];
    for (let i = 0; i <= 6; i++) {
      const a = Math.PI - (Math.PI * i) / 6;
      out.push([Math.cos(a) * hw, zw + Math.sin(a) * (zc - zw)]);
    }
    out.push([hw, zf]);
    return out;
  };
  const outer = ring(11.6, z0 + 9.5, z0 + 17.7, z0 - 1.5);
  const inner = ring(10.05, z0 + 9, z0 + 16.2, z0 - 1.5);
  const at = (r: V2[], y: number): V3[] => r.map(([x, z]) => [x, y, z] as V3);
  b.color(BB_CONC).ribbon(at(outer, 0), at(inner, 0)).ribbon(at(outer, 0), at(outer, 8)).ribbon(at(inner, 0), at(inner, 8));
  // headwall around the bore
  for (const sx of [-1, 1]) b.box(sx * 17.5, 1.5, z0 - 1.5, 12, 3, 21.5);
  b.box(0, 1.5, z0 + 17.7, 47, 3, 4);
}
const bayBridgeTunnel: Landmark = {
  id: 'bay_bridge_ybi_tunnel',
  name: 'Yerba Buena Tunnel (Bay Bridge)',
  kind: 'bridge',
  built: [1933.52, 1936.87],
  end: 9999,
  anchor: BB_ANCHOR,
  build: b =>
    bbWestFrame(b, (_, k) => {
      b.frame(0, BB_S.portalW * k, 0, 0, () => bbPortal(b, tab(BB_WEST_Z, BB_S.portalW) - BB_DECKS));
      b.frame(0, BB_S.portalE * k, 0, 180, () => bbPortal(b, 56.6 - BB_DECKS));
    }),
  facts: {
    Opened: 'Nov 12, 1936 (with the bridge)',
    Form: 'double-deck bore through Yerba Buena Island between the two crossings',
    Length: '165 m (540 ft)',
    Bore: '23 m wide × 18 m high (76 × 58 ft), 20 × 16 m inside',
    Model: 'portals only (the bore is inside the hill); positions from the 2023 USGS lidar; headwalls schematic'
  },
  sources: [BB_WIKI, BB_LIDAR]
};

// --------------------------------------------------------------- original east span (1936–2013)
// dismantled in stages Nov 2013 – Mar 2017 (steel) and to Nov 2017 (piers): cantilever gone by Jun 12, 2015
// (Wikipedia); the five 504 ft trusses lowered Feb 4 – Aug 2016; the last of the fourteen 288 ft causeway
// trusses removed Mar 13, 2017 (ABC7 / KTVU)
const BB_E2: V2 = [-122.358551, 37.814304]; // west main pier of the cantilever (frame origin)
/** 1936 alignment: tunnel portal, viaduct curve on the island (R ≈ 550 m), piers E1 … E23, landfall. */
const BB_OLD_LL: V2[] = [
  [-122.365028, 37.810156], [-122.362654, 37.812371], [-122.362402, 37.812593], [-122.362132, 37.812803], [-122.361848, 37.813], [-122.361549, 37.813182],
  [-122.361237, 37.81335], [-122.360913, 37.813503], [-122.360578, 37.81364], [-122.360233, 37.813761],
  [-122.36018, 37.813778], BB_E2, [-122.35406, 37.815753], [-122.352418, 37.816283], [-122.350801, 37.816804], [-122.349184, 37.817326],
  [-122.347567, 37.817847], [-122.345951, 37.818369], [-122.344334, 37.81889], [-122.343366, 37.819162], [-122.342378, 37.819384], [-122.341371, 37.819542],
  [-122.340364, 37.8197], [-122.339356, 37.819858], [-122.338349, 37.820016], [-122.337342, 37.820173], [-122.336335, 37.820331], [-122.335327, 37.820489],
  [-122.33432, 37.820647], [-122.333313, 37.820805], [-122.332306, 37.820962], [-122.331298, 37.82112], [-122.330291, 37.821278], [-122.326445, 37.82188]
];
const BB_OLD_E1 = 10; // index of pier E1 in BB_OLD_LL (E2 = 11 … E23 = 32)
/** Temporary bypass ("S-curve", Sep 2009 – Aug 2013) from the tunnel to pier E1, up to 58 m south-east of the
 *  original viaduct: centre of the structure in the 2010 lidar; the reverse curve in the first 130 m at the
 *  tunnel is hidden among ground returns there and drawn as a smooth S. */
const BB_SCURVE_LL: V2[] = [
  [-122.365028, 37.810156], [-122.364823, 37.810324], [-122.364596, 37.810473], [-122.364352, 37.810608], [-122.363323, 37.811102], [-122.36308, 37.811238],
  [-122.362855, 37.811388], [-122.362651, 37.811557], [-122.362215, 37.811973], [-122.361498, 37.812729], [-122.360976, 37.813264], [-122.360854, 37.81336],
  [-122.360723, 37.813446], [-122.360325, 37.813701], [-122.36018, 37.813778]
];
const BB_SCURVE_Z: Tab = [[0, 56.6], [270, 61.5], [397, 63.6], [457, 64.4], [517, 65.1], [593, 66.6]];
/** Upper roadway of the 1936 east span (station from E2, m NAVD88): 2010 lidar; 2.7 % down from pier E7. */
const BB_OLD_Z: Tab = [
  [-748, 56.6], [-155, 66.6], [0, 68.5], [106, 69.5], [212, 69.9], [318, 69.5], [427, 68.4], [583, 66.4], [738, 64.4], [892, 62.4], [969, 61], [1046, 59.4],
  [1125, 57.1], [2364, 23.4], [2616, 16.6], [2730, 13.2], [2830, 9.2], [2875, 7.2], [2961, 4.6]
];
function bbOldPath() {
  const p = bbPath(BB_OLD_LL.map(q => lngLatToLocal(BB_E2, q)));
  p.s0 = -p.cum[BB_OLD_E1 + 1];
  p.s1 = p.s0 + p.cum[p.cum.length - 1];
  return {p, pier: (k: number) => p.s0 + p.cum[BB_OLD_E1 + k - 1], zU: (s: number) => tab(BB_OLD_Z, s)};
}
/** Concrete pier under the double-deck trusses, standing in the bay: frame at the pier, +y along the bridge. */
function bbOldPier(b: MeshBuilder, zTop: number, sx: number, sy: number, base = true) {
  b.color(BB_CONC);
  if (base) b.box(0, 0, 0, sx + 10, sy + 8, 6);
  b.loft([rect(0, 0, sx, sy), rect(0, 0, sx - 3, sy - 2.5)], [base ? 6 : 0, zTop], {top: false});
}
function eastOldPart(part: 'viaduct' | 'detour' | 'cantilever' | 'trusses' | 'causeway' | 'approach') {
  return (b: MeshBuilder) => {
    const {p, pier, zU} = bbOldPath();
    const zN = BB_OLD_Z.map(r => r[0]);
    const decks = (a: number, c: number, color: string, extra: number[] = []) => {
      bbSweep(b, p, a, c, {half: BB_HALF, top: zU, depth: 1.6, color, road: BB_ROAD, extra: [...zN, ...extra], ends: true});
      bbSweep(b, p, a, c, {half: BB_HALF, top: s => zU(s) - BB_DECKS, depth: BB_TRUSS - BB_DECKS, color, road: BB_ROAD, extra: [...zN, ...extra], ends: true});
    };
    const frameAt = (s: number, fn: () => void) => {
      const q = bbPos(p, s);
      b.frame(q[0], q[1], 0, bbBearing(p, s), fn);
    };
    if (part === 'detour') {
      // temporary double-deck steel viaduct on steel bents
      const q = bbPath(BB_SCURVE_LL.map(c => lngLatToLocal(BB_E2, c)));
      const z = (s: number) => tab(BB_SCURVE_Z, s);
      const zs = BB_SCURVE_Z.map(r => r[0]);
      bbSweep(b, q, 0, q.s1, {half: BB_HALF, top: z, depth: 1.6, color: STEEL_GREY, road: BB_ROAD, extra: zs, ends: true});
      bbSweep(b, q, 0, q.s1, {half: BB_HALF, top: s => z(s) - BB_DECKS, depth: 2.1, color: STEEL_GREY, road: BB_ROAD, extra: zs, ends: true});
      b.color(STEEL_GREY);
      for (let s = 40; s < q.s1 - 20; s += 55) {
        const c = bbPos(q, s);
        b.frame(c[0], c[1], 0, bbBearing(q, s), () => {
          for (const x of [-8.5, 8.5]) b.box(x, 0, 0, 2, 2, z(s) - BB_TRUSS, {top: false});
        });
      }
      return;
    }
    if (part === 'viaduct') {
      // island viaduct: 790.8 ft of concrete, then 1,169.7 ft of curved steel deck trusses to pier E1
      const sC = pier(1) - 356.5;
      decks(p.s0, sC, BB_CONC);
      decks(sC, pier(1), BB_OLD);
      for (let s = p.s0 + 30; s < sC; s += 35) frameAt(s, () => b.color(BB_CONC).box(0, 0, 0, 16, 3, zU(s) - BB_TRUSS, {top: false}));
      b.color(BB_OLD);
      for (let s = sC; s < pier(1) - 20; s += 59.4) {
        frameAt(s, () => {
          for (const x of [-8, 8]) b.beam([x, 0, 0], [x * 0.9, 0, zU(s) - BB_TRUSS], 2.2);
        });
      }
      for (const o of [-BB_HALF, BB_HALF]) {
        let up = true;
        for (let s = sC; s < pier(1) - 1; s += 17.8) {
          const s1 = Math.min(s + 17.8, pier(1));
          const [sl, sh] = up ? [s, s1] : [s1, s];
          const lo = bbAt(p, sl, o);
          const hi = bbAt(p, sh, o);
          bbWeb(b, [lo[0], lo[1], zU(sl) - BB_DECKS], [hi[0], hi[1], zU(sh) - 1.6], 0.8);
          up = !up;
        }
      }
      return;
    }
    if (part === 'approach') {
      // girder spans from pier E23 down to the Oakland fill; the lower roadway reaches the ground first
      const s23 = pier(23);
      const sLow = 2762;
      bbSweep(b, p, s23, p.s1, {half: BB_HALF, top: zU, depth: 2, color: BB_OLD, road: BB_ROAD, extra: zN, ends: true});
      bbSweep(b, p, s23, sLow, {half: BB_HALF, top: s => zU(s) - BB_DECKS, depth: 1.4, color: BB_OLD, road: BB_ROAD, extra: zN, ends: true});
      for (let s = s23 + 30; s < p.s1 - 60; s += 30) frameAt(s, () => b.color(BB_CONC).box(0, 0, 0, 19, 2, zU(s) - 2, {top: false}));
      return;
    }
    if (part === 'causeway') {
      // fourteen deck-truss spans E9 – E23 round the bend
      decks(pier(9), pier(23), BB_OLD);
      b.color(BB_OLD);
      for (const o of [-BB_HALF, BB_HALF]) {
        for (let k = 9; k < 23; k++) {
          const a = pier(k);
          const step = (pier(k + 1) - a) / 4;
          for (let i = 0; i < 4; i++) {
            const [sl, sh] = i % 2 === 0 ? [a + i * step, a + (i + 1) * step] : [a + (i + 1) * step, a + i * step];
            const lo = bbAt(p, sl, o);
            const hi = bbAt(p, sh, o);
            bbWeb(b, [lo[0], lo[1], zU(sl) - BB_DECKS], [hi[0], hi[1], zU(sh) - 1.6], 0.8);
          }
        }
      }
      for (let k = 10; k <= 23; k++) frameAt(pier(k), () => bbOldPier(b, zU(pier(k)) - BB_TRUSS, 20, 6.5, false));
      return;
    }
    // cantilever and through trusses: one straight frame, +y from E2 toward E3
    b.frame(0, 0, 0, bbBearing(p, 200), () => {
      const s = bbPath([[0, pier(1)], [0, pier(9)]], pier(1));
      const slabs = (a: number, c: number) => {
        bbSweep(b, s, a, c, {half: BB_HALF, top: zU, depth: 1.6, color: BB_OLD, road: BB_ROAD, extra: zN, ends: true});
        bbSweep(b, s, a, c, {half: BB_HALF, top: y => zU(y) - BB_DECKS, depth: BB_TRUSS - BB_DECKS, color: BB_OLD, road: BB_ROAD, extra: zN, ends: true});
      };
      if (part === 'cantilever') {
        // 508 ft anchor arm, 1,400 ft main span, 512 ft anchor arm; top chord from the 2010 lidar: 87–95 m on
        // the arms, 100–103 m over the main piers, 90 m on the suspended span
        const e1 = pier(1);
        const e3 = pier(3);
        const e4 = pier(4);
        slabs(e1, e4);
        const top: Tab = [
          [e1, 67.5], [e1 + 9, 68], [e1 + 28, 87], [-97, 89.5], [-70, 94.5], [-38, 103], [0, 103], [30, 100], [52, 99.5], [75, 95], [95, 91.5], [125, 90.2],
          [300, 90.2], [330, 91.5], [350, 94.5], [372, 99.5], [e3, 100.5], [476, 99.5], [500, 93.5], [525, 89.5], [552, 87], [e4 - 11, 68], [e4, 67]
        ];
        const ys = [e1 + 9, e1 + 28, -97, -70, -38, 0, 30, 52, 75, 95, 125, 160, 195, 230, 265, 300, 330, 350, 372, 399, e3, 454, 476, 500, 525, 552, e4 - 11];
        b.color(BB_OLD);
        bbTruss(
          b,
          BB_HALF,
          ys.map(y => ({y, zb: zU(y) - BB_TRUSS, zt: tab(top, y)}))
        );
        // main posts over E2 / E3 spread from the pier to the top chord
        for (const y of [0, e3])
          for (const x of [-BB_HALF, BB_HALF]) {
            const zb = zU(y) - BB_TRUSS;
            bbRod(b, [x, y, zb], [x, y - 32, tab(top, y - 32)], 2.4);
            bbRod(b, [x, y, zb], [x, y + 30, tab(top, y + 30)], 2.4);
          }
        b.frame(0, e1, 0, 0, () => bbOldPier(b, zU(e1) - BB_TRUSS, 22, 7, false));
        b.frame(0, 0, 0, 0, () => bbOldPier(b, zU(0) - BB_TRUSS, 26, 13));
        b.frame(0, e3, 0, 0, () => bbOldPier(b, zU(e3) - BB_TRUSS, 28, 15));
        b.frame(0, e4, 0, 0, () => bbOldPier(b, zU(e4) - BB_TRUSS, 24, 10));
      } else {
        // five 504 ft through trusses E4 – E9: top chord 16.3 m above the upper roadway, end posts raked over 25 m
        slabs(pier(4), pier(9));
        b.color(BB_OLD);
        for (let k = 4; k < 9; k++) {
          const a = pier(k);
          const L = pier(k + 1) - a;
          const ys = [0, 1, 2, 3, 4, 5, 6].map(i => a + (L * i) / 6);
          bbTruss(
            b,
            BB_HALF,
            ys.map((y, i) => ({y, zb: zU(y) - BB_TRUSS, zt: i === 0 || i === 6 ? zU(y) + 0.5 : zU(y) + 16.3})),
            1
          );
          b.frame(0, a + L, 0, 0, () => bbOldPier(b, zU(a + L) - BB_TRUSS, 22, 9));
        }
      }
    });
  };
}
const eastFacts = {
  Opened: 'Nov 12, 1936',
  Form: 'double-deck: island viaduct, cantilever (508 + 1,400 + 512 ft, main span 427 m), five 504 ft (154 m) through trusses, fourteen 288 ft deck trusses, girder spans to the Oakland fill',
  Clearance: '58 m (191 ft) under the cantilever; trusses 100–103 m high over the main piers',
  '1989': 'a 15 m section of upper deck at pier E9 collapsed in the Loma Prieta quake',
  Replaced: 'closed Aug 28, 2013; dismantled Nov 2013 – Nov 2017: cantilever gone by Jun 12, 2015, the five 504 ft trusses lowered Feb – Aug 2016, the last 288 ft truss removed Mar 2017, the piers imploded Nov 2015 – Nov 2017',
  Model:
    'alignment (south of today’s span: 50 m off along the causeway, up to 200 m at the through trusses) and heights from the 2010 USGS lidar of the standing bridge and the three foundations kept for the 2020 observation pier; the 11° bend east of pier E9 lies in a gap of the 2010 surveys and is spread over piers E9–E11, the fourteen deck spans over the surveyed distance (90 m each) — estimated; member sizes estimated'
};
const eastSrc = [BB_WIKI_EAST, BB_WIKI, BB_LIDAR, 'https://www.cbsnews.com/sanfrancisco/news/demolition-of-old-bay-bridge-to-take-years', 'https://abc7news.com/demolition-of-old-span-bay-bridge-project/1799171/'];
const bayBridgeEastOld: Landmark[] = [
  {
    id: 'bay_bridge_ybi_viaduct_1936',
    name: 'Bay Bridge east span (1936) — Yerba Buena Island viaduct',
    kind: 'bridge',
    built: [1933.52, 1936.87],
    end: 2009.68,
    anchor: BB_E2,
    build: eastOldPart('viaduct'),
    facts: {
      Opened: 'Nov 12, 1936',
      Form: 'double-deck viaduct from the tunnel to the cantilever: 241 m (790.8 ft) of concrete, then 357 m (1,169.7 ft) of curved steel deck trusses',
      Replaced: 'a 300 ft section by the tunnel was renewed over Labor Day 2007; in Sep 2009 traffic moved to a temporary bypass and the viaduct was taken down for the transition structure of the new span',
      Model: 'tangent – curve (R ≈ 550 m) – tangent between the tunnel axis and the cantilever axis of the 2010 lidar (the viaduct itself was gone by then); piers schematic'
    },
    sources: [BB_WIKI, BB_WIKI_EAST, BB_LIDAR]
  },
  {
    id: 'bay_bridge_ybi_detour_2009',
    name: 'Bay Bridge — Yerba Buena Island temporary bypass ("S-curve")',
    kind: 'bridge',
    built: [2008.0, 2009.68],
    end: 2013.66,
    anchor: BB_E2,
    build: eastOldPart('detour'),
    facts: {
      'In service': 'Sep 2009 – Aug 28, 2013',
      Form: 'temporary double-deck steel viaduct swinging south of the old one between the tunnel and the cantilever, so the transition structure of the new span could be built in its place',
      Known: 'for its tight reverse curve: 40 mph limit after a fatal accident',
      Model: 'centreline and roadway heights (57–66 m) from the 2010 USGS lidar; the reverse curve at the tunnel smoothed; start of construction estimated; bents schematic'
    },
    sources: [BB_WIKI_EAST, BB_LIDAR]
  },
  {id: 'bay_bridge_east_1936_cantilever', name: 'Bay Bridge east span (1936) — cantilever', kind: 'bridge', built: [1933.52, 1936.87], end: 2015.45, anchor: BB_E2, build: eastOldPart('cantilever'), facts: eastFacts, sources: eastSrc},
  {id: 'bay_bridge_east_1936_trusses', name: 'Bay Bridge east span (1936) — truss spans', kind: 'bridge', built: [1933.52, 1936.87], end: 2016.6, anchor: BB_E2, build: eastOldPart('trusses'), facts: eastFacts, sources: eastSrc},
  {id: 'bay_bridge_east_1936_causeway', name: 'Bay Bridge east span (1936) — causeway', kind: 'bridge', built: [1933.52, 1936.87], end: 2017.2, anchor: BB_E2, build: eastOldPart('causeway'), facts: eastFacts, sources: eastSrc},
  {
    id: 'bay_bridge_east_1936_approach',
    name: 'Bay Bridge east span (1936) — Oakland approach spans',
    kind: 'bridge',
    built: [1933.52, 1936.87],
    end: 2012.13,
    anchor: BB_E2,
    build: eastOldPart('approach'),
    facts: {
      Opened: 'Nov 12, 1936',
      Form: 'low girder spans from the last deck truss (pier E23) down to the fill of the Oakland approach',
      Replaced: 'the eastbound touchdown of the new span stands on the same ground: traffic was moved to temporary detours and the spans removed before the touchdown was finished in 2013',
      Model: 'alignment and roadway heights (17 m at E23 to the ground, 2.7 %) from the 2010 USGS lidar; removal dated to the second stage of the touchdown work (Feb 19, 2012) — estimated; the detour roads are not modelled; bents schematic'
    },
    sources: [BB_WIKI_EAST, BB_LIDAR]
  }
];

// --------------------------------------------------------------- new east span (2013)
// island transition structure (2010–13), self-anchored suspension span (2009–13), skyway (2002–07) and
// Oakland touchdown: the OSM centrelines of the westbound (north) and eastbound (south) roadways
const SAS_TOWER: V2 = [-122.358479, 37.815265];
const SAS_CX = 1.35; // the bridge centreline passes 1.35 m south-east of the OSM tower centroid (lidar)
const BB_WHITE = '#F1F1EE';
const BB_NEWDECK = '#C9CDD0';
const YBITS_WB: V2[] = [
  [-122.365053, 37.810174], [-122.364722, 37.810474], [-122.364471, 37.810711], [-122.363962, 37.811202], [-122.363652, 37.81151], [-122.362513, 37.812749],
  [-122.362315, 37.812951], [-122.36211, 37.81315], [-122.361787, 37.813436], [-122.361317, 37.813815], [-122.360846, 37.814138], [-122.360592, 37.814299],
  [-122.360305, 37.814471]
];
const YBITS_EB: V2[] = [
  [-122.365024, 37.810153], [-122.36469, 37.810457], [-122.364032, 37.81107], [-122.363126, 37.81194], [-122.362835, 37.812202], [-122.362609, 37.812396],
  [-122.362386, 37.812579], [-122.362153, 37.812763], [-122.361802, 37.813028], [-122.361316, 37.813371], [-122.360943, 37.813617], [-122.360688, 37.813777],
  [-122.360432, 37.813932], [-122.360027, 37.814164]
];
const SKY_WB: V2[] = [
  [-122.355096, 37.817447], [-122.354819, 37.817601], [-122.354544, 37.817746], [-122.353977, 37.818018], [-122.353689, 37.818144], [-122.353394, 37.818265],
  [-122.353088, 37.818384], [-122.352797, 37.818488], [-122.352181, 37.818687], [-122.351873, 37.818774], [-122.351558, 37.818857], [-122.350923, 37.819003],
  [-122.350605, 37.819066], [-122.350281, 37.81912], [-122.333686, 37.821549], [-122.332754, 37.821678], [-122.331781, 37.821801], [-122.331127, 37.821877],
  [-122.329817, 37.822015], [-122.329161, 37.822075], [-122.328175, 37.822157], [-122.324869, 37.822408]
];
const SKY_EB: V2[] = [
  [-122.354819, 37.817141], [-122.35453, 37.8173], [-122.354254, 37.817444], [-122.353832, 37.817648], [-122.353528, 37.817782], [-122.353237, 37.817904],
  [-122.352944, 37.818019], [-122.352644, 37.818128], [-122.352187, 37.81828], [-122.351874, 37.818373], [-122.351563, 37.818458], [-122.35125, 37.818537],
  [-122.350932, 37.81861], [-122.350297, 37.818733], [-122.34999, 37.818781], [-122.333602, 37.821178], [-122.332283, 37.82136], [-122.331631, 37.821443],
  [-122.330629, 37.821561], [-122.329012, 37.821722], [-122.327715, 37.821831], [-122.325392, 37.821999]
];
// roadway heights (m NAVD88, 2023 / 2021 lidar) by distance along each path
const YBITS_WB_Z: Tab = [[0, 56.6], [35, 57.4], [75, 58.1], [115, 58.6], [155, 59.4], [195, 60.1], [235, 60.6], [275, 61.1], [315, 61.1], [515, 59.6], [595, 58.6], [637, 58.1]];
const YBITS_EB_Z: Tab = [[0, 48.7], [325, 52.9], [405, 53.4], [445, 53.9], [485, 54.6], [565, 55.6], [605, 56.1], [628, 56.1]];
const SAS_WB_Z: Tab = [[-181, 58.1], [-101, 57.1], [-21, 56.1], [59, 55.4], [139, 54.4], [219, 53.4], [299, 52.1], [385, 50.8]];
const SAS_EB_Z: Tab = [[-181, 56.1], [-124, 56.1], [-44, 55.6], [36, 54.6], [116, 53.9], [196, 52.9], [276, 51.6], [385, 50]];
const SKY_WB_Z: Tab = [
  [0, 50.8], [34, 50.4], [314, 46.6], [514, 43.4], [674, 40.9], [834, 38.1], [994, 35.6], [1154, 32.9], [1314, 29.9], [1474, 27.1], [1634, 24.1], [1794, 20.9],
  [1954, 17.9], [2114, 14.6], [2274, 11.6], [2394, 9.4], [2494, 7.4], [2554, 6.1], [2634, 5.4], [2694, 4.6], [2734, 4.4]
];
const SKY_EB_Z: Tab = [
  [0, 50], [51, 49.4], [131, 48.1], [251, 46.6], [411, 44.4], [531, 42.6], [691, 40.4], [851, 37.6], [1011, 35.1], [1171, 32.1], [1331, 29.4], [1491, 26.4],
  [1651, 23.1], [1811, 20.1], [1971, 17.1], [2131, 14.1], [2291, 10.9], [2411, 8.6], [2511, 6.9], [2571, 5.9], [2611, 5.4], [2661, 4.9]
];
const SAS_W2 = -180; // west pier (back span 180 m)
const SAS_E2 = 385; // east pier (main span 385 m)
const SAS_DECK_X = 21.6; // centres of the two 28 m box girders either side of the centreline (lidar)

const ybits: Landmark = {
  id: 'bay_bridge_east_2013_ybits',
  name: 'Bay Bridge east span (2013) — Yerba Buena Island transition structure',
  kind: 'bridge',
  built: [2010.0, 2013.67],
  end: 9999,
  anchor: SAS_TOWER,
  build: b => {
    for (const [ll, zt, wb] of [[YBITS_WB, YBITS_WB_Z, true], [YBITS_EB, YBITS_EB_Z, false]] as [V2[], Tab, boolean][]) {
      const p = bbPath(ll.map(q => lngLatToLocal(SAS_TOWER, q)));
      const z = (s: number) => tab(zt, s);
      // the roadways leave the tunnel stacked (westbound above) and fan out to the two decks of the span
      const half = (s: number) => 10.3 + (3.7 * s) / p.s1;
      const st = bbStations(p, 0, p.s1, 60, zt.map(r => r[0]));
      for (let i = 0; i < st.length - 1; i++)
        bbSweep(b, p, st[i], st[i + 1], {half: half((st[i] + st[i + 1]) / 2), off: wb ? 0.85 : 1.5, top: z, depth: 3.2, color: BB_CONC, road: BB_ROAD});
      for (let s = wb ? 60 : 95; s < p.s1 - 20; s += 70) {
        const q = bbAt(p, s, wb ? 0.85 : 1.5);
        b.frame(q[0], q[1], 0, bbBearing(p, s), () => b.color(BB_CONC).box(0, 0, 0, 7, 3, z(s) - 3.2, {top: false}));
      }
    }
  },
  facts: {
    Opened: 'Sep 2, 2013',
    Form: 'concrete box-girder viaducts carrying the stacked roadways of the tunnel out to the side-by-side decks of the suspension span',
    Length: '≈ 630 m',
    Model: 'OSM centrelines; heights from the 2023 USGS lidar (westbound 57–61 m, eastbound 48–56 m); the eastbound roadway under the westbound one east of the tunnel is hidden from the lidar and interpolated; columns schematic'
  },
  sources: [BB_WIKI_EAST, BB_LIDAR, BB_OSM]
};

const sasSpan: Landmark = {
  id: 'bay_bridge_east_2013_sas',
  name: 'Bay Bridge east span (2013) — self-anchored suspension span',
  kind: 'bridge',
  built: [2009.0, 2013.67],
  end: 9999,
  anchor: SAS_TOWER,
  build: b => {
    // frame: +y along the straight span (OSM centreline of the eastbound roadway), +x to the south-east
    b.frame(0, 0, 0, along(SAS_TOWER, [-122.360101, 37.814122], [-122.354804, 37.81715]).bearing, () => {
      const axis = bbPath([[SAS_CX, SAS_W2], [SAS_CX, SAS_E2]], SAS_W2);
      const zW = (y: number) => tab(SAS_WB_Z, y);
      const zE = (y: number) => tab(SAS_EB_Z, y);
      // twin steel box girders (28 m each, 5.5 m deep) tied by crossbeams every 30 m; bike path on the south side
      bbSweep(b, axis, SAS_W2, SAS_E2, {half: 14, off: -SAS_DECK_X, top: zW, depth: 5.5, color: BB_NEWDECK, road: BB_ROAD, extra: SAS_WB_Z.map(r => r[0]), ends: true});
      bbSweep(b, axis, SAS_W2, SAS_E2, {half: 14, off: SAS_DECK_X, top: zE, depth: 5.5, color: BB_NEWDECK, road: BB_ROAD, extra: SAS_EB_Z.map(r => r[0]), ends: true});
      bbSweep(b, axis, SAS_W2, SAS_E2, {half: 2.35, off: SAS_DECK_X + 18, top: y => zE(y) - 0.3, depth: 1, color: BB_NEWDECK, road: '#8A8D8C', extra: SAS_EB_Z.map(r => r[0])});
      b.color(BB_NEWDECK);
      for (let y = SAS_W2 + 25; y < SAS_E2; y += 30) if (Math.abs(y) > 12) b.box(SAS_CX, y, zE(y) - 5, 2 * (SAS_DECK_X - 14), 3, 4, {top: false});
      // piers: W2 on the island (cap beam where the cable turns back), E2 in the bay
      b.color(BB_CONC).box(SAS_CX, SAS_W2 - 4, zE(SAS_W2) - 12, 76, 10, 11);
      for (const sx of [-1, 1]) b.box(SAS_CX + sx * SAS_DECK_X, SAS_W2 - 4, 0, 10, 8, zE(SAS_W2) - 12, {top: false});
      b.box(SAS_CX, SAS_E2, zE(SAS_E2) - 10.7, 72, 6, 5);
      for (const sx of [-1, 1]) b.box(SAS_CX + sx * SAS_DECK_X, SAS_E2, 0, 9, 7, zE(SAS_E2) - 10.7, {top: false});
      // single tower: four legs tied by shear links, 525 ft; lidar: 13 m wide at the roadway, 9 m at the top (163 m)
      b.color(BB_CONC).box(SAS_CX, 0, 0, 39, 30, 4.5);
      b.color(BB_WHITE);
      const top = 158;
      const lc = (z: number) => 4.2 - (1.4 * (z - 4.5)) / (top - 4.5);
      for (const sx of [-1, 1]) for (const sy of [-1, 1]) b.loft([rect(SAS_CX + sx * lc(4.5), sy * lc(4.5), 5.4, 5.4), rect(SAS_CX + sx * lc(top), sy * lc(top), 3.4, 3.4)], [4.5, top], {top: false});
      for (let z = 22; z < top - 6; z += 18) b.box(SAS_CX, 0, z, 2 * lc(z), 1.3, 2.4).box(SAS_CX, 0, z, 1.3, 2 * lc(z), 2.4);
      b.box(SAS_CX, 0, top, 9.4, 9.4, 5);
      // one cable: anchored in the deck at the east pier, over the tower, round the west end and back
      const edge = SAS_DECK_X + 13.2; // the suspenders hold the outer edges of the two girders
      for (const sx of [-1, 1]) {
        const cable = (y0: number, y1: number, x1: number, z1: number, sagX: number, sagZ: number, n: number): V3[] => {
          const out: V3[] = [];
          for (let i = 0; i <= n; i++) {
            const t = i / n;
            const k = 4 * t * (1 - t);
            out.push([SAS_CX + sx * (2.4 + (x1 - 2.4) * t + sagX * k), y0 + (y1 - y0) * t, top + 1 + (z1 - top - 1) * t - sagZ * k]);
          }
          return out;
        };
        const back = cable(0, SAS_W2, edge, zE(SAS_W2) + 2.5, 1.4, 6.3, 8);
        const main = cable(0, 300, edge, zE(300) + 2.5, 5, 18.5, 12);
        b.color(BB_WHITE);
        for (const c of [back, main]) {
          for (let i = 0; i < c.length - 1; i++) bbRod(b, c[i], c[i + 1], 1.3);
          for (let i = 1; i < c.length - 1; i++) {
            const zd = (sx < 0 ? zW : zE)(c[i][1]);
            if (c[i][2] - zd > 5) bbRod(b, [SAS_CX + sx * edge, c[i][1], zd], c[i], 0.5);
          }
        }
        const e = main[main.length - 1];
        bbRod(b, e, [e[0], SAS_E2 - 4, zE(SAS_E2) + 0.5], 1.3);
      }
      const zl = zE(SAS_W2) + 2.5;
      bbRod(b, [SAS_CX - edge, SAS_W2, zl], [SAS_CX - edge, SAS_W2 - 7, zl - 1.5], 1.3);
      bbRod(b, [SAS_CX + edge, SAS_W2, zl], [SAS_CX + edge, SAS_W2 - 7, zl - 1.5], 1.3);
      bbRod(b, [SAS_CX - edge, SAS_W2 - 7, zl - 1.5], [SAS_CX + edge, SAS_W2 - 7, zl - 1.5], 1.3);
    });
  },
  // the tower's generic footprint (OSM bridge structure, a 53 m LiDAR prism) stands inside the model
  replaces: [rect(0, 0, 120, 120)],
  facts: {
    Opened: 'Sep 2, 2013',
    Form: 'single-tower self-anchored suspension span (world’s largest): one cable anchored in the deck at the east pier, over the tower and looped round the west end',
    Tower: '160 m (525 ft), four legs with shear links; top 163 m above the bay',
    Spans: 'main span 385 m (1,263 ft), back span 180 m; 624 m in all',
    Decks: 'two steel box girders side by side, 78.7 m over all (258 ft) with the bike path; roadway 50–58 m above the bay (58 m / 191 ft clear)',
    Model: 'tower from the OSM footprint; decks, cable and heights measured on the 2023 USGS lidar; piers and member sizes estimated'
  },
  sources: [BB_WIKI_EAST, BB_LIDAR, BB_OSM]
};

/** One roadway of the skyway / Oakland touchdown between distances a and c along its OSM centreline. */
const SKY_LEN = 2103; // 6,900 ft of skyway; beyond it the low touchdown spans, then fill
const SKY_EB_2007 = 2300; // the eastbound roadway ended here until the old approach was out of the way (2010 lidar)
function bbSkyDeck(b: MeshBuilder, wb: boolean, a: number, c: number) {
  const p = bbPath((wb ? SKY_WB : SKY_EB).map(q => lngLatToLocal(SAS_TOWER, q)));
  const zt = wb ? SKY_WB_Z : SKY_EB_Z;
  const z = (s: number) => tab(zt, s);
  const off = wb ? 0.85 : 1.5;
  const SPAN = 160; // 525 ft, fourteen piers
  const fill = wb ? 2560 : 2480; // from here the road is on the touchdown fill
  const end = Math.min(c, p.s1);
  // haunched box girder: 5.5 m at mid-span, 9 m over the piers (estimated)
  const depth = (s: number) => {
    if (s > fill) return Math.max(z(s) - 2.5, 1);
    if (s > SKY_LEN) return 3;
    return 5.5 + 3.5 * Math.abs((2 * (s % SPAN)) / SPAN - 1);
  };
  const extra = zt.map(r => r[0]).filter(s => s < 300 || s > SKY_LEN);
  for (let s = SPAN / 2; s < SKY_LEN; s += SPAN / 2) extra.push(s);
  extra.push(SKY_LEN, SKY_LEN + 1.5, fill, fill + 1.5);
  bbSweep(b, p, a, end, {half: 13.8, off, top: z, depth, color: BB_NEWDECK, road: BB_ROAD, extra, ends: true});
  if (!wb && a < fill) bbSweep(b, p, a, Math.min(end, fill), {half: 2.35, off: off + 16.3, top: s => z(s) - 0.3, depth: 1, color: BB_NEWDECK, road: '#8A8D8C', step: 320});
  const piers: number[] = [];
  for (let s = SPAN; s < SKY_LEN; s += SPAN) piers.push(s);
  for (let s = SKY_LEN + 50; s < fill - 20; s += 62) piers.push(s);
  for (const s of piers) {
    if (s < a || s > end) continue;
    const q = bbAt(p, s, off);
    b.frame(q[0], q[1], 0, bbBearing(p, s), () => b.color('#BDBAB3').box(0, 0, 0, s < SKY_LEN ? 8.5 : 6, s < SKY_LEN ? 6 : 2.5, z(s) - depth(s), {top: false}));
  }
}
const skyway: Landmark = {
  id: 'bay_bridge_east_2013_skyway',
  name: 'Bay Bridge east span (2013) — skyway',
  kind: 'bridge',
  built: [2002.08, 2007.5],
  end: 9999,
  anchor: SAS_TOWER,
  build: b => {
    bbSkyDeck(b, true, 0, 1e9);
    bbSkyDeck(b, false, 0, SKY_EB_2007);
  },
  facts: {
    Construction: '2002 – 2007 (opened with the suspension span, Sep 2, 2013)',
    Form: 'twin precast segmental concrete box-girder viaducts, 2.1 km (6,900 ft), typical span 160 m (525 ft); then the low spans of the Oakland touchdown',
    Grade: '1.8 % down from 50 m at the suspension span to the Oakland shore',
    Model: 'OSM centrelines of the two roadways (curve at the island end included); heights from the 2023 and 2021 USGS lidar; girder depth and piers estimated; the westbound touchdown is dated with the skyway'
  },
  sources: [BB_WIKI_EAST, 'https://asbi-assoc.org/project/san-francisco-oakland-bay-bridge-new-east-span-skyway-san-francisco-and-oakland-california/', BB_LIDAR, BB_OSM]
};
const touchdown: Landmark = {
  id: 'bay_bridge_east_2013_touchdown',
  name: 'Bay Bridge east span (2013) — eastbound Oakland touchdown',
  kind: 'bridge',
  built: [2012.13, 2013.67],
  end: 9999,
  anchor: SAS_TOWER,
  build: b => bbSkyDeck(b, false, SKY_EB_2007, 1e9),
  facts: {
    Opened: 'Sep 2, 2013',
    Form: 'last 360 m of the eastbound roadway, low spans and fill, on the ground of the old bridge’s approach',
    Construction: 'on the ground of the old approach once it was out of the way: second stage of the touchdown work Feb 19, 2012, finished Mar 2013',
    Model: 'OSM centreline; heights from the 2021 USGS lidar (9 m down to 5 m); the split from the skyway is where the eastbound roadway ended in the 2010 lidar'
  },
  sources: [BB_WIKI_EAST, BB_LIDAR, BB_OSM]
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
  bayBridgeTunnel,
  ...bayBridgeEastOld,
  ybits,
  sasSpan,
  skyway,
  touchdown,
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
