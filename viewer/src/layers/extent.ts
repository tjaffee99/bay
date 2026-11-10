/**
 * The map's extent (pipeline/extent.py → data/map-extent.json): ten counties, Sonoma and Napa to Santa Cruz.
 * A signed-distance grid (km, positive inside) lets the terrain fade out over the last
 * few km inside the line, like the edge of an old game map, and lets other layers drop
 * what lies outside.
 */
type Extent = {ring: [number, number][]; fadeKm: number};

let ext: Extent | null = null;
let grid: Float32Array | null = null;
const G = {x0: 0, y0: 0, dx: 0.01, dy: 0.01, nx: 0, ny: 0};

const KX = 111.32 * Math.cos((37.75 * Math.PI) / 180);
const KY = 110.57;

function distToRing(x: number, y: number, ring: [number, number][]) {
  let best = Infinity;
  let inside = false;
  for (let i = 0, j = ring.length - 1; i < ring.length; j = i++) {
    const [xi, yi] = ring[i];
    const [xj, yj] = ring[j];
    if (yi > y !== yj > y && x < ((xj - xi) * (y - yi)) / (yj - yi) + xi) inside = !inside;
    // distance to the segment in km
    const ax = (x - xj) * KX;
    const ay = (y - yj) * KY;
    const bx = (xi - xj) * KX;
    const by = (yi - yj) * KY;
    const t = Math.max(0, Math.min(1, (ax * bx + ay * by) / (bx * bx + by * by || 1)));
    best = Math.min(best, Math.hypot(ax - t * bx, ay - t * by));
  }
  return inside ? best : -best;
}

export const extentReady: Promise<void> = (async () => {
  try {
    const r = await fetch('data/map-extent.json');
    if (!r.ok) return;
    const j = await r.json();
    ext = {ring: j.ring, fadeKm: j.fade_km ?? 4};
    const xs = ext.ring.map(p => p[0]);
    const ys = ext.ring.map(p => p[1]);
    G.x0 = Math.min(...xs) - 0.3;
    G.y0 = Math.min(...ys) - 0.3;
    G.nx = Math.ceil((Math.max(...xs) + 0.3 - G.x0) / G.dx) + 1;
    G.ny = Math.ceil((Math.max(...ys) + 0.3 - G.y0) / G.dy) + 1;
    grid = new Float32Array(G.nx * G.ny);
    for (let j2 = 0; j2 < G.ny; j2++)
      for (let i = 0; i < G.nx; i++) grid[j2 * G.nx + i] = distToRing(G.x0 + i * G.dx, G.y0 + j2 * G.dy, ext.ring);
  } catch (e) {
    console.warn('map extent', e);
  }
})();

/** Signed distance to the extent line in km (positive inside); +Infinity if unknown. */
export function extentDistance(lon: number, lat: number): number {
  if (!grid) return Infinity;
  const fx = (lon - G.x0) / G.dx;
  const fy = (lat - G.y0) / G.dy;
  if (fx < 0 || fy < 0 || fx >= G.nx - 1 || fy >= G.ny - 1) return -50;
  const i = Math.floor(fx);
  const j = Math.floor(fy);
  const tx = fx - i;
  const ty = fy - j;
  const g = (a: number, b: number) => grid![b * G.nx + a];
  return (g(i, j) * (1 - tx) + g(i + 1, j) * tx) * (1 - ty) + (g(i, j + 1) * (1 - tx) + g(i + 1, j + 1) * tx) * ty;
}

/** 0 outside the extent … 1 from fadeKm inside the line. */
export function extentFade(lon: number, lat: number): number {
  if (!ext) return 1;
  return Math.max(0, Math.min(1, extentDistance(lon, lat) / ext.fadeKm));
}

/** [west, south, east, north] with a margin, for the camera. */
export function extentBounds(): [number, number, number, number] | null {
  if (!ext) return null;
  const xs = ext.ring.map(p => p[0]);
  const ys = ext.ring.map(p => p[1]);
  return [Math.min(...xs) - 0.15, Math.min(...ys) - 0.12, Math.max(...xs) + 0.15, Math.max(...ys) + 0.12];
}
