/**
 * All landmark reconstructions in ONE draw call.
 *
 * Each landmark used to be its own SimpleMeshLayer (~70–150 layers); deck.gl's
 * per-layer overhead (uniforms, bindings) then dominated every frame. Here the
 * meshes are merged once into a single vertex buffer in lng/lat offsets, and
 * every vertex carries its landmark's [start, complete, end, base z] so the
 * vertex shader does what TimeExtension('mesh-z') did per layer: hide outside
 * the lifespan, rise over the construction years, darken while being removed.
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
out vec3 vColor;
out vec3 vCommon;
out vec3 vCamera;
void main(void) {
  float y = landmarks.year;
  bool vis = y >= times.x && y < times.z;
  float ending = smoothstep(times.z - 0.8, times.z, y);
  float grow = smoothstep(times.x, max(times.y, times.x + 0.5), y) * (1.0 - ending);
  vec3 p = positions;
  p.z = times.w + (p.z - times.w) * grow;
  picking_setPickingColor(pickingColors);
  vec4 commonPos;
  gl_Position = project_position_to_clipspace(p, vec3(0.0), vec3(0.0), commonPos);
  if (!vis) gl_Position = vec4(0.0);
  vCommon = commonPos.xyz;
  vCamera = project.cameraPosition;
  vec3 col = landmarks.quality > 0.5 ? vec3(0.84, 0.69, 0.2) : colors;
  vColor = mix(col, vec3(0.42, 0.3, 0.24), 0.5 * ending);
}
`;

const fs = `#version 300 es
#define SHADER_NAME landmarks-fs
precision highp float;
in vec3 vColor;
in vec3 vCommon;
in vec3 vCamera;
out vec4 fragColor;
void main(void) {
  vec3 n = normalize(cross(dFdx(vCommon), dFdy(vCommon)));
  // screen-space derivatives give a normal that always faces the camera (as in deck's SimpleMeshLayer)
  fragColor = picking_filterColor(vec4(lighting_getLightColor(vColor, vCamera, vCommon, n), 1.0));
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
          pickingColors: {size: 3, value: m.pickingColors}
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
