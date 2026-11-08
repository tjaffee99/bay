/**
 * Transbay Terminal (1939–2010/11): the Bay Bridge railway terminal on Mission St
 * between First and Fremont, later the bus terminal; demolished 2010–11 for the
 * Salesforce Transit Center. Research: data/tables/transbay_terminal.md (HAER CA-32
 * photos and data pages, TRB 1991, TJPA EIR). The loop ramps are routes
 * (`transbay_terminal_loop` in data/manual/routes.csv), drawn by the roads layer.
 */
import type {Landmark} from './types';

const WP = 'https://en.wikipedia.org/wiki/San_Francisco_Transbay_Terminal';
const HAER = 'https://www.loc.gov/item/ca1352/';

// Local frame (bearing 45°): +y runs north-east along Mission St, +x south-east
// toward Natoma St; the origin is the middle of the Mission St frontage.
const LEN = 265; // 870 ft (TRB 1991)
const DEPTH = 85; // aerials HAER CA-32-70/-71: ~85–100 m; EIR lot depth 107 m is the upper bound
const DECK = 13.5; // track (later bus) deck: clears First and Fremont streets
const FIRST_Y = -55; // First St centreline (block First–Fremont 110 m, building centred on it)
const FREMONT_Y = 55;
const STREET = 25; // 82.5 ft right of way

const terminal: Landmark = {
  id: 'transbay_terminal_1939',
  name: 'Transbay Terminal',
  kind: 'building',
  built: [1937.57, 1939.04],
  end: 2011.0,
  anchor: [-122.3970315, 37.7900315],
  build: b => {
    const conc = '#D8D2C4';
    const shade = '#BDB6A8';
    const roof = '#C6C3BB';
    const glass = '#8E969C';
    b.frame(0, 0, 0, 45, () => {
      const h = LEN / 2;
      // three units between the streets that pass under the deck
      const units: [number, number][] = [
        [-h, FIRST_Y - STREET / 2],
        [FIRST_Y + STREET / 2, FREMONT_Y - STREET / 2],
        [FREMONT_Y + STREET / 2, h]
      ];
      for (const [y0, y1] of units) {
        b.color(conc).box(DEPTH / 2, (y0 + y1) / 2, 0, DEPTH, y1 - y0, DECK);
        // horizontal band of mezzanine windows along Mission St
        b.color(glass).box(-0.15, (y0 + y1) / 2, 6.2, 0.4, y1 - y0 - 6, 2.4);
      }
      // the deck spans the two streets on steel girders
      for (const yc of [FIRST_Y, FREMONT_Y]) b.color(shade).box(DEPTH / 2, yc, DECK - 3.2, DEPTH, STREET, 3.2);
      // Art Moderne front: tall entrance pavilion on the Mission St concourse
      b.color(conc).box(4, 0, 0, 8, 46, DECK + 4.5);
      for (let k = -4; k <= 4; k++) b.color(shade).box(-0.4, k * 4.6, 1.5, 0.8, 1.2, DECK + 2.5);
      b.color(glass).box(-0.2, 0, 0.5, 0.4, 14, 5.5);
      // deck parapet and the long platform sheds (corrugated, gabled, skylight bands)
      b.color(shade).prism(
        [
          [0, -h],
          [DEPTH, -h],
          [DEPTH, h],
          [0, h]
        ],
        DECK,
        DECK + 1.1,
        {top: false}
      );
      const sheds = 6;
      const w = (DEPTH - 6) / sheds;
      for (let i = 0; i < sheds; i++) {
        const cx = 3 + w * (i + 0.5);
        b.color(roof).box(cx, 0, DECK, w - 1.6, LEN - 14, 5.6);
        b.color(i % 2 ? roof : '#D3D1CB').gable(cx, 0, w - 1.6, LEN - 14, DECK + 5.6, 1.6, true);
      }
    });
  },
  facts: {
    Opened: 'dedicated 14 Jan 1939; Key System, SP Interurban Electric and Sacramento Northern trains from 15 Jan 1939',
    Later: 'trains ended 20 Apr 1958; rebuilt as a bus terminal (all lines by Jul 1959, Greyhound 1960)',
    Closed: 'last bus 7 Aug 2010; demolished Dec 2010 – Sep 2011 for the Salesforce Transit Center',
    Architects: 'Timothy Pflueger, Arthur Brown Jr., John J. Donovan (Art Moderne)',
    Size: '870 ft (265 m) long, straddling First and Fremont streets; third-level track deck with six tracks',
    Model: 'LOW CONFIDENCE: depth (~85 m), deck height (~13.5 m) and shed roofs estimated from HAER aerial photos CA-32-70/-71/-130'
  },
  sources: [WP, HAER, 'https://onlinepubs.trb.org/Onlinepubs/trr/1991/1308/1308-015.pdf', 'https://www.tjpa.org/media/30677/download']
};

export const TRANSBAY: Landmark[] = [terminal];
