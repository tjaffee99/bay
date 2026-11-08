/**
 * The industrial waterfront — data/research/landmarks_ports.md.
 *
 *  * Port of Oakland container cranes, terminal by terminal and generation by generation
 *    (PACECO A-frames 1966–, the NAS-Alameda low-profile cranes 1968–, Panamax 1977/1981,
 *    post-Panamax, Vision 2000 super-post-Panamax 2000–02, the 2018 raised cranes, the 2021
 *    ZPMC cranes), plus Matson's first container crane at Encinal Terminals, Alameda (1959) and
 *    the 1961 whirley cranes at Howard Terminal. Today's cranes stand where the March 2026
 *    orthophoto shows them (Esri World Imagery, viewed only), measured along each wharf face
 *    (OpenStreetMap coastline, © OSM contributors, ODbL). Earlier cranes stand on the same
 *    berths; their counts and years are documented, their spacing along the berth is estimated.
 *  * Container stacks on the terminal yards (ports-yards.ts): footprints, orientation and paint
 *    colour of each 40 ft stack from the orthophoto; heights procedural.
 *  * NAS Alameda (1940–97): landplane hangars 20–23, seaplane hangars 39–41 and 11/12, the
 *    control tower (Building 19), the seaplane ramps, and aircraft carriers at Piers 2 and 3
 *    in their documented homeport years (generic class massing, named as such in the facts).
 *
 * Wharf frames: s = metres along the wharf face from A to B, n = metres inland (to the left of
 * A → B). A crane's waterside rail is 5 m inside the face; its boom reaches out over the water.
 * Everything estimated is named in the model's facts ("Model: …").
 */
import {MeshBuilder, lngLatToLocal, localToLngLat, rect, type V2, type V3} from './kit';
import type {Landmark} from './types';
import {elevationAt} from '../layers/elevation';
import {YARDS} from './ports-yards';

const WIKI = 'https://en.wikipedia.org/wiki/';
const FT = 0.3048;
const OSM_NOTE = 'footprint from OpenStreetMap (© OSM contributors, ODbL)';
const ORTHO = 'positions from the Esri World Imagery orthophoto of March 2026 (viewed only)';

// ------------------------------------------------------------------ sources
const SRC_HOWARD_EIR =
  'https://www.oaklandca.gov/files/assets/city/v/1/public-meetings/landmarks-preservation-advisory-board/2021/er18-016-waterfront-ballpark-district-deir-landmarks-board-report.pdf';
const SRC_ASME = 'https://www.asme.org/about-asme/engineering-history/landmarks/85-paceco-container-crane';
const SRC_ENCINAL = 'https://alamedapost.com/history/canner-ships-railroad-shaped-alamedas-north-shore/';
const SRC_RAISE = 'https://www.portofoakland.com/port-oakland-cranes-going-higher-largest-marine-terminal';
const SRC_RAISE2 = 'https://www.porttechnology.org/news/oakland_completes_crane_raising_initiative/';
const SRC_ZPMC = 'https://www.seatrade-maritime.com/terminals/largest-quay-cranes-in-us-west-coast-arrive-at-oakland-s-oict-terminal';
const SRC_HANJIN = 'https://arccadigest.org/?p=44772';
const SRC_FACILITIES = 'https://www.oaklandseaport.com/facilities/seaport-facilities';
const SRC_OHT = 'https://ttnews.com/articles/terminal-operator-exits-port-oakland';
const SRC_TRAPAC = 'https://www.ship-technology.com/news/trapac-completes-67m-expansion';
const SRC_BOSTON = 'https://www.freightwaves.com/news/port-of-boston-receives-new-cranes';
const SRC_MTO2005 = 'https://www.baaqmd.gov/~/media/Files/Compliance%20and%20Enforcement/Idling%20Trucks/port_of_oakland_mto_info_8-24-05.ashx';
const SRC_SSA2002 = 'https://freightwaves.com/?p=178161';
const SRC_NAS_NRHP = 'https://npgallery.nps.gov/AssetDetail/NRIS/12001191';
const SRC_NAS = WIKI + 'Naval_Air_Station_Alameda';

// ------------------------------------------------------------------ helpers

type Wharf = {A: V2; brg: number; len: number};

/** Wharf face from A to B (lon, lat); inland is to the left of A → B. */
function wharf(A: V2, B: V2): Wharf {
  const [x, y] = lngLatToLocal(A, B);
  return {A, brg: (Math.atan2(x, y) * 180) / Math.PI, len: Math.hypot(x, y)};
}

/** Anchor-frame metres (anchor = A) of wharf coordinates (s along A → B, n inland). */
function wpt(w: Wharf, s: number, n: number): V2 {
  const a = (w.brg * Math.PI) / 180;
  return [Math.sin(a) * s - Math.cos(a) * n, Math.cos(a) * s + Math.sin(a) * n];
}

/** Ground at an anchor-frame point relative to the anchor's ground (the landmark's z = 0). */
function dz(anchor: V2, p: V2) {
  const q = localToLngLat(anchor, p);
  return elevationAt(q[0], q[1]) - elevationAt(anchor[0], anchor[1]);
}

/** Model z of sea level (the waterline) for a landmark anchored at `anchor`. */
function seaZ(anchor: V2) {
  return 0.5 - elevationAt(anchor[0], anchor[1]);
}

/** A local-frame ring (bearing `brg`) as anchor-frame polygon (for `replaces`). */
function rotRing(ring: V2[], brg: number, dx = 0, dy = 0): V2[] {
  const a = (-brg * Math.PI) / 180;
  const c = Math.cos(a);
  const s = Math.sin(a);
  return ring.map(([x, y]) => [dx + c * x - s * y, dy + s * x + c * y] as V2);
}

function scaleRing(ring: V2[], k: number): V2[] {
  const cx = ring.reduce((s, p) => s + p[0], 0) / ring.length;
  const cy = ring.reduce((s, p) => s + p[1], 0) / ring.length;
  return ring.map(([x, y]) => [cx + (x - cx) * k, cy + (y - cy) * k] as V2);
}

// =================================================================== CONTAINER CRANES

/**
 * Ship-to-shore crane generations. Local crane frame: x along the wharf, y inland, the
 * waterside rail at y = 0 and the landside rail at y = gauge, z up from the wharf deck.
 *  gauge  rail gauge;  span  distance between the leg pairs along the wharf
 *  girder underside of the main girder (≈ lift height + trolley and spreader)
 *  outreach boom length beyond the waterside rail; backreach girder beyond the landside rail
 *  apex   top of the A-frame (the forestays and backstays hang from it)
 */
type CraneType = {
  frame: 'paceco' | 'modern' | 'low';
  gauge: number;
  span: number;
  girder: number;
  outreach: number;
  backreach: number;
  apex: number;
  leg: number;
  color: string;
  dark: string;
  house: string;
};

const STEEL_DARK = '#4F5459';

/** Matson's 1959 crane: no published dimensions; scaled from the ASME photographs (estimate). */
const T_PACECO_1959: CraneType = {frame: 'paceco', gauge: 15.2, span: 13, girder: 21, outreach: 24, backreach: 10, apex: 31, leg: 1.2, color: '#B7BDBF', dark: STEEL_DARK, house: '#C9CCC8'};
/** 1960s PACECO A-frame Portainer: 100 ft lift, ≈115 ft outreach, 100 ft gauge (7th Street standard), boom raised ≈22 storeys. */
const T_PACECO: CraneType = {frame: 'paceco', gauge: 100 * FT, span: 16, girder: 33, outreach: 35, backreach: 14, apex: 47, leg: 1.5, color: '#C3C7C6', dark: STEEL_DARK, house: '#D2D3CE'};
/** PACECO low-profile cranes X-421/422/423 (NAS Alameda flight path): 96 ft high, 74 ft lift, 115.5 ft outreach, 182 ft back, 96 ft gauge. */
const T_LOW: CraneType = {frame: 'low', gauge: 96 * FT, span: 16, girder: 21.5, outreach: 115.5 * FT, backreach: (182 - 96) * FT, apex: 0, leg: 1.6, color: '#C6C9C4', dark: STEEL_DARK, house: '#D5D5CF'};
/** X-422 after its 1993–94 rebuild for Howard Terminal: 100 ft gauge, deck raised 26 ft + 4 ft. */
const T_LOW_RAISED: CraneType = {...T_LOW, gauge: 100 * FT, girder: 21.5 + 30 * FT};
/** Panamax (1977 Outer Harbor cranes, Hitachi 1981 at Howard): ≈100–110 ft lift, 13 rows ≈ 38 m outreach. */
const T_PANAMAX: CraneType = {frame: 'modern', gauge: 100 * FT, span: 18, girder: 36, outreach: 38, backreach: 15, apex: 55, leg: 1.6, color: '#D9D7CF', dark: STEEL_DARK, house: '#E4E2DA'};
/** Post-Panamax (KSEC 1987; 1990s): ≈18 rows ≈ 48 m outreach. */
const T_POSTPANAMAX: CraneType = {frame: 'modern', gauge: 100 * FT, span: 20, girder: 40, outreach: 48, backreach: 18, apex: 62, leg: 1.8, color: '#E2E2DD', dark: STEEL_DARK, house: '#EBEBE6'};
/** Super-post-Panamax (Vision 2000): 115 ft lift, ≈22 rows; 379 ft with the boom raised. */
const T_SPP: CraneType = {frame: 'modern', gauge: 100 * FT, span: 22, girder: 41, outreach: 63, backreach: 22, apex: 68, leg: 2.0, color: '#E6E6E1', dark: STEEL_DARK, house: '#EEEEE9'};
const T_SPP_GREEN: CraneType = {...T_SPP, color: '#5D9270', house: '#E6E6E1'};
/** The four OICT cranes lifted 27 ft in 2017–18 (115 → 142 ft lift). */
const T_SPP_RAISED: CraneType = {...T_SPP, girder: 41 + 27 * FT, apex: 68 + 27 * FT};
/** ZPMC 2021 at OICT: 174 ft lift above the dock, 225 ft outreach. */
const T_ZPMC: CraneType = {frame: 'modern', gauge: 100 * FT, span: 24, girder: 174 * FT + 5, outreach: 225 * FT, backreach: 24, apex: 174 * FT + 30, leg: 2.2, color: '#E9E9E4', dark: STEEL_DARK, house: '#F0F0EB'};

/** One crane in its local frame (see CraneType). `up`: boom raised (≈80°). */
function crane(b: MeshBuilder, t: CraneType, up: boolean) {
  const {gauge: g, span: L, girder: H, outreach: R, backreach: K, apex: AP, leg: w} = t;
  const gx = L / 2 - w / 2;
  const D = t.frame === 'low' ? 3.4 : 3.2; // girder depth
  const zt = H + D;
  // sill beams with the bogies on both rails
  b.color(t.dark);
  for (const y of [0, g]) b.box(0, y, 0, L + 7, 1.8, 1.9);
  b.color(t.color);
  if (t.frame === 'paceco') {
    // the PACECO "A": waterside and landside legs lean together to an apex over mid-gauge
    for (const x of [-gx, gx]) {
      b.beam([x, 0, 1.9], [x, g * 0.5, AP], w);
      b.beam([x, g, 1.9], [x, g * 0.5, AP], w);
      b.beam([x, g * 0.18, H * 0.4], [x, g * 0.82, H * 0.4], w * 0.7); // tie
    }
    b.beam([-gx, g * 0.5, AP], [gx, g * 0.5, AP], w);
    for (const y of [g * 0.18, g * 0.82]) b.beam([-gx, y, H * 0.4], [gx, y, H * 0.4], w * 0.8);
  } else {
    for (const x of [-gx, gx]) for (const y of [0, g]) b.box(x, y, 1.9, w, w, H - 1.9, {top: false});
    const zp = t.frame === 'low' ? H - 2.4 : H * 0.42;
    for (const y of [0, g]) b.box(0, y, zp, L + w, w * 0.8, 2.2);
    for (const x of [-gx, gx]) b.beam([x, 0, zp + 2.2], [x, g, H - 0.5], w * 0.6);
  }
  // main girders over the portal and the backreach
  for (const x of [-gx, gx]) b.box(x, (g + K) / 2, H, 1.4, g + K, D);
  // boom: lowered over the water, or raised to ≈80°
  const th = (80 * Math.PI) / 180;
  const tip: V3 = up ? [0, -1 - Math.cos(th) * R, H + D / 2 + Math.sin(th) * R] : [0, -R, zt];
  if (t.frame === 'low') {
    // shuttle boom: slides back over the wharf instead of luffing
    for (const x of [-gx, gx]) b.box(x, up ? 4 : -R / 2, H, 1.4, R, D);
  } else if (up) {
    for (const x of [-gx, gx]) b.beam([x, -1, H + D / 2], [x, tip[1], tip[2]], 1.4, D);
  } else {
    for (const x of [-gx, gx]) b.box(x, -R / 2, H, 1.4, R, D);
  }
  // A-frame and stays
  if (t.frame === 'modern') {
    const ay = g * 0.2;
    for (const x of [-gx, gx]) {
      b.beam([x, 0, zt], [x, ay, AP], w * 0.8);
      b.beam([x, g * 0.75, zt], [x, ay, AP], w * 0.8);
    }
    b.beam([-gx, ay, AP], [gx, ay, AP], w * 0.8);
  }
  if (t.frame !== 'low') {
    const ay = t.frame === 'modern' ? g * 0.2 : g * 0.5;
    b.color(t.dark);
    for (const x of [-gx, gx]) {
      const fore: V3 = up ? [x, tip[1] + 2, tip[2] - 3] : [x, -R * 0.7, zt];
      b.beam([x, ay, AP], fore, 0.5);
      b.beam([x, ay, AP], [x, g + K, zt], 0.5);
    }
  }
  // machinery house at the back, trolley + operator's cab under the girder
  b.color(t.house).box(0, g + K - 6, zt, L - 1, 11, t.frame === 'paceco' ? 4.5 : 5.5);
  b.color(t.dark).box(0, up ? g * 0.3 : -R * 0.3, H - 2.4, 5, 5.5, 2.4);
  b.color('#8E949A').box(1.6, up ? g * 0.3 - 2 : -R * 0.3 - 2, H - 5, 2.4, 3, 2.4);
}

/** A crane at chainage s of a wharf, its waterside rail `rail` metres inland of the face. */
function craneAt(b: MeshBuilder, w: Wharf, s: number, t: CraneType, up: boolean, rail = 5) {
  const p = wpt(w, s, rail);
  b.frame(p[0], p[1], dz(w.A, wpt(w, s, rail + t.gauge / 2)), w.brg - 90, () => crane(b, t, up));
}

function craneSet(
  id: string,
  name: string,
  w: Wharf,
  built: [number, number],
  end: number,
  t: CraneType,
  at: number[],
  up: number[],
  facts: Record<string, string>,
  sources: string[]
): Landmark {
  return {id, name, kind: 'tower', built, end, anchor: w.A, build: b => at.forEach((s, i) => craneAt(b, w, s, t, up.includes(i))), facts, sources};
}

// ------------------------------------------------------------------ whirley (revolving gantry) cranes

/** Revolving gantry crane on a portal straddling the wharf track; boom slewed `slew`° off the wharf normal. */
function whirley(b: MeshBuilder, gauge: number, portal: number, boom: number, luff: number, slew: number, color = '#5C6268') {
  const h = gauge / 2;
  b.color(color);
  for (const x of [-h, h]) for (const y of [-h, h]) b.beam([x * 1.25, y * 1.25, 0], [x * 0.7, y * 0.7, portal], 0.8);
  b.box(0, 0, portal, gauge * 0.9, gauge * 0.9, 1.4); // portal deck
  b.frame(0, 0, portal + 1.4, slew, () => {
    b.color('#6B6F72').box(0, 1.5, 0, 6, 9, 5); // revolving house (cab, hoists, counterweight)
    b.color('#2F3336').box(0, 5.5, 0.5, 5.4, 1.8, 3.5); // counterweight
    b.color(color);
    const a = (luff * Math.PI) / 180;
    const tip: V3 = [0, -2 - Math.cos(a) * boom, 4 + Math.sin(a) * boom];
    b.beam([-1.6, -2, 1], [0, tip[1], tip[2]], 0.9).beam([1.6, -2, 1], [0, tip[1], tip[2]], 0.9); // lattice boom
    b.beam([0, 2.5, 5], [0, 0.5, 13], 0.8); // gantry mast
    b.color('#2F3336').beam([0, 0.5, 13], tip, 0.25); // pendants
  });
}

// =================================================================== PORT OF OAKLAND WHARVES

// Wharf faces (OSM coastline, straightened) — inland to the left of A → B.
const W_OUTER = wharf([-122.313306, 37.819247], [-122.322696, 37.81032]); // Outer Harbor, Berths 20 (NE) → 26 (SW)
const W_7TH_N = wharf([-122.323276, 37.810097], [-122.333068, 37.81103]); // 7th Street, Berths 30–34 (E → W)
const W_7TH_W = wharf([-122.333187, 37.810626], [-122.34263, 37.805782]); // 7th Street tip, Berths 35–38 (NE → SW)
const W_MIDDLE = wharf([-122.325312, 37.798801], [-122.305558, 37.793725]); // Middle Harbor, Berths 55–59 (W → E)
const W_60 = wharf([-122.305558, 37.793725], [-122.296073, 37.793392]); // Berths 60–63 (W → E)
const W_HOWARD = wharf([-122.287947, 37.794963], [-122.281163, 37.79466]); // Howard Terminal, Berths 67–68 (W → E)
const W_ENCINAL = wharf([-122.259466, 37.781213], [-122.259864, 37.777966]); // Encinal Terminals pier, west face (N → S)

const OAK_SRC = [SRC_HOWARD_EIR, WIKI + 'Port_of_Oakland'];

const OAKLAND_CRANES: Landmark[] = [
  // ------------------------------------------------------------ Encinal Terminals (Alameda)
  craneSet('encinal_matson_crane_1959', 'Matson container crane, Encinal Terminals (the first container crane)', W_ENCINAL, [1958.7, 1959.02], 1987.5, T_PACECO_1959, [120], [],
    {
      Built: 'PACECO for Matson, erected fall 1958; in service Jan 7, 1959 — the world’s first high-speed dockside container crane (ASME landmark #85, 1983)',
      Changes: 'modified 1963–64 and 1974–75 (outreach, height, 25 → 30 short tons); dismantled 1987 and sold to the Port of Nanjing',
      Model: 'no published dimensions: A-frame, 50 ft gauge and boom scaled from the ASME photographs (estimate); position on the Encinal pier’s basin face estimated'
    }, [SRC_ASME, SRC_ENCINAL, SRC_HOWARD_EIR]),
  craneSet('encinal_paceco_1977', 'PACECO Portainer, Encinal Terminals (1977)', W_ENCINAL, [1977.0, 1977.5], 1987.5, T_PANAMAX, [230], [0],
    {
      Built: '1977: “a new generation PACECO Portainer crane, the big brother of the original” (ASME 1983); dismantled with the 1959 crane in 1987; terminal closed to shipping 1993',
      Model: 'generic Panamax massing; position estimated'
    }, [SRC_ASME, SRC_ENCINAL]),

  // ------------------------------------------------------------ Howard Terminal (Berths 67–68)
  {
    id: 'howard_whirley_cranes_1961',
    name: 'Howard Terminal revolving gantry cranes (1961)',
    kind: 'tower',
    built: [1961.6, 1961.8],
    end: 1977.5,
    anchor: W_HOWARD.A,
    build: b => {
      for (const s of [180, 330]) {
        const p = wpt(W_HOWARD, s, 9);
        b.frame(p[0], p[1], dz(W_HOWARD.A, p), W_HOWARD.brg - 90, () => whirley(b, 9, 10, 32, 58, 15));
      }
    },
    facts: {
      Built: 'October 1961: Washington revolving (“whirling”) gantry cranes at Howard Terminal for scrap metal and 20-ton containers ($300,000) — Oakland’s first landside container cranes',
      End: 'the break-bulk Howard / Grove Street terminals were cleared for the new Charles P. Howard Terminal after 1974',
      Model: 'two cranes (count and positions estimated); generic whirley massing; removal year estimated'
    },
    sources: [SRC_HOWARD_EIR]
  },
  craneSet('howard_cranes_1981', 'Howard Terminal cranes X-415 and X-416 (Hitachi, 1981)', W_HOWARD, [1981.0, 1981.9], 9999, T_PANAMAX, [60, 96], [0, 1],
    {
      Built: 'Hitachi Panamax cranes installed 1981 for the Charles P. Howard Terminal (opened 1982); container operations ended early 2014, cranes standing (2026)',
      Model: ORTHO + ' (booms raised); which crane is which estimated'
    }, OAK_SRC),
  craneSet('howard_crane_x417', 'Howard Terminal crane X-417 (KSEC, 1987)', W_HOWARD, [1987.0, 1987.5], 9999, T_POSTPANAMAX, [132], [0],
    {Built: 'Kunming Shipbuilding Equipment Co. post-Panamax crane installed 1987', Model: ORTHO + ' (boom raised)'}, OAK_SRC),
  craneSet('howard_crane_x422', 'Crane X-422 (PACECO low-profile, at Howard since 1994)', W_HOWARD, [1994.15, 1994.25], 9999, T_LOW_RAISED, [24], [],
    {
      History: 'erected 1970 at Berth 35 (7th Street Terminal), moved to Berth 38 after the 1989 earthquake, rebuilt 1993 (gauge 96 → 100 ft, deck raised 26 + 4 ft) and barged to Howard Terminal March 1994 — the westernmost crane there; the last first-generation crane of the port',
      Model: 'low-profile PACECO Portainer: 115.5 ft outreach, 182 ft back from the waterside rail; ' + ORTHO
    }, OAK_SRC),

  // ------------------------------------------------------------ Outer Harbor (Berths 20–26)
  craneSet('oak_sealand_cranes_1966', 'Sea-Land Terminal PACECO cranes (Outer Harbor, 1966)', W_OUTER, [1965.8, 1966.4], 1999.5, T_PACECO, [110, 180], [1],
    {
      Built: 'the port’s first two PACECO A-frame container cranes, 1966, at Sea-Land’s Outer Harbor terminal (Sea-Land service from Sept 5, 1962)',
      Model: 'A-frame Portainer massing (100 ft lift, ≈22 storeys with the boom raised); positions on Berths 20–21 and the replacement year (Maersk Sealand / APM era) estimated'
    }, OAK_SRC),
  craneSet('oak_sealand_cranes_1968', 'Sea-Land Terminal PACECO cranes (Outer Harbor, late 1960s)', W_OUTER, [1967.8, 1968.6], 1999.5, T_PACECO, [330, 400], [0],
    {
      Built: 'the Sea-Land terminal grew to 59 acres, three berths and four cranes (Minor 2000, via the Howard Terminal EIR)',
      Model: 'years of the 3rd and 4th cranes, positions and replacement year estimated'
    }, OAK_SRC),
  craneSet('oak_maersk_cranes_1977', 'Maersk Terminal cranes (Outer Harbor, 1977)', W_OUTER, [1976.6, 1977.4], 2010.1, T_PANAMAX, [560, 640, 720], [1],
    {
      Built: '1977: the one-berth, three-crane, 36-acre Maersk Terminal replaced the Seventh Street Unit, the Oil Pier and the Fourteenth Street Unit',
      Model: 'Panamax massing; positions and replacement year (APM handed Berths 20–24 to Ports America in 2010) estimated'
    }, [...OAK_SRC, SRC_BOSTON]),
  craneSet('oak_transbay_cranes_1977', 'TransBay Container Terminal cranes (Berths 25–26, 1977)', W_OUTER, [1976.6, 1977.4], 2016.25, T_PANAMAX, [1000, 1080], [],
    {
      Built: '1977: the two-berth, two-crane, 29-acre Outer Harbor Container Terminal (renamed TransBay Container Terminal 1986)',
      Model: 'Panamax massing; positions and end year estimated (Berths 25–26 went to TraPac when the Outer Harbor Terminal closed, March 2016)'
    }, [...OAK_SRC, SRC_MTO2005]),
  craneSet('oak_outer_harbor_cranes', 'Outer Harbor Terminal cranes (Berths 20–24)', W_OUTER, [1999.5, 2000.0], 9999, T_POSTPANAMAX, [41, 95, 158, 188], [],
    {
      History: 'Maersk Sealand / APM Terminals (Berths 20–22, 24, 2005) until 2010, then Ports America’s Outer Harbor Terminal; idle since the terminal closed on March 31, 2016',
      Model: ORTHO + ' (four cranes, booms lowered); post-Panamax massing; installation year estimated'
    }, [SRC_MTO2005, SRC_OHT, SRC_BOSTON]),
  craneSet('oak_trapac_cranes_25_26', 'TraPac cranes, Berths 25–26', W_OUTER, [2016.5, 2017.0], 9999, T_SPP, [1062, 1092, 1122], [],
    {
      History: 'TraPac took over Berths 25–26 after the Outer Harbor Terminal closed (2016); its 2019 buildout doubled the terminal to 123 acres and raised its ship-to-shore cranes from four to seven',
      Model: ORTHO + '; super-post-Panamax massing; year estimated'
    }, [SRC_TRAPAC, SRC_FACILITIES]),

  // ------------------------------------------------------------ Seventh Street Terminal (Berths 30–38)
  craneSet('oak_7th_street_cranes_1968', 'Seventh Street Terminal PACECO cranes (Berths 30–33)', W_7TH_N, [1967.9, 1969.0], 2001.0, T_PACECO, [250, 340], [0],
    {
      Built: 'the Seventh Street Terminal was built 1967–71 on the old Southern Pacific mole and 140 acres of fill (BART tunnel spoil), designed by Kaiser Engineers; X-422 (Aug 1970) was its fourth crane',
      Model: 'two A-frame Portainers before 1970 (count from the EIR’s crane chronology), positions and replacement year estimated'
    }, OAK_SRC),
  craneSet('oak_7th_street_cranes_1972', 'Seventh Street Terminal cranes (Berths 30–33, early 1970s)', W_7TH_N, [1971.5, 1972.5], 2001.0, T_PACECO, [580, 700], [1],
    {
      Built: '1965–74: the Seventh Street and APL terminals added 221 acres, at least seven berths and at least seven more container cranes',
      Model: 'years, positions and replacement year estimated'
    }, OAK_SRC),
  craneSet('oak_crane_x421', 'Crane X-421 (PACECO low-profile, 1968)', W_7TH_W, [1968.2, 1968.7], 1989.8, T_LOW, [330], [],
    {
      Built: '1968: the first of three low-profile cranes the Navy required under the NAS Alameda flight path (132 ft height limit)',
      Model: 'position on Berths 35–36 and removal year estimated (two low-profile cranes from Oakland went to Boston’s Conley Terminal in 2010)'
    }, [SRC_HOWARD_EIR, SRC_BOSTON]),
  craneSet('oak_crane_x422_berth35', 'Crane X-422 at Berth 35 (1970)', W_7TH_W, [1970.3, 1970.59], 1989.8, T_LOW, [200], [],
    {
      Built: 'commissioned Aug 4, 1970 at Berth 35 — the fourth crane of the 7th Street Terminal, the ninth landside crane of the port; 96 ft high, 74 ft lift, 40 long tons',
      Later: 'out of service after the 1989 Loma Prieta earthquake, moved to Berth 38, rebuilt 1993 and moved to Howard Terminal 1994',
      Model: 'chainage of Berth 35 estimated'
    }, OAK_SRC),
  craneSet('oak_crane_x422_berth38', 'Crane X-422 at Berth 38 (1990–94)', W_7TH_W, [1990.3, 1990.6], 1993.5, T_LOW, [880], [],
    {History: 'relocated to Berth 38 after the Loma Prieta earthquake, seldom used; surplus 1992; rebuilt 1993', Model: 'chainage of Berth 38 and dates estimated'}, OAK_SRC),
  craneSet('oak_crane_x423', 'Crane X-423 (PACECO low-profile, 1971)', W_7TH_W, [1971.0, 1971.5], 1989.8, T_LOW, [460], [],
    {Built: '1971, third low-profile crane', Model: 'position and removal year estimated'}, [SRC_HOWARD_EIR, SRC_BOSTON]),
  craneSet('oak_nutter_cranes_1991', 'Ben E. Nutter Terminal cranes (Berths 35–38)', W_7TH_W, [1991.0, 1991.6], 2002.0, T_POSTPANAMAX, [360, 612, 775], [2],
    {
      History: 'the wharf at Berths 35–38 was the worst damage of the 1989 Loma Prieta earthquake (closed for months); the rebuilt Ben E. Nutter Terminal served Berths 35/36–39 (2005)',
      Model: 'post-Panamax massing; count, positions and years estimated'
    }, [SRC_MTO2005, 'https://www.adaptingtorisingtides.org/wp-content/uploads/2014/12/Seaport_ECS.pdf']),
  craneSet('oak_everport_cranes', 'Everport Terminal cranes (Berths 35–38)', W_7TH_W, [2002.0, 2002.5], 9999, T_SPP_GREEN, [360, 612, 718, 775], [3],
    {
      History: 'Ben E. Nutter Terminal, operated by Everport (Evergreen); four super-post-Panamax cranes (Port of Oakland facilities list)',
      Model: ORTHO + ' (green cranes); installation year estimated'
    }, [SRC_FACILITIES]),
  craneSet('oak_trapac_cranes_30_33', 'TraPac cranes, Berths 30–33', W_7TH_N, [2001.0, 2001.5], 9999, T_SPP, [134, 305, 626, 839], [],
    {
      History: 'TraPac (Berth 30 in 2005; Berths 25–33 and 123 acres after the 2019 buildout, 5 post-Panamax + 2 super-post-Panamax cranes)',
      Model: ORTHO + '; installation year estimated'
    }, [SRC_MTO2005, SRC_TRAPAC, SRC_FACILITIES]),

  // ------------------------------------------------------------ Middle Harbor (Berths 55–59): Vision 2000
  craneSet('oak_hanjin_cranes_2000', 'Hanjin Terminal cranes, Berths 55–56 (2000)', W_MIDDLE, [2000.81, 2001.3], 9999, T_SPP, [53, 101, 353, 461], [],
    {
      Built: 'four super-post-Panamax cranes (≈22 storeys, 65 tons) delivered by the ship Zhen Hua on Oct 22, 2000 for the Hanjin Terminal — the first terminal of the Vision 2000 program, on the former Fleet Industrial Supply Center; part of OICT since 2015',
      Model: ORTHO
    }, [SRC_HANJIN, SRC_FACILITIES]),
  craneSet('oak_ssa_cranes_2002', 'SSA Terminal cranes, Berths 57–59 (2002)', W_MIDDLE, [2002.3, 2002.85], 2020.9, T_SPP, [551, 821, 1482], [],
    {
      Built: 'Stevedoring Services of America’s 150-acre terminal opened November 2002 (later Oakland International Container Terminal)',
      Model: ORTHO + '; which three cranes the 2021 ZPMC cranes replaced is estimated'
    }, [SRC_SSA2002, SRC_FACILITIES]),
  craneSet('oak_ssa_cranes_2002b', 'SSA Terminal cranes, Berths 57–59 (2002, before raising)', W_MIDDLE, [2002.3, 2002.85], 2017.4, T_SPP, [1329, 1359, 1614, 1659], [],
    {Built: 'opened November 2002', Model: ORTHO + '; which four were raised in 2017–18 is estimated'}, [SRC_SSA2002]),
  craneSet('oak_oict_raised_cranes', 'OICT raised cranes (2018)', W_MIDDLE, [2017.4, 2018.6], 9999, T_SPP_RAISED, [1329, 1359, 1614, 1659], [],
    {
      Built: 'four OICT gantry cranes lifted 27 ft on longer legs, May 2017 – 2018 (lift height 115 → 142 ft above the dock), for the new 14,000+ TEU ships',
      Model: ORTHO + '; which four were raised estimated'
    }, [SRC_RAISE, SRC_RAISE2]),
  craneSet('oak_oict_zpmc_cranes_2021', 'OICT ZPMC cranes (2021)', W_MIDDLE, [2020.9, 2021.2], 9999, T_ZPMC, [551, 821, 1482], [],
    {
      Built: 'three ZPMC cranes, $30 million: 174 ft lift above the dock, 225 ft outreach — the tallest on the U.S. West Coast (2021); three older cranes removed',
      Model: ORTHO + '; which three estimated'
    }, [SRC_ZPMC]),

  // ------------------------------------------------------------ Berths 60–63 (APL, now Matson)
  craneSet('oak_apl_cranes_1972', 'APL Terminal cranes, Berths 60–63 (1970s)', W_60, [1971.5, 1972.5], 2002.0, T_PACECO, [419, 608, 806], [2],
    {
      Built: 'the American President Lines terminal was developed with the 7th Street Terminal, 1965–74',
      Model: 'A-frame massing; count, positions and years estimated'
    }, OAK_SRC),
  craneSet('oak_matson_cranes', 'Matson Terminal cranes, Berths 60–63', W_60, [2002.0, 2002.6], 9999, T_POSTPANAMAX, [419, 608, 638, 806], [],
    {
      History: 'APL’s Global Gateway Central (rebuilt over two years without closing; APL at Berths 60–63 in 2005), then the SSA-operated Matson Terminal (Berths 61–63, four post-Panamax cranes)',
      Model: ORTHO + '; installation year estimated'
    }, [SRC_MTO2005, SRC_FACILITIES])
];

// =================================================================== CONTAINER STACKS

const BOX_COLORS = ['#8C4B3F', '#6C3A34', '#A86A43', '#A38F57', '#55755C', '#4A6D6F', '#4B5F7C', '#7F99A8', '#8B8D8C', '#CFCDC4'];
const B64 = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/';
const BOX_H = 2.59;
const PITCH_L = 12.8; // 40 ft box (12.19 m) + gap
const PITCH_W = 2.8; // 8 ft box (2.44 m) + gap

type Stack = {s: number; n: number; along: boolean; color: number; h: number; si: number; ni: number};

/** Runs of stacks (consecutive along s) decoded from the yard string. */
function decodeYard(cells: string): Stack[][] {
  const runs: Stack[][] = [];
  const v = (i: number, k: number) => {
    let x = 0;
    for (let j = 0; j < k; j++) x = x * 64 + B64.indexOf(cells[i + j]);
    return x;
  };
  let i = 0;
  while (i < cells.length) {
    const s0 = v(i, 3);
    const n0 = v(i + 3, 3);
    const c = v(i + 6, 1);
    const along = c >= 32;
    const count = c % 32;
    i += 7;
    const run: Stack[] = [];
    for (let k = 0; k < count; k++) {
      const code = v(i + k, 1);
      const si = s0 + Math.round(k * (along ? PITCH_L : PITCH_W) * 10);
      run.push({s: si / 10 - 1000, n: n0 / 10 - 1000, along, color: Math.floor(code / 6), h: code % 6, si, ni: n0});
    }
    runs.push(run);
    i += count;
  }
  return runs;
}

/** Colour family of a box colour for the merged side walls: reds, ochre, greens/blues, greys. */
const FAMILY = [0, 0, 0, 1, 2, 2, 2, 2, 3, 3];
const FAMILY_WALL = ['#874A3E', '#9C8853', '#52695E', '#A9A9A4'];

/**
 * Container stacks of one terminal yard. Each stack fills its pitch cell so a block reads as one
 * mass; tops keep each stack's colour (merged where neighbours match), side walls are merged
 * along a run by colour family and drawn only where the next row of the block is lower; single
 * boxes (h = 1) stand on chassis.
 */
function stacks(b: MeshBuilder, key: string) {
  const y = YARDS[key];
  const w = wharf(y.A, y.B);
  const runs = decodeYard(y.cells);
  const tall = new Map<string, number>();
  for (const r of runs) for (const c of r) tall.set(`${c.along ? 1 : 0}:${c.si}:${c.ni}`, c.h);
  const look = (al: number, si: number, ni: number) => {
    for (const ds of [0, -1, 1]) for (const dn of [0, -1, 1]) {
      const h = tall.get(`${al}:${si + ds}:${ni + dn}`);
      if (h !== undefined) return h;
    }
    return 0;
  };
  // runs go along s for both orientations (pitch 12.8 m for boxes lying along the wharf, 2.8 m
  // for boxes lying across it); the next row of the block is one row pitch over in n
  const nb = (c: Stack, d: number) => (c.h === 1 ? 0 : look(c.along ? 1 : 0, c.si, c.ni + d * (c.along ? 28 : 128)));
  // one ground height per 100 m square (the yards are flat; keeps neighbouring rows level)
  const ground = new Map<string, number>();
  const gz = (s: number, n: number) => {
    const k = `${Math.round(s / 100)}:${Math.round(n / 100)}`;
    let z = ground.get(k);
    if (z === undefined) {
      z = dz(w.A, wpt(w, Math.round(s / 100) * 100, Math.max(60, Math.round(n / 100) * 100)));
      ground.set(k, z);
    }
    return z;
  };
  const geom = (c: Stack) => {
    const ch = c.h === 1;
    const z0 = gz(c.s, c.n) + (ch ? 1.25 : 0);
    const lx = c.along ? (ch ? 12.19 : PITCH_L - 0.1) : ch ? 2.44 : PITCH_W - 0.1;
    const ly = c.along ? (ch ? 2.44 : PITCH_W - 0.1) : ch ? 12.19 : PITCH_L - 0.1;
    return {z0, z1: z0 + (ch ? 1 : c.h) * BOX_H, x0: c.s, x1: c.s + lx, y0: c.n, y1: c.n + ly};
  };
  b.frame(0, 0, 0, w.brg - 90, () => {
    // local frame: x = s (along the wharf), y = n (inland)
    for (const run of runs) {
      const G = run.map(geom);
      // tops, merged over neighbours of the same colour and height (chassis boxes stand apart)
      for (let i = 0; i < run.length; ) {
        let j = i;
        while (j + 1 < run.length && run[j + 1].h === run[i].h && FAMILY[run[j + 1].color] === FAMILY[run[i].color] && run[i].h > 1 && Math.abs(G[j + 1].z0 - G[i].z0) < 0.01) j++;
        const a = G[i];
        const e = G[j];
        b.color(BOX_COLORS[run[i].color] ?? BOX_COLORS[8]).quad([a.x0, a.y0, a.z1], [e.x1, a.y0, a.z1], [e.x1, a.y1, a.z1], [a.x0, a.y1, a.z1]);
        i = j + 1;
      }
      // walls across the run (x = const): at the run ends, where the height steps, and around chassis boxes
      for (let i = 0; i < run.length; i++) {
        const c = run[i];
        const g = G[i];
        const pitch = c.along ? 128 : 28;
        const al = c.along ? 1 : 0;
        const prev = c.h > 1 ? (i > 0 ? run[i - 1].h : look(al, c.si - pitch, c.ni)) : 0;
        const next = c.h > 1 ? (i + 1 < run.length ? run[i + 1].h : look(al, c.si + pitch, c.ni)) : 0;
        b.color(FAMILY_WALL[FAMILY[c.color] ?? 3]);
        // (a chassis box only shows its long sides: its ends are 2.4 m and the gaps in the parking rows are small)
        if (c.h === 1 && !c.along) continue;
        for (const [x, lowH] of [[g.x0, prev], [g.x1, next]] as [number, number][]) {
          const lo = c.h === 1 ? g.z0 : g.z0 + Math.min(lowH, c.h) * BOX_H;
          if (lo < g.z1 - 0.01) b.quad([x, g.y0, lo], [x, g.y1, lo], [x, g.y1, g.z1], [x, g.y0, g.z1]);
        }
      }
      // long walls (y = const) on both sides of the run, merged by colour family and height range
      for (const side of [-1, 1]) {
        let seg: {x0: number; x1: number; lo: number; hi: number; f: number} | null = null;
        const flush = () => {
          if (!seg) return;
          const yy = side < 0 ? G[0].y0 : G[0].y1;
          b.color(FAMILY_WALL[seg.f]).quad([seg.x0, yy, seg.lo], [seg.x1, yy, seg.lo], [seg.x1, yy, seg.hi], [seg.x0, yy, seg.hi]);
          seg = null;
        };
        for (let i = 0; i < run.length; i++) {
          const c = run[i];
          const g = G[i];
          const lo = c.h === 1 ? g.z0 : g.z0 + Math.min(nb(c, side), c.h) * BOX_H;
          const f = FAMILY[c.color] ?? 3;
          if (lo >= g.z1 - 0.01 || (c.h === 1 && c.along)) {
            flush();
            continue;
          }
          if (seg && c.h > 1 && Math.abs(seg.lo - lo) < 0.01 && Math.abs(seg.hi - g.z1) < 0.01 && seg.f === f && Math.abs(seg.x1 + 0.1 - g.x0) < 0.3) seg.x1 = g.x1;
          else {
            flush();
            seg = {x0: g.x0, x1: g.x1, lo, hi: g.z1, f};
          }
        }
        flush();
      }
    }
  });
}

function yardSet(id: string, name: string, key: string, built: [number, number], end: number, facts: Record<string, string>, sources: string[]): Landmark {
  return {id, name, kind: 'building', built, end, anchor: YARDS[key].A, build: b => stacks(b, key), facts, sources};
}

const STACK_MODEL =
  '40 ft container stacks (12.19 × 2.44 × 2.59 m): footprint, orientation and paint colour of each stack from the March 2026 orthophoto (Esri World Imagery, viewed only); heights procedural (blocks 3–4 high ±1, lone boxes on chassis); the same layout is shown for the whole container era';

const OAKLAND_YARDS: Landmark[] = [
  yardSet('oak_yard_sealand', 'Container yard, Berths 20–22 (Sea-Land / APM / Outer Harbor Terminal)', 'oh2022', [1962.65, 1962.7], 9999,
    {History: 'Sea-Land from Sept 1962 (650 ft of berth and 6 acres), 24 + 14 more acres from 1966; APM until 2010, Ports America until March 2016; chassis and container parking since', Model: STACK_MODEL}, [SRC_HOWARD_EIR, SRC_OHT]),
  yardSet('oak_yard_berth23', 'Container yard, Berth 23', 'oh23', [1977.3, 1977.35], 9999, {History: 'Maersk Terminal (1977), later APM / Outer Harbor Terminal', Model: STACK_MODEL}, [SRC_HOWARD_EIR]),
  yardSet('oak_yard_berth24', 'Container yard, Berth 24', 'oh24', [1977.3, 1977.35], 9999, {History: 'Maersk Terminal (1977), later APM / Outer Harbor Terminal', Model: STACK_MODEL}, [SRC_HOWARD_EIR]),
  yardSet('oak_yard_transbay', 'Container yard, Berths 25–26 (TransBay / TraPac)', 'transbay', [1977.3, 1977.35], 9999, {History: 'Outer Harbor Container Terminal 1977 (TransBay Container Terminal from 1986), TraPac since 2016', Model: STACK_MODEL}, [SRC_HOWARD_EIR, SRC_TRAPAC]),
  yardSet('oak_yard_trapac', 'Container yard, Berths 30–34 (7th Street / TraPac)', 'trapac', [1968.5, 1968.55], 9999, {History: 'Seventh Street Terminal (1967–71); TraPac', Model: STACK_MODEL}, [SRC_HOWARD_EIR, SRC_TRAPAC]),
  yardSet('oak_yard_nutter', 'Container yard, Berths 35–38 (Ben E. Nutter / Everport)', 'everport', [1969.5, 1969.55], 9999, {History: 'Seventh Street Terminal; Ben E. Nutter Terminal (Everport)', Model: STACK_MODEL}, [SRC_HOWARD_EIR, SRC_FACILITIES]),
  yardSet('oak_yard_hanjin', 'Container yard, Berths 55–56 (Hanjin / OICT)', 'hanjin', [2001.3, 2001.35], 9999, {History: 'Hanjin Terminal, the first Vision 2000 terminal (2001), on the former Fleet Industrial Supply Center; OICT', Model: STACK_MODEL}, [SRC_HANJIN]),
  yardSet('oak_yard_ssa', 'Container yard, Berths 57–59 (SSA / OICT)', 'ssa', [2002.85, 2002.9], 9999, {History: 'SSA terminal opened November 2002 (150 acres); Oakland International Container Terminal', Model: STACK_MODEL}, [SRC_SSA2002]),
  yardSet('oak_yard_60_63', 'Container yard, Berths 60–63 (APL / Matson)', 'matson', [1972.5, 1972.55], 9999, {History: 'APL terminal (developed 1965–74; Global Gateway Central), Matson Terminal since APL moved to OICT', Model: STACK_MODEL + '; start year estimated'}, [SRC_HOWARD_EIR, SRC_FACILITIES])
];

// =================================================================== NAS ALAMEDA (1940–1997)

const STUCCO = '#E3DED1';
const STUCCO_SH = '#CFC9BA';
const HANGAR_ROOF = '#8C9196';
const DOOR_GLASS = '#7E8C93';
const NAS_FACTS_SRC = [SRC_NAS_NRHP, SRC_NAS];

/** Landplane hangars 20–23: 254 × 213 ft, low-pitched gable roof with two monitors, glazed sliding doors on the north and south fronts between pylon-like door pockets. */
function landplaneHangar(no: number, anchor: V2, brg: number, door: V2[]): Landmark {
  return {
    id: `nas_alameda_hangar_${no}`,
    name: `NAS Alameda landplane hangar (Building ${no})`,
    kind: 'building',
    built: [1940.6, 1941.4],
    end: 9999,
    anchor,
    build: b =>
      b.frame(0, 0, 0, brg, () => {
        // local: x across (65 m, doors on the ±x fronts = north/south), y along (78 m, E–W)
        const hx = 32.6;
        const hy = 39.0;
        b.color(STUCCO).box(0, -hy + 4.5, -0.5, 2 * hx, 9, 10.5); // west office wing, 2 storeys
        b.box(0, hy - 4.5, -0.5, 2 * hx, 9, 10.5); // east office wing
        b.color(STUCCO_SH).box(0, 0, -0.5, 2 * hx - 4, 2 * hy - 6, 16.5, {top: false}); // hangar bay + set-back 3rd storey
        b.color(HANGAR_ROOF);
        b.gable(0, 0, 2 * hx - 4, 2 * hy - 6, 16, 2.6, false); // low-pitched gable, ridge from door front to door front
        b.color('#B9BDB8');
        for (const x of [-9, 9]) b.box(x, 0, 17.3, 3.2, 2 * hy - 18, 1.6); // two clerestory monitors
        for (const sx of [-1, 1]) {
          // glazed sliding doors with the shed roof over them, and the corner door pockets
          b.color(DOOR_GLASS).box(sx * (hx - 0.6), 0, -0.5, 1.2, 2 * hy - 18, 13.5, {top: false});
          b.color(STUCCO).box(sx * (hx - 1.0), 0, 13, 2.4, 2 * hy - 14, 0.8);
          for (const sy of [-1, 1]) b.box(sx * (hx - 1.2), sy * (hy - 4.5), -0.5, 3.6, 9, 18.5);
        }
      }),
    replaces: [door],
    facts: {
      Built: '1940–41 for the new Naval Air Station Alameda (commissioned Nov 1, 1940); contributing building of the NAS Alameda Historic District (NRHP 2013)',
      Size: '254 × 213 ft (≈66,000 sq ft), low-pitched gable roof with two monitors, glazed segmental sliding doors on the north and south fronts between pylon-like door pockets',
      Model: OSM_NOTE + '; heights (≈16 m eaves, 2-storey office wings) estimated from photos'
    },
    sources: NAS_FACTS_SRC
  };
}

/** Seaplane hangars (and the matching shops 11, 12): ≈117 × 80 m, very low-pitched gable roof, sliding doors on the east and west sides, three storeys of shops at the north and south ends. */
function seaplaneHangar(id: string, name: string, built: [number, number], anchor: V2, brg: number, facts: Record<string, string>): Landmark {
  const hx = 39.9;
  const hy = 58.6;
  return {
    id,
    name,
    kind: 'building',
    built,
    end: 9999,
    anchor,
    build: b =>
      b.frame(0, 0, 0, brg, () => {
        // local: y along the long axis (≈N–S), doors on the ±x (east/west) sides
        b.color(STUCCO);
        for (const sy of [-1, 1]) b.box(0, sy * (hy - 5), -0.5, 2 * hx, 10, 12.5); // shop / office ends
        b.color(STUCCO_SH).box(0, 0, -0.5, 2 * hx - 3, 2 * hy - 4, 19, {top: false});
        b.color(HANGAR_ROOF).gable(0, 0, 2 * hx - 3, 2 * hy - 4, 18.5, 2.2, true);
        b.color('#B9BDB8');
        for (const x of [-12, 12]) b.box(x, 0, 19.6, 3.2, 2 * hy - 24, 1.4);
        for (const sx of [-1, 1]) {
          b.color(DOOR_GLASS).box(sx * (hx - 0.7), 0, -0.5, 1.4, 2 * hy - 26, 15.5, {top: false});
          b.color(STUCCO).box(sx * (hx - 1.1), 0, 15, 2.6, 2 * hy - 22, 0.8);
          for (const sy of [-1, 1]) b.box(sx * (hx - 1.6), sy * (hy - 6), -0.5, 4, 12, 21);
        }
      }),
    replaces: [rotRing(rect(0, 0, 2 * hx + 3, 2 * hy + 3), brg)],
    facts,
    sources: NAS_FACTS_SRC
  };
}

const HANGARS: Landmark[] = [
  landplaneHangar(20, [-122.309169, 37.7887], 93.97, rotRing(rect(0, 0, 68, 81), 93.97)),
  landplaneHangar(21, [-122.30926, 37.787606], 93.8, rotRing(rect(0, 0, 68, 81), 93.8)),
  landplaneHangar(22, [-122.309349, 37.78652], 93.95, rotRing(rect(0, 0, 68, 81), 93.95)),
  landplaneHangar(23, [-122.309439, 37.785418], 93.95, rotRing(rect(0, 0, 68, 81), 93.95)),
  seaplaneHangar('nas_alameda_hangar_40', 'NAS Alameda seaplane hangar (Building 40)', [1940.8, 1941.6], [-122.301157, 37.782293], 3.84, {
    Built: '1941, maintenance (seaplane) hangar facing the Seaplane Lagoon; 118,190 sq ft; contributing building of the historic district',
    Model: OSM_NOTE + '; heights (≈19 m eaves, three-storey shop ends) estimated from photos'
  }),
  seaplaneHangar('nas_alameda_hangar_39', 'NAS Alameda seaplane hangar (Building 39)', [1943.5, 1944.3], [-122.303189, 37.782401], 3.84, {
    Built: '1944, maintenance hangar; 110,139 sq ft; contributing building',
    Model: OSM_NOTE + '; heights estimated from photos'
  }),
  seaplaneHangar('nas_alameda_hangar_41', 'NAS Alameda seaplane hangar (Building 41)', [1944.5, 1945.3], [-122.299113, 37.782198], 3.84, {
    Built: '1945, aircraft intermediate maintenance shop in the third seaplane hangar; 118,041 sq ft; contributing building',
    Model: OSM_NOTE + '; heights estimated from photos'
  }),
  seaplaneHangar('nas_alameda_hangar_12', 'NAS Alameda hangar (Building 12)', [1940.8, 1941.6], [-122.30521, 37.782505], 3.8, {
    Built: '1941, aircraft maintenance shop (NRHP inventory; non-contributing after later alterations)',
    Model: OSM_NOTE + '; massing assumed to match the seaplane hangars beside it; heights estimated'
  }),
  seaplaneHangar('nas_alameda_hangar_11', 'NAS Alameda hangar (Building 11)', [1940.8, 1941.6], [-122.307277, 37.782613], 3.8, {
    Built: '1941, aircraft maintenance shop (NRHP inventory; non-contributing after later alterations)',
    Model: OSM_NOTE + '; massing assumed to match the seaplane hangars; heights estimated'
  })
];

// ------------------------------------------------------------ Building 19, the control tower
const TOWER19: V2 = [-122.310005, 37.782309];
const B19_RING: V2[] = [[-10.2, 28.5], [3.2, 27.5], [1.5, 3.7], [18.7, 2.4], [17.7, -9.9], [23.5, -10.3], [22.9, -17.7], [-2.8, -15.9], [-2.8, -17.2], [-6.5, -17.0], [-6.4, -15.6], [-20.0, -14.6], [-19.3, -4.8], [-12.6, -5.3]];
const controlTower: Landmark = {
  id: 'nas_alameda_control_tower',
  name: 'NAS Alameda control tower (Building 19)',
  kind: 'tower',
  built: [1940.9, 1941.5],
  end: 9999,
  anchor: TOWER19,
  build: b => {
    // L-shaped operations building: two-storey N–S wing, one-storey E–W wing on a high base
    b.color(STUCCO).prism([[-10.2, 28.5], [3.2, 27.5], [1.6, 2.5], [-12.4, 3.4]], -0.5, 8.4);
    b.prism([[1.6, 3.7], [18.7, 2.4], [17.7, -9.9], [23.5, -10.3], [22.9, -17.7], [-2.8, -15.9], [-2.0, 3.8]], -0.5, 5.2);
    b.color(STUCCO_SH).prism([[-12.6, -5.3], [-19.3, -4.8], [-20.0, -14.6], [-6.4, -15.6], [-2.0, 3.8], [-12.4, 3.4]], -0.5, 5.2);
    // the four-storey square tower at the SW corner (OSM part, 10 m) with the octagonal glass cab
    b.frame(-14.7, -10.1, 0, 4.2, () => {
      b.color(STUCCO).box(0, 0, -0.5, 9.8, 9.8, 17.5);
      b.color('#BFB9AB').box(0, 0, 17, 10.4, 10.4, 0.6);
      const oct = (r: number) => Array.from({length: 8}, (_, i) => [Math.cos(((i + 0.5) * Math.PI) / 4) * r, Math.sin(((i + 0.5) * Math.PI) / 4) * r] as V2);
      b.color('#9DB0B8').loft([oct(3.4), oct(4.1), oct(3.6)], [17.6, 19.4, 21.2], {top: false});
      b.color('#CFCABE').prism(oct(4.2), 21.2, 21.8);
      b.color('#5E6266').beam([1.5, 1.5, 21.8], [1.5, 1.5, 25.5], 0.25);
    });
  },
  replaces: [scaleRing(B19_RING, 1.04)],
  facts: {
    Built: '1941, operations building with a four-storey concrete control tower at the south-west corner topped by an octagonal glass control room; wings added 1945 (some removed); contributing building',
    Model: OSM_NOTE + ' (building and tower part); storey heights estimated (≈21 m to the cab roof)'
  },
  sources: NAS_FACTS_SRC
};

// ------------------------------------------------------------ the seaplane ramps
// OSM “Seaplane Ramp 1–4” (NRHP district; 1940, 1940, 1941, 1941): concrete ramps from the
// apron down into the Seaplane Lagoon, ≈15 m wide, 43–54 m long, perpendicular to the north shore.
const RAMPS: {c: V2; len: number; y: number}[] = [
  {c: [-122.30645, 37.780295], len: 43, y: 1940},
  {c: [-122.304416, 37.780156], len: 54, y: 1940},
  {c: [-122.302376, 37.780027], len: 53, y: 1941},
  {c: [-122.300333, 37.779962], len: 43, y: 1941}
];
const seaplaneRamps: Landmark = {
  id: 'nas_alameda_seaplane_ramps',
  name: 'NAS Alameda seaplane ramps',
  kind: 'monument',
  built: [1940.3, 1940.9],
  end: 9999,
  anchor: RAMPS[1].c,
  build: b => {
    const z0 = seaZ(RAMPS[1].c);
    for (const r of RAMPS) {
      const p = lngLatToLocal(RAMPS[1].c, r.c);
      b.frame(p[0], p[1], 0, 3.4, () => {
        // slab sloping from the apron (north end) down below the waterline (south end)
        const top = Math.max(z0 + 3.2, dz(RAMPS[1].c, [p[0], p[1] + r.len / 2]));
        const bot = z0 - 1.2;
        const hx = 7.5;
        const hy = r.len / 2;
        b.color('#C4C0B5').quad([-hx, -hy, bot], [hx, -hy, bot], [hx, hy, top], [-hx, hy, top]);
        b.color('#9E9A90');
        for (const sx of [-1, 1]) b.quad([sx * hx, -hy, bot - 0.6], [sx * hx, hy, top - 0.6], [sx * hx, hy, top], [sx * hx, -hy, bot]);
      });
    }
  },
  facts: {
    Built: 'Seaplane Ramps 1–2 1940, 3–4 1941 (NRHP district structures): PBY Catalinas and PBM Mariners were hauled up from the lagoon to the apron in front of the seaplane hangars',
    Model: 'ramp outlines from OSM; slope and the ramps’ ends below the waterline estimated'
  },
  sources: NAS_FACTS_SRC
};

// ------------------------------------------------------------ aircraft carriers at the piers
// Piers 2 (387 × 38 m) and 3 (416 × 65 m) at 93.6° (OSM). The USS Hornet museum ship lies on
// the north side of Pier 3 since 1998 (eastbay.ts). The models below are generic class massing.

type Carrier = {L: number; beam: number; deck: number; deckW: number; angled: boolean; island: [number, number, number, number]; hull: string; deckCol: string};

/** Generic carrier at a berth: local y = bow direction, x to starboard; z from the waterline. */
function carrier(b: MeshBuilder, c: Carrier, zw: number) {
  const hl = c.L / 2;
  const hb = c.beam / 2;
  const hull: V2[] = [[-hb * 0.6, -hl], [hb * 0.6, -hl], [hb, -hl * 0.8], [hb, hl * 0.45], [hb * 0.55, hl * 0.85], [0, hl], [-hb * 0.55, hl * 0.85], [-hb, hl * 0.45], [-hb, -hl * 0.8]];
  b.color(c.hull).prism(hull, zw - 1, zw + c.deck * 0.55);
  const dw = c.deckW / 2;
  const upper: V2[] = [[-dw * 0.75, -hl * 1.01], [dw * 0.85, -hl * 1.01], [dw, -hl * 0.6], [dw, hl * 0.5], [dw * 0.5, hl * 0.93], [0, hl * 1.02], [-dw * 0.5, hl * 0.93], [-dw * 0.8, hl * 0.6], [-dw * 0.8, -hl * 0.6]];
  b.color('#7A8086').prism(scaleRing(upper, 0.97), zw + c.deck * 0.55, zw + c.deck - 0.9);
  // flight deck; the angled deck juts out to port amidships
  const deck: V2[] = c.angled
    ? [[-dw * 0.7, -hl * 1.01], [dw * 0.85, -hl * 1.01], [dw, -hl * 0.5], [dw, hl * 0.6], [dw * 0.45, hl * 1.0], [-dw * 0.45, hl * 1.0], [-dw * 0.55, hl * 0.62], [-dw * 1.55, hl * 0.1], [-dw * 1.6, -hl * 0.15], [-dw * 0.9, -hl * 0.55]]
    : [[-dw * 0.75, -hl * 1.01], [dw * 0.85, -hl * 1.01], [dw, -hl * 0.6], [dw, hl * 0.6], [dw * 0.5, hl * 1.0], [-dw * 0.5, hl * 1.0], [-dw, hl * 0.6], [-dw, -hl * 0.6]];
  b.color(c.deckCol).prism(deck, zw + c.deck - 0.9, zw + c.deck);
  b.color('#D8D8D0').box(c.angled ? -dw * 0.35 : 0, 0, zw + c.deck + 0.02, 0.6, c.L * 0.8, 0.05);
  // island on the starboard edge with mast
  const [iy, il, iw, ih] = c.island;
  b.color('#868C92').box(dw - iw / 2, iy, zw + c.deck, iw, il, ih);
  b.color('#9A9FA4').box(dw - iw / 2, iy + il * 0.15, zw + c.deck + ih, iw * 0.8, il * 0.5, 4);
  b.color('#5E6369').beam([dw - iw / 2, iy, zw + c.deck + ih + 4], [dw - iw / 2, iy, zw + c.deck + ih + 16], 0.8);
}

const PIER2: V2 = [-122.302578, 37.774165];
const PIER3: V2 = [-122.303552, 37.772315];

function carrierAt(id: string, name: string, pier: V2, side: number, pierHalfW: number, c: Carrier, built: [number, number], end: number, facts: Record<string, string>, sources: string[]): Landmark {
  // moored alongside: bow east (93.6°), starboard (island) against the pier when side = -1 (north of the pier ⇒ island to the south)
  const off = side * (pierHalfW + c.deckW / 2 + 4);
  const anchor = localToLngLat(pier, [Math.sin(((93.6 - 90) * Math.PI) / 180) * off, Math.cos(((93.6 - 90) * Math.PI) / 180) * off]);
  return {
    id,
    name,
    kind: 'monument',
    built,
    end,
    anchor,
    build: b => b.frame(0, 0, 0, 93.6, () => b.frame(0, 0, 0, side > 0 ? 0 : 180, () => carrier(b, c, seaZ(anchor)))),
    facts,
    sources
  };
}

const ESSEX: Carrier = {L: 266, beam: 28.4, deck: 16.4, deckW: 45, angled: true, island: [8, 38, 8, 10], hull: '#6A7076', deckCol: '#4F5459'};
const ENTERPRISE: Carrier = {L: 342, beam: 40.5, deck: 19, deckW: 78.4, angled: true, island: [30, 26, 12, 14], hull: '#6A7076', deckCol: '#4C5156'};
const NIMITZ: Carrier = {L: 332.8, beam: 40.8, deck: 19, deckW: 76.8, angled: true, island: [32, 30, 10, 14], hull: '#6A7076', deckCol: '#4C5156'};

const CARRIERS: Landmark[] = [
  carrierAt('nas_alameda_carrier_essex', 'Essex-class carrier at NAS Alameda (generic)', PIER3, 1, 32.5, ESSEX, [1946.0, 1946.05], 1976.0,
    {
      Presence: 'NAS Alameda was home port of carriers from WWII (the USS Hornet loaded the Doolittle raiders’ B-25s at its pier, April 1942) through the Vietnam era: Hancock and Oriskany (Essex class, both decommissioned 1976), Coral Sea, Ranger',
      Model: 'generic Essex-class (SCB-27C/125 angled deck) massing: 266 m × 28 m hull, 45 m flight deck; shown as one carrier on the north side of Pier 3 (the museum ship’s berth today), 1946–76 (berth and continuous presence are a simplification)'
    }, [SRC_NAS, WIKI + 'USS_Hancock_(CV-19)', WIKI + 'USS_Oriskany']),
  carrierAt('nas_alameda_carrier_enterprise', 'USS Enterprise (CVN-65) at NAS Alameda', PIER2, -1, 19, ENTERPRISE, [1965.85, 1965.9], 1990.7,
    {
      Presence: 'home-ported at NAS Alameda from November 1965 (Seventh Fleet) until her 1990 move to Norfolk',
      Size: '1,123 ft (342 m) overall, flight deck 257 ft (78 m) wide',
      Model: 'generic massing from the published dimensions; berth (north side of Pier 2) and island shape simplified; end month estimated'
    }, [WIKI + 'USS_Enterprise_(CVN-65)', SRC_NAS]),
  carrierAt('nas_alameda_carrier_carl_vinson', 'USS Carl Vinson (CVN-70) at NAS Alameda', PIER2, 1, 19, NIMITZ, [1983.82, 1983.85], 1997.05,
    {
      Presence: 'first home port NAS Alameda from Oct 28, 1983 (temporarily Bremerton 1990); the last carrier home-ported there — left for Bremerton, arriving Jan 17, 1997',
      Size: 'Nimitz class: 1,092 ft (333 m) overall, flight deck 252 ft (77 m)',
      Model: 'generic Nimitz-class massing; berth (south side of Pier 2) simplified'
    }, [WIKI + 'USS_Carl_Vinson', SRC_NAS])
];

// =================================================================== registry

export const PORTS: Landmark[] = [...OAKLAND_CRANES, ...OAKLAND_YARDS, ...HANGARS, controlTower, seaplaneRamps, ...CARRIERS];
