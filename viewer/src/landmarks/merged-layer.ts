/**
 * All landmark reconstructions in ONE draw call.
 *
 * Each landmark used to be its own SimpleMeshLayer (~70–150 layers); deck.gl's
 * per-layer overhead (uniforms, bindings) then dominated every frame. Here the
 * meshes are merged once into a single vertex buffer in lng/lat offsets, and
 * every vertex carries its landmark's [start, complete, end, base z] so the
 * vertex shader hides it outside its lifespan and darkens it while being removed.
 * Between start and completion it stands at full height under construction: a
 * frame (floor slabs and columns, the rest see-through) — or, for bridges
 * (`builds` = 1), the whole structure in unpainted steel — then it is finished.
 * Picking colours are per vertex (= landmark index).
 */
import {COORDINATE_SYSTEM, Layer, picking, project32, phongMaterial} from '@deck.gl/core';
import type {DefaultProps, LayerContext, UpdateParameters} from '@deck.gl/core';
import {Geometry, Model} from '@luma.gl/engine';
import type {ShaderModule} from '@luma.gl/shadertools';

export type MergedLandmarks = {
  origin: [number, number];
  positions: Float32Array;
  colors: Float32Array;
  times: Float32Array;
  pickingColors: Float32Array;
  /** per vertex: 0 = frame while under construction, 1 = whole structure in raw steel (bridges) */
  builds?: Float32Array;
};

type LmUniforms = {year: number; quality: number};
const lmModule: ShaderModule<LmUniforms> = {
  name: 'landmarks',
  vs: `layout(std140) uniform landmarksUniforms {
  float year;
  float quality;
} landmarks;
`,
  uniformTypes: {year: 'f32', quality: 'f32'}
};

const vs = `#version 300 es
#define SHADER_NAME landmarks-vs
in vec3 positions;
in vec3 colors;
in vec4 times;
in vec3 pickingColors;
in float builds;
out vec3 vColor;
out vec3 vCommon;
out vec3 vCamera;
out vec3 vLocal;
out float vBuild;
void main(void) {
  float y = landmarks.year;
  bool vis = y >= times.x && y < times.z;
  float ending = smoothstep(times.z - 0.8, times.z, y);
  float grow = 1.0 - ending;
  vec3 p = positions;
  p.z = times.w + (p.z - times.w) * grow;
  vBuild = y < times.y ? 1.0 + builds : 0.0;
  vLocal = vec3(positions.xy * vec2(88000.0, 111000.0), positions.z - times.w);
  picking_setPickingColor(pickingColors);
  vec4 commonPos;
  gl_Position = project_position_to_clipspace(p, vec3(0.0), vec3(0.0), commonPos);
  geometry.position = commonPos;
  DECKGL_FILTER_GL_POSITION(gl_Position, geometry);
  if (!vis) gl_Position = vec4(0.0);
  vCommon = commonPos.xyz;
  vCamera = project.cameraPosition;
  vec3 col = landmarks.quality > 0.5 ? vec3(0.84, 0.69, 0.2) : colors;
  if (vBuild > 1.5) col = mix(col, vec3(0.5, 0.36, 0.3), 0.75);
  vColor = mix(col, vec3(0.42, 0.3, 0.24), 0.5 * ending);
}
`;

const fs = `#version 300 es
#define SHADER_NAME landmarks-fs
precision highp float;
in vec3 vColor;
in vec3 vCommon;
in vec3 vCamera;
in vec3 vLocal;
in float vBuild;
out vec4 fragColor;
void main(void) {
  vec3 c = vColor;
  if (vBuild > 0.5 && vBuild < 1.5) {
    // under construction: a frame of slabs every 3.8 m and columns every 5 m
    vec3 g = vLocal / vec3(5.0, 5.0, 3.8);
    vec3 fw = fwidth(g);
    float detail = 1.0 - smoothstep(0.07, 0.13, max(max(fw.x, fw.y), fw.z));
    vec3 f = abs(fract(g + 0.5) - 0.5);
    float beam = max(max(1.0 - smoothstep(0.05, 0.05 + fw.x, f.x), 1.0 - smoothstep(0.05, 0.05 + fw.y, f.y)), 1.0 - smoothstep(0.07, 0.07 + fw.z, f.z));
    if (beam < 0.5 && detail > 0.5) discard;
    c = vec3(0.66, 0.64, 0.6) * mix(0.72, 1.0, beam);
  }
  vec3 n = normalize(cross(dFdx(vCommon), dFdy(vCommon)));
  // screen-space derivatives give a normal that always faces the camera (as in deck's SimpleMeshLayer)
  fragColor = vec4(lighting_getLightColor(c, vCamera, vCommon, n), 1.0);
  DECKGL_FILTER_COLOR(fragColor, geometry);
}
`;

type Props = {data: any[]; merged: MergedLandmarks; year: number; quality: boolean; material: any};

const defaults: DefaultProps<Props> = {
  merged: {type: 'object', value: null as any, compare: true},
  year: 2026,
  quality: false,
  material: {ambient: 0.56, diffuse: 0.66, shininess: 10, specularColor: [36, 34, 30]}
};

export class LandmarkMeshLayer extends Layer<Props> {
  static layerName = 'LandmarkMeshLayer';
  static defaultProps = defaults;
  state!: {model?: Model};

  getShaders() {
    return super.getShaders({vs, fs, modules: [project32, phongMaterial, picking, lmModule]});
  }

  initializeState(_: LayerContext) {
    this.setState({});
  }

  updateState(params: UpdateParameters<this>) {
    super.updateState(params);
    if (params.props.merged !== params.oldProps.merged || params.changeFlags.extensionsChanged) {
      this.state.model?.destroy();
      this.setState({model: this._getModel()});
    }
  }

  finalizeState(context: LayerContext) {
    super.finalizeState(context);
    this.state.model?.destroy();
  }

  _getModel() {
    const m = this.props.merged;
    if (!m) return undefined;
    return new Model(this.context.device, {
      ...this.getShaders(),
      id: this.props.id,
      geometry: new Geometry({
        topology: 'triangle-list',
        attributes: {
          positions: {size: 3, value: m.positions},
          colors: {size: 3, value: m.colors},
          times: {size: 4, value: m.times},
          pickingColors: {size: 3, value: m.pickingColors},
          builds: {size: 1, value: m.builds ?? new Float32Array(m.positions.length / 3)}
        }
      }),
      isInstanced: false
    });
  }

  draw() {
    const {model} = this.state;
    if (!model) return;
    model.shaderInputs.setProps({landmarks: {year: this.props.year, quality: this.props.quality ? 1 : 0}});
    model.draw(this.context.renderPass);
  }
}

export const LANDMARK_COORDS = {coordinateSystem: COORDINATE_SYSTEM.LNGLAT_OFFSETS};
