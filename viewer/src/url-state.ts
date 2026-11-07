/** Shareable URL state: #year=1937&c=-122.4194,37.7749&z=13.5&p=55&b=-20 */
import type maplibregl from 'maplibre-gl';

export type HashState = {year?: number; center?: [number, number]; zoom?: number; pitch?: number; bearing?: number};

export function readHash(): HashState {
  const p = new URLSearchParams(location.hash.replace(/^#/, '') || location.search.replace(/^\?/, ''));
  const num = (k: string) => (p.has(k) && Number.isFinite(Number(p.get(k))) ? Number(p.get(k)) : undefined);
  const out: HashState = {year: num('year'), zoom: num('z') ?? num('zoom'), pitch: num('p'), bearing: num('b')};
  const c = p.get('c');
  if (c) {
    const [lng, lat] = c.split(',').map(Number);
    if (Number.isFinite(lng) && Number.isFinite(lat)) out.center = [lng, lat];
  } else if (num('lat') !== undefined && num('lng') !== undefined) {
    out.center = [num('lng')!, num('lat')!];
  }
  return out;
}

export function writeHash(map: maplibregl.Map, year: number) {
  const c = map.getCenter();
  const h =
    `year=${year.toFixed(1)}&c=${c.lng.toFixed(5)},${c.lat.toFixed(5)}` +
    `&z=${map.getZoom().toFixed(2)}&p=${map.getPitch().toFixed(0)}&b=${map.getBearing().toFixed(0)}`;
  history.replaceState(null, '', `#${h}`);
}
