/**
 * Terrain tile worker: fetches, unpacks and decodes a tile (mesh attributes + tree /
 * farm-building instances) off the main thread and hands the typed arrays over without
 * copying. The triangle indices are not sent: every tile of a size shares one array, which
 * the main thread keeps itself.
 */
import {loadTerrainTile} from './terrain-tile';

type Req = {id: number; z: number; x: number; y: number};

self.onmessage = async (e: MessageEvent<Req>) => {
  const {id, z, x, y} = e.data;
  try {
    const c = await loadTerrainTile(z, x, y);
    if (!c) {
      (self as any).postMessage({id, content: null});
      return;
    }
    const m = c.mesh;
    const mesh = {...m, indices: undefined};
    const transfer: ArrayBuffer[] = [m.positions, m.normals, m.uv, m.covers, m.cover4, m.years, m.skirt, m.fade].map(a => a.buffer as ArrayBuffer);
    for (const b of c.deco) transfer.push(b.pos.buffer as ArrayBuffer, b.scale.buffer as ArrayBuffer, b.angle.buffer as ArrayBuffer, b.years.buffer as ArrayBuffer, b.color.buffer as ArrayBuffer);
    (self as any).postMessage({id, content: {mesh, deco: c.deco}}, [...new Set(transfer)]);
  } catch (err) {
    (self as any).postMessage({id, error: String(err)});
  }
};
