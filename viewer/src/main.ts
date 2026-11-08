import '@fontsource/cormorant-garamond/500.css';
import '@fontsource/cormorant-garamond/600.css';
import '@fontsource/cormorant-garamond/500-italic.css';
import '@fontsource/eb-garamond/400.css';
import 'maplibre-gl/dist/maplibre-gl.css';
import './style.css';

import maplibregl from 'maplibre-gl';
import {MapboxOverlay} from '@deck.gl/mapbox';
import {AmbientLight, DirectionalLight, LightingEffect} from '@deck.gl/core';
import type {Layer, PickingInfo} from '@deck.gl/core';

import {WATER} from './palette';
import {terrainLayer} from './layers/terrain';
import {loadElevation} from './layers/elevation';
import {labelLayers, loadPlaces, placeLabelsOnTerrain} from './layers/labels';
import {loadBuildings, buildingsLayer, type BuildingSet} from './layers/buildings';
import {landmarkLayers, landmarkInfo, loadLandmarks, replacedMask, type LandmarkSet} from './landmarks';
import {loadTrees, treesLayer, type TreeSet} from './layers/trees';
import {loadRoads, roadLayers, trafficLayers, hasTraffic} from './layers/roads';
import {events, eventTime, populationLabelAt} from './data/tables';
import {readHash, writeHash} from './url-state';
import {installCameraControls} from './camera-controls';
import {CONFIDENCE, CONFIDENCE_COLORS} from './palette';

export const YEAR_MIN = 1769;
export const YEAR_MAX = 2026;

// ---------------------------------------------------------------- state
const initial = readHash();
const state = {
  year: initial.year ?? 1848,
  playing: false,
  speed: 6,
  quality: false,
};

let buildings: BuildingSet | null = null;
let landmarks: LandmarkSet | null = null;
let trees: TreeSet[] = [];

// ---------------------------------------------------------------- map + deck
const map = new maplibregl.Map({
  container: 'map',
  style: {
    version: 8,
    sources: {},
    layers: [{id: 'water', type: 'background', paint: {'background-color': WATER}}]
  },
  center: initial.center ?? [-122.4235, 37.7835],
  zoom: initial.zoom ?? 13.1,
  pitch: initial.pitch ?? 58,
  bearing: initial.bearing ?? -22,
  maxPitch: 80,
  minZoom: 9,
  maxZoom: 19,
  attributionControl: false,
  canvasContextAttributes: {antialias: true}
});
installCameraControls(map);

const lighting = new LightingEffect({
  ambient: new AmbientLight({color: [255, 250, 242], intensity: 1.0}),
  // late-afternoon sun from the south-west
  sun: new DirectionalLight({color: [255, 238, 214], intensity: 1.25, direction: [1.2, 1.6, -1.3]}),
  // cool skylight fill from the north-east so shaded walls aren't flat grey
  sky: new DirectionalLight({color: [200, 215, 255], intensity: 0.35, direction: [-1, -1.2, -0.6]})
});

const overlay = new MapboxOverlay({
  interleaved: false,
  effects: [lighting],
  layers: [],
  getTooltip: null as any,
  onClick: (info: PickingInfo) => showInfo(info),
  getCursor: ({isHovering}: {isHovering: boolean}) => (isHovering ? 'pointer' : 'grab')
});
map.addControl(overlay as any);

/** Extent of the terrain tiles (Sonoma/Napa to Santa Cruz). */
const REGION: [number, number, number, number] = [-123.2, 36.85, -121.2, 38.9];

function render() {
  const layers: Layer[] = [];
  const zoom = map.getZoom();
  layers.push(terrainLayer(state.year, REGION) as any);
  layers.push(...roadLayers(state.year, zoom));
  for (const t of trees) layers.push(...treesLayer(t, state.year));
  if (buildings) layers.push(buildingsLayer(buildings, state.year, state.quality, !!landmarks));
  if (landmarks) layers.push(...landmarkLayers(landmarks, state.year, state.quality));
  layers.push(...trafficLayers(state.year, zoom, performance.now() / 1000));
  layers.push(...(labelLayers(state.year, zoom) as any));
  overlay.setProps({layers});
  updateOverlays();
}

// ---------------------------------------------------------------- DOM
const $ = <T extends HTMLElement = HTMLElement>(id: string) => document.getElementById(id) as T;
const slider = $<HTMLInputElement>('slider');
const playBtn = $<HTMLButtonElement>('play');
const yearLabel = $('year-label');
const popValue = $('population-value');
const popArea = $('population-area');
const infoBox = $('info');
const legend = $('legend');

slider.min = String(YEAR_MIN);
slider.max = String(YEAR_MAX);
slider.value = String(state.year);

function updateOverlays() {
  const y = Math.floor(state.year);
  yearLabel.textContent = String(y);
  if (document.activeElement !== slider || state.playing) slider.value = String(state.year);
  const pop = populationLabelAt(state.year);
  popValue.textContent = pop == null ? '—' : Math.round(pop.value).toLocaleString('en-US');
  popArea.textContent = pop == null ? '' : pop.label;
}

slider.addEventListener('input', () => {
  state.year = Number(slider.value);
  render();
  scheduleHash();
});

function setPlaying(p: boolean) {
  state.playing = p;
  playBtn.textContent = p ? '❚❚' : '▶';
  playBtn.setAttribute('aria-label', p ? 'Pause' : 'Play');
  if (p) {
    if (state.year >= YEAR_MAX - 0.01) state.year = YEAR_MIN;
    lastT = performance.now();
    requestAnimationFrame(tick);
  }
}
playBtn.addEventListener('click', () => setPlaying(!state.playing));
$<HTMLSelectElement>('speed').addEventListener('change', e => (state.speed = Number((e.target as HTMLSelectElement).value)));

let lastT = 0;
function tick(t: number) {
  if (!state.playing) return;
  const dt = Math.min(0.1, (t - lastT) / 1000);
  lastT = t;
  state.year = Math.min(YEAR_MAX, state.year + dt * state.speed);
  render();
  if (state.year >= YEAR_MAX) {
    setPlaying(false);
    scheduleHash();
    return;
  }
  requestAnimationFrame(tick);
}

document.addEventListener('keydown', e => {
  if ((e.target as HTMLElement).tagName === 'SELECT') return;
  if (e.code === 'Space') {
    e.preventDefault();
    setPlaying(!state.playing);
  } else if (e.key === 'ArrowRight' || e.key === 'ArrowLeft') {
    if (document.activeElement === slider) return;
    state.year = Math.max(YEAR_MIN, Math.min(YEAR_MAX, Math.floor(state.year) + (e.key === 'ArrowRight' ? 1 : -1)));
    render();
    scheduleHash();
  }
});

const DEBUG = new URLSearchParams(location.search).has('debug');
$('toolbar').hidden = !DEBUG;
$<HTMLInputElement>('toggle-quality').addEventListener('change', e => {
  state.quality = (e.target as HTMLInputElement).checked;
  legend.hidden = !state.quality;
  render();
});

legend.innerHTML = CONFIDENCE.map(
  (c, i) => `<div><span class="swatch" style="background:rgb(${CONFIDENCE_COLORS[i].slice(0, 3).join(',')})"></span>${c}</div>`
).join('');

// ---------------------------------------------------------------- events / bookmarks
const ticks = $('event-ticks');
const select = $<HTMLSelectElement>('events-select');
events.forEach((ev, i) => {
  const t = eventTime(ev);
  if (t < YEAR_MIN || t > YEAR_MAX) return;
  const el = document.createElement('div');
  el.className = 'tick';
  el.style.left = `${((t - YEAR_MIN) / (YEAR_MAX - YEAR_MIN)) * 100}%`;
  el.title = `${ev.year} — ${ev.title}`;
  el.addEventListener('click', () => goToEvent(i));
  ticks.appendChild(el);
  const opt = document.createElement('option');
  opt.value = String(i);
  opt.textContent = `${ev.year} · ${ev.title}`;
  select.appendChild(opt);
});
select.addEventListener('change', () => {
  if (select.value !== '') goToEvent(Number(select.value));
  select.value = '';
});

function goToEvent(i: number) {
  const ev = events[i];
  setPlaying(false);
  const target = Math.max(YEAR_MIN, eventTime(ev) - 0.25);
  if (ev.lat != null && ev.lon != null) {
    map.flyTo({center: [ev.lon, ev.lat], zoom: ev.zoom ?? 14.5, pitch: 60, duration: 3500, essential: true});
  }
  // Ease the year towards the event while the camera flies.
  const from = state.year;
  const t0 = performance.now();
  const dur = 3200;
  const step = (t: number) => {
    const k = Math.min(1, (t - t0) / dur);
    const e = k < 0.5 ? 2 * k * k : 1 - Math.pow(-2 * k + 2, 2) / 2;
    state.year = from + (target - from) * e;
    render();
    if (k < 1) requestAnimationFrame(step);
    else scheduleHash();
  };
  requestAnimationFrame(step);
  infoBox.hidden = false;
  infoBox.innerHTML = `<button class="close" aria-label="Close">✕</button><h3>${ev.year} · ${escapeHtml(ev.title)}</h3><div>${escapeHtml(ev.description ?? '')}</div>`;
  infoBox.querySelector('.close')!.addEventListener('click', () => (infoBox.hidden = true));
}

// ---------------------------------------------------------------- picking popup
function showInfo(info: PickingInfo) {
  if (!info.picked || info.index < 0) {
    infoBox.hidden = true;
    return;
  }
  let title = 'Building';
  let rows: Record<string, string | number> = {};
  if (info.layer?.id === 'buildings' && buildings) {
    rows = buildings.info(info.index);
  } else if (info.layer?.id.startsWith('landmark') && landmarks) {
    const r = landmarkInfo(landmarks, info);
    if (!r) return;
    title = r.title;
    rows = r.rows;
  } else return;
  infoBox.hidden = false;
  infoBox.innerHTML =
    `<button class="close" aria-label="Close">✕</button><h3>${escapeHtml(title)}</h3><table>` +
    Object.entries(rows)
      .map(([k, v]) => `<tr><td>${escapeHtml(k)}</td><td>${escapeHtml(String(v))}</td></tr>`)
      .join('') +
    '</table>';
  infoBox.querySelector('.close')!.addEventListener('click', () => (infoBox.hidden = true));
}

function escapeHtml(s: string) {
  return s.replace(/[&<>"']/g, c => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'})[c]!);
}

// ---------------------------------------------------------------- URL state
let hashTimer = 0;
function scheduleHash() {
  clearTimeout(hashTimer);
  hashTimer = window.setTimeout(() => writeHash(map, state.year), 400);
}
map.on('moveend', scheduleHash);
// labels fade by zoom band: re-render when the zoom changes (once per frame at most)
let zoomPending = false;
map.on('zoom', () => {
  if (zoomPending) return;
  zoomPending = true;
  requestAnimationFrame(() => {
    zoomPending = false;
    if (!state.playing) render();
  });
});

// traffic moves continuously when zoomed in close enough to see it (~30 fps)
let lastTraffic = 0;
function trafficLoop(t: number) {
  requestAnimationFrame(trafficLoop);
  if (state.playing || !hasTraffic() || map.getZoom() < 12.5 || document.hidden) return;
  if (t - lastTraffic < 33) return;
  lastTraffic = t;
  render();
}
if (!new URLSearchParams(location.search).has('notraffic')) requestAnimationFrame(trafficLoop);

// ---------------------------------------------------------------- attribution
$('attribution').innerHTML =
  'Buildings &amp; trees: <a href="https://datasf.org/opendata/" target="_blank" rel="noopener">DataSF</a> · ' +
  'Shoreline: US Census TIGER/Line · Landmarks reconstructed from cited references · ' +
  '<a href="https://github.com/tjaffee99/bay/blob/main/SOURCES.md" target="_blank" rel="noopener">Sources</a>';

// ---------------------------------------------------------------- load
const loading = $('loading');
async function boot() {
  render();
  loadPlaces();
  const elevP = Promise.all([loadElevation(), document.fonts.ready]).then(() => {
    placeLabelsOnTerrain();
    render();
  });
  const lmP = Promise.all([loadLandmarks(), elevP])
    .then(([l]) => {
      landmarks = l;
      render();
    })
    .catch(e => console.warn('landmarks', e));
  const roadP = elevP
    .then(() => loadRoads())
    .then(render)
    .catch(e => console.warn('roads', e));
  const treeP = elevP
    .then(() => loadTrees('data/sf-trees.bin.gz', 'street', 6))
    .then(t => {
      trees.push(t);
      render();
    })
    .catch(e => console.warn('trees', e));
  // ?nobuildings skips the city (fast landmark previews / debugging)
  if (!new URLSearchParams(location.search).has('nobuildings')) {
    buildings = await loadBuildings(f => (loading.textContent = `Loading San Francisco… ${Math.round(f * 100)}%`));
  }
  render();
  await Promise.all([lmP, treeP, roadP]);
  if (buildings && landmarks) {
    buildings.replaced = replacedMask(landmarks, buildings.centroids, buildings.count);
    render();
  }
  loading.classList.add('done');
  (window as any).__ready = true;
}
boot();

// For automated screenshots / debugging.
(window as any).__setYear = (y: number) => {
  state.year = y;
  render();
};
(window as any).__map = map;
