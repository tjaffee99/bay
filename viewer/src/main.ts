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

import {terrainLayer, setTerrainChangeCallback, refreshDecoSoon} from './layers/terrain';
import {loadElevation} from './layers/elevation';
import {addStationLabels, dropLabels, labelLayers, labelZoomKey, loadParkLabels, loadPlaces, placeLabelsOnTerrain, setLabelProjector} from './layers/labels';
import {extentBounds, extentDistance, extentReady} from './layers/extent';
import {hasTransit, loadTransit, stations, tickTransit, transitLayers} from './layers/transit';
import {loadRegionIndex, regionBuildingLayers, setRegionLandmarks} from './layers/region-buildings';
import {airportLayers, groundDetailLayers, loadAirports, loadGroundDetail, setGroundDetailRedraw} from './layers/ground-detail';
import {loadBuildings, buildingsLayer, type BuildingSet} from './layers/buildings';
import {landmarkLayers, landmarkInfo, loadLandmarks, replacedMask, type LandmarkSet} from './landmarks';
import {loadTrees, treesLayer, type TreeSet} from './layers/trees';
import {treeLod} from './layers/decoration-meshes';
import {loadLocalStreetIndex, loadRoads, localStreetLayers, roadLayers, trafficLayers, tickTraffic, hasTraffic} from './layers/roads';
import {events, eventTime, loadCities, localPopulationAt} from './data/tables';
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
    // beyond the terrain tiles: the parchment the map fades into at its edges
    layers: [{id: 'water', type: 'background', paint: {'background-color': '#ece6d6'}}]
  },
  center: initial.center ?? [-122.4235, 37.7835],
  zoom: initial.zoom ?? 13.1,
  pitch: initial.pitch ?? 58,
  bearing: initial.bearing ?? -22,
  maxPitch: 80,
  minZoom: 9,
  maxZoom: 19,
  // MapLibre only paints the flat water background here: no need for retina pixels
  pixelRatio: 1,
  attributionControl: false,
  canvasContextAttributes: {antialias: true}
});
installCameraControls(map);
// first visit (no view in the URL): the whole of San Francisco, gently tilted
if (!initial.center) {
  map.fitBounds([[-122.516, 37.706], [-122.357, 37.812]], {padding: 24, pitch: 45, bearing: -12, duration: 0});
}
setTerrainChangeCallback(() => render());

// Late-afternoon sun from the south-west and a cool skylight fill from the north-east.
// Sun shadows are opt-in (?shadow): a deck shadow map, re-rendered only when the view
// or a shadow caster changes, at zoom >= 13.5.
const SUN = {color: [255, 238, 214] as [number, number, number], intensity: 1.25, direction: [1.2, 1.6, -1.3] as [number, number, number]};
const AMBIENT = {color: [255, 250, 242] as [number, number, number], intensity: 1.0};
const SHADOWS = new URLSearchParams(location.search).has('shadow');
/** LightingEffect that re-renders its shadow map only when the view or the layers'
 *  data / year changed — not on the ~30 fps redraws that only move traffic and
 *  trains (which cast no shadows). */
const dataIds = new WeakMap<object, number>();
let nextDataId = 1;
const idOf = (o: any) => {
  if (!o || typeof o !== 'object') return String(o);
  let k = dataIds.get(o);
  if (!k) dataIds.set(o, (k = nextDataId++));
  return k;
};
class CachedShadowLighting extends LightingEffect {
  private shadowKey = '';
  preRender(opts: any) {
    const vp = opts.viewports?.[0];
    let key = vp ? `${vp.width}x${vp.height}|${Array.from(vp.viewProjectionMatrix as number[], v => v.toPrecision(7)).join(',')}` : '';
    for (const l of opts.layers ?? []) {
      if (l.props.shadowEnabled === false || !l.props.visible) continue;
      key += `|${l.id}:${idOf(l.props.data)}:${l.props.year ?? l.props.currentYear ?? ''}:${idOf(l.props.merged)}`;
    }
    if (key && key === this.shadowKey) return;
    this.shadowKey = key;
    super.preRender(opts);
  }
}
const lighting = new LightingEffect({
  ambient: new AmbientLight(AMBIENT),
  sun: new DirectionalLight(SUN),
  sky: new DirectionalLight({color: [200, 215, 255], intensity: 0.35, direction: [-1, -1.2, -0.6]})
});
const shadowLighting = new CachedShadowLighting({ambient: new AmbientLight({...AMBIENT, intensity: 1.1}), sun: new DirectionalLight({...SUN, _shadow: true})});
shadowLighting.shadowColor = [0.07, 0.09, 0.15, 0.45];
const SHADOW_ZOOM = 13.5;
const wantShadow = (z: number) => SHADOWS && z >= SHADOW_ZOOM;

const overlay = new MapboxOverlay({
  interleaved: false,
  effects: [lighting],
  layers: [],
  getTooltip: null as any,
  // No hover picking: it re-renders every pickable layer (220k buildings) into a
  // picking buffer on each mouse move and at the start of every drag, then stalls
  // the GPU to read it back. Objects are picked on click only (below).
  pickAsync: false,
  // a composite layer (TextLayer labels, …) marked shadowEnabled: false must not cast
  // shadows through its sublayers either (pixel-sized text seen from the sun is huge)
  layerFilter: ({layer, renderPass}: any) => !(renderPass === 'shadow' && layer.props.shadowEnabled === false),
  // full resolution up to 2× (3× phone screens would cost 9× the pixels of 1×)
  useDevicePixels: Math.min(2, window.devicePixelRatio || 1),
  getCursor: ({isDragging}: {isDragging: boolean}) => (isDragging ? 'grabbing' : 'grab'),
  // ask for the discrete GPU on dual-GPU laptops; MSAA on
  deviceProps: {powerPreference: 'high-performance', webgl: {antialias: true}}
} as any);
map.addControl(overlay as any);
let shadowsOn = false;
function setShadows(z: number) {
  const on = wantShadow(z);
  if (on === shadowsOn) return;
  shadowsOn = on;
  overlay.setProps({effects: [on ? shadowLighting : lighting]});
}
setShadows(map.getZoom());
map.on('click', e => {
  const info = overlay.pickObject({x: e.point.x, y: e.point.y, radius: 3});
  showInfo((info ?? {picked: false, index: -1}) as PickingInfo);
});

/** Extent of the terrain tiles (Sonoma/Napa to Santa Cruz). */
const REGION: [number, number, number, number] = [-123.2, 36.85, -121.2, 38.9];

function render() {
  const layers: Layer[] = [];
  const zoom = map.getZoom();
  layers.push(...(terrainLayer(state.year, REGION, zoom) as any[]));
  layers.push(...groundDetailLayers(state.year, zoom));
  layers.push(...airportLayers(state.year, zoom));
  const b = map.getBounds();
  layers.push(...localStreetLayers(state.year, zoom));
  layers.push(...roadLayers(state.year, zoom, [b.getWest(), b.getSouth(), b.getEast(), b.getNorth()]));
  for (const t of trees) layers.push(...treesLayer(t, state.year, zoom));
  if (buildings) layers.push(buildingsLayer(buildings, state.year, state.quality, !!landmarks));
  layers.push(...regionBuildingLayers(state.year, zoom, state.quality));
  if (landmarks) layers.push(...landmarkLayers(landmarks, state.year, state.quality));
  layers.push(...trafficLayers(state.year, zoom));
  layers.push(...transitLayers(state.year, zoom));
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
  const c = map.getCenter();
  const pop = localPopulationAt(state.year, c.lng, c.lat, map.getZoom());
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
// labels are decluttered for the camera at rest
function updateLabelProjector() {
  const c = map.getCanvas();
  setLabelProjector((lon, lat) => {
    const p = map.project([lon, lat]);
    return [p.x, p.y];
  }, [c.clientWidth, c.clientHeight]);
}
map.on('moveend', () => {
  refreshDecoSoon();
  updateLabelProjector();
  if (!state.playing) render();
});
map.on('load', updateLabelProjector);
// labels fade by zoom band, traffic and region roads switch by zoom: re-render only
// when one of those actually changes (not on every zoom frame)
let zoomKey = '';
map.on('zoom', () => {
  const z = map.getZoom();
  const lod = treeLod(z);
  const key = `${labelZoomKey(z)}|${z >= 9}|${z >= 11}|${z >= 12.5}|${z >= 13}|${z >= 13.5}|${z > 15.5}|${lod.low}|${lod.keep}|${wantShadow(z)}`;
  if (key === zoomKey || state.playing) return;
  zoomKey = key;
  setShadows(z);
  render();
});

// traffic and trains move on the GPU: just ask for a redraw when they are visible —
// ~30 fps close in; trains seen from far away move under a pixel a second, so less often
let lastTraffic = 0;
let lastTrain = 0;
function trafficLoop(t: number) {
  requestAnimationFrame(trafficLoop);
  const z = map.getZoom();
  if (document.hidden || z < 11.5) return;
  if (hasTraffic() && z >= 12.5 && t - lastTraffic >= 33) {
    lastTraffic = t;
    tickTraffic();
  }
  const trainEvery = z >= 14 ? 33 : z >= 13 ? 100 : 250;
  if (hasTransit() && t - lastTrain >= trainEvery) {
    lastTrain = t;
    tickTransit();
  }
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
  const transitP = loadTransit().then(() => addStationLabels(stations));
  loadRegionIndex().then(render);
  loadCities().then(updateOverlays);
  // the counter follows the place under the centre of the map
  map.on('moveend', updateOverlays);
  extentReady.then(() => {
    const b = extentBounds();
    if (b) map.setMaxBounds([[b[0], b[1]], [b[2], b[3]]]);
    // labels in the faded margin or outside the map go (and their station / park twins)
    dropLabels((lon, lat) => extentDistance(lon, lat) > 2.5);
    render();
  });
  loadLocalStreetIndex().then(render);
  const elevP = Promise.all([loadElevation(), document.fonts.ready, loadParkLabels(), transitP]).then(() => {
    placeLabelsOnTerrain();
    render();
  });
  loadAirports().then(render);
  setGroundDetailRedraw(render);
  const groundP = loadGroundDetail()
    .then(render)
    .catch(e => console.warn('ground detail', e));
  // landmark meshes are merged with their ground elevation baked in: after elevation
  const lmP = elevP
    .then(() => loadLandmarks())
    .then(l => {
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
  await Promise.all([lmP, treeP, roadP, groundP]);
  if (buildings && landmarks) {
    buildings.replaced = replacedMask(landmarks, buildings.centroids, buildings.count, buildings.height);
    render();
  }
  setRegionLandmarks(landmarks);
  loading.classList.add('done');
  warnIfSoftwareRendering();
  (window as any).__ready = true;
}
boot();

/** Browsers with hardware acceleration off (or a blocklisted GPU) draw WebGL on the CPU. */
function warnIfSoftwareRendering() {
  const gl = (overlay as any)._deck?.device?.gl as WebGL2RenderingContext | undefined;
  if (!gl) return;
  const ext = gl.getExtension('WEBGL_debug_renderer_info');
  const renderer = String(ext ? gl.getParameter(ext.UNMASKED_RENDERER_WEBGL) : gl.getParameter(gl.RENDERER));
  (window as any).__renderer = renderer;
  if (!/swiftshader|llvmpipe|softpipe|software|basic render/i.test(renderer) || new URLSearchParams(location.search).has('nobanner')) return;
  const el = document.createElement('div');
  el.id = 'gpu-warning';
  el.innerHTML =
    'Your browser is drawing this map <b>without the graphics card</b> (' +
    escapeHtml((renderer.match(/swiftshader|llvmpipe|softpipe|basic render[a-z ]*/i) ?? [renderer])[0]) +
    '), so it will be slow. Turn on hardware acceleration in the browser settings and reload.' +
    ' <button aria-label="Dismiss">✕</button>';
  el.querySelector('button')!.addEventListener('click', () => el.remove());
  document.body.appendChild(el);
}

// For automated screenshots / debugging.
(window as any).__setYear = (y: number) => {
  state.year = y;
  render();
};
(window as any).__map = map;
(window as any).__overlay = overlay;
