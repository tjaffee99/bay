/**
 * Story mode: a guided tour through the map's history (data/tables/story.csv).
 *
 * Each stop has a year, a camera target and a caption. The engine flies to the stop while
 * the year runs to the stop's year, then holds for a reading time (2 s + 50 ms per
 * character, 6–16 s, or the stop's `dwell_s`) while the camera turns slowly and — where the
 * stop has a `year_end` — the year runs on, so a building goes up or a district burns and
 * is rebuilt on screen. A `quake` stop shakes the view when the year passes `effect_year`.
 * The tour starts at the stop of the year the map is showing. Any drag, wheel or slider
 * input pauses it; it never fights the visitor.
 *
 * Nothing here draws on the map: the engine only moves the camera (MapLibre) and sets the
 * year through the callbacks of main.ts.
 */
import type {Map as MlMap} from 'maplibre-gl';
import type {StoryStop} from './data/tables';

type Phase = 'off' | 'fly' | 'dwell' | 'paused';

export type StoryHooks = {
  getYear: () => number;
  /** set the map's year and redraw */
  setYear: (y: number) => void;
  /** the tour starts: stop the plain time-lapse, close pop-ups */
  onStart: () => void;
  /** the tour ended or was left */
  onExit: () => void;
  /** earthquake: 0..1 while the view shakes (the buildings sway with it) */
  shake?: (amount: number) => void;
};

export type Story = {
  start: (index?: number) => void;
  exit: () => void;
  isActive: () => boolean;
  /** flying or holding a stop (not paused) */
  isRunning: () => boolean;
  /** keyboard: returns true when the key was used */
  key: (e: KeyboardEvent) => boolean;
  /** the visitor took the controls (drag, wheel, slider): pause */
  interrupt: () => void;
};

const FLY_MIN = 2600;
const FLY_MAX = 5500;

/** Time to hold a stop: the caption is already up during the flight, so this is short. */
export function readingMs(text: string): number {
  return Math.max(6000, Math.min(16000, 2000 + 50 * text.length));
}

function kmBetween(a: [number, number], b: [number, number]): number {
  const r = Math.PI / 180;
  const dLat = (b[1] - a[1]) * r;
  const dLon = (b[0] - a[0]) * r;
  const h = Math.sin(dLat / 2) ** 2 + Math.cos(a[1] * r) * Math.cos(b[1] * r) * Math.sin(dLon / 2) ** 2;
  return 12742 * Math.asin(Math.min(1, Math.sqrt(h)));
}

const ease = (k: number) => (k < 0.5 ? 2 * k * k : 1 - Math.pow(-2 * k + 2, 2) / 2);

export function createStory(map: MlMap, stops: StoryStop[], hooks: StoryHooks, button: HTMLButtonElement | null): Story {
  const params = new URLSearchParams(location.search);
  // ?storyspeed=N runs the tour N times faster (testing)
  const speed = Math.max(0.25, Number(params.get('storyspeed')) || 1);
  const still = window.matchMedia?.('(prefers-reduced-motion: reduce)').matches ?? false;

  const card = document.createElement('div');
  card.id = 'story-card';
  card.hidden = true;
  card.innerHTML =
    '<div class="story-meta"><span class="story-count"></span><button class="story-exit" aria-label="Leave the story" title="Leave the story (Esc)">✕</button></div>' +
    '<h3 class="story-title"></h3><p class="story-text"></p>' +
    '<div class="story-bar"><i></i></div>' +
    '<div class="story-ctrl">' +
    '<button class="story-prev" aria-label="Previous stop" title="Previous (←)">⏮</button>' +
    '<button class="story-pause" aria-label="Pause the story" title="Pause (space)">❚❚</button>' +
    '<button class="story-next" aria-label="Next stop" title="Next (→)">⏭</button>' +
    '<a class="story-source" target="_blank" rel="noopener">source</a>' +
    '</div>';
  document.body.appendChild(card);
  const q = <T extends HTMLElement>(sel: string) => card.querySelector(sel) as T;
  const elCount = q<HTMLElement>('.story-count');
  const elTitle = q<HTMLElement>('.story-title');
  const elText = q<HTMLElement>('.story-text');
  const elBar = q<HTMLElement>('.story-bar i');
  const elPause = q<HTMLButtonElement>('.story-pause');
  const elSource = q<HTMLAnchorElement>('.story-source');

  let phase: Phase = 'off';
  let resumeTo: 'fly' | 'dwell' = 'fly';
  let idx = 0;
  let raf = 0;
  let t0 = 0; // start of the current phase (performance.now)
  let dur = 0; // length of the current phase, ms
  let done = 0; // share of the dwell already shown when it was paused
  let yearFrom = 0;
  let yearSetAt = 0; // last year update during a flight (they are spaced out: tiles are loading)
  let shook = false; // the stop's earthquake has fired
  let shakeRaf = 0;

  /** The stop to start from when the map shows year y: the one whose years contain or follow it. */
  function indexForYear(y: number): number {
    const last = stops.length - 1;
    if (last < 0 || y >= stops[last].year - 0.5) return 0; // at "today": from the beginning
    for (let i = 0; i <= last; i++) if ((stops[i].yearEnd ?? stops[i].year) >= y - 0.05) return i;
    return 0;
  }

  /** Earthquake: the whole view shakes for a few seconds (and the buildings sway). */
  function quake(ms = 3000) {
    if (still) return;
    const el = map.getContainer();
    const t1 = performance.now();
    cancelAnimationFrame(shakeRaf);
    const step = (t: number) => {
      const k = (t - t1) / ms;
      if (k >= 1 || phase === 'off') {
        el.style.transform = '';
        hooks.shake?.(0);
        return;
      }
      const env = Math.pow(Math.sin(Math.PI * Math.min(1, k * 1.1)), 0.6) * (1 - 0.35 * k);
      const a = 7 * env;
      const dx = a * Math.sin(t * 0.047) + 0.5 * a * Math.sin(t * 0.113 + 2);
      const dy = a * Math.sin(t * 0.061 + 1) + 0.4 * a * Math.sin(t * 0.127);
      el.style.transform = `translate(${dx.toFixed(1)}px, ${dy.toFixed(1)}px) scale(1.014)`;
      hooks.shake?.(env);
      shakeRaf = requestAnimationFrame(step);
    };
    shakeRaf = requestAnimationFrame(step);
  }

  function show(i: number) {
    const s = stops[i];
    elCount.textContent = `${i + 1} / ${stops.length}`;
    elTitle.textContent = s.title;
    elText.textContent = s.text;
    if (s.source) {
      elSource.href = s.source;
      elSource.hidden = false;
    } else elSource.hidden = true;
    elBar.style.width = '0%';
    card.classList.remove('story-in');
    void card.offsetWidth; // restart the fade
    card.classList.add('story-in');
  }

  function setPauseLabel(paused: boolean) {
    elPause.textContent = paused ? '▶' : '❚❚';
    elPause.setAttribute('aria-label', paused ? 'Resume the story' : 'Pause the story');
    card.classList.toggle('story-paused', paused);
  }

  function camera(opts: Record<string, unknown>, ms: number, fly: boolean) {
    if (still || ms <= 0) map.jumpTo(opts as any);
    else if (fly) map.flyTo({...opts, duration: ms, essential: true, curve: 1.1} as any);
    else map.easeTo({...opts, duration: ms, essential: true, easing: (t: number) => t} as any);
  }

  function go(i: number) {
    cancelAnimationFrame(raf);
    idx = Math.max(0, Math.min(stops.length - 1, i));
    const s = stops[idx];
    card.classList.remove('story-end');
    show(idx);
    const c = map.getCenter();
    const km = kmBetween([c.lng, c.lat], [s.lon, s.lat]);
    dur = Math.max(FLY_MIN, Math.min(FLY_MAX, FLY_MIN + km * 40)) / speed;
    yearFrom = hooks.getYear();
    yearSetAt = 0;
    shook = false;
    phase = 'fly';
    setPauseLabel(false);
    t0 = performance.now();
    // a low arc: fewer zoom levels of tiles to load on the way
    camera({center: [s.lon, s.lat], zoom: s.zoom, pitch: s.pitch, bearing: s.bearing}, dur, true);
    raf = requestAnimationFrame(frame);
  }

  function dwell(from: number) {
    const s = stops[idx];
    done = from;
    dur = ((s.dwell != null ? s.dwell * 1000 : readingMs(s.text)) * (1 - from)) / speed;
    phase = 'dwell';
    setPauseLabel(false);
    t0 = performance.now();
    if (s.orbit && !still) camera({bearing: s.bearing + s.orbit}, dur, false);
    raf = requestAnimationFrame(frame);
  }

  function frame(t: number) {
    if (phase !== 'fly' && phase !== 'dwell') return;
    const s = stops[idx];
    const k = dur > 0 ? Math.min(1, (t - t0) / dur) : 1;
    if (phase === 'fly') {
      // the camera is moving and tiles are loading: the year moves in steps (about ten a
      // second), not on every frame
      if (k >= 1 || t - yearSetAt >= 90) {
        yearSetAt = t;
        hooks.setYear(yearFrom + (s.year - yearFrom) * ease(k));
      }
      if (k >= 1) {
        dwell(0);
        return;
      }
    } else {
      const kk = done + (1 - done) * k;
      const yNow = s.yearEnd != null && s.yearEnd > s.year ? s.year + (s.yearEnd - s.year) * kk : s.year;
      if (s.yearEnd != null && s.yearEnd > s.year) hooks.setYear(yNow);
      if (s.effect === 'quake' && !shook && (s.effectYear == null ? kk > 0.08 : yNow >= s.effectYear)) {
        shook = true;
        quake();
      }
      elBar.style.width = `${(kk * 100).toFixed(1)}%`;
      if (k >= 1) {
        if (idx + 1 < stops.length) go(idx + 1);
        else finish();
        return;
      }
    }
    raf = requestAnimationFrame(frame);
  }

  function pause() {
    if (phase !== 'fly' && phase !== 'dwell') return;
    cancelAnimationFrame(raf);
    resumeTo = phase;
    if (phase === 'dwell') done = done + (1 - done) * Math.min(1, (performance.now() - t0) / Math.max(1, dur));
    phase = 'paused';
    map.stop();
    setPauseLabel(true);
  }

  function resume() {
    if (phase !== 'paused') return;
    if (resumeTo === 'dwell') {
      // back to where the stop left off (the visitor may have moved the camera)
      const s = stops[idx];
      camera({center: [s.lon, s.lat], zoom: s.zoom, pitch: s.pitch, bearing: s.bearing + (s.orbit || 0) * done}, 900 / speed, false);
      const d = done;
      phase = 'fly';
      yearFrom = hooks.getYear();
      // a short settle, then the rest of the reading time
      t0 = performance.now();
      dur = 900 / speed;
      setPauseLabel(false);
      const settle = (t: number) => {
        if (phase !== 'fly') return;
        if (t - t0 >= dur) dwell(d);
        else raf = requestAnimationFrame(settle);
      };
      raf = requestAnimationFrame(settle);
    } else go(idx);
  }

  function finish() {
    // the last stop stays on screen, paused, until the visitor leaves
    cancelAnimationFrame(raf);
    phase = 'paused';
    resumeTo = 'dwell';
    done = 1;
    setPauseLabel(true);
    card.classList.add('story-end');
    (window as any).__storyDone = true;
  }

  function start(i?: number) {
    if (!stops.length) return;
    if (i === undefined) i = indexForYear(hooks.getYear());
    hooks.onStart();
    card.hidden = false;
    card.classList.remove('story-end');
    document.body.classList.add('story-on');
    button?.setAttribute('aria-pressed', 'true');
    (window as any).__storyDone = false;
    go(i);
  }

  function exit() {
    if (phase === 'off') return;
    cancelAnimationFrame(raf);
    cancelAnimationFrame(shakeRaf);
    map.getContainer().style.transform = '';
    hooks.shake?.(0);
    phase = 'off';
    map.stop();
    card.hidden = true;
    document.body.classList.remove('story-on');
    button?.setAttribute('aria-pressed', 'false');
    hooks.onExit();
  }

  function toggle() {
    if (phase === 'paused') {
      if (card.classList.contains('story-end')) start(0);
      else resume();
    } else pause();
  }

  q<HTMLButtonElement>('.story-exit').addEventListener('click', exit);
  q<HTMLButtonElement>('.story-prev').addEventListener('click', () => go(idx - 1));
  q<HTMLButtonElement>('.story-next').addEventListener('click', () => (idx + 1 < stops.length ? go(idx + 1) : finish()));
  elPause.addEventListener('click', toggle);
  button?.addEventListener('click', () => (phase === 'off' ? start() : exit()));
  if (button) button.hidden = !stops.length;

  // the visitor takes the camera (drag, wheel, touch, a click on the map): pause
  const interrupt = () => {
    if (phase === 'fly' || phase === 'dwell') pause();
  };
  const el = map.getCanvasContainer();
  for (const ev of ['mousedown', 'wheel', 'touchstart'] as const) el.addEventListener(ev, interrupt, {passive: true});
  // a hidden tab draws no frames: wait there instead of skipping the stop on return
  document.addEventListener('visibilitychange', () => {
    if (document.hidden) interrupt();
  });

  function key(e: KeyboardEvent): boolean {
    if (phase === 'off') return false;
    if (e.code === 'Space') toggle();
    else if (e.key === 'ArrowRight') {
      if (idx + 1 < stops.length) go(idx + 1);
      else finish();
    }
    else if (e.key === 'ArrowLeft') go(idx - 1);
    else if (e.key === 'Escape') exit();
    else return false;
    e.preventDefault();
    return true;
  }

  // for automated checks
  (window as any).__story = {start, exit, state: () => ({phase, idx, n: stops.length})};

  return {start, exit, isActive: () => phase !== 'off', isRunning: () => phase === 'fly' || phase === 'dwell', key, interrupt};
}
