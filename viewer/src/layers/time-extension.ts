/**
 * TimeExtension — makes any deck.gl layer time-aware.
 *
 * Each object carries [start_year, end_year] (accessor `getYears`). On the GPU:
 *   visible  iff  start_year <= year < end_year
 *   grow     = smoothstep(start, start + growYears, year)        (rise when built)
 *            * (1 - smoothstep(end - shrinkYears, end, year))   (sink when removed)
 *
 * Moving the slider only changes the `currentYear` uniform — no attribute
 * buffers are rebuilt. This replaces DataFilterExtension (same GPU technique,
 * one attribute instead of two, plus the grow animation; see CLAUDE.md).
 *
 * Modes decide how `grow` is applied:
 *   'polygon' — SolidPolygonLayer buildings: a building goes up as its frame, floor by
 *               floor, over its construction period before start_year (longer for
 *               taller ones; `time_building` = 1 + progress), is clad from the ground
 *               up in the last part of it, and stands finished from start_year (the
 *               layer's shader draws the frame).
 *               Disasters (setTimeFx): a building whose end falls on a fire / earthquake
 *               stands until the event, then burns (`time_fire`, flames on the roof) and
 *               collapses in the days after it, instead of sinking before its end.
 *   'mesh-z'  — SimpleMeshLayer:   scales the mesh vertically (buildings, bridges).
 *   'mesh'    — SimpleMeshLayer:   scales uniformly (trees growing).
 *   'fade'    — anything flat:     fades alpha in/out instead.
 */
import {LayerExtension} from '@deck.gl/core';
import type {Layer, Accessor, DefaultProps} from '@deck.gl/core';
import type {ShaderModule} from '@luma.gl/shadertools';

export type TimeMode = 'polygon' | 'mesh-z' | 'mesh' | 'fade';

export type TimeExtensionProps<DataT = any> = {
  /** [start_year, end_year] of each object. */
  getYears?: Accessor<DataT, [number, number]>;
  /** Fractional year currently displayed. */
  currentYear?: number;
  /** Years over which a new object rises from the ground. */
  growYears?: number;
  /** Years over which a removed object sinks before disappearing. */
  shrinkYears?: number;
  /** Optional tint (rgb 0-1, a = strength) for objects in their last `shrinkYears`. */
  endTint?: [number, number, number, number];
};

type TimeUniforms = {
  year: number;
  growYears: number;
  shrinkYears: number;
  fade: number;
  endTint: [number, number, number, number];
  build: number;
  fx: [number, number, number, number];
  clock: number;
  shake: number;
};

/**
 * Disasters: buildings whose end_year is `match` (± 0.006) were destroyed by the event
 * at `t0`. They ignite over `spread` years after it (a slow, patchy front), burn for
 * `burn` years and fall; `burn` = 0 is a collapse without fire. Dates: the events table
 * and the pipeline's own end years (fire_1906, fires.py, redevelopment_areas.csv).
 */
export type Disaster = {match: number; t0: number; spread: number; burn: number; name: string};
const DAY = 1 / 365;
export const DISASTERS: Disaster[] = [
  {name: 'San Francisco fire of May 3-4, 1851', match: 1851.34, t0: 1851.3368, spread: 0.4 * DAY, burn: 0.5 * DAY},
  {name: 'Earthquake and fire of April 18-21, 1906', match: 1906.29, t0: 1906.2937, spread: 3 * DAY, burn: 1.2 * DAY},
  {name: 'Berkeley fire of September 17, 1923', match: 1923.71, t0: 1923.7112, spread: 0.25 * DAY, burn: 0.4 * DAY},
  {name: 'Loma Prieta earthquake of October 17, 1989', match: 1989.79, t0: 1989.7937, spread: 0.02 * DAY, burn: 0},
  {name: 'Oakland Hills firestorm of October 20, 1991', match: 1991.8, t0: 1991.8013, spread: 0.4 * DAY, burn: 0.4 * DAY},
  {name: 'Tubbs, Nuns and Atlas fires of October 8-9, 2017', match: 2017.77, t0: 2017.7696, spread: 1 * DAY, burn: 0.5 * DAY},
  {name: 'Kincade Fire of October 2019', match: 2019.82, t0: 2019.812, spread: 3 * DAY, burn: 0.6 * DAY},
  {name: 'Lightning complexes of August 2020', match: 2020.625, t0: 2020.622, spread: 3 * DAY, burn: 0.6 * DAY},
  {name: 'Glass Fire of September 27, 2020', match: 2020.74, t0: 2020.7377, spread: 2 * DAY, burn: 0.6 * DAY}
];
const FALL = (d: Disaster) => Math.max(d.burn * 0.35, 0.15 * DAY);

const fxState = {fx: [0, 0, 0, 0] as [number, number, number, number], clock: 0, shake: 0, active: false};
/** The disaster in play at this year (if any) and the wall clock for flames; called by main.ts on every render. */
export function setTimeFx(year: number, clockSeconds: number) {
  fxState.clock = clockSeconds % 1000;
  fxState.active = false;
  fxState.fx = [0, 0, 0, 0];
  for (const d of DISASTERS) {
    if (year > d.t0 - 1 && year < d.t0 + d.spread + d.burn + FALL(d) + 0.01) {
      fxState.fx = [d.match, year - d.t0, d.spread, d.burn];
      // flames need redrawing every frame only while something burns
      fxState.active = year > d.t0 - 0.0005;
      break;
    }
  }
}
/** Earthquake sway of the buildings, 0..1 (story mode). */
export function setTimeShake(a: number) {
  fxState.shake = a;
}
/** The disaster uniforms for layers with their own shader (landmarks). */
export function timeFxUniforms() {
  return fxState;
}
/** True while flames or shaking are on screen: the caller keeps redrawing. */
export function timeFxActive() {
  return fxState.active || fxState.shake > 0;
}

const uniformBlock = /* glsl */ `\
layout(std140) uniform timeUniforms {
  float year;
  float growYears;
  float shrinkYears;
  float fade;
  vec4 endTint;
  float build;
  vec4 fx;
  float clock;
  float shake;
} time;
`;

const timeModule: ShaderModule<TimeUniforms> = {
  name: 'time',
  vs: `${uniformBlock}
in vec2 timeYears;
float time_grow;
float time_visible;
float time_ending;
float time_building;
float time_fire;
float time_tip;
`,
  uniformTypes: {
    year: 'f32',
    growYears: 'f32',
    shrinkYears: 'f32',
    fade: 'f32',
    endTint: 'vec4<f32>',
    build: 'f32',
    fx: 'vec4<f32>',
    clock: 'f32',
    shake: 'f32'
  },
  inject: {
    'vs:#main-start': /* glsl */ `
      time_visible = (time.year >= timeYears.x && time.year < timeYears.y) ? 1.0 : 0.0;
      time_ending = smoothstep(timeYears.y - time.shrinkYears, timeYears.y, time.year);
      time_grow = smoothstep(timeYears.x, timeYears.x + time.growYears, time.year) * (1.0 - time_ending);
      time_building = 0.0;
      time_fire = 0.0;
      time_tip = 0.0;
#ifdef TIME_POLYGON_BUILD
      if (time.build > 0.5) {
        // construction: ~4 months for a house, ~1 year at 40 m, 3 years for a tower. The
        // frame rises floor by floor (topped out at 70 % of the time), then it is clad
        float dur = clamp(0.25 + elevations / 55.0, 0.33, 3.0);
        float prog = clamp((time.year - (timeYears.x - dur)) / dur, 0.0, 1.0);
        float lastYear = timeYears.y;
        // destroyed by the disaster in play: stands until it, then burns and falls
        if (time.fx.x > 0.5 && abs(timeYears.y - time.fx.x) < 0.006) {
          // ignition spreads in patches a few hundred metres across (smooth in space, so a
          // building's walls and roof go together)
          vec2 q = vertexPositions.xy;
          float patchy = 0.5 + 0.25 * sin(q.x * 900.0 + 1.3) * cos(q.y * 1100.0 + 0.7) + 0.25 * sin((q.x + q.y) * 2300.0);
          float since = time.fx.y - patchy * time.fx.z;
          float burn = time.fx.w;
          float fall = max(burn * 0.35, 0.0004);
          time_ending = clamp((since - burn) / fall, 0.0, 1.0);
          time_fire = burn > 0.0 ? clamp(since / (burn * 0.2), 0.0, 1.0) * (1.0 - time_ending) : 0.0;
          // (no per-vertex cut-off — the delay varies a little across a footprint and a
          // half-hidden triangle would stretch to the screen centre: the ruin lies flat, under
          // the ground, until the event is over and the whole district is dropped at once)
          lastYear = 1.0e5;
        }
        time_visible = (time.year >= timeYears.x - dur && time.year < lastYear) ? 1.0 : 0.0;
        time_building = time.year < timeYears.x ? 1.0 + prog : 0.0;
        time_grow = (time.year < timeYears.x ? clamp(prog / 0.7, 0.03, 1.0) : 1.0) * (1.0 - time_ending);
      }
#endif
    `,
    'vs:#main-end': /* glsl */ `
      if (time_visible < 0.5) {
        gl_Position = vec4(0.0);
      }
    `,
    'vs:DECKGL_FILTER_COLOR': /* glsl */ `
      color.rgb = mix(color.rgb, time.endTint.rgb, time.endTint.a * time_ending);
      if (time.fade > 0.5) {
        color.a *= time_grow;
      }
    `
  }
};

const defaultProps: DefaultProps<TimeExtensionProps> = {
  getYears: {type: 'accessor', value: [-10000, 10000]},
  currentYear: 2026,
  growYears: 2,
  shrinkYears: 0.6,
  endTint: [0, 0, 0, 0]
};

export class TimeExtension extends LayerExtension<{mode: TimeMode}> {
  static defaultProps = defaultProps;
  static extensionName = 'TimeExtension';

  constructor(opts: {mode: TimeMode}) {
    super(opts);
  }

  getShaders(this: Layer<TimeExtensionProps>, extension: this) {
    const inject: Record<string, string> = {};
    switch (extension.opts.mode) {
      case 'polygon':
        // Regex-style injection right after the extrusion line in
        // solid-polygon-layer-vertex-main.glsl (deck.gl 9.x): only the sinking on removal
        inject['pos.z += props.elevations * solidPolygon.elevationScale;'] = `
pos.z -= props.elevations * solidPolygon.elevationScale * (1.0 - time_grow);
if (props.elevations > 0.01) {
  float rnd = fract(sin(dot(props.positions.xy, vec2(12989.8, 78233.0))) * 43758.5453);
  if (time_fire > 0.0) {
    // flames: the roof line flickers upward, each corner on its own beat
    float flick = 0.5 + 0.5 * sin(time.clock * (6.0 + 7.0 * rnd) + rnd * 40.0);
    time_tip = flick * time_fire;
    pos.z += time_tip * clamp(elevations * 0.55, 3.5, 13.0) * time_grow;
  }
  if (time.shake > 0.0) {
    // earthquake: the tops sway (exaggerated, like the trees, to read at map scale)
    float amp = time.shake * min(4.0, 0.3 * props.elevations);
    pos.xy += amp * vec2(sin(time.clock * 37.0 + rnd * 3.0) / 88000.0, cos(time.clock * 31.0 + rnd * 5.0) / 111000.0);
  }
}
`;
        return {modules: [timeModule], inject, defines: {TIME_POLYGON_BUILD: 1}};
      case 'mesh-z':
        inject['vs:DECKGL_FILTER_SIZE'] = 'size.z *= time_grow;';
        break;
      case 'mesh':
        inject['vs:DECKGL_FILTER_SIZE'] = 'size *= time_grow;';
        break;
      default:
        break;
    }
    return {modules: [timeModule], inject};
  }

  initializeState(this: Layer<TimeExtensionProps>) {
    this.getAttributeManager()?.add({
      timeYears: {
        size: 2,
        type: 'float32',
        stepMode: 'dynamic',
        accessor: 'getYears'
      }
    });
  }

  draw(this: Layer<TimeExtensionProps>, _params: any, extension: this) {
    const {currentYear, growYears, shrinkYears, endTint} = this.props;
    const uniforms: TimeUniforms = {
      year: currentYear!,
      growYears: Math.max(growYears!, 1e-3),
      shrinkYears: Math.max(shrinkYears!, 1e-3),
      fade: extension.opts.mode === 'fade' ? 1 : 0,
      endTint: endTint!,
      build: extension.opts.mode === 'polygon' ? 1 : 0,
      fx: fxState.fx,
      clock: fxState.clock,
      shake: fxState.shake
    };
    this.setShaderModuleProps({time: uniforms});
  }
}
