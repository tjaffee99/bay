/**
 * Small committed tables from data/tables/*.csv (eras, events, population).
 * Imported at build time; missing files simply yield empty tables.
 */
// only the tables the viewer shows (the research tables are pipeline inputs: don't bundle them)
const files = import.meta.glob(['../../../data/tables/eras.csv', '../../../data/tables/events.csv', '../../../data/tables/population.csv'], {
  query: '?raw',
  import: 'default',
  eager: true
}) as Record<string, string>;

function table(name: string): Record<string, string>[] {
  const key = Object.keys(files).find(k => k.endsWith(`/${name}.csv`));
  return key ? parseCsv(files[key]) : [];
}

/** Minimal RFC-4180 CSV parser (quoted fields, embedded commas/newlines). */
export function parseCsv(text: string): Record<string, string>[] {
  const rows: string[][] = [];
  let row: string[] = [];
  let field = '';
  let quoted = false;
  for (let i = 0; i < text.length; i++) {
    const c = text[i];
    if (quoted) {
      if (c === '"') {
        if (text[i + 1] === '"') {
          field += '"';
          i++;
        } else quoted = false;
      } else field += c;
    } else if (c === '"') quoted = true;
    else if (c === ',') {
      row.push(field);
      field = '';
    } else if (c === '\n' || c === '\r') {
      if (c === '\r' && text[i + 1] === '\n') i++;
      row.push(field);
      field = '';
      if (row.some(f => f !== '')) rows.push(row);
      row = [];
    } else field += c;
  }
  if (field !== '' || row.length) {
    row.push(field);
    if (row.some(f => f !== '')) rows.push(row);
  }
  const [header, ...body] = rows;
  if (!header) return [];
  const keys = header.map(h => h.trim());
  return body.map(r => Object.fromEntries(keys.map((k, i) => [k, (r[i] ?? '').trim()])));
}

export type Era = {start: number; end: number; title: string; subtitle: string};
export type HistEvent = {
  year: number;
  month?: number;
  day?: number;
  title: string;
  description: string;
  lat?: number;
  lon?: number;
  zoom?: number;
};

export const eras: Era[] = table('eras')
  .map(r => ({start: +r.start_year, end: +r.end_year, title: r.title, subtitle: r.subtitle}))
  .filter(e => Number.isFinite(e.start))
  .sort((a, b) => a.start - b.start);

export const events: HistEvent[] = table('events')
  .map(r => ({
    year: +r.year,
    month: r.month ? +r.month : undefined,
    day: r.day ? +r.day : undefined,
    title: r.title,
    description: r.description,
    lat: r.lat ? +r.lat : undefined,
    lon: r.lon ? +r.lon : undefined,
    zoom: r.zoom ? +r.zoom : undefined
  }))
  .filter(e => Number.isFinite(e.year))
  .sort((a, b) => a.year - b.year);

/** Fractional year of an event (mid-month if the day is unknown). */
export function eventTime(e: HistEvent): number {
  if (!e.month) return e.year + 0.5;
  const day = e.day ?? 15;
  return e.year + (e.month - 1) / 12 + (day - 1) / 365;
}

type PopPoint = {year: number; pop: number; estimate: boolean};
const popRows = table('population');

function series(match: (area: string) => boolean): PopPoint[] {
  return popRows
    .filter(r => match((r.area || '').toLowerCase()))
    .map(r => ({year: +r.year, pop: +String(r.population).replace(/[, ]/g, ''), estimate: /estim/i.test(r.note || '')}))
    .filter(p => Number.isFinite(p.year) && p.pop > 0)
    .sort((a, b) => a.year - b.year);
}

export const sfPopulation = series(a => /san[ _-]?francisco/.test(a) && !/bay|county_total|9/.test(a)).filter(p => p.year >= 1844);

/** Pre-1844 rows describe different places (Yelamu, Presidio, Mission): shown as-is, not interpolated. */
const AREA_LABELS: Record<string, string> = {
  san_francisco: 'Yelamu Ohlone',
  presidio: 'Presidio of San Francisco',
  mission_dolores: 'Mission Dolores'
};
const earlyRows = popRows
  .map(r => ({year: +r.year, pop: +String(r.population).replace(/[, ]/g, ''), area: r.area, estimate: /estim/i.test(r.note || '')}))
  .filter(r => r.year < 1844 && r.pop > 0)
  .sort((a, b) => a.year - b.year);

export function populationLabelAt(year: number): {value: number; label: string} | null {
  if (sfPopulation.length && year >= sfPopulation[0].year) {
    const v = populationAt(year);
    return v == null ? null : {value: v, label: 'San Francisco'};
  }
  const r = [...earlyRows].reverse().find(e => e.year <= year);
  if (!r) return null;
  return {value: r.pop, label: `${AREA_LABELS[r.area] ?? r.area}${r.estimate ? ', estimate' : ''} (${r.year})`};
}

export function eraAt(year: number): Era | undefined {
  return eras.find(e => year >= e.start && year < e.end);
}

/** Log-linear interpolation between census points (populations grow ~exponentially). */
export function populationAt(year: number, pts: PopPoint[] = sfPopulation): number | null {
  if (!pts.length || year < pts[0].year) return null;
  const last = pts[pts.length - 1];
  if (year >= last.year) return last.pop;
  for (let i = 0; i < pts.length - 1; i++) {
    const a = pts[i];
    const b = pts[i + 1];
    if (year >= a.year && year < b.year) {
      const t = (year - a.year) / (b.year - a.year);
      return Math.exp(Math.log(a.pop) * (1 - t) + Math.log(b.pop) * t);
    }
  }
  return last.pop;
}

// ------------------------------------------------------------------ city populations
// pipeline/cities.py -> data/cities.json: city / town / CDP and county outlines with their
// census series (data/tables/population_places.csv). Zoomed in, the counter shows the
// place under the centre of the map; zoomed out, the whole mapped area.
type Ring = [number, number][];
type Place = {name: string; geoid: string; kind: string; rings: Ring[]; bbox?: [number, number, number, number]};
let cities: {places: Place[]; counties: Place[]; pop: Record<string, [number, number][]>; region: [number, number][]; region_label: string} | null =
  null;

export async function loadCities() {
  try {
    const r = await fetch('data/cities.json');
    if (!r.ok || !(r.headers.get('content-type') ?? '').includes('json')) return;
    cities = await r.json();
    for (const p of [...cities!.places, ...cities!.counties]) {
      const xs = p.rings.flat().map(q => q[0]);
      const ys = p.rings.flat().map(q => q[1]);
      p.bbox = [Math.min(...xs), Math.min(...ys), Math.max(...xs), Math.max(...ys)];
    }
  } catch (e) {
    console.warn('cities', e);
  }
}

function inRings(x: number, y: number, rings: Ring[]) {
  let inside = false;
  for (const ring of rings)
    for (let i = 0, j = ring.length - 1; i < ring.length; j = i++) {
      const [xi, yi] = ring[i];
      const [xj, yj] = ring[j];
      if (yi > y !== yj > y && x < ((xj - xi) * (y - yi)) / (yj - yi) + xi) inside = !inside;
    }
  return inside;
}

function placeAt(list: Place[], x: number, y: number) {
  return list.find(p => p.bbox && x >= p.bbox[0] && x <= p.bbox[2] && y >= p.bbox[1] && y <= p.bbox[3] && inRings(x, y, p.rings));
}

function seriesAt(year: number, s: [number, number][] | undefined) {
  if (!s || !s.length || year < s[0][0]) return null;
  return populationAt(year, s.map(([y, v]) => ({year: y, pop: v, estimate: false})));
}

/** The population to show for the year at this map centre and zoom. */
export function localPopulationAt(year: number, lon: number, lat: number, zoom: number): {value: number; label: string} | null {
  if (!cities) return populationLabelAt(year);
  if (zoom >= 11.5) {
    const city = placeAt(cities.places, lon, lat);
    if (city) {
      const v = seriesAt(year, cities.pop[city.geoid] ?? cities.pop[city.name]);
      if (v != null) return {value: v, label: city.name};
      if (city.name === 'San Francisco') return populationLabelAt(year);
    }
    const county = placeAt(cities.counties, lon, lat);
    if (county) {
      const v = seriesAt(year, cities.pop[`county:${county.name.replace(/ County$/, '')}`] ?? cities.pop[`county:${county.name}`]);
      if (v != null) return {value: v, label: county.name};
      if (county.name === 'San Francisco') return populationLabelAt(year);
    }
  }
  const v = seriesAt(year, cities.region);
  if (v != null) return {value: v, label: cities.region_label};
  return populationLabelAt(year);
}
