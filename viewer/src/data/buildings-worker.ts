/**
 * Web Worker: fetch + decode the SF buildings file and triangulate roofs.
 *
 * positions_delta: int32 1e-7° deltas within each feature (first vertex is
 * relative to the file origin) -> Float32 lon/lat offsets (XY, or XYZ when any
 * feature has a non-zero base height, e.g. OSM tower parts).
 * Triangulation: earcut per polygon (outer ring + holes), indices remapped to
 * the closed-ring vertex layout the side walls use.
 */
import {earcut} from '@math.gl/polygon';
import {loadColumnar} from './columnar';

self.onmessage = async (e: MessageEvent<{url: string; id?: number}>) => {
  const id = e.data.id;
  try {
    const file = await loadColumnar(e.data.url, f => (id === undefined ? (self as any).postMessage({progress: f}) : undefined));
    const c = file.columns;
    const n = file.header.counts.features;
    const scale = file.header.meta.position_scale ?? 1e-7;
    const starts = c.start_indices as Uint32Array;
    const delta = c.positions_delta as Int32Array;
    const valid = c.vertex_valid as Uint8Array;
    const base = c.base as Float32Array | undefined;
    const nv = starts[n];
    const hasZ = !!base && base.some(b => b > 0);
    const dim = hasZ ? 3 : 2;
    const positions = new Float32Array(nv * dim);

    // 1) decode positions
    for (let f = 0; f < n; f++) {
      let x = 0;
      let y = 0;
      const z = hasZ ? base![f] : 0;
      for (let v = starts[f]; v < starts[f + 1]; v++) {
        x += delta[v * 2];
        y += delta[v * 2 + 1];
        positions[v * dim] = x * scale;
        positions[v * dim + 1] = y * scale;
        if (hasZ) positions[v * dim + 2] = z;
      }
    }

    // 2) triangulate (open rings for earcut, then remap to closed layout)
    let indices = new Uint32Array(Math.ceil(nv * 3));
    let ni = 0;
    const tmp = new Float64Array(4096 * 2);
    let tmpBuf = tmp;
    const map: number[] = [];
    const holes: number[] = [];
    for (let f = 0; f < n; f++) {
      const s = starts[f];
      const e2 = starts[f + 1];
      if (e2 - s > tmpBuf.length / 2) tmpBuf = new Float64Array((e2 - s) * 2);
      map.length = 0;
      holes.length = 0;
      let k = 0;
      let ringStart = true;
      for (let v = s; v < e2; v++) {
        if (valid[v] === 0) {
          // closing vertex of a ring: skip it, next vertex starts a new ring
          ringStart = true;
          continue;
        }
        if (ringStart && k > 0) holes.push(k);
        ringStart = false;
        tmpBuf[k * 2] = positions[v * dim];
        tmpBuf[k * 2 + 1] = positions[v * dim + 1];
        map.push(v);
        k++;
      }
      if (k < 3) continue;
      const tri = earcut(tmpBuf.subarray(0, k * 2), holes.length ? holes : undefined, 2);
      if (ni + tri.length > indices.length) {
        const grown = new Uint32Array(Math.max(indices.length * 2, ni + tri.length));
        grown.set(indices);
        indices = grown;
      }
      for (let t = 0; t < tri.length; t++) indices[ni++] = map[tri[t]];
    }
    indices = indices.slice(0, ni);

    const out: Record<string, any> = {};
    const transfer: ArrayBuffer[] = [];
    for (const [k, v] of Object.entries(c)) {
      if (k === 'positions_delta') continue;
      const copy = (v as any).slice();
      out[k] = copy;
      transfer.push(copy.buffer);
    }
    out.positions = positions;
    out.indices = indices;
    transfer.push(positions.buffer, indices.buffer);
    (self as any).postMessage({id, header: file.header, columns: out, dim}, transfer);
  } catch (err) {
    (self as any).postMessage({id, error: String(err)});
  }
};
