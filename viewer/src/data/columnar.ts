/**
 * Loader for the pipeline's compact columnar binary format ("BAYT").
 *
 *   bytes 0-3   magic "BAYT"
 *   bytes 4-7   uint32 header length H (bytes of UTF-8 JSON)
 *   bytes 8..   JSON header, padded with spaces to a multiple of 8
 *   then        column data; each column starts at `offset` (relative to the
 *               start of the data block) and is 8-byte aligned
 *
 * Header: { version, origin: [lon, lat], counts: {...}, meta: {...},
 *           columns: [{ name, dtype, length, offset }] }
 * dtype: f32 | f64 | u32 | i32 | u16 | i16 | u8
 * shuffle: true when the column's bytes were stored byte-plane by byte-plane
 *          (all first bytes, then all second bytes, ...) for better gzip.
 *
 * Files are gzip-compressed on disk (.bin.gz); if the server already decoded
 * the gzip (Content-Encoding) we detect that from the magic bytes.
 */

export type Columns = Record<string, Float32Array | Float64Array | Uint32Array | Int32Array | Uint16Array | Int16Array | Uint8Array>;

export type ColumnarFile = {
  header: {
    version: number;
    origin: [number, number];
    counts: Record<string, number>;
    meta: Record<string, any>;
    columns: {name: string; dtype: string; length: number; offset: number; shuffle?: boolean}[];
  };
  columns: Columns;
};

const CTORS: Record<string, any> = {
  f32: Float32Array,
  f64: Float64Array,
  u32: Uint32Array,
  i32: Int32Array,
  u16: Uint16Array,
  i16: Int16Array,
  u8: Uint8Array
};

async function gunzip(buf: ArrayBuffer): Promise<ArrayBuffer> {
  const bytes = new Uint8Array(buf);
  if (bytes[0] !== 0x1f || bytes[1] !== 0x8b) return buf; // already decoded
  const stream = new Blob([bytes]).stream().pipeThrough(new DecompressionStream('gzip'));
  return await new Response(stream).arrayBuffer();
}

export async function loadColumnar(url: string, onProgress?: (frac: number) => void): Promise<ColumnarFile> {
  const res = await fetch(url);
  if (!res.ok) throw new Error(`${url}: HTTP ${res.status}`);
  let raw: ArrayBuffer;
  const total = Number(res.headers.get('content-length')) || 0;
  if (onProgress && res.body && total) {
    const reader = res.body.getReader();
    const chunks: Uint8Array[] = [];
    let got = 0;
    for (;;) {
      const {done, value} = await reader.read();
      if (done) break;
      chunks.push(value);
      got += value.length;
      onProgress(Math.min(1, got / total));
    }
    const all = new Uint8Array(got);
    let o = 0;
    for (const c of chunks) {
      all.set(c, o);
      o += c.length;
    }
    raw = all.buffer;
  } else {
    raw = await res.arrayBuffer();
  }
  const buf = await gunzip(raw);
  const view = new DataView(buf);
  const magic = String.fromCharCode(view.getUint8(0), view.getUint8(1), view.getUint8(2), view.getUint8(3));
  if (magic !== 'BAYT') throw new Error(`${url}: bad magic ${magic}`);
  const headerLen = view.getUint32(4, true);
  const header = JSON.parse(new TextDecoder().decode(new Uint8Array(buf, 8, headerLen)));
  const dataStart = 8 + Math.ceil(headerLen / 8) * 8;
  const columns: Columns = {};
  for (const c of header.columns) {
    const Ctor = CTORS[c.dtype];
    if (c.shuffle) {
      const size = Ctor.BYTES_PER_ELEMENT;
      const src = new Uint8Array(buf, dataStart + c.offset, c.length * size);
      const dst = new Uint8Array(c.length * size);
      for (let b = 0; b < size; b++) {
        const plane = b * c.length;
        for (let i = 0; i < c.length; i++) dst[i * size + b] = src[plane + i];
      }
      columns[c.name] = new Ctor(dst.buffer, 0, c.length);
    } else {
      columns[c.name] = new Ctor(buf, dataStart + c.offset, c.length);
    }
  }
  return {header, columns};
}
