/** Constants and helpers shared by the decoration layer and the tile decoder (no WebGL: also used in a worker). */

export const DECO_ORIGIN: [number, number] = [-122.2, 37.85];

/** One kind's instances in one tile (positions relative to DECO_ORIGIN). */
export type DecoBatch = {kind: number; count: number; pos: Float32Array; scale: Float32Array; angle: Float32Array; years: Float32Array; color: Uint8Array};

/** Stable rank byte (0..255) of a position, ~3 m cells: stored in an instance's colour
 *  alpha; the deco shader keeps an instance while rank / 255 <= the zoom's keep share. */
export function rankByte(lon: number, lat: number) {
  let h = Math.imul(Math.round(lon * 3.3e4) | 0, 73856093) ^ Math.imul(Math.round(lat * 3.3e4) | 0, 19349663);
  h = Math.imul(h ^ (h >>> 13), 0x5bd1e995);
  h ^= h >>> 15;
  return (h >>> 0) % 256;
}

