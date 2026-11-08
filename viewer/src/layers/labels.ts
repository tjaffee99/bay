/**
 * Era-accurate place labels (data/tables/places.csv): each name shows only in
 * the years it was in use, by zoom tier, standing above the terrain, with a
 * collision filter so labels don't pile up (bigger tiers win).
 */
import {TextLayer} from '@deck.gl/layers';
import {CollisionFilterExtension} from '@deck.gl/extensions';
import {parseCsv} from '../data/tables';
import {elevationAt} from './elevation';

const files = import.meta.glob('../../../data/tables/places.csv', {query: '?raw', import: 'default', eager: true}) as Record<string, string>;

type Place = {name: string; tier: string; lon: number; lat: number; start: number; end: number; z: number};

// zoom band per tier [fade-in start, fully visible, fully visible until, gone]
const TIERS: Record<string, {zoom: [number, number, number, number]; size: number; color: number[]; italic?: boolean; priority: number; caps?: boolean}> = {
  region: {zoom: [6, 7, 9.2, 10.2], size: 17, color: [70, 64, 56], priority: 6, caps: true},
  city: {zoom: [7.6, 8.4, 13.2, 14.2], size: 19, color: [40, 36, 31], priority: 5},
  town: {zoom: [9.4, 10.2, 13.8, 14.8], size: 15, color: [50, 45, 39], priority: 4},
  landscape: {zoom: [11, 11.8, 16, 17], size: 14, color: [96, 76, 52], italic: true, priority: 2},
  neighborhood: {zoom: [12.2, 12.9, 16.2, 17.2], size: 15, color: [52, 47, 40], priority: 3, caps: true},
  historic: {zoom: [12.8, 13.4, 16.5, 17.5], size: 14, color: [120, 64, 44], italic: true, priority: 1}
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
      z: 0
    }))
    .filter(p => p.name && Number.isFinite(p.lon) && Number.isFinite(p.lat) && TIERS[p.tier]);
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

const collision = new CollisionFilterExtension();

// keep the same data array while the visible set is unchanged, so re-renders
// (traffic animation, zoom) don't re-layout the text
const cache: Record<string, Place[]> = {};
function visible(tier: string, year: number) {
  const next = places.filter(p => p.tier === tier && year >= p.start && year < p.end);
  const prev = cache[tier];
  if (prev && prev.length === next.length && prev.every((p, i) => p === next[i])) return prev;
  return (cache[tier] = next);
}

export function labelLayers(year: number, zoom: number) {
  const out: TextLayer[] = [];
  for (const [tier, cfg] of Object.entries(TIERS)) {
    const alpha = zoomAlpha(zoom, cfg.zoom);
    if (alpha <= 0.01) continue;
    const data = visible(tier, year);
    if (!data.length) continue;
    out.push(
      new TextLayer<Place>({
        id: `labels-${tier}`,
        data,
        getPosition: (p: Place) => [p.lon, p.lat, p.z],
        getText: (p: Place) => (cfg.caps ? p.name.toUpperCase() : p.name),
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
        parameters: {depthCompare: 'always'} as any,
        extensions: [collision],
        collisionGroup: 'labels',
        getCollisionPriority: cfg.priority,
        collisionTestProps: {sizeScale: 2.0},
        updateTriggers: {getColor: [alpha], getPosition: [places.length && places[0].z]}
      } as any)
    );
  }
  return out;
}
