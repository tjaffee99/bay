/**
 * Ground elevation lookup (metres) from the pipeline's coarse elevation grids
 * (elevation-detail: San Francisco ~60 m; elevation-region: Bay Area ~240 m),
 * on the same Web-Mercator lattice as the terrain tiles. Used to stand
 * landmarks, labels and traffic on the hills.
 */
import {loadColumnar} from '../data/columnar';

type Grid = {elev: Int16Array; rows: number; cols: number; X0: number; Y0: number; res: number};
const grids: Grid[] = [];
const R = 6378137;

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
}

export function hasElevation() {
  return grids.length > 0;
}

/** Bilinear ground elevation in metres (0 where unknown / water). */
export function elevationAt(lon: number, lat: number): number {
  const X = (lon * Math.PI * R) / 180;
  const Y = R * Math.log(Math.tan(Math.PI / 4 + (lat * Math.PI) / 360));
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
