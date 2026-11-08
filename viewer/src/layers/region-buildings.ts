/**
 * Buildings of the counties around San Francisco (pipeline/region_buildings.py):
 * ~2 M footprints in z13 map tiles (BAYT, same format as the SF file) loaded on demand
 * when zoomed in, decoded and triangulated in a small worker pool, and drawn with the
 * same time-aware BuildingLayer as San Francisco (construction frames, removal).
 */
import {TileLayer} from '@deck.gl/geo-layers';
import type {Layer} from '@deck.gl/core';
import {buildingsLayer, fromBinary, loadTileInWorker, type BuildingSet} from './buildings';

type Index = {z: number; tiles: {x: number; y: number; n: number; bbox: [number, number, number, number]}[]};

let index: Index | null = null;
let have = new Set<string>();

export async function loadRegionIndex() {
  try {
    const r = await fetch('data/region-buildings/index.json');
    if (!r.ok) return;
    index = (await r.json()) as Index;
    have = new Set(index.tiles.map(t => `${t.x}/${t.y}`));
  } catch (e) {
    console.warn('region buildings index', e);
  }
}

let live: TileLayer<BuildingSet | null> | null = null;
let liveYear = NaN;
let liveQuality = false;

/** Region building tiles (only drawn from zoom ~12.5: at city scale the land cover shows the built-up area). */
export function regionBuildingLayers(year: number, zoom: number, quality: boolean): Layer[] {
  if (!index || zoom < 12.5) return [];
  if (!live || liveYear !== year || liveQuality !== quality) {
    liveYear = year;
    liveQuality = quality;
    live = new TileLayer<BuildingSet | null>({
      id: 'region-buildings',
      minZoom: index.z,
      maxZoom: index.z,
      tileSize: 256,
      // load z13 tiles while the view is at zoom 12.5+ (a z13 tile is ~3.9 km wide)
      zoomOffset: 1,
      maxCacheSize: 160,
      extent: [-123.2, 36.85, -121.2, 38.9],
      getTileData: async ({index: t}: any) => {
        if (!have.has(`${t.x}/${t.y}`)) return null;
        const file = await loadTileInWorker(new URL(`data/region-buildings/${index!.z}/${t.x}/${t.y}.bin.gz`, document.baseURI).href);
        return fromBinary(file);
      },
      renderSubLayers: (props: any) => {
        const set = props.data as BuildingSet | null;
        if (!set) return null;
        return buildingsLayer(set, year, quality, false, `${props.id}-b`) as any;
      },
      updateTriggers: {renderSubLayers: [year, quality]}
    } as any);
  }
  return [live as any];
}
