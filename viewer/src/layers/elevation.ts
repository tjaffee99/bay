/**
 * Ground elevation lookup (metres) from the pipeline's coarse elevation grids
 * (elevation-detail: San Francisco ~60 m; elevation-region: Bay Area ~240 m),
 * on the same Web-Mercator lattice as the terrain tiles. Used to stand
 * landmarks, labels and traffic on the hills.
 *
 * Around every landmark model the pipeline also ships a patch of the full-resolution
 * grid the terrain mesh is cut from (elevation-spots, pipeline/landmark_ground.py):
 * the coarse grids were up to tens of metres off on steep ground, and Fort Ross, Lick
 * Observatory or Coit Tower stood partly inside their hills.
 */
import {loadColumnar} from '../data/columnar';

type Grid = {elev: Int16Array; rows: number; cols: number; X0: number; Y0: number; res: number};
const grids: Grid[] = [];
const R = 6378137;
// full-resolution patches around the landmarks, found through 2 km buckets
type Spot = {X0: number; Y0: number; res: number; rows: number; cols: number; off: number};
let spots: Spot[] = [];
let spotElev: Int16Array | null = null;
const BUCKET = 2000;
const buckets = new Map<number, number[]>();
const bucketKey = (bx: number, by: number) => bx * 100003 + by;

export async function loadElevation() {
  for (const name of ['detail', 'region']) {
    try {
      const f = await loadColumnar(`data/elevation-${name}.bin.gz`);
      grids.push({
        elev: f.columns.elev as Int16Array,
        rows: f.header.counts.rows,
        cols: f.header.counts.cols,
        X0: f.header.meta.X0,
        Y0: f.header.meta.Y0,
        res: f.header.meta.res
      });
    } catch (e) {
      console.warn('elevation', name, e);
    }
  }
  try {
    const f = await loadColumnar('data/elevation-spots.bin.gz');
    const p = f.columns.patch as Float64Array;
    spotElev = f.columns.elev as Int16Array;
    spots = [];
    for (let i = 0; i + 5 < p.length; i += 6) {
      const sp = {X0: p[i], Y0: p[i + 1], res: p[i + 2], rows: p[i + 3], cols: p[i + 4], off: p[i + 5]};
      const k = spots.push(sp) - 1;
      const bx0 = Math.floor(sp.X0 / BUCKET);
      const bx1 = Math.floor((sp.X0 + (sp.cols - 1) * sp.res) / BUCKET);
      const by0 = Math.floor((sp.Y0 - (sp.rows - 1) * sp.res) / BUCKET);
      const by1 = Math.floor(sp.Y0 / BUCKET);
      for (let bx = bx0; bx <= bx1; bx++)
        for (let by = by0; by <= by1; by++) {
          const key = bucketKey(bx, by);
          const list = buckets.get(key);
          if (list) list.push(k);
          else buckets.set(key, [k]);
        }
    }
  } catch (e) {
    console.warn('elevation spots', e);
  }
}

export function hasElevation() {
  return grids.length > 0;
}

/** Bilinear ground elevation in metres (0 where unknown / water). */
export function elevationAt(lon: number, lat: number): number {
  const X = (lon * Math.PI * R) / 180;
  const Y = R * Math.log(Math.tan(Math.PI / 4 + (lat * Math.PI) / 360));
  const near = spotElev ? buckets.get(bucketKey(Math.floor(X / BUCKET), Math.floor(Y / BUCKET))) : undefined;
  if (near) {
    for (const k of near) {
      const sp = spots[k];
      const c = (X - sp.X0) / sp.res;
      const r = (sp.Y0 - Y) / sp.res;
      if (c < 0 || r < 0 || c > sp.cols - 1 || r > sp.rows - 1) continue;
      const c0 = Math.min(Math.floor(c), sp.cols - 2);
      const r0 = Math.min(Math.floor(r), sp.rows - 2);
      const fx = c - c0;
      const fy = r - r0;
      const v = (rr: number, cc: number) => spotElev![sp.off + rr * sp.cols + cc] / 10;
      return (v(r0, c0) * (1 - fx) + v(r0, c0 + 1) * fx) * (1 - fy) + (v(r0 + 1, c0) * (1 - fx) + v(r0 + 1, c0 + 1) * fx) * fy;
    }
  }
  for (const g of grids) {
    const c = (X - g.X0) / g.res;
    const r = (g.Y0 - Y) / g.res;
    if (c < 0 || r < 0 || c > g.cols - 1 || r > g.rows - 1) continue;
    const c0 = Math.floor(c);
    const r0 = Math.floor(r);
    const c1 = Math.min(c0 + 1, g.cols - 1);
    const r1 = Math.min(r0 + 1, g.rows - 1);
    const fx = c - c0;
    const fy = r - r0;
    const v = (rr: number, cc: number) => Math.max(g.elev[rr * g.cols + cc] / 10, 0);
    return (v(r0, c0) * (1 - fx) + v(r0, c1) * fx) * (1 - fy) + (v(r1, c0) * (1 - fx) + v(r1, c1) * fx) * fy;
  }
  return 0;
}
