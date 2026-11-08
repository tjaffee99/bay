/**
 * Terrain decorations (trees, orchard rows, farmsteads, shrubs) for all visible
 * tiles in one instanced draw per kind.
 *
 * Tiles used to add one SimpleMeshLayer per decoration kind (~100 small layers
 * on screen), and deck.gl's per-layer cost dominated every frame. Now each tile
 * keeps its instances relative to a shared origin; when the set of visible tiles
 * settles, the instances are concatenated per kind and drawn by this layer,
 * which also does the time filter / grow-in in the vertex shader.
 */
import {COORDINATE_SYSTEM, Layer, project32, phongMaterial} from '@deck.gl/core';
import type {DefaultProps, LayerContext, UpdateParameters} from '@deck.gl/core';
import {Geometry, Model} from '@luma.gl/engine';
import type {ShaderModule} from '@luma.gl/shadertools';
import {DECO_MESHES, DECO_MESHES_LOW, treeLod} from './decoration-meshes';

export const DECO_ORIGIN: [number, number] = [-122.2, 37.85];

/** One kind's instances in one tile (positions relative to DECO_ORIGIN). */
export type DecoBatch = {kind: number; count: number; pos: Float32Array; scale: Float32Array; angle: Float32Array; years: Float32Array; color: Uint8Array};

type Merged = {kind: number; data: any};
let merged: Merged[] = [];
let mergedKey = '';

/** Rebuild the per-kind buffers from the given tiles' batches; returns true if changed. */
export function setVisibleDeco(tiles: {key: string; batches: DecoBatch[]}[]): boolean {
  const key = tiles
    .map(t => t.key)
    .sort()
    .join(';');
  if (key === mergedKey) return false;
  mergedKey = key;
  const byKind = new Map<number, DecoBatch[]>();
  for (const t of tiles) for (const b of t.batches) byKind.set(b.kind, [...(byKind.get(b.kind) ?? []), b]);
  merged = [];
  for (const [kind, list] of byKind) {
    const n = list.reduce((a, b) => a + b.count, 0);
    const pos = new Float32Array(n * 3);
    const scale = new Float32Array(n * 3);
    const angle = new Float32Array(n);
    const years = new Float32Array(n * 2);
    const color = new Uint8Array(n * 4);
    let o = 0;
    for (const b of list) {
      pos.set(b.pos, o * 3);
      scale.set(b.scale, o * 3);
      angle.set(b.angle, o);
      years.set(b.years, o * 2);
      color.set(b.color, o * 4);
      o += b.count;
    }
    merged.push({
      kind,
      data: {
        length: n,
        attributes: {
          getPosition: {value: pos, size: 3},
          getScale: {value: scale, size: 3},
          getAngle: {value: angle, size: 1},
          getYears: {value: years, size: 2},
          getColor: {value: color, size: 4, normalized: true}
        }
      }
    });
  }
  return true;
}

export function decoLayers(year: number, zoom: number): Layer[] {
  const lod = treeLod(zoom);
  return merged.map(
    m =>
      new DecoLayer({
        id: `deco-${m.kind}`,
        data: m.data,
        mesh: (lod.low ? DECO_MESHES_LOW : DECO_MESHES)[m.kind],
        // farmsteads are few and big: never thinned
        keep: m.kind === 4 || m.kind === 6 ? 1 : lod.keep,
        coordinateSystem: COORDINATE_SYSTEM.LNGLAT_OFFSETS,
        coordinateOrigin: [DECO_ORIGIN[0], DECO_ORIGIN[1], 0],
        year,
        growYears: m.kind === 4 || m.kind === 6 ? 1.5 : 6,
        shrinkYears: 1
      }) as any
  );
}

// ------------------------------------------------------------------ layer

type DecoUniforms = {year: number; growYears: number; shrinkYears: number; keep: number};
const decoModule: ShaderModule<DecoUniforms> = {
  name: 'deco',
  vs: `layout(std140) uniform decoUniforms {
  float year;
  float growYears;
  float shrinkYears;
  float keep;
} deco;
`,
  uniformTypes: {year: 'f32', growYears: 'f32', shrinkYears: 'f32', keep: 'f32'}
};

const vs = `#version 300 es
#define SHADER_NAME deco-vs
in vec3 positions;
in vec3 colors;
in vec3 instancePositions;
in vec3 instanceScale;
in float instanceAngle;
in vec2 instanceYears;
in vec4 instanceColors;
out vec3 vColor;
out vec3 vCommon;
out vec3 vCamera;
void main(void) {
  float y = deco.year;
  // thinning when zoomed out: a stable pseudo-random subset of instances
  bool vis = y >= instanceYears.x && y < instanceYears.y && fract(float(gl_InstanceID) * 0.6180339887) < deco.keep;
  float ending = smoothstep(instanceYears.y - deco.shrinkYears, instanceYears.y, y);
  float grow = smoothstep(instanceYears.x, instanceYears.x + deco.growYears, y) * (1.0 - ending);
  vec3 m = positions * instanceScale * grow;
  float c = cos(instanceAngle);
  float s = sin(instanceAngle);
  vec3 r = vec3(m.x * c - m.y * s, m.x * s + m.y * c, m.z);
  vec4 commonPos;
  gl_Position = project_position_to_clipspace(instancePositions, vec3(0.0), project_size(r), commonPos);
  geometry.position = commonPos;
  DECKGL_FILTER_GL_POSITION(gl_Position, geometry);
  if (!vis || grow <= 0.0) gl_Position = vec4(0.0);
  vCommon = commonPos.xyz;
  vCamera = project.cameraPosition;
  vColor = colors * instanceColors.rgb;
}
`;

const fs = `#version 300 es
#define SHADER_NAME deco-fs
precision highp float;
in vec3 vColor;
in vec3 vCommon;
in vec3 vCamera;
out vec4 fragColor;
void main(void) {
  vec3 n = normalize(cross(dFdx(vCommon), dFdy(vCommon)));
  fragColor = vec4(lighting_getLightColor(vColor, vCamera, vCommon, n), 1.0);
  DECKGL_FILTER_COLOR(fragColor, geometry);
}
`;

type Props = {data: any; mesh: any; year: number; growYears: number; shrinkYears: number; keep: number; material: any; getColor: any; getAngle: any};

const defaults: DefaultProps<Props> = {
  mesh: {type: 'object', value: null as any, compare: true},
  year: 2026,
  growYears: 6,
  shrinkYears: 1,
  keep: 1,
  getColor: {type: 'accessor', value: [255, 255, 255, 255]},
  getAngle: {type: 'accessor', value: 0},
  material: {ambient: 0.58, diffuse: 0.55, shininess: 4, specularColor: [20, 22, 18]}
};

/** Instanced low-poly mesh with per-instance position / scale / yaw / colour / lifespan. */
export class DecoLayer extends Layer<Props> {
  static layerName = 'DecoLayer';
  static defaultProps = defaults;
  state!: {model?: Model};

  getShaders() {
    return super.getShaders({vs, fs, modules: [project32, phongMaterial, decoModule]});
  }

  initializeState(_: LayerContext) {
    this.getAttributeManager()!.addInstanced({
      instancePositions: {size: 3, accessor: 'getPosition'},
      instanceScale: {size: 3, accessor: 'getScale'},
      instanceAngle: {size: 1, accessor: 'getAngle'},
      instanceYears: {size: 2, accessor: 'getYears'},
      instanceColors: {size: 4, type: 'unorm8', accessor: 'getColor', defaultValue: [255, 255, 255, 255]}
    });
    this.setState({});
  }

  updateState(params: UpdateParameters<this>) {
    super.updateState(params);
    if (params.props.mesh !== params.oldProps.mesh || params.changeFlags.extensionsChanged) {
      this.state.model?.destroy();
      this.setState({model: this._getModel()});
      this.getAttributeManager()!.invalidateAll();
    }
  }

  finalizeState(context: LayerContext) {
    super.finalizeState(context);
    this.state.model?.destroy();
  }

  _getModel() {
    const m = this.props.mesh;
    return new Model(this.context.device, {
      ...this.getShaders(),
      id: this.props.id,
      bufferLayout: this.getAttributeManager()!.getBufferLayouts(),
      geometry: new Geometry({topology: 'triangle-list', attributes: {positions: m.positions, colors: m.colors}}),
      isInstanced: true
    });
  }

  draw() {
    const {model} = this.state;
    if (!model) return;
    const {year, growYears, shrinkYears, keep} = this.props;
    model.shaderInputs.setProps({deco: {year, growYears, shrinkYears, keep}});
    model.draw(this.context.renderPass);
  }
}
