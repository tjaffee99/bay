/**
 * Buildings of the counties around San Francisco (pipeline/region_buildings.py):
 * ~2 M footprints in z13 map tiles (BAYT, same format as the SF file) loaded on demand
 * when zoomed in, decoded and triangulated in a small worker pool, and drawn with the
 * same time-aware BuildingLayer as San Francisco (construction frames, removal).
 */
import {TileLayer} from '@deck.gl/geo-layers';
import type {Layer} from '@deck.gl/core';
import {buildingsLayer, fromBinary, loadTileInWorker, type BuildingSet} from './buildings';

type Index = {
  z: number;
  tiles: {x: number; y: number; n: number}[];
  /** zoomed-out set: only buildings big enough to see at city scale */
  low?: {z: number; tiles: {x: number; y: number; n: number}[]};
};

let index: Index | null = null;
let have = new Set<string>();
let haveLow = new Set<string>();

export async function loadRegionIndex() {
  try {
    const r = await fetch('data/region-buildings/index.json');
    if (!r.ok || !(r.headers.get('content-type') ?? '').includes('json')) return; // not built yet
    index = (await r.json()) as Index;
    have = new Set(index.tiles.map(t => `${t.x}/${t.y}`));
    haveLow = new Set((index.low?.tiles ?? []).map(t => `${t.x}/${t.y}`));
  } catch (e) {
    console.warn('region buildings index', e);
  }
}

const FULL_FROM = 12.5;

function tileLayer(id: string, z: number, set: Set<string>, zoomOffset: number, year: number, quality: boolean, visible: boolean) {
  return new TileLayer<BuildingSet | null>({
    id,
    minZoom: z,
    maxZoom: z,
    tileSize: 256,
    zoomOffset,
    maxCacheSize: 160,
    visible,
    extent: [-123.2, 36.85, -121.2, 38.9],
    getTileData: async ({index: t}: any) => {
      if (!set.has(`${t.x}/${t.y}`)) return null;
      const file = await loadTileInWorker(new URL(`data/region-buildings/${z}/${t.x}/${t.y}.bin.gz`, document.baseURI).href);
      return fromBinary(file);
    },
    renderSubLayers: (props: any) => {
      const s = props.data as BuildingSet | null;
      if (!s) return null;
      return buildingsLayer(s, year, quality, false, `${props.id}-b`) as any;
    },
    updateTriggers: {renderSubLayers: [year, quality]}
  } as any);
}

/** Region buildings: every footprint in z13 tiles from zoom 12.5; zoomed out, only the
 *  large / tall ones (z11 tiles) — houses are below a pixel there and the suburban ground
 *  colour stands for them. */
export function regionBuildingLayers(year: number, zoom: number, quality: boolean): Layer[] {
  if (!index) return [];
  const out: Layer[] = [];
  if (index.low && zoom >= 9 && zoom < FULL_FROM)
    out.push(tileLayer('region-buildings-low', index.low.z, haveLow, 2, year, quality, true) as any);
  if (zoom >= FULL_FROM) out.push(tileLayer('region-buildings', index.z, have, 1, year, quality, true) as any);
  return out;
}
