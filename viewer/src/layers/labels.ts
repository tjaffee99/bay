/**
 * Era-accurate place labels (data/tables/places.csv): each name shows only in
 * the years it was in use, by zoom tier, standing above the terrain.
 *
 * Decluttering is done here on the CPU, once per quarter zoom level, in Web
 * Mercator metres (which map 1:1 to screen pixels at a given zoom): labels are
 * taken greedily by tier priority and skipped if their box would overlap one
 * already placed. Unlike deck.gl's GPU CollisionFilterExtension this doesn't
 * re-run every frame while panning, so labels don't flicker in and out.
 */
import {TextLayer} from '@deck.gl/layers';
import {parseCsv} from '../data/tables';
import {elevationAt} from './elevation';

const files = import.meta.glob('../../../data/tables/places.csv', {query: '?raw', import: 'default', eager: true}) as Record<string, string>;

type Place = {name: string; tier: string; lon: number; lat: number; start: number; end: number; z: number; mx: number; my: number; text: string};

const R = 6378137;
const mercX = (lon: number) => (lon * Math.PI * R) / 180;
const mercY = (lat: number) => R * Math.log(Math.tan(Math.PI / 4 + (lat * Math.PI) / 360));

// zoom band per tier [fade-in start, fully visible, fully visible until, gone]
const TIERS: Record<string, {zoom: [number, number, number, number]; size: number; color: number[]; italic?: boolean; priority: number; caps?: boolean}> = {
  region: {zoom: [6, 7, 9.2, 10.2], size: 17, color: [70, 64, 56], priority: 6, caps: true},
  city: {zoom: [7.6, 8.4, 13.2, 14.2], size: 19, color: [40, 36, 31], priority: 5},
  town: {zoom: [9.4, 10.2, 13.8, 14.8], size: 15, color: [50, 45, 39], priority: 4},
  landscape: {zoom: [11, 11.8, 16, 17], size: 14, color: [96, 76, 52], italic: true, priority: 2},
  neighborhood: {zoom: [12.2, 12.9, 16.2, 17.2], size: 15, color: [52, 47, 40], priority: 3, caps: true},
  historic: {zoom: [12.8, 13.4, 16.5, 17.5], size: 14, color: [120, 64, 44], italic: true, priority: 1},
  // city parks (pipeline/ground_detail.py -> park-labels.json): big ones earlier
  park_major: {zoom: [12.3, 12.9, 16.5, 17.5], size: 14, color: [62, 104, 52], italic: true, priority: 3},
  park: {zoom: [14.3, 14.9, 17.5, 18.5], size: 13, color: [62, 104, 52], italic: true, priority: 0},
  // military / industrial and vanished large sites (refineries, shipyards, bases, quarries,
  // racetracks, amusement parks): over the years they stood
  site: {zoom: [11.8, 12.5, 16.5, 17.5], size: 13, color: [104, 80, 64], italic: true, priority: 2},
  // contact-era Native villages (Ohlone, Bay and Coast Miwok), 1769 until they emptied
  village: {zoom: [10.2, 10.9, 16.5, 17.5], size: 13, color: [120, 64, 44], italic: true, priority: 2},
  // BART and Muni Metro stations (pipeline/transit.py -> transit-stations.json)
  station: {zoom: [12.4, 13.0, 17.5, 18.5], size: 12, color: [32, 66, 128], priority: 1},
  station_muni: {zoom: [14.3, 14.9, 17.5, 18.5], size: 12, color: [150, 40, 40], priority: 0}
};

let places: Place[] = [];

export function loadPlaces() {
  const text = Object.values(files)[0];
  if (!text) return;
  places = parseCsv(text)
    .map(r => ({
      name: r.name,
      tier: r.tier,
      lon: +r.lon,
      lat: +r.lat,
      start: +r.year_start,
      end: r.year_end ? +r.year_end : 9999,
      z: 0,
      mx: mercX(+r.lon),
      my: mercY(+r.lat),
      text: TIERS[r.tier]?.caps ? r.name.toUpperCase() : r.name
    }))
    .filter(p => p.name && Number.isFinite(p.lon) && Number.isFinite(p.lat) && TIERS[p.tier]);
}

/** City park labels (generated): park_major for parks of 8 ha or more. */
export async function loadParkLabels() {
  try {
    const res = await fetch('data/park-labels.json');
    if (!res.ok) return;
    const rows = (await res.json()) as {name: string; lon: number; lat: number; start: number; end?: number; ha: number; tier?: string}[];
    // the same name is skipped only near an existing label (many towns have a "Central Park")
    const byName = new Map<string, {lon: number; lat: number}[]>();
    for (const p of places) (byName.get(p.name) ?? byName.set(p.name, []).get(p.name)!).push(p);
    const near = (r: {name: string; lon: number; lat: number}) =>
      (byName.get(r.name) ?? []).some(p => Math.abs(p.lon - r.lon) < 0.02 && Math.abs(p.lat - r.lat) < 0.02);
    for (const r of rows) {
      if (near(r) || (keepFn && !keepFn(r.lon, r.lat))) continue;
      const tier = r.tier === 'site' || r.tier === 'village' ? r.tier : r.ha >= 8 ? 'park_major' : 'park';
      places.push({name: r.name, tier, lon: r.lon, lat: r.lat, start: r.start, end: r.end ?? 9999, z: 0, mx: mercX(r.lon), my: mercY(r.lat), text: r.name});
      (byName.get(r.name) ?? byName.set(r.name, []).get(r.name)!).push(r);
    }
    placedKey = '';
  } catch (e) {
    console.warn('park labels', e);
  }
}

/** Station names, each from its opening year (a shared BART/Muni station is labelled once). */
export function addStationLabels(rows: {name: string; system: string; lon: number; lat: number; start: number; end: number;
  names?: {name: string; start: number; end: number}[]}[]) {
  const bart = rows.filter(r => r.system === 'bart');
  for (const r of rows) {
    if (keepFn && !keepFn(r.lon, r.lat)) continue;
    if (r.system !== 'bart' && bart.some(b => Math.hypot(b.lon - r.lon, b.lat - r.lat) < 0.0015)) continue;
    const tier = r.system === 'bart' ? 'station' : 'station_muni';
    // a renamed station is labelled with the name in use that year (Oakland West, Berkeley, ...)
    for (const n of r.names ?? [{name: r.name, start: r.start, end: r.end}])
      places.push({name: n.name, tier, lon: r.lon, lat: r.lat, start: n.start, end: n.end, z: 0, mx: mercX(r.lon), my: mercY(r.lat), text: n.name});
  }
  placedKey = '';
}

/** Drop labels outside the map's extent (or in its faded margin). */
let keepFn: ((lon: number, lat: number) => boolean) | null = null;
export function dropLabels(keep: (lon: number, lat: number) => boolean) {
  keepFn = keep;
  places = places.filter(p => keep(p.lon, p.lat));
  placedKey = '';
}

/** Call once elevation is loaded. */
export function placeLabelsOnTerrain() {
  for (const p of places) p.z = elevationAt(p.lon, p.lat) + (p.tier === 'landscape' ? 25 : 45);
}

function zoomAlpha(zoom: number, band: [number, number, number, number]) {
  const [a, b, c, d] = band;
  if (zoom <= a || zoom >= d) return 0;
  if (zoom < b) return (zoom - a) / (b - a);
  if (zoom > c) return (d - zoom) / (d - c);
  return 1;
}

/** Changes only when some tier's zoom fade changes (used to skip re-renders while zooming). */
export function labelZoomKey(zoom: number) {
  return Object.values(TIERS)
    .map(t => Math.round(zoomAlpha(zoom, t.zoom) * 20))
    .join(',') + `|${Math.round(zoom * 4)}`;
}

const ORDER = Object.entries(TIERS).sort((a, b) => b[1].priority - a[1].priority);

/** lon/lat → screen pixels for the current camera (set by main.ts from MapLibre). */
let project: ((lon: number, lat: number) => [number, number]) | null = null;
let screen: [number, number] = [1, 1];
export function setLabelProjector(fn: (lon: number, lat: number) => [number, number], size: [number, number]) {
  project = fn;
  screen = size;
  placedKey = '';
}

/** Labels shown at this year and zoom, decluttered in screen space for the camera at
 *  rest; kept while it moves (no flicker), recomputed on moveend / zoom step / year. */
let placedKey = '';
let placed: Record<string, Place[]> = {};
function declutter(year: number, zoom: number) {
  const visibleNow = places.filter(p => year >= p.start && year < p.end);
  const key = `${Math.round(zoom * 4)}|${visibleNow.length}|${Math.floor(year)}`;
  if (key === placedKey) return placed;
  placedKey = key;
  const mpp = (2 * Math.PI * R) / (512 * 2 ** zoom); // fallback: flat mercator metres per pixel
  const toScreen = (p: Place): [number, number] => (project ? project(p.lon, p.lat) : [p.mx / mpp, -p.my / mpp]);
  const [W, H] = screen;
  const margin = 300;
  const boxes: [number, number, number, number][] = [];
  const next: Record<string, Place[]> = {};
  for (const [tier, cfg] of ORDER) {
    const out: Place[] = [];
    if (zoomAlpha(zoom, cfg.zoom) > 0.01) {
      for (const p of visibleNow) {
        if (p.tier !== tier) continue;
        const [x, y] = toScreen(p);
        if (project && (x < -margin || y < -margin || x > W + margin || y > H + margin)) continue;
        // estimated text box in pixels, with padding
        const hw = (p.text.length * cfg.size * (cfg.caps ? 0.68 : 0.5)) / 2 + 10;
        const hh = (cfg.size * 1.2) / 2 + 6;
        let hit = false;
        for (const o of boxes) {
          if (x - hw < o[2] && x + hw > o[0] && y - hh < o[3] && y + hh > o[1]) {
            hit = true;
            break;
          }
        }
        if (hit) continue;
        boxes.push([x - hw, y - hh, x + hw, y + hh]);
        out.push(p);
      }
    }
    // keep the previous array when nothing changed so deck doesn't re-layout the text
    const prev = placed[tier];
    next[tier] = prev && prev.length === out.length && prev.every((q, i) => q === out[i]) ? prev : out;
  }
  placed = next;
  return placed;
}

export function labelLayers(year: number, zoom: number) {
  const out: TextLayer[] = [];
  for (const [tier, cfg] of Object.entries(TIERS)) {
    const alpha = zoomAlpha(zoom, cfg.zoom);
    if (alpha <= 0.01) continue;
    const data = declutter(year, zoom)[tier] ?? [];
    if (!data.length) continue;
    out.push(
      new TextLayer<Place>({
        id: `labels-${tier}`,
        data,
        getPosition: (p: Place) => [p.lon, p.lat, p.z],
        getText: (p: Place) => p.text,
        getSize: cfg.size,
        getColor: [cfg.color[0], cfg.color[1], cfg.color[2], Math.round(255 * alpha)],
        fontFamily: `'Cormorant Garamond', 'EB Garamond', Georgia, serif`,
        fontWeight: cfg.italic ? 500 : 600,
        fontSettings: {sdf: true, fontSize: 64, buffer: 8},
        outlineWidth: 5,
        outlineColor: [250, 246, 238, Math.round(225 * alpha)],
        characterSet: 'auto',
        billboard: true,
        sizeUnits: 'pixels',
        getTextAnchor: 'middle',
        getAlignmentBaseline: 'center',
        characterSpacing: cfg.caps ? 0.08 : 0,
        pickable: false,
        shadowEnabled: false,
        parameters: {depthCompare: 'always'} as any,
        updateTriggers: {getColor: [alpha], getPosition: [places.length && places[0].z]}
      } as any)
    );
  }
  return out;
}
