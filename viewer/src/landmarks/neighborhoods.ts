/**
 * Legion of Honor and the Painted Ladies — reconstructed from
 * data/research/landmarks.md (OSM footprints + 1932 NARA aerial + 2022 photos).
 */
import {lngLatToLocal, MeshBuilder, rect, rotRect, type V2} from './kit';
import type {Landmark} from './types';

// ------------------------------------------------------------ Legion of Honor
// U-shaped museum around the Court of Honor; long axis bearing 49° (entrance
// gate at the NE end). Layout measured from the OSM 3D parts (audit 2026-11):
// building axis 3 m SE of the anchor; solid gallery block Y −34…+5 (60 m wide,
// 17 m) with the rotunda (Ø 13.6 m, dome to ~21 m) half-projecting at the SW end;
// outer wings 12.6 m wide run on to the NE end (Y 54); single-storey Ionic
// colonnades (11 m) frame the 30 × 41 m court; portico Y 9–15; triumphal-arch
// gate in the NE screen.
const LOH_ANCHOR: V2 = [-122.500846, 37.78451];
const STONE = '#E3DCCB';
const STONE_SHADE = '#CFC6B2';
const ROOF = '#9A9C9E';

function buildLegion(b: MeshBuilder) {
  b.frame(0, 0, 0, 49, () =>
    b.frame(3.0, 0, 0, 0, () => {
      // solid SW gallery block (inner galleries + central halls)
      b.color(STONE).box(0, -14.3, 0, 60.5, 39, 15);
      b.color(ROOF).box(0, -14.3, 15, 58.5, 37, 1.6);
      b.color('#6E747A').box(-18, -14.3, 16.6, 3, 30, 0.6).box(18, -14.3, 16.6, 3, 30, 0.6); // skylights
      // outer wings along the court to the NE end
      for (const sx of [-1, 1]) {
        const cx = sx * 23.9;
        b.color(STONE).box(cx, 29.75, 0, 12.6, 49, 15);
        b.color(ROOF).hip(cx, 29.75, 12.6, 49, 15, 2.2);
        b.color('#6E747A').box(cx, 29.75, 16.2, 2.5, 38, 0.8);
      }
      // rotunda + verdigris dome on the axis at the SW end
      b.color(STONE_SHADE).cylinder(-0.1, -32.5, 6.8, 0, 17.5, 20);
      b.color(STONE).cylinder(-0.1, -32.5, 7.3, 15.5, 16.4, 20);
      b.color('#B9C07F').dome(-0.1, -32.5, 6.8, 17.5, 4.2, 20, 4);
      // portico at the SW end of the court: 4 columns + pediment block
      b.color(STONE).box(0, 11, 0, 12.6, 4, 15);
      b.color(STONE_SHADE);
      for (const x of [-4.5, -1.5, 1.5, 4.5]) b.cylinder(x, 14.2, 0.7, 0, 12, 8);
      b.color(STONE).box(0, 14.2, 12, 12.6, 1.8, 2.6);
      // court colonnades (single storey) along both wings and the NE screen
      for (const sx of [-1, 1]) {
        b.color(STONE).box(sx * 16.3, 28.75, 8.2, 2.8, 41, 2.8);
        b.color(STONE_SHADE);
        for (let y = 9.5; y < 49; y += 3.4) b.cylinder(sx * 15.2, y, 0.4, 0, 8.2, 6);
        b.color(STONE).box(sx * 11.45, 51, 8.2, 12.3, 3.7, 2.8);
        for (let x = 6.5; x < 17; x += 3) b.color(STONE_SHADE).cylinder(sx * x, 49.6, 0.4, 0, 8.2, 6);
      }
      // court paving + 1995 glass pyramid skylight
      b.color('#D9D2C1').box(0, 28.75, 0, 30, 41, 0.15);
      b.color('#A9C1CC').pyramid(rect(0, 26, 5.2, 5.2), 0.15, [0, 26, 1.8]);
      // triumphal-arch gateway in the NE screen
      b.color(STONE).box(-4, 51.5, 0, 3, 5, 16).box(4, 51.5, 0, 3, 5, 16).box(0, 51.5, 10.5, 11, 5, 5.5);
    })
  );
  // El Cid equestrian statue (Anna Hyatt Huntington, 1937) on the lawn NW of the forecourt walk
  const cid = lngLatToLocal(LOH_ANCHOR, [-122.5004, 37.78521]);
  b.color('#8E8A80').box(cid[0], cid[1], 0, 2.5, 4, 3);
  b.color('#5E6A5C').box(cid[0], cid[1], 3, 1.4, 3, 3.2);
}

export const legionOfHonor: Landmark = {
  id: 'legion_of_honor',
  name: 'California Palace of the Legion of Honor',
  kind: 'building',
  built: [1921.5, 1924.86],
  end: 9999,
  anchor: LOH_ANCHOR,
  build: buildLegion,
  replaces: [rotRect(lngLatToLocal(LOH_ANCHOR, [-122.50079, 37.784513])[0], lngLatToLocal(LOH_ANCHOR, [-122.50079, 37.784513])[1], 66, 100, 49)],
  facts: {
    Construction: '1921 – 1924',
    Opened: 'Nov 11, 1924 (Armistice Day)',
    Design: '¾-scale replica of the Palais de la Légion d’Honneur, Paris (via the 1915 PPIE French Pavilion)',
    Architect: 'George Applegarth & Henri Guillaume',
    'Site before': 'Golden Gate Cemetery (1870–1909)',
    Model: 'plan from OSM 3D parts (wings 17 m, colonnades 11 m); roof and gate heights estimated'
  },
  sources: ['https://en.wikipedia.org/wiki/Legion_of_Honor_(museum)', 'https://famsf.org/legion/history']
};

// ------------------------------------------------------------ Painted Ladies
// 710–720 Steiner: six Queen Anne row houses 6.9 × 16 m, eaves ~10 m, front
// gables to ~13.5 m, angled two-storey bay window; 722 (Kavanaugh's own 1892
// house) is 9.1 × 18.8 m with a hipped roof. Facades face 261° (onto Alamo
// Square). Colours sampled from 2022 photos (body / trim / roof).
type House = {num: number; at: V2; w: number; d: number; body: string; trim: string; accent: string; roof: string};
const HOUSES: House[] = [
  {num: 710, at: [-122.432725, 37.776062], w: 6.9, d: 15.9, body: '#CFC3A6', trim: '#F0EADB', accent: '#6B5A47', roof: '#515151'},
  {num: 712, at: [-122.432739, 37.776125], w: 6.9, d: 16.1, body: '#A8C2D0', trim: '#F4F4F0', accent: '#5F7F9A', roof: '#434142'},
  {num: 714, at: [-122.432739, 37.776193], w: 6.9, d: 16.1, body: '#E4D6BE', trim: '#7A3B2E', accent: '#C9A26A', roof: '#8C543D'},
  {num: 716, at: [-122.432742, 37.776252], w: 6.9, d: 15.9, body: '#D4B77A', trim: '#F1ECDD', accent: '#8E2F25', roof: '#8F7D67'},
  {num: 718, at: [-122.43275, 37.776319], w: 7.1, d: 15.9, body: '#8F9479', trim: '#EAE6D6', accent: '#6E7357', roof: '#4A4A4A'},
  {num: 720, at: [-122.432764, 37.776374], w: 6.9, d: 16.1, body: '#9C9165', trim: '#E8DDB5', accent: '#C9A54F', roof: '#4A4A4A'}
];
const KAVANAUGH: House = {num: 722, at: [-122.432781, 37.776463], w: 9.1, d: 18.8, body: '#36404D', trim: '#F2F0EA', accent: '#9AA9B8', roof: '#9C8C7C'};
const PL_ANCHOR: V2 = [-122.43275, 37.776262];

function rowHouse(b: MeshBuilder, h: House, hipped: boolean) {
  const p = lngLatToLocal(PL_ANCHOR, h.at);
  const eave = hipped ? 9.5 : 10;
  b.frame(p[0], p[1], 0, 261, () => {
    // local +y = toward the street/park
    b.color(h.body).box(0, 0, 0, h.w, h.d, eave);
    b.color(h.trim).box(0, 0, eave, h.w + 0.5, h.d + 0.5, 0.45); // cornice
    if (hipped) {
      b.color(h.roof).hip(0, 0, h.w + 0.5, h.d + 0.5, eave + 0.45, 4);
      // corner turret
      b.color(h.body).cylinder(-h.w / 2 + 1.6, h.d / 2 - 0.2, 1.7, 1.5, eave + 1, 8);
      b.color(h.roof).frustum(-h.w / 2 + 1.6, h.d / 2 - 0.2, 1.9, 0.1, eave + 1, eave + 4.5, 8, false);
    } else {
      b.color(h.roof).gable(0, 0, h.w + 0.5, h.d + 0.5, eave + 0.45, 3.2, true);
      // decorated gable field facing the street
      b.color(h.accent).tri([-h.w / 2 + 0.6, h.d / 2 + 0.26, eave + 0.7], [h.w / 2 - 0.6, h.d / 2 + 0.26, eave + 0.7], [0, h.d / 2 + 0.26, eave + 3.1]);
    }
    // angled bay window (left of the facade as seen from the park) and porch
    const bx = -h.w / 2 + 1.7;
    b.color(h.body).prism(
      [
        [bx - 1.5, h.d / 2],
        [bx + 1.5, h.d / 2],
        [bx + 0.9, h.d / 2 + 0.9],
        [bx - 0.9, h.d / 2 + 0.9]
      ],
      2.2,
      eave - 0.3
    );
    b.color(h.trim).box(bx, h.d / 2 + 0.45, eave - 0.3, 3.2, 1.0, 0.3);
    b.color(h.accent).box(h.w / 2 - 1.6, h.d / 2 + 0.6, 5.2, 2.6, 1.2, 0.35); // porch roof
    b.color(h.trim).box(h.w / 2 - 1.6, h.d / 2 + 1.4, 0, 1.6, 1.6, 2.2); // stoop
    b.color('#5B544B').box(-h.w / 2 + 1.7, h.d / 2 + 0.05, 0, 2.6, 0.2, 2.1); // garage door
  });
}

export const paintedLadies: Landmark = {
  id: 'painted_ladies',
  name: 'Painted Ladies (Postcard Row, 710–720 Steiner St)',
  kind: 'building',
  built: [1893, 1895],
  end: 9999,
  anchor: PL_ANCHOR,
  build: b => HOUSES.forEach(h => rowHouse(b, h, false)),
  replaces: HOUSES.map(h => {
    const p = lngLatToLocal(PL_ANCHOR, h.at);
    return rect(p[0], p[1], 9, 9);
  }),
  facts: {
    Built: '1892–1896 by developer Matthew Kavanaugh (per-house years undocumented; shown 1893–95, estimated)',
    Style: 'Queen Anne Victorian',
    Colours: 'as photographed in 2022 (body / trim / gable accents)',
    District: 'Alamo Square Historic District (1984)'
  },
  sources: ['https://en.wikipedia.org/wiki/Painted_ladies', 'https://en.wikipedia.org/wiki/Alamo_Square,_San_Francisco']
};

export const kavanaughHouse: Landmark = {
  id: 'painted_ladies_722',
  name: '722 Steiner St (Kavanaugh House)',
  kind: 'building',
  built: [1891.6, 1892.6],
  end: 9999,
  anchor: PL_ANCHOR,
  build: b => rowHouse(b, KAVANAUGH, true),
  replaces: [
    (() => {
      const p = lngLatToLocal(PL_ANCHOR, KAVANAUGH.at);
      return rect(p[0], p[1], 11, 11);
    })()
  ],
  facts: {Built: '1892, developer Matthew Kavanaugh’s own house', Style: 'Queen Anne, hipped roof with corner turret'},
  sources: ['https://en.wikipedia.org/wiki/Painted_ladies']
};
