/**
 * Stadiums and arenas — reconstructed from data/research/landmarks.md
 * ("Stadiums and arenas"): real sites, home-plate orientation and fence
 * distances; grandstand heights are photo estimates where nothing is
 * published (noted in each model's facts).
 */
import {MeshBuilder, rect, rotRect, roundedRect, type V2, type V3} from './kit';
import type {Landmark} from './types';

const FT = 0.3048;

// ------------------------------------------------------------------ helpers

type Park = {
  /** home plate, local metres from the landmark anchor */
  home: V2;
  /** compass bearing from home plate to centre field */
  cf: number;
  /** fence distances (m): LF line, LC, CF, RC, RF line */
  fence: [number, number, number, number, number];
};

/** Fair-territory fence outline from home (field frame: +y = CF, +x = RF side). */
function fenceArc(f: Park['fence'], n = 24): V2[] {
  const angs = [-45, -22.5, 0, 22.5, 45];
  const pts: V2[] = [];
  for (let i = 0; i <= n; i++) {
    const a = -45 + (90 * i) / n;
    let k = 0;
    while (k < 3 && a > angs[k + 1]) k++;
    const t = (a - angs[k]) / (angs[k + 1] - angs[k]);
    const r = f[k] + (f[k + 1] - f[k]) * (0.5 - 0.5 * Math.cos(Math.PI * t));
    const rad = (a * Math.PI) / 180;
    pts.push([Math.sin(rad) * r, Math.cos(rad) * r]);
  }
  return pts;
}

/**
 * Path offset `off` metres outside the foul lines: from `lfEnd` along the LF
 * line, round behind home plate, out to `rfEnd` along the RF line.
 */
function foulPath(off: number, lfEnd: number, rfEnd: number, n = 10): V2[] {
  const s2 = Math.SQRT1_2;
  const pts: V2[] = [];
  // LF line dir (-s2, s2), outward normal (-s2, -s2)
  for (let i = 0; i <= n; i++) {
    const s = lfEnd * (1 - i / n);
    pts.push([-s2 * s - s2 * off, s2 * s - s2 * off]);
  }
  for (let i = 1; i < n; i++) {
    const a = (-135 + (90 * i) / n) * (Math.PI / 180);
    pts.push([Math.cos(a) * off, Math.sin(a) * off]);
  }
  for (let i = 0; i <= n; i++) {
    const s = (rfEnd * i) / n;
    pts.push([s2 * s + s2 * off, s2 * s - s2 * off]);
  }
  return pts;
}

/** Seating bowl between two paths, field wall, back wall and end walls. */
function stands(b: MeshBuilder, inner: V2[], outer: V2[], zIn: number, zOut: number, c: {seats: string; wall: string; rim?: string}) {
  const A: V3[] = inner.map(p => [p[0], p[1], zIn]);
  const B: V3[] = outer.map(p => [p[0], p[1], zOut]);
  b.color(c.seats).ribbon(A, B);
  b.color(c.wall).wallProfile(inner, 0, zIn).wallProfile(outer, 0, zOut);
  for (const i of [0, inner.length - 1]) {
    b.quad([inner[i][0], inner[i][1], 0], [outer[i][0], outer[i][1], 0], [outer[i][0], outer[i][1], zOut], [inner[i][0], inner[i][1], zIn]);
  }
  if (c.rim) b.color(c.rim).ribbon(outer.map(p => [p[0], p[1], zOut] as V3), outer.map(p => [p[0], p[1], zOut + 1.2] as V3));
}

function diamond(b: MeshBuilder, park: Park, grass: string, dirt: string, standsInner: V2[]) {
  const fence = fenceArc(park.fence);
  // playing surface: foul territory inside the stands + fair territory to the fence
  b.color(grass).cap([...standsInner, ...fence.slice().reverse().filter(p => Math.hypot(p[0], p[1]) > 1)], 0.25);
  const d = 27.43 * Math.SQRT1_2;
  b.color(dirt).cap(
    [
      [0, -4],
      [d + 5, d - 2],
      [0, 2 * d + 7],
      [-d - 5, d - 2]
    ],
    0.35
  );
  b.color(grass).cap(
    [
      [0, 3],
      [d - 4, d],
      [0, 2 * d - 3],
      [-d + 4, d]
    ],
    0.45
  );
  return fence;
}

function lightTower(b: MeshBuilder, x: number, y: number, h: number, color = '#6E7276') {
  b.color(color).beam([x, y, 0], [x, y, h], 0.9);
  b.box(x, y, h - 3, 4, 1.2, 3);
}

// ------------------------------------------------------------------ Oracle Park
const ORACLE: V2 = [-122.389847, 37.778661];
const oraclePark: Landmark = {
  id: 'oracle_park',
  name: 'Oracle Park',
  kind: 'stadium',
  built: [1997.95, 2000.25],
  end: 9999,
  anchor: ORACLE,
  build: b => {
    const park: Park = {home: [-100, -6], cf: 90, fence: [339 * FT, 354 * FT, 391 * FT, 415 * FT, 309 * FT]};
    b.frame(park.home[0], park.home[1], 0, park.cf, () => {
      const inner = foulPath(16, 103, 72);
      const outer = foulPath(62, 103, 72);
      diamond(b, park, '#4E8B3A', '#B9906A', foulPath(16, 110, 96));
      stands(b, inner, outer, 3, 30, {seats: '#2F5E46', wall: '#8E4B3A', rim: '#3C6E5A'});
      // suites band splitting the decks
      b.color('#D8D2C6').ribbon(
        foulPath(36, 103, 72).map(p => [p[0], p[1], 15.5] as V3),
        foulPath(37.5, 103, 72).map(p => [p[0], p[1], 17.5] as V3)
      );
      // right field: low brick arcade along McCovey Cove (no stands)
      const fence = fenceArc(park.fence);
      const cove = fence.filter(([x]) => x > 20).map(([x, y]) => [x + 5, y - 3] as V2);
      b.color('#8E4B3A').wallProfile(cove, 0, 8);
      // left-field bleachers
      const lf = fence.filter(([x]) => x < -15 && x > -80);
      const lfOut = lf.map(([x, y]) => [x * 1.17, y * 1.17] as V2);
      stands(b, lf, lfOut, 2.5, 11, {seats: '#2F5E46', wall: '#8E4B3A'});
      // centre-field scoreboard on posts
      b.frame(0, 132, 0, 0, () => {
        b.color('#4A4F55').box(-10, 0, 0, 1.5, 1.5, 14).box(10, 0, 0, 1.5, 1.5, 14);
        b.color('#2C3136').box(0, 0, 14, 32, 2.5, 11);
      });
      // Coca-Cola bottle and the giant glove behind the LF bleachers
      b.color('#B23A33').beam([-112, 70, 3], [-100, 88, 7], 7);
      b.color('#B23A33').beam([-100, 88, 7], [-96, 94, 8], 3);
      b.color('#8A5A33').dome(-118, 52, 5, 0, 7, 10, 3);
      // light standards on the rim
      for (const p of foulPath(60, 95, 66).filter((_, i) => i % 6 === 3)) lightTower(b, p[0], p[1], 45);
      // clock tower over the Willie Mays Plaza gate (3rd & King)
      b.color('#8E4B3A').box(0, -70, 0, 9, 9, 30);
      b.color('#5D6B66').pyramid(rect(0, -70, 10, 10), 30, [0, -70, 36]);
    });
  },
  replaces: [rotRect(0, 0, 195, 215, 45)],
  facts: {
    Construction: 'Dec 1997 – Mar 2000',
    Opened: 'Mar 31, 2000 (as Pacific Bell Park)',
    Capacity: '≈ 41,900',
    Fences: 'LF 339 ft · CF 391 ft · RC 415 ft · RF 309 ft',
    Model: 'field from published fence distances; stand heights estimated from aerial photo'
  },
  sources: ['https://en.wikipedia.org/wiki/Oracle_Park']
};

// ------------------------------------------------------------------ Chase Center
const chaseCenter: Landmark = {
  id: 'chase_center',
  name: 'Chase Center',
  kind: 'stadium',
  built: [2017.05, 2019.68],
  end: 9999,
  anchor: [-122.38752, 37.767915],
  build: b => {
    const ring = (s: number) => roundedRect(0, 0, s, s * 0.994, s * 0.36, 6);
    b.color('#6E8796').loft([ring(146), ring(146)], [0, 11], {top: false});
    b.color('#E8EAEC').loft([ring(150), ring(155), ring(157), ring(152)], [11, 18, 27, 36.5], {top: false});
    b.color('#DADDE0').loft([ring(152), ring(110)], [36.5, 38.1], {top: true});
    // entrance canopy + LED screen toward the 3rd/16th St plaza (west)
    b.color('#F2F3F4').box(-86, -10, 9, 22, 44, 1.2);
    b.color('#2B2F36').box(-78.5, 25, 12, 1.5, 26, 14);
  },
  replaces: [roundedRect(0, 0, 165, 165, 50)],
  facts: {
    Construction: 'Jan 2017 – Sep 2019',
    Opened: 'Sep 6, 2019',
    Capacity: '18,064 (basketball)',
    Height: '≈ 38 m (OSM)'
  },
  sources: ['https://en.wikipedia.org/wiki/Chase_Center']
};

// ------------------------------------------------------------------ Kezar Stadium
const KEZAR: V2 = [-122.456077, 37.766924];
function kezarArch(b: MeshBuilder, x: number, y: number) {
  // 1925 triumphal-arch gate at the east end (≈ 12 m tall, 10 m wide), salmon trim
  b.frame(x, y, 0, 90, () => {
    b.color('#CDB79E').box(-4, 0, 0, 3, 3.5, 9).box(4, 0, 0, 3, 3.5, 9).box(0, 0, 9, 11, 3.5, 2.4);
    b.color('#C9795E').box(0, 0, 11.4, 12, 4, 0.8);
  });
}
function track(b: MeshBuilder) {
  b.color('#A65A4A').cap(roundedRect(0, 0, 176, 92, 44, 8), 0.25);
  b.color('#5E9442').cap(roundedRect(0, 0, 150, 66, 31, 8), 0.35);
}
const kezar1925: Landmark = {
  id: 'kezar_stadium_1925',
  name: 'Kezar Stadium (1925 bowl)',
  kind: 'stadium',
  built: [1924.4, 1925.33],
  end: 1989.45,
  anchor: KEZAR,
  build: b => {
    track(b);
    const inner = roundedRect(0, 0, 182, 98, 47, 10);
    const outer = roundedRect(0, 0, 232, 132, 64, 10);
    // embanked concrete terraces ~15 m at the rim, lower toward the open east end
    const zOut = outer.map(([x]) => (x > 70 ? 15 - Math.min(9, (x - 70) * 0.25) : 15));
    b.color('#CFC6B6').ribbon(
      inner.map(p => [p[0], p[1], 1.2] as V3),
      outer.map((p, i) => [p[0], p[1], zOut[i]] as V3),
      true
    );
    b.color('#BDB3A2').wallProfile(outer, 0, zOut, true);
    b.color('#8F8A80').box(0, -58, 15, 40, 6, 5); // press box on the south rim
    kezarArch(b, 118, 0);
  },
  replaces: [rect(0, 0, 250, 150)],
  facts: {
    Opened: 'May 2, 1925 (designed by Willis Polk)',
    Capacity: '59,942',
    Tenants: '49ers 1946–1970',
    Demolished: 'June 1989',
    Model: 'LOW CONFIDENCE: bowl massing from the site outline; no 1925 plan or photo available'
  },
  sources: ['https://en.wikipedia.org/wiki/Kezar_Stadium', 'https://pcad.lib.washington.edu/building/3893']
};
const kezar1990: Landmark = {
  id: 'kezar_stadium_1990',
  name: 'Kezar Stadium (1990)',
  kind: 'stadium',
  built: [1989.5, 1990.6],
  end: 9999,
  anchor: KEZAR,
  build: b => {
    track(b);
    for (const sy of [-1, 1]) {
      const y0 = sy * 52;
      const y1 = sy * 72;
      b.color('#CDB79E');
      b.ribbon(
        [
          [-54, y0, 1],
          [54, y0, 1]
        ],
        [
          [-54, y1, 9.5],
          [54, y1, 9.5]
        ]
      );
      b.wallProfile(
        [
          [-54, y1],
          [54, y1]
        ],
        0,
        9.5
      );
      b.wallProfile(
        [
          [-54, y0],
          [54, y0]
        ],
        0,
        1
      );
    }
    b.color('#B9A893').box(0, 76, 0, 34, 7, 14); // press box (north)
    for (const [x, y] of [
      [-60, 80],
      [0, 84],
      [60, 80],
      [-60, -80],
      [0, -80],
      [60, -80]
    ] as V2[])
      lightTower(b, x, y, 30);
    // salmon colonnade and the surviving 1925 arch at the east end
    b.color('#C9795E');
    for (let y = -30; y <= 30; y += 7.5) b.cylinder(104, y, 0.8, 0, 7, 8);
    kezarArch(b, 118, 0);
  },
  replaces: [rect(0, 0, 250, 150)],
  facts: {Opened: '1990 (≈10,000 seats)', 'Kept from 1925': 'the triumphal-arch entrance gate'},
  sources: ['https://en.wikipedia.org/wiki/Kezar_Stadium', 'https://broughttolight.ucsf.edu/2016/02/03/kezar/']
};

// ------------------------------------------------------------------ Candlestick Park
const CANDLESTICK: V2 = [-122.38611, 37.71361];
const candlestick1960: Landmark = {
  id: 'candlestick_park_1960',
  name: 'Candlestick Park (1960)',
  kind: 'stadium',
  built: [1958.61, 1960.28],
  end: 1970.9,
  anchor: CANDLESTICK,
  build: b => {
    const park: Park = {home: [-62, 0], cf: 95, fence: [330 * FT, 365 * FT, 420 * FT, 365 * FT, 330 * FT]};
    b.frame(park.home[0], park.home[1], 0, park.cf, () => {
      diamond(b, park, '#4E8B3A', '#B9906A', foulPath(18, 105, 105));
      stands(b, foulPath(18, 100, 100), foulPath(58, 100, 100), 3, 27, {seats: '#9C3B2C', wall: '#D9D5CC', rim: '#BDB8AE'});
      const fence = fenceArc(park.fence);
      stands(b, fence, fence.map(([x, y]) => [x * 1.1, y * 1.1] as V2), 1.5, 6, {seats: '#9C3B2C', wall: '#D9D5CC'});
      for (const p of foulPath(56, 90, 90).filter((_, i) => i % 7 === 2)) lightTower(b, p[0], p[1], 45);
    });
  },
  replaces: [rect(0, 0, 260, 230)],
  facts: {
    Opened: 'Apr 12, 1960 — first all-reinforced-concrete MLB park',
    Form: 'open horseshoe facing the Bay',
    Capacity: '43,765',
    Model: 'field from published distances; stand massing estimated from photos'
  },
  sources: ['https://en.wikipedia.org/wiki/Candlestick_Park']
};
const candlestick1971: Landmark = {
  id: 'candlestick_park_1971',
  name: 'Candlestick Park (enclosed, 1971)',
  kind: 'stadium',
  built: [1970.9, 1971.6],
  end: 2015.7,
  anchor: CANDLESTICK,
  build: b => {
    const inner = roundedRect(0, 0, 150, 116, 46, 10);
    const mid = roundedRect(0, 0, 196, 162, 66, 10);
    const outer = roundedRect(0, 0, 240, 210, 82, 10);
    b.color('#4E8B3A').cap(inner, 0.3);
    b.color('#8E2F25').ribbon(inner.map(p => [p[0], p[1], 3] as V3), mid.map(p => [p[0], p[1], 15] as V3), true);
    b.color('#C1503A').ribbon(mid.map(p => [p[0], p[1], 15] as V3), outer.map(p => [p[0], p[1], 30] as V3), true);
    b.color('#D9D5CC').wallProfile(inner, 0, 3, true).wallProfile(outer, 0, 30, true);
    b.color('#EEEBE4').ribbon(outer.map(p => [p[0], p[1], 30] as V3), outer.map(p => [p[0] * 1.015, p[1] * 1.015, 32] as V3), true);
    // external ramps
    b.color('#CFCAC0').box(-128, -40, 0, 10, 40, 22).box(128, 40, 0, 10, 40, 22);
    for (const [x, y] of [
      [-100, 95],
      [100, 95],
      [-118, -60],
      [118, -60]
    ] as V2[])
      lightTower(b, x, y, 48);
  },
  replaces: [rect(0, 0, 260, 230)],
  facts: {
    Enclosed: '1971 (outfield stands added for the 49ers)',
    Capacity: '≈ 63,000 baseball / 69,732 football',
    'Last event': 'Aug 14, 2014',
    Demolished: 'Feb – Sep 2015',
    Model: 'outline ≈ 240 × 210 m and 30 m rim estimated from aerial photos'
  },
  sources: ['https://en.wikipedia.org/wiki/Candlestick_Park']
};

// ------------------------------------------------------------------ Seals Stadium
const SEALS: V2 = [-122.409239, 37.766756];
function sealsModel(b: MeshBuilder, color: string, bleachers: boolean) {
  const park: Park = {home: [-88, 58], cf: 135, fence: [365 * FT, 380 * FT, 405 * FT, 375 * FT, 348 * FT]};
  b.frame(park.home[0], park.home[1], 0, park.cf, () => {
    diamond(b, park, '#5E9442', '#B9906A', foulPath(14, 112, 108));
    stands(b, foulPath(14, 95, 95), foulPath(44, 95, 95), 2, 13, {seats: color, wall: color});
    for (const p of foulPath(42, 90, 90).filter((_, i) => i % 6 === 2)) lightTower(b, p[0], p[1], 30, '#5A5E58');
    if (bleachers) {
      // 1946 right-field bleachers along 16th St
      const rf = fenceArc(park.fence).filter(([x]) => x > 25);
      stands(b, rf, rf.map(([x, y]) => [x * 1.12, y * 1.12] as V2), 1.5, 7, {seats: color, wall: color});
    }
  });
}
const seals1931: Landmark = {
  id: 'seals_stadium',
  name: 'Seals Stadium',
  kind: 'stadium',
  built: [1930.6, 1931.27],
  end: 1946.2,
  anchor: SEALS,
  build: b => sealsModel(b, '#CFCABF', false),
  replaces: [rect(0, 0, 234, 173)],
  facts: {
    Opened: 'Apr 7, 1931 — "the Queen of Concrete"',
    Grandstand: 'single deck, no roof, foul pole to foul pole',
    Model: 'field orientation and distances documented; stand height estimated'
  },
  sources: ['https://en.wikipedia.org/wiki/Seals_Stadium']
};
const seals1946: Landmark = {
  id: 'seals_stadium_1946',
  name: 'Seals Stadium (painted green, RF bleachers)',
  kind: 'stadium',
  built: [1946.15, 1946.2],
  end: 1959.88,
  anchor: SEALS,
  build: b => sealsModel(b, '#4F7A55', true),
  replaces: [rect(0, 0, 234, 173)],
  facts: {
    '1946': 'right-field bleachers added; owner Paul Fagan has the stadium painted green',
    '1958–59': 'temporary home of the San Francisco Giants',
    Demolished: 'Nov 1959 (now Potrero Center)'
  },
  sources: ['https://en.wikipedia.org/wiki/Seals_Stadium']
};

// ------------------------------------------------------------------ Ewing Field
const EWING: V2 = [-122.448, 37.7801];
function ewingPark(): Park {
  return {home: [55, 45], cf: 225, fence: [340 * FT, 370 * FT, 400 * FT, 375 * FT, 356 * FT]};
}
const ewingGrandstand: Landmark = {
  id: 'ewing_field',
  name: 'Ewing Field grandstand',
  kind: 'stadium',
  built: [1914.0, 1914.37],
  end: 1926.43,
  anchor: EWING,
  build: b => {
    const park = ewingPark();
    b.frame(park.home[0], park.home[1], 0, park.cf, () => {
      const inner = foulPath(14, 60, 60);
      const outer = foulPath(34, 60, 60);
      stands(b, inner, outer, 1.5, 9, {seats: '#9C8B74', wall: '#8A7A64'});
      // roof on posts over the grandstand
      b.color('#6B5E52').ribbon(
        foulPath(16, 60, 60).map(p => [p[0], p[1], 12] as V3),
        outer.map(p => [p[0], p[1], 12.5] as V3)
      );
      for (const p of foulPath(16, 60, 60).filter((_, i) => i % 3 === 0)) b.beam([p[0], p[1], 1.5], [p[0], p[1], 12], 0.4);
    });
  },
  replaces: [rect(0, 0, 200, 200)],
  facts: {
    Opened: 'May 16, 1914 — Seals home for the 1914 season only (fog and cold)',
    Fate: 'wooden grandstand burned Jun 5, 1926 (≈100 houses also burned)',
    Model: 'L-shaped roofed wooden grandstand from a 1914 newspaper aerial view'
  },
  sources: ['https://en.wikipedia.org/wiki/Ewing_Field']
};
const ewingField: Landmark = {
  id: 'ewing_field_bleachers',
  name: 'Ewing Field',
  kind: 'stadium',
  built: [1914.0, 1914.37],
  end: 1938.5,
  anchor: EWING,
  build: b => {
    const park = ewingPark();
    b.frame(park.home[0], park.home[1], 0, park.cf, () => {
      diamond(b, park, '#6E9A4E', '#B9906A', foulPath(14, 105, 105));
      // uncovered bleachers continuing down the lines
      const s2 = Math.SQRT1_2;
      for (const side of [-1, 1]) {
        const a: V2[] = [];
        const c: V2[] = [];
        for (let s = 62; s <= 100; s += 9.5) {
          a.push([side * (s2 * s + s2 * 14), s2 * s - s2 * 14]);
          c.push([side * (s2 * s + s2 * 30), s2 * s - s2 * 30]);
        }
        stands(b, a, c, 1, 6, {seats: '#A8977E', wall: '#8A7A64'});
      }
    });
  },
  facts: {Opened: 'May 16, 1914', 'After 1926': 'bleachers used for football (SF State 1931–35)', Demolished: '1938 (Ewing Terrace housing)'},
  sources: ['https://en.wikipedia.org/wiki/Ewing_Field']
};

// ------------------------------------------------------------------ Recreation Park (14th & Valencia)
const recreationPark: Landmark = {
  id: 'recreation_park_valencia',
  name: 'Recreation Park (14th & Valencia)',
  kind: 'stadium',
  built: [1906.9, 1907.3],
  end: 1940.5,
  anchor: [-122.423198, 37.76716],
  build: b => {
    const park: Park = {home: [68, -44], cf: 315, fence: [315 * FT, 330 * FT, 340 * FT, 305 * FT, 284 * FT]};
    b.frame(park.home[0], park.home[1], 0, park.cf, () => {
      diamond(b, park, '#6E9A4E', '#B9906A', foulPath(12, 98, 90));
      stands(b, foulPath(12, 72, 72), foulPath(36, 72, 72), 2, 14, {seats: '#9C8B74', wall: '#8A7A64', rim: '#6B5E52'});
    });
  },
  replaces: [rect(0, 0, 176, 120)],
  facts: {
    Built: '1907, after the fire destroyed the 8th & Market ballpark',
    Tenants: 'San Francisco Seals 1907–13, 1915–30',
    Fate: 'site cleared c. 1940 for Valencia Gardens',
    Model: 'LOW CONFIDENCE: two-level wooden grandstand massing estimated (no photo found)'
  },
  sources: ['https://en.wikipedia.org/wiki/Recreation_Park_(San_Francisco)']
};

// ------------------------------------------------------------------ Cow Palace
const cowPalace: Landmark = {
  id: 'cow_palace',
  name: 'Cow Palace',
  kind: 'stadium',
  built: [1940.4, 1941.3],
  end: 9999,
  anchor: [-122.418864, 37.706764],
  build: b => {
    b.frame(0, 0, 0, 19, () => {
      const L = 120;
      const W = 90;
      const wall = 16;
      const rise = 14;
      b.color('#C9CACB').box(0, 0, 0, W, L, wall, {top: false});
      // segmental barrel vault along the long axis
      const n = 12;
      const z = (x: number) => wall + rise * (1 - (x / (W / 2)) ** 2);
      b.color('#B5B8BA');
      for (let i = 0; i < n; i++) {
        const x0 = -W / 2 + (W * i) / n;
        const x1 = -W / 2 + (W * (i + 1)) / n;
        b.quad([x0, -L / 2, z(x0)], [x1, -L / 2, z(x1)], [x1, L / 2, z(x1)], [x0, L / 2, z(x0)]);
        // arched gable ends
        for (const y of [-L / 2, L / 2]) b.color('#C9CACB').tri([x0, y, wall], [x1, y, wall], [x1, y, z(x1)]).tri([x0, y, wall], [x1, y, z(x1)], [x0, y, z(x0)]);
        b.color('#B5B8BA');
      }
      b.color('#D2405A').box(0, -L / 2 - 0.3, wall + 2, 40, 0.6, 3); // COW PALACE sign band
      // low annexes
      b.color('#BFC1C3').box(-W / 2 - 15, 0, 0, 30, 150, 8).box(W / 2 + 15, 0, 0, 30, 150, 8);
    });
  },
  replaces: [rect(0, 0, 190, 190)],
  facts: {Opened: 'Apr 20, 1941 (California State Livestock Pavilion)', Location: 'Daly City, just south of the SF line', Model: 'vault height estimated from photo'},
  sources: ['https://en.wikipedia.org/wiki/Cow_Palace']
};

export const STADIUMS: Landmark[] = [
  oraclePark,
  chaseCenter,
  kezar1925,
  kezar1990,
  candlestick1960,
  candlestick1971,
  seals1931,
  seals1946,
  ewingGrandstand,
  ewingField,
  recreationPark,
  cowPalace
];

