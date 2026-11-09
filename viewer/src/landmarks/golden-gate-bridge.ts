/**
 * Golden Gate Bridge — reconstructed from data/research/landmarks.md:
 * tower positions from OSM pier geometry, tier sizes from the OSM 3D parts
 * (consistent with the District's 227 m / 10 × 16 m leg figures), deck 27 m
 * wide with 7.6 m stiffening trusses at ~75 m, main cable sag to ~83 m,
 * suspenders every 15.2 m, Fort Point arch between pylons S1/S2,
 * International Orange #C0362C.
 */
import {lngLatToLocal, parabola, rect, ellipse, type V2, type V3, MeshBuilder} from './kit';
import type {Landmark} from './types';

const ORANGE = '#C0362C';
const ORANGE_DARK = '#9E2B23';
const CONCRETE = '#BDB8AE';
const ROAD = '#55524E';

const ANCHOR: V2 = [-122.478563, 37.819757]; // mid-span
const S_TOWER: V2 = [-122.477892, 37.814013];
const N_TOWER: V2 = [-122.479234, 37.8255];
const S_ANCH: V2 = [-122.477426, 37.809601];
const N_ANCH: V2 = [-122.479678, 37.829063];
const PYLON_S1: V2 = [-122.47752, 37.81096];
const PYLON_S2: V2 = [-122.47741, 37.80994];
const PYLON_N1: V2 = [-122.4796, 37.82859];
const S_ABUT: V2 = [-122.47665, 37.808];
const N_ABUT: V2 = [-122.4807, 37.8323];

const DECK_Z = 75; // roadway at the towers (m above water)
const TRUSS = 7.6;
const HALF_W = 13.7; // cable / truss planes (cables 27.4 m apart)
const TOWER_TOP = 225;

/** Along-axis coordinate of a lon/lat (projected on the bridge axis). */
function axisFrame() {
  const s = lngLatToLocal(ANCHOR, S_TOWER);
  const n = lngLatToLocal(ANCHOR, N_TOWER);
  const dx = n[0] - s[0];
  const dy = n[1] - s[1];
  const len = Math.hypot(dx, dy);
  const bearing = (Math.atan2(dx, dy) * 180) / Math.PI;
  const ux = dx / len;
  const uy = dy / len;
  const along = (p: V2) => {
    const l = lngLatToLocal(ANCHOR, p);
    return l[0] * ux + l[1] * uy;
  };
  const across = (p: V2) => {
    const l = lngLatToLocal(ANCHOR, p);
    return l[0] * uy - l[1] * ux;
  };
  return {bearing, along, across, half: len / 2};
}

function tower(b: MeshBuilder, y: number, inWater: boolean) {
  // concrete pier (shared by both legs)
  b.color(CONCRETE).box(0, y, 0, 42, 20.3, 13);
  if (inWater) {
    // oval fender ring ("bathtub") ~90 m across × 45 m along, 4 m above water
    const outer = ellipse(0, y, 45, 22.5, 28);
    const inner = ellipse(0, y, 40, 17.5, 28);
    b.color(CONCRETE).prism(outer, 0, 4, {holes: [inner]});
  }
  // legs: tiers (z0, z1, along-axis size, across size)
  const tiers: [number, number, number, number][] = [
    [13, 21, 15.6, 9.6],
    [21, 74, 13.8, 7.5],
    [74, 123, 11.7, 7.5],
    [123, 162, 9.8, 7.5],
    [162, 195, 9.8, 5.4],
    [195, TOWER_TOP, 7.4, 3.3]
  ];
  b.color(ORANGE);
  for (const sx of [-HALF_W, HALF_W]) {
    for (const [z0, z1, along, across] of tiers) b.box(sx, y, z0, across, along, z1 - z0);
    // stepped cap with beacon
    b.box(sx, y, TOWER_TOP, 2.6, 5, 2.2);
  }
  // horizontal portal struts (above deck the openings shrink going up)
  const struts: [number, number][] = [
    [24, 26],
    [50, 52],
    [111, 121],
    [151, 161],
    [185, 193],
    [215, 223]
  ];
  for (const [z0, z1] of struts) b.box(0, y, z0, 2 * HALF_W, 3.7, z1 - z0);
  // below-deck X bracing
  b.color(ORANGE_DARK);
  b.beam([-HALF_W, y, 26], [HALF_W, y, DECK_Z - TRUSS - 2], 1.6);
  b.beam([HALF_W, y, 26], [-HALF_W, y, DECK_Z - TRUSS - 2], 1.6);
}

function deckSegment(b: MeshBuilder, y0: number, y1: number, z0: number, z1: number) {
  // stiffening truss box (orange sides) + roadway top
  const d = TRUSS;
  const xs = [-HALF_W, HALF_W];
  b.color(ORANGE);
  b.quad([xs[0], y0, z0 - d], [xs[0], y1, z1 - d], [xs[0], y1, z1], [xs[0], y0, z0]);
  b.quad([xs[1], y0, z0 - d], [xs[1], y1, z1 - d], [xs[1], y1, z1], [xs[1], y0, z0]);
  b.color(ORANGE_DARK);
  b.quad([xs[0], y0, z0 - d], [xs[1], y0, z0 - d], [xs[1], y1, z1 - d], [xs[0], y1, z1 - d]);
  b.color(ROAD);
  b.quad([xs[0], y0, z0], [xs[1], y0, z0], [xs[1], y1, z1], [xs[0], y1, z1]);
}

function build(b: MeshBuilder) {
  const ax = axisFrame();
  const yS = -ax.half;
  const yN = ax.half;
  const yS1 = ax.along(PYLON_S1);
  const yS2 = ax.along(PYLON_S2);
  const yN1 = ax.along(PYLON_N1);
  const ySA = ax.along(S_ANCH);
  const yNA = ax.along(N_ANCH);

  b.frame(0, 0, 0, ax.bearing, () => {
    tower(b, yS, true);
    tower(b, yN, false);

    // deck: crowns gently from 75 m at the towers to ~74.6+ at mid-span; side spans level
    const deckZ = (y: number) => {
      const t = Math.min(1, Math.abs(y) / ax.half);
      return DECK_Z - 0.4 * (1 - t * t) + 0.4;
    };
    const ys = [yS2, ySA, yS1, yS];
    for (let i = 0; i <= 24; i++) ys.push(yS + ((yN - yS) * i) / 24);
    ys.push(yN, yN1, yNA);
    ys.sort((a, c) => a - c);
    for (let i = 0; i < ys.length - 1; i++) {
      if (ys[i + 1] - ys[i] < 0.5) continue;
      deckSegment(b, ys[i], ys[i + 1], deckZ(ys[i]), deckZ(ys[i + 1]));
    }

    // main cables + suspenders
    b.color(ORANGE);
    for (const x of [-HALF_W, HALF_W]) {
      const main = parabola([x, yS, TOWER_TOP - 1], [x, yN, TOWER_TOP - 1], DECK_Z + 8, 40);
      b.polyline(main, 1.3);
      const sideS = parabola([x, yS1, DECK_Z + 4], [x, yS, TOWER_TOP - 1], (DECK_Z + 4 + TOWER_TOP) / 2 - 18, 12);
      const sideN = parabola([x, yN, TOWER_TOP - 1], [x, yN1, DECK_Z + 4], (DECK_Z + 4 + TOWER_TOP) / 2 - 18, 12);
      b.polyline(sideS, 1.3);
      b.polyline(sideN, 1.3);
      // suspenders every 15.2 m (rendered a little thicker than the 68 mm ropes so they read)
      const cableZ = (pts: V3[], y: number) => {
        for (let i = 0; i < pts.length - 1; i++) {
          const [a, c] = [pts[i], pts[i + 1]];
          if ((y - a[1]) * (y - c[1]) <= 0) {
            const t = (y - a[1]) / (c[1] - a[1] || 1);
            return a[2] + (c[2] - a[2]) * t;
          }
        }
        return null;
      };
      for (const [pts, y0, y1] of [
        [main, yS, yN],
        [sideS, yS1, yS],
        [sideN, yN, yN1]
      ] as [V3[], number, number][]) {
        for (let y = Math.min(y0, y1) + 15.2; y < Math.max(y0, y1) - 3; y += 15.2) {
          const z = cableZ(pts, y);
          if (z && z - deckZ(y) > 1.5) b.beam([x, y, deckZ(y)], [x, y, z], 0.45);
        }
      }
    }

    // anchorage housings + pylons (unpainted concrete). The map is flat, so they
    // stand on the ground plane rather than on the real bluffs.
    b.color(CONCRETE);
    b.box(0, ySA, 0, 40, 101, DECK_Z - TRUSS - 1, {top: true});
    b.box(0, yNA, 0, 48, 109, DECK_Z - TRUSS - 1, {top: true});
    for (const [y, extra] of [
      [yS2, 10],
      [yS1, 4],
      [yN1, 4]
    ] as [number, number][]) {
      for (const x of [-HALF_W - 4.5, HALF_W + 4.5]) {
        b.box(x, y, 0, 8, 12, DECK_Z + extra);
        if (extra > 6) b.box(x, y, DECK_Z + extra, 5.5, 8.5, 3.5).box(x, y, DECK_Z + extra + 3.5, 3, 5, 2.5);
      }
    }

    // Fort Point arch: two parabolic ribs between S2 and S1 with spandrel posts
    b.color(ORANGE);
    const crown = DECK_Z - TRUSS - 1;
    for (const x of [-HALF_W + 3, HALF_W - 3]) {
      const archPts: V3[] = [];
      for (let i = 0; i <= 20; i++) {
        const t = i / 20;
        archPts.push([x, yS2 + (yS1 - yS2) * t, 18 + (crown - 18) * 4 * t * (1 - t)]);
      }
      b.polyline(archPts, 2.4);
      for (let i = 2; i < archPts.length - 2; i += 2) {
        const p = archPts[i];
        b.beam(p, [p[0], p[1], DECK_Z - TRUSS], 0.9);
      }
    }

    // approach viaducts on steel bents: straight runs from the anchorage to the
    // abutment, descending slightly (the real ones curve; flat map, see note above)
    const approach = (from: number, to: V2) => {
      const yt = ax.along(to);
      const xt = ax.across(to);
      const n = 8;
      for (let i = 0; i < n; i++) {
        const t0 = i / n;
        const t1 = (i + 1) / n;
        const p0: V3 = [xt * t0, from + (yt - from) * t0, DECK_Z - 5 * t0];
        const p1: V3 = [xt * t1, from + (yt - from) * t1, DECK_Z - 5 * t1];
        b.color(ORANGE);
        b.beam([p0[0], p0[1], p0[2] - TRUSS / 2], [p1[0], p1[1], p1[2] - TRUSS / 2], 2 * HALF_W, TRUSS);
        b.color(ROAD);
        b.quad([p0[0] - HALF_W, p0[1], p0[2] + 0.05], [p0[0] + HALF_W, p0[1], p0[2] + 0.05], [p1[0] + HALF_W, p1[1], p1[2] + 0.05], [p1[0] - HALF_W, p1[1], p1[2] + 0.05]);
        b.color(ORANGE_DARK);
        b.box(p1[0], p1[1], 0, 2.5, 2.5, p1[2] - TRUSS);
      }
    };
    approach(ySA - 50, S_ABUT);
    approach(yNA + 55, N_ABUT);
  });
}

const ax0 = axisFrame();

export const goldenGateBridge: Landmark = {
  id: 'golden_gate_bridge',
  name: 'Golden Gate Bridge',
  kind: 'bridge',
  built: [1933.01, 1937.4],
  end: 9999,
  anchor: ANCHOR,
  build,
  // suppress generic footprints of the anchorage housings / toll structures under the deck,
  // and of the towers (OSM maps the south tower as a building part; the 2023 LiDAR split it
  // into 223 / 146 / 76 m prisms that stood inside the model)
  replaces: [
    ...[S_ANCH, N_ANCH].map(p => {
      const l = lngLatToLocal(ANCHOR, p);
      return rect(l[0], l[1], 120, 120);
    }),
    ...[S_TOWER, N_TOWER].map(p => {
      const l = lngLatToLocal(ANCHOR, p);
      return rect(l[0], l[1], 90, 90);
    })
  ],
  facts: {
    'Construction': 'Jan 5, 1933 – Apr 1937',
    'Opened': 'May 27, 1937',
    'Main span': '1,280 m',
    'Towers': '227 m above water',
    'Colour': 'International Orange',
    'Bridge axis bearing': `${ax0.bearing.toFixed(1)}°`
  },
  sources: [
    'https://www.goldengate.org/bridge/history-research/statistics-data/design-construction-stats/',
    'https://www.goldengate.org/exhibits/fort-point-arch/',
    'https://en.wikipedia.org/wiki/Golden_Gate_Bridge'
  ]
};
