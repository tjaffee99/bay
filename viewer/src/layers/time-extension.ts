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
 *   'polygon' — SolidPolygonLayer buildings: no rise. A building stands at full
 *               height as a frame / scaffold (`time_building` = 1) for its
 *               construction period before start_year — longer for taller ones —
 *               then pops up finished (the layer's shader draws the frame).
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
};

const uniformBlock = /* glsl */ `\
layout(std140) uniform timeUniforms {
  float year;
  float growYears;
  float shrinkYears;
  float fade;
  vec4 endTint;
  float build;
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
`,
  uniformTypes: {
    year: 'f32',
    growYears: 'f32',
    shrinkYears: 'f32',
    fade: 'f32',
    endTint: 'vec4<f32>',
    build: 'f32'
  },
  inject: {
    'vs:#main-start': /* glsl */ `
      time_visible = (time.year >= timeYears.x && time.year < timeYears.y) ? 1.0 : 0.0;
      time_ending = smoothstep(timeYears.y - time.shrinkYears, timeYears.y, time.year);
      time_grow = smoothstep(timeYears.x, timeYears.x + time.growYears, time.year) * (1.0 - time_ending);
      time_building = 0.0;
#ifdef TIME_POLYGON_BUILD
      if (time.build > 0.5) {
        // construction: ~4 months for a house, ~1 year at 40 m, 3 years for a tower
        float dur = clamp(0.25 + elevations / 55.0, 0.33, 3.0);
        time_visible = (time.year >= timeYears.x - dur && time.year < timeYears.y) ? 1.0 : 0.0;
        time_building = time.year < timeYears.x ? 1.0 : 0.0;
        time_grow = 1.0 - time_ending;
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
        inject['pos.z += props.elevations * solidPolygon.elevationScale;'] =
          '\npos.z -= props.elevations * solidPolygon.elevationScale * (1.0 - time_grow);\n';
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
      build: extension.opts.mode === 'polygon' ? 1 : 0
    };
    this.setShaderModuleProps({time: uniforms});
  }
}
