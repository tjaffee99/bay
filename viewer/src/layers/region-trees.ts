/**
 * Street trees of the five counties (pipeline/region_trees.py): ~710k trees from 20 city /
 * county / campus inventories, dated by recorded planting date or trunk diameter, in z12
 * tiles (data/region-trees/). Loaded from zoom 12.5 for the tiles in view; the visible
 * tiles' trees are joined per form and drawn as three instanced layers (decision 18).
 */
import type {Layer} from '@deck.gl/core';
import {loadColumnar} from '../data/columnar';
import {extentDistance} from './extent';
import {decodeTrees, treesLayer, type TreeSet} from './trees';

type Index = {z: number; origin: [number, number]; tiles: {x: number; y: number; n: number}[]; attribution?: Record<string, string>};
let index: Index | null = null;
let have: Set<string> = new Set();
const cache = new Map<string, {data: any; count: number}[] | 'loading' | 'failed'>();
let merged: TreeSet | null = null;
let mergedKey = '';
let ready = false;
let redraw: (() => void) | null = null;

export async function loadRegionTreeIndex(onTile: () => void) {
  redraw = onTile;
  try {
    const r = await fetch('data/region-trees/index.json');
    if (!r.ok) return;
    index = (await r.json()) as Index;
    have = new Set(index.tiles.map(t => `${t.x}/${t.y}`));
  } catch (e) {
    console.warn('region trees', e);
  }
}

/** Call once the elevation lookups are loaded (trees stand on the terrain). */
export function regionTreesReady() {
  ready = true;
}

export function regionTreeAttribution(): Record<string, string> {
  return index?.attribution ?? {};
}

function tileXY(lon: number, lat: number, z: number) {
  const n = 2 ** z;
  const x = Math.floor(((lon + 180) / 360) * n);
  const r = (lat * Math.PI) / 180;
  const y = Math.floor(((1 - Math.log(Math.tan(r) + 1 / Math.cos(r)) / Math.PI) / 2) * n);
  return [x, y];
}

function tileCenter(x: number, y: number, z: number): [number, number] {
  const n = 2 ** z;
  const lon = ((x + 0.5) / n) * 360 - 180;
  const lat = (Math.atan(Math.sinh(Math.PI * (1 - (2 * (y + 0.5)) / n))) * 180) / Math.PI;
  return [lon, lat];
}

function merge(keys: string[]): TreeSet {
  const forms = [0, 1, 2].map(k => {
    const parts = keys.map(key => (cache.get(key) as {data: any; count: number}[])[k]).filter(p => p && p.count);
    const n = parts.reduce((a, p) => a + p.count, 0);
    const names = ['getPosition', 'getScale', 'getAngle', 'getYears', 'getColor'];
    const attrs: any = {};
    for (const nm of names) {
      const first = parts[0]?.data.attributes[nm];
      const size = first?.size ?? 1;
      const Ctor = (first?.value?.constructor ?? Float32Array) as any;
      const arr = new Ctor(n * size);
      let o = 0;
      for (const p of parts) {
        arr.set(p.data.attributes[nm].value, o * size);
        o += p.count;
      }
      attrs[nm] = {...(first ?? {}), value: arr, size};
    }
    return {count: n, data: {length: n, attributes: attrs}};
  });
  return {id: 'region', origin: index!.origin, growYears: 6, forms};
}

export function regionTreeLayers(year: number, zoom: number, bounds: [number, number, number, number]): Layer[] {
  if (!index || !ready) return [];
  // zoomed out: hidden but kept (the merged buffers stay on the GPU for the way back in)
  if (zoom < 12.5) return merged ? treesLayer(merged, year, zoom, 12.5).map(l => l.clone({visible: false})) : [];
  const z = index.z;
  const [x0, y1] = tileXY(bounds[0], bounds[1], z);
  const [x1, y0] = tileXY(bounds[2], bounds[3], z);
  const want: string[] = [];
  for (let x = x0; x <= x1; x++)
    for (let y = y0; y <= y1; y++) {
      const key = `${x}/${y}`;
      if (!have.has(key)) continue;
      const [lon, lat] = tileCenter(x, y, z);
      if (extentDistance(lon, lat) < -8) continue;
      want.push(key);
    }
  if (want.length > 24) return merged ? treesLayer(merged, year, zoom, 12.5) : [];
  for (const key of want) {
    if (cache.has(key)) continue;
    cache.set(key, 'loading');
    loadColumnar(`data/region-trees/${z}/${key}.bin.gz`)
      .then(f => {
        cache.set(key, decodeTrees(f));
        redraw?.();
      })
      .catch(e => {
        cache.set(key, 'failed');
        console.warn('region trees tile', key, e);
      });
  }
  const loaded = want.filter(k => typeof cache.get(k) === 'object').sort();
  const key = loaded.join(';');
  if (key !== mergedKey) {
    mergedKey = key;
    merged = loaded.length ? merge(loaded) : null;
  }
  // (they fade in over 12.5-13.1: tiles load from 12.5)
  return merged ? treesLayer(merged, year, zoom, 12.5) : [];
}
