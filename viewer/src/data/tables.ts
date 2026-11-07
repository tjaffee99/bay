/**
 * Small committed tables from data/tables/*.csv (eras, events, population).
 * Imported at build time; missing files simply yield empty tables.
 */
const files = import.meta.glob('../../../data/tables/*.csv', {query: '?raw', import: 'default', eager: true}) as Record<string, string>;

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

export const sfPopulation = series(a => /san[ _-]?francisco/.test(a) && !/bay|county_total|9/.test(a));

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
