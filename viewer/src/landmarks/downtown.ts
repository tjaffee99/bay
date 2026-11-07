/**
 * Downtown towers — reconstructed from data/research/landmarks.md.
 */
import {MeshBuilder, rect, roundedRect, type V2} from './kit';
import type {Landmark} from './types';

// ------------------------------------------------------------ Transamerica Pyramid
// Square frustum, base 53.3 m, linear taper to the 260 m apex; faces rotated 9°
// (bearings 81°/171°); spire = top 65 m; elevator (E) and stair (W) wings 6.5 m
// thick with outer faces 13.6 m from centre, emerging ~z 127 (29th floor) to ~212 m;
// inclined-column arcade at the base.
function buildTransamerica(b: MeshBuilder) {
  const H = 260;
  const hw = (z: number) => 26.65 * (1 - z / H);
  const sq = (z: number): V2[] => rect(0, 0, 2 * hw(z), 2 * hw(z));
  b.frame(0, 0, 0, -9, () => {
    // base arcade: dark recess + A-shaped legs
    b.color('#4A4E55').prism(sq(0).map(([x, y]) => [x * 0.9, y * 0.9] as V2), 0, 13, {top: false});
    b.color('#E6E3DB');
    const s0 = hw(0);
    const s13 = hw(13);
    for (const side of [0, 1, 2, 3]) {
      for (let k = 0; k < 5; k++) {
        const t0 = -1 + (2 * k) / 5;
        const t1 = -1 + (2 * (k + 1)) / 5;
        const tm = (t0 + t1) / 2;
        const P = (t: number, s: number, z: number) => {
          const u = t * s;
          return side === 0 ? [u, -s, z] : side === 1 ? [s, u, z] : side === 2 ? [-u, s, z] : [-s, -u, z];
        };
        // inverted-V leg pair meeting at the top midpoint of each bay
        b.beam(P(t0, s0, 0) as any, P(tm, s13, 13) as any, 1.4);
        b.beam(P(t1, s0, 0) as any, P(tm, s13, 13) as any, 1.4);
      }
    }
    // main body to 195 m, then the aluminium spire
    const zs = [13, 60, 120, 195];
    b.color('#E6E3DB').loft(zs.map(sq), zs, {top: false});
    b.color('#C8CCCF').pyramid(sq(195), 195, [0, 0, H]);
    // wings (E = +x, W = -x)
    // a slab from the centre line out to x = xo, 6.5 m thick
    const wing = (xo: number): V2[] => {
      const a = Math.min(0, xo);
      const c = Math.max(0, xo);
      return [
        [a, -3.25],
        [c, -3.25],
        [c, 3.25],
        [a, 3.25]
      ];
    };
    for (const sgn of [1, -1]) {
      // vertical outer face from inside the pyramid up to 205 m, then sloping in toward the spire
      b.color('#E1DDD3').loft([wing(13.6 * sgn), wing(13.6 * sgn), wing(5.5 * sgn)], [120, 205, 214], {top: true});
    }
  });
}

export const transamerica: Landmark = {
  id: 'transamerica_pyramid',
  name: 'Transamerica Pyramid',
  kind: 'tower',
  built: [1969.95, 1972.5],
  end: 9999,
  anchor: [-122.402651, 37.795187],
  build: buildTransamerica,
  replaces: [rect(0, 0, 58, 58)],
  facts: {
    Construction: 'Dec 1969 – 1972',
    Height: '260 m (853 ft)',
    Floors: '48',
    Architect: 'William Pereira',
    Site: 'Montgomery Block (1853–1959)'
  },
  sources: ['https://en.wikipedia.org/wiki/Transamerica_Pyramid', 'https://vibrationdata.com/earthquakes/Pyramid.htm']
};

// ------------------------------------------------------------ Salesforce Tower
// Rounded-square "obelisk": side 54 m at grade held nearly constant to ~55 % of the
// height, curving in to ~27 m at the 326 m top (profile estimated from photo);
// corner radius growing from ~15 % to ~28 %; open crown above ~290 m.
function buildSalesforceTower(b: MeshBuilder) {
  const prof: [number, number][] = [
    [0, 54],
    [100, 53],
    [180, 51],
    [230, 47],
    [270, 41],
    [290, 37],
    [300, 34],
    [326, 27]
  ];
  const ring = (side: number, f: number) => roundedRect(0, 0, side, side, side * f, 4);
  const crFrac = (z: number) => 0.15 + 0.13 * (z / 326);
  b.frame(0, 0, 0, 45, () => {
    const body = prof.filter(([z]) => z <= 290);
    b.color('#B9C9D6').loft(
      body.map(([z, s]) => ring(s, crFrac(z))),
      body.map(([z]) => z),
      {top: false}
    );
    const crown = prof.filter(([z]) => z >= 290);
    b.color('#E4E8EC').loft(
      crown.map(([z, s]) => ring(s, crFrac(z))),
      crown.map(([z]) => z),
      {top: false}
    );
    // hollow crown: inner skin + roof deck a few metres down
    const inner = ring(27 - 5, crFrac(326));
    b.color('#D4D9DE').loft([ring(27, crFrac(326)), inner], [326, 326], {top: false});
    b.color('#C2C9D0').prism(inner, 312, 326, {top: false});
    b.color('#8F9BA6').cap(inner, 312);
  });
}

export const salesforceTower: Landmark = {
  id: 'salesforce_tower',
  name: 'Salesforce Tower',
  kind: 'tower',
  built: [2013.24, 2018.02],
  end: 9999,
  anchor: [-122.396959, 37.78978],
  build: buildSalesforceTower,
  replaces: [roundedRect(0, 0, 62, 62, 10)],
  facts: {
    Construction: 'Mar 2013 – Jan 2018',
    Height: '326 m (1,070 ft); roof 296 m',
    Floors: '61',
    Architect: 'Pelli Clarke Pelli'
  },
  sources: ['https://en.wikipedia.org/wiki/Salesforce_Tower']
};

// ------------------------------------------------------------ Salesforce Transit Center + Park
// 436 × 50 m along bearing 45°; undulating white perforated skin from ~8 m to the
// 21 m rooftop park; glazed ground storey set back behind V-columns; First St
// (+24 m along the axis) and Fremont St (+133 m) pass beneath.
function buildTransitCenter(b: MeshBuilder) {
  const L = 436;
  const W = 50;
  const streets: [number, number][] = [
    [24 - 12, 24 + 12],
    [133 - 12, 133 + 12]
  ];
  const n = 72;
  const wave = (y: number, side: number) => 2.4 * Math.sin((y + 31 * side) / 14) * Math.sin((y + 17) / 41);
  b.frame(0, 0, 0, 45, () => {
    // undulating skin: ring in plan with wavy long sides
    const ring: V2[] = [];
    for (let i = 0; i <= n; i++) {
      const y = -L / 2 + (L * i) / n;
      ring.push([W / 2 + wave(y, 1), y]);
    }
    for (let i = n; i >= 0; i--) {
      const y = -L / 2 + (L * i) / n;
      ring.push([-W / 2 - wave(y, -1), y]);
    }
    b.color('#ECEDEC').prism(ring, 9, 21.5, {top: false, bottom: true});
    // park roof
    b.color('#86AE5A').cap(rect(0, 0, W - 2, L - 2), 21.5);
    // amphitheatre lawn at the SW end, paths
    b.color('#9CC06E').box(0, -L / 2 + 25, 21.5, 30, 28, 0.6);
    b.color('#D8D2C2').box(0, 0, 21.5, 3, L - 20, 0.3);
    // glass domes / oculus
    b.color('#A7BCC6').dome(-8, 75, 6, 21.5, 3.5, 12, 3).dome(8, 10, 5, 21.5, 3, 12, 3);
    // glazed ground storey, set back 4 m, interrupted where streets pass under
    const segs: [number, number][] = [];
    let y0 = -L / 2 + 2;
    for (const [a, c] of streets) {
      segs.push([y0, a]);
      y0 = c;
    }
    segs.push([y0, L / 2 - 2]);
    for (const [a, c] of segs) b.color('#9DB4BE').box(0, (a + c) / 2, 0, W - 8, c - a, 9, {top: false});
    // V-columns along both sides
    b.color('#E6E6E3');
    for (let y = -L / 2 + 12; y < L / 2 - 8; y += 24) {
      if (streets.some(([a, c]) => y > a - 2 && y < c + 2)) continue;
      for (const sx of [-1, 1]) {
        const x = sx * (W / 2 - 5);
        b.beam([x, y, 0], [x + sx * 3, y - 5, 9], 0.9);
        b.beam([x, y, 0], [x + sx * 3, y + 5, 9], 0.9);
      }
    }
    // rooftop trees (600 in reality; ~140 clustered here, decorative placement)
    let seed = 7;
    const rnd = () => ((seed = (seed * 16807) % 2147483647) - 1) / 2147483646;
    for (let i = 0; i < 140; i++) {
      const y = -L / 2 + 50 + rnd() * (L - 70);
      const x = (rnd() - 0.5) * (W - 10);
      if (Math.abs(x) < 3) continue;
      const h = 5 + rnd() * 6;
      b.color(rnd() > 0.5 ? '#4F7F38' : '#3E6B2C').frustum(x, y, 2.2 + rnd(), 0.2, 21.5 + 1.5, 21.5 + h, 6, false);
      b.color('#6B5640').box(x, y, 21.5, 0.4, 0.4, 1.6);
    }
  });
}

export const transitCenter: Landmark = {
  id: 'salesforce_transit_center',
  name: 'Salesforce Transit Center & Salesforce Park',
  kind: 'building',
  built: [2010.6, 2018.61],
  end: 9999,
  anchor: [-122.397009, 37.78901],
  build: buildTransitCenter,
  replaces: [
    (() => {
      // rotate a 440 × 56 rectangle to bearing 45°
      const c = Math.cos(-Math.PI / 4);
      const s = Math.sin(-Math.PI / 4);
      return rect(0, 0, 56, 440).map(([x, y]) => [c * x - s * y, s * x + c * y] as V2);
    })()
  ],
  facts: {
    Construction: '2010 – Aug 2018',
    'Rooftop park': '5.4 acres, ~21 m above the street, 600 trees',
    Length: '436 m',
    Predecessor: 'Transbay Terminal (1939–2010)',
    Architect: 'Pelli Clarke Pelli'
  },
  sources: [
    'https://en.wikipedia.org/wiki/Salesforce_Transit_Center',
    'https://pcparch.com/work/salesforce-transit-center',
    'https://www.tjpa.org/salesforce-transit-center/salesforce-park'
  ]
};
