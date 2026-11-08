/**
 * Ground detail (pipeline/ground_detail.py): golf fairways, greens, tees and bunkers,
 * sports pitches, running tracks, playgrounds, plazas, gardens and lawns — real
 * OpenStreetMap outlines draped on the terrain, each from its (estimated) year.
 */
import {COORDINATE_SYSTEM} from '@deck.gl/core';
import type {Layer} from '@deck.gl/core';
import {SolidPolygonLayer} from '@deck.gl/layers';
import {loadColumnar} from '../data/columnar';
import {TimeExtension} from './time-extension';

// kinds — keep in sync with pipeline/ground_detail.py
const COLORS: [number, number, number][] = [
  [134, 178, 92], // 0 fairway
  [112, 186, 88], // 1 green
  [124, 176, 90], // 2 tee
  [104, 146, 76], // 3 rough
  [226, 214, 172], // 4 bunker
  [138, 174, 98], // 5 driving range
  [116, 164, 86], // 6 pitch
  [182, 102, 82], // 7 running track
  [210, 190, 150], // 8 playground
  [150, 166, 112], // 9 dog park
  [206, 202, 194], // 10 plaza / pedestrian paving
  [118, 152, 88], // 11 garden / flowerbed
  [128, 166, 94] // 12 lawn
];

let data: any = null;
let origin: [number, number] = [0, 0];
let colors: Uint8Array | null = null;
let years: Float32Array | null = null;
const fade = new TimeExtension({mode: 'fade'});

export async function loadGroundDetail() {
  const f = await loadColumnar('data/ground-detail.bin.gz');
  const c = f.columns;
  const n = f.header.counts.polygons;
  origin = f.header.origin;
  const kind = c.kind as Uint8Array;
  years = c.years as Float32Array;
  colors = new Uint8Array(n * 4);
  for (let i = 0; i < n; i++) {
    const base = COLORS[kind[i]] ?? COLORS[12];
    const v = ((i * 2654435761) >>> 0) % 13 - 6; // slight variation, like real turf
    colors.set([base[0] + v, base[1] + v, base[2] + v, 255], i * 4);
  }
  data = {length: n, startIndices: c.start_indices, attributes: {getPolygon: {value: c.positions, size: 3}}};
}

export function groundDetailLayers(year: number, zoom: number): Layer[] {
  if (!data || zoom < 13) return [];
  const col = colors!;
  const yrs = years!;
  return [
    new SolidPolygonLayer({
      id: 'ground-detail',
      data,
      positionFormat: 'XYZ',
      _normalize: false,
      coordinateSystem: COORDINATE_SYSTEM.LNGLAT_OFFSETS,
      coordinateOrigin: [origin[0], origin[1], 0],
      extruded: false,
      getFillColor: (_: any, {index, target}: any) => {
        target[0] = col[index * 4];
        target[1] = col[index * 4 + 1];
        target[2] = col[index * 4 + 2];
        target[3] = 255;
        return target;
      },
      extensions: [fade],
      getYears: (_: any, {index, target}: any) => {
        target[0] = yrs[index * 2];
        target[1] = yrs[index * 2 + 1];
        return target;
      },
      currentYear: year,
      growYears: 1.5,
      shrinkYears: 0.5,
      pickable: false,
      shadowEnabled: false,
      parameters: {depthBias: -2, depthBiasSlopeScale: -1} as any
    } as any) as any
  ];
}

// ------------------------------------------------------------------ airports
// pipeline/airports.py: runways, taxiways and aprons (OSM via Overture), from each
// airport's opening year (and not before its fill); visible from city scale.
const AIRPORT_COLORS: [number, number, number][] = [
  [104, 106, 110], // 0 runway (asphalt)
  [124, 126, 128], // 1 taxiway
  [176, 176, 172] // 2 apron (concrete)
];
let apData: any = null;
let apOrigin: [number, number] = [0, 0];
let apColors: Uint8Array | null = null;
let apYears: Float32Array | null = null;

export async function loadAirports() {
  try {
    const f = await loadColumnar('data/airports.bin.gz');
    const c = f.columns;
    const n = f.header.counts.polygons;
    apOrigin = f.header.origin;
    const kind = c.kind as Uint8Array;
    apYears = c.years as Float32Array;
    apColors = new Uint8Array(n * 4);
    for (let i = 0; i < n; i++) apColors.set([...(AIRPORT_COLORS[kind[i]] ?? AIRPORT_COLORS[1]), 255], i * 4);
    apData = {length: n, startIndices: c.start_indices, attributes: {getPolygon: {value: c.positions, size: 3}}};
  } catch (e) {
    console.warn('airports', e);
  }
}

export function airportLayers(year: number, zoom: number): Layer[] {
  if (!apData || zoom < 9.5) return [];
  const col = apColors!;
  const yrs = apYears!;
  return [
    new SolidPolygonLayer({
      id: 'airports',
      data: apData,
      positionFormat: 'XYZ',
      _normalize: false,
      coordinateSystem: COORDINATE_SYSTEM.LNGLAT_OFFSETS,
      coordinateOrigin: [apOrigin[0], apOrigin[1], 0],
      extruded: false,
      getFillColor: (_: any, {index, target}: any) => {
        target[0] = col[index * 4];
        target[1] = col[index * 4 + 1];
        target[2] = col[index * 4 + 2];
        target[3] = 255;
        return target;
      },
      extensions: [fade],
      getYears: (_: any, {index, target}: any) => {
        target[0] = yrs[index * 2];
        target[1] = yrs[index * 2 + 1];
        return target;
      },
      currentYear: year,
      growYears: 1,
      shrinkYears: 0.5,
      pickable: false,
      shadowEnabled: false,
      parameters: {depthBias: -2, depthBiasSlopeScale: -1} as any
    } as any) as any
  ];
}
