/**
 * Time-varying terrain: Web-Mercator tiles from pipeline/terrain_tiles.py.
 *
 * Each tile is a 65×65 vertex grid with elevation and a land-cover history
 * (up to four covers + three change years per vertex). The vertex shader picks
 * the cover for the current year, blends changes over ~2.5 years, and moves
 * the surface: bay/ocean sits at sea level, marsh and mudflats just above,
 * land at its elevation — so filling the bay visibly raises new ground.
 * The fragment shader shades facets (flat, low-poly look) and turns steep
 * natural slopes into rock (cliffs). Decorations (trees on real canopy pixels,
 * orchard rows, farmsteads) come with each high-zoom tile.
 */
import {COORDINATE_SYSTEM, Layer, project32, phongMaterial} from '@deck.gl/core';
import type {LayerContext, UpdateParameters, DefaultProps} from '@deck.gl/core';
import {TileLayer} from '@deck.gl/geo-layers';
import {SimpleMeshLayer} from '@deck.gl/mesh-layers';
import {Geometry, Model} from '@luma.gl/engine';
import type {ShaderModule} from '@luma.gl/shadertools';
import {loadColumnar} from '../data/columnar';
import {TimeExtension} from './time-extension';
import {DECO_MESHES, DECO_COLORS} from './decoration-meshes';

// cover codes — keep in sync with pipeline/terrain_tiles.py
const PALETTE: [number, number, number][] = [
  [0.56, 0.71, 0.79], // 0 deep water
  [0.66, 0.79, 0.84], // 1 shallow water
  [0.6, 0.55, 0.49], // 2 tidal flat (mud)
  [0.57, 0.6, 0.37], // 3 tidal marsh
  [0.93, 0.88, 0.74], // 4 beach
  [0.9, 0.84, 0.66], // 5 dunes
  [0.8, 0.77, 0.52], // 6 grassland (golden hills)
  [0.56, 0.58, 0.39], // 7 scrub / chaparral
  [0.55, 0.6, 0.38], // 8 oak woodland
  [0.36, 0.48, 0.3], // 9 forest
  [0.82, 0.75, 0.5], // 10 farmland
  [0.6, 0.69, 0.41], // 11 orchard
  [0.64, 0.64, 0.42], // 12 vineyard
  [0.69, 0.76, 0.48], // 13 pasture
  [0.86, 0.73, 0.7], // 14 salt pond
  [0.63, 0.61, 0.43], // 15 diked wetland
  [0.86, 0.84, 0.79], // 16 urban
  [0.62, 0.73, 0.47], // 17 park
  [0.68, 0.64, 0.58], // 18 rock
  [0.44, 0.57, 0.35], // 19 riparian
  [0.75, 0.71, 0.63], // 20 fill
  [0.56, 0.63, 0.47], // 21 freshwater wetland
  [0.62, 0.76, 0.83], // 22 reservoir / lake
  [0.32, 0.25, 0.21] // 23 burned (1906)
];

const N = 65;
const TILE_ZOOM_DETAIL = 14;

type TerrainUniforms = {year: number; exaggeration: number};
const terrainModule: ShaderModule<TerrainUniforms> = {
  name: 'terrain',
  vs: `layout(std140) uniform terrainUniforms {
  float year;
  float exaggeration;
} terrain;
`,
  fs: `layout(std140) uniform terrainUniforms {
  float year;
  float exaggeration;
} terrain;
`,
  uniformTypes: {year: 'f32', exaggeration: 'f32'}
};

const glslPalette = `const vec3 PAL[${PALETTE.length}] = vec3[${PALETTE.length}](${PALETTE.map(c => `vec3(${c.map(v => v.toFixed(3)).join(',')})`).join(',')});`;

const vs = `#version 300 es
#define SHADER_NAME terrain-tile-vs
in vec3 positions;
in vec4 covers;
in float cover4;
in vec4 years;
in float skirt;
out vec4 vColor;
out vec3 vCommon;
out float vWater;
out vec3 vCamera;
${glslPalette}
float coverZ(float c, float z) {
  if (c < 1.5) return 0.0;                         // bay / ocean surface
  if (abs(c - 22.0) < 0.5) return z;               // reservoir surface
  if (abs(c - 2.0) < 0.5) return 0.25;             // tidal flat
  if (abs(c - 3.0) < 0.5) return 0.6;              // tidal marsh
  if (abs(c - 14.0) < 0.5) return 0.35;            // salt pond
  return max(z, 0.9);                              // land
}
float waterness(float c) { return (c < 1.5 || abs(c - 22.0) < 0.5 || abs(c - 14.0) < 0.5) ? 1.0 : 0.0; }
void main(void) {
  float y = terrain.year;
  float c = covers.x;
  float prev = covers.x;
  float t0 = -100000.0;
  if (years.x > 0.0 && y >= years.x) { prev = c; c = covers.y; t0 = years.x; }
  if (years.y > 0.0 && y >= years.y) { prev = c; c = covers.z; t0 = years.y; }
  if (years.z > 0.0 && y >= years.z) { prev = c; c = covers.w; t0 = years.z; }
  if (years.w > 0.0 && y >= years.w) { prev = c; c = cover4; t0 = years.w; }
  // land changes blend over ~2.5 years; fire is instant
  float dur = abs(c - 23.0) < 0.5 ? 0.04 : 2.5;
  float k = smoothstep(0.0, 1.0, clamp((y - t0) / dur, 0.0, 1.0));
  vec3 col = mix(PAL[int(prev + 0.5)], PAL[int(c + 0.5)], k);
  float z = mix(coverZ(prev, positions.z), coverZ(c, positions.z), k) * terrain.exaggeration;
  if (skirt > 0.5) z -= 80.0;
  vWater = mix(waterness(prev), waterness(c), k);
  vec4 commonPos;
  gl_Position = project_position_to_clipspace(vec3(positions.xy, z), vec3(0.0), vec3(0.0), commonPos);
  vCommon = commonPos.xyz;
  vCamera = project.cameraPosition;
  vColor = vec4(col, 1.0);
}
`;

const fs = `#version 300 es
#define SHADER_NAME terrain-tile-fs
precision highp float;
in vec4 vColor;
in vec3 vCommon;
in float vWater;
in vec3 vCamera;
out vec4 fragColor;
void main(void) {
  vec3 n = normalize(cross(dFdx(vCommon), dFdy(vCommon)));
  if (n.z < 0.0) n = -n;
  vec3 base = vColor.rgb;
  float steep = 1.0 - n.z;
  base = mix(base, vec3(0.64, 0.6, 0.54), smoothstep(0.45, 0.75, steep) * 0.75 * (1.0 - vWater));
  vec3 lit = lighting_getLightColor(base, vCamera, vCommon, n);
  // water: keep it calm and bright
  lit = mix(lit, base * 1.02, vWater * 0.7);
  fragColor = vec4(lit, 1.0);
}
`;

export type TerrainMesh = {
  positions: Float32Array;
  covers: Float32Array;
  cover4: Float32Array;
  years: Float32Array;
  skirt: Float32Array;
  indices: Uint32Array;
  origin: [number, number];
};

type TerrainMeshLayerProps = {mesh: TerrainMesh; currentYear: number; exaggeration: number; material: any};

const meshDefaults: DefaultProps<TerrainMeshLayerProps> = {
  mesh: {type: 'object', value: null as any, compare: true},
  currentYear: 2026,
  exaggeration: 1,
  material: {ambient: 0.62, diffuse: 0.55, shininess: 4, specularColor: [20, 20, 20]}
};

/** One terrain tile mesh. */
class TerrainMeshLayer extends Layer<TerrainMeshLayerProps> {
  static layerName = 'TerrainMeshLayer';
  static defaultProps = meshDefaults;
  state!: {model?: Model};

  getShaders() {
    return super.getShaders({vs, fs, modules: [project32, phongMaterial, terrainModule]});
  }

  initializeState(_: LayerContext) {
    this.setState({});
  }

  updateState(params: UpdateParameters<this>) {
    super.updateState(params);
    if (params.props.mesh !== params.oldProps.mesh || params.changeFlags.extensionsChanged) {
      this.state.model?.destroy();
      this.setState({model: this._getModel()});
    }
  }

  finalizeState(context: LayerContext) {
    super.finalizeState(context);
    this.state.model?.destroy();
  }

  _getModel() {
    const m = this.props.mesh;
    if (!m) return undefined;
    return new Model(this.context.device, {
      ...this.getShaders(),
      id: this.props.id,
      geometry: new Geometry({
        topology: 'triangle-list',
        attributes: {
          positions: {size: 3, value: m.positions},
          covers: {size: 4, value: m.covers},
          cover4: {size: 1, value: m.cover4},
          years: {size: 4, value: m.years},
          skirt: {size: 1, value: m.skirt}
        },
        indices: {size: 1, value: m.indices}
      }),
      isInstanced: false
    });
  }

  draw() {
    const {model} = this.state;
    if (!model) return;
    model.shaderInputs.setProps({terrain: {year: this.props.currentYear, exaggeration: this.props.exaggeration}});
    model.draw(this.context.renderPass);
  }
}

// ------------------------------------------------------------------ tile decoding

const R = 6378137;
function tileLon(x: number, z: number) {
  return (x / 2 ** z) * 360 - 180;
}
function tileLat(y: number, z: number) {
  const n = Math.PI - (2 * Math.PI * y) / 2 ** z;
  return (180 / Math.PI) * Math.atan(Math.sinh(n));
}
void R;

const indexCache = new Map<number, Uint32Array>();
function gridIndices(n: number) {
  let idx = indexCache.get(n);
  if (idx) return idx;
  const quads = (n - 1) * (n - 1) + 4 * (n - 1);
  idx = new Uint32Array(quads * 6);
  let k = 0;
  const q = (a: number, b: number, c: number, d: number) => {
    idx![k++] = a;
    idx![k++] = b;
    idx![k++] = d;
    idx![k++] = b;
    idx![k++] = c;
    idx![k++] = d;
  };
  for (let i = 0; i < n - 1; i++)
    for (let j = 0; j < n - 1; j++) q(i * n + j, i * n + j + 1, (i + 1) * n + j + 1, (i + 1) * n + j);
  // skirts: 4 edges, skirt vertices start at n*n in edge order (top, right, bottom, left)
  const base = n * n;
  const edge = (e: number, t: number) => base + e * n + t;
  const top = (t: number) => t;
  const right = (t: number) => t * n + (n - 1);
  const bottom = (t: number) => (n - 1) * n + t;
  const left = (t: number) => t * n;
  const edges = [top, right, bottom, left];
  for (let e = 0; e < 4; e++)
    for (let t = 0; t < n - 1; t++) q(edges[e](t), edges[e](t + 1), edge(e, t + 1), edge(e, t));
  indexCache.set(n, idx);
  return idx;
}

export type DecoInstances = {kind: number; data: any; count: number; scale: Float32Array}[];
export type TileContent = {mesh: TerrainMesh; deco: DecoInstances} | null;

function decodeYear(v: number) {
  return v === 0 ? 0 : v / 10 + 1000;
}

async function fetchTile(z: number, x: number, y: number) {
  try {
    return await loadColumnar(`tiles/terrain/${z}/${x}/${y}.bin.gz`);
  } catch {
    return null;
  }
}

/** Load a tile; z14 outside the San Francisco detail grid falls back to a quadrant of its z13 parent. */
export async function loadTerrainTile(z: number, x: number, y: number): Promise<TileContent> {
  let f = await fetchTile(z, x, y);
  let sub = {r0: 0, c0: 0, step: 1, n: N, srcZ: z, srcX: x, srcY: y};
  if (!f && z === TILE_ZOOM_DETAIL) {
    f = await fetchTile(z - 1, x >> 1, y >> 1);
    if (!f) return null;
    sub = {r0: (y & 1) * 32, c0: (x & 1) * 32, step: 1, n: 33, srcZ: z - 1, srcX: x >> 1, srcY: y >> 1};
  }
  if (!f) return null;
  const c = f.columns;
  const elev = c.elev as Int16Array;
  const cov = c.cover as Uint8Array;
  const yrs = c.year as Uint16Array;
  const n = sub.n;
  const west = tileLon(x, z);
  const east = tileLon(x + 1, z);
  const north = tileLat(y, z);
  const nv = n * n + 4 * n;
  const positions = new Float32Array(nv * 3);
  const covers = new Float32Array(nv * 4);
  const cover4 = new Float32Array(nv);
  const years = new Float32Array(nv * 4);
  const skirt = new Float32Array(nv);
  const latAt = (i: number) => tileLat(y + i / (n - 1), z) - north;
  const lats = Array.from({length: n}, (_, i) => latAt(i));
  const setV = (v: number, i: number, j: number) => {
    const src = (sub.r0 + i) * N + (sub.c0 + j);
    positions[v * 3] = ((east - west) * j) / (n - 1);
    positions[v * 3 + 1] = lats[i];
    positions[v * 3 + 2] = elev[src] / 10;
    for (let k = 0; k < 4; k++) covers[v * 4 + k] = cov[src * 5 + k];
    cover4[v] = cov[src * 5 + 4];
    for (let k = 0; k < 4; k++) years[v * 4 + k] = decodeYear(yrs[src * 4 + k]);
  };
  for (let i = 0; i < n; i++) for (let j = 0; j < n; j++) setV(i * n + j, i, j);
  const edges: [number, number][][] = [
    Array.from({length: n}, (_, t) => [0, t]),
    Array.from({length: n}, (_, t) => [t, n - 1]),
    Array.from({length: n}, (_, t) => [n - 1, t]),
    Array.from({length: n}, (_, t) => [t, 0])
  ];
  edges.forEach((edge, e) =>
    edge.forEach(([i, j], t) => {
      const v = n * n + e * n + t;
      setV(v, i, j);
      skirt[v] = 1;
    })
  );
  const mesh: TerrainMesh = {positions, covers, cover4, years, skirt, indices: gridIndices(n), origin: [west, north]};

  // decorations
  const deco: DecoInstances = [];
  const dpos = c.deco_pos as Uint16Array | undefined;
  if (dpos && dpos.length) {
    const kinds = c.deco_kind as Uint8Array;
    const sizes = c.deco_size as Uint8Array;
    const dy = c.deco_years as Uint16Array;
    const groups = new Map<number, number[]>();
    for (let i = 0; i < kinds.length; i++) {
      let gx = (dpos[i * 2] / 65535) * (N - 1);
      let gy = (dpos[i * 2 + 1] / 65535) * (N - 1);
      if (sub.n !== N) {
        gx -= sub.c0;
        gy -= sub.r0;
        if (gx < 0 || gy < 0 || gx > n - 1 || gy > n - 1) continue;
      }
      if (kinds[i] <= 1 && kinds.length > 6000 && (i * 2654435761) % 5 >= 2) continue;
      const arr = groups.get(kinds[i]) ?? [];
      arr.push(i);
      groups.set(kinds[i], arr);
    }
    const elevAt = (gx: number, gy: number) => {
      const j0 = Math.min(Math.floor(gx), N - 2);
      const i0 = Math.min(Math.floor(gy), N - 2);
      const fx = gx - j0;
      const fy = gy - i0;
      const e = (i: number, j: number) => Math.max(elev[i * N + j] / 10, 0.9);
      return (e(i0, j0) * (1 - fx) + e(i0, j0 + 1) * fx) * (1 - fy) + (e(i0 + 1, j0) * (1 - fx) + e(i0 + 1, j0 + 1) * fx) * fy;
    };
    for (const [kind, ids] of groups) {
      const m = ids.length;
      const pos = new Float32Array(m * 3);
      const scl = new Float32Array(m * 3);
      const yr = new Float32Array(m * 2);
      const col = new Uint8Array(m * 4);
      const pal = DECO_COLORS[kind] ?? DECO_COLORS[0];
      ids.forEach((i, k) => {
        const gx = (dpos[i * 2] / 65535) * (N - 1);
        const gy = (dpos[i * 2 + 1] / 65535) * (N - 1);
        const lx = sub.n !== N ? gx - sub.c0 : gx;
        const ly = sub.n !== N ? gy - sub.r0 : gy;
        pos[k * 3] = ((east - west) * lx) / (n - 1);
        pos[k * 3 + 1] = tileLat(y + ly / (n - 1), z) - north;
        pos[k * 3 + 2] = elevAt(gx, gy) - 0.3;
        const s = sizes[i];
        // stylised: crowns ~2x and trunks ~1.5x real size so trees read at city scale (Civ-like)
        const crown = kind === 4 ? s : Math.max(4.5, s * 0.62);
        scl[k * 3] = crown;
        scl[k * 3 + 1] = crown;
        scl[k * 3 + 2] = kind === 4 ? s : s * 1.45;
        yr[k * 2] = dy[i * 2] ? decodeYear(dy[i * 2]) : -10000;
        yr[k * 2 + 1] = dy[i * 2 + 1] ? decodeYear(dy[i * 2 + 1]) : 10000;
        col.set(pal[(i * 2654435761) % pal.length >>> 0] ?? pal[0], k * 4);
        col[k * 4 + 3] = 255;
      });
      deco.push({
        kind,
        count: m,
        scale: scl,
        data: {
          length: m,
          attributes: {
            getPosition: {value: pos, size: 3},
            getYears: {value: yr, size: 2},
            getColor: {value: col, size: 4, normalized: true}
          }
        }
      });
    }
  }
  return {mesh, deco};
}

const decoTime = new TimeExtension({mode: 'mesh'});

export function terrainLayer(year: number, extent: [number, number, number, number]) {
  return new TileLayer<TileContent>({
    id: 'terrain',
    minZoom: 8,
    maxZoom: TILE_ZOOM_DETAIL,
    tileSize: 256,
    extent,
    zRange: [-80, 1300],
    maxRequests: 12,
    refinementStrategy: 'best-available',
    getTileData: ({index}: any) => loadTerrainTile(index.z, index.x, index.y),
    updateTriggers: {renderSubLayers: [Math.round(year * 20) / 20]},
    renderSubLayers: (props: any) => {
      const content = props.data as TileContent;
      if (!content) return null;
      const {mesh, deco} = content;
      const common = {coordinateSystem: COORDINATE_SYSTEM.LNGLAT_OFFSETS, coordinateOrigin: [mesh.origin[0], mesh.origin[1], 0]};
      const layers: any[] = [
        new TerrainMeshLayer({id: `${props.id}-mesh`, mesh, currentYear: year, exaggeration: 1, ...common} as any)
      ];
      for (const d of deco) {
        layers.push(
          new SimpleMeshLayer({
            id: `${props.id}-deco-${d.kind}`,
            data: d.data,
            mesh: DECO_MESHES[d.kind],
            ...common,
            // SimpleMeshLayer builds its model matrix from accessors (binary getScale is ignored)
            getScale: (_: any, {index, target}: any) => {
              target[0] = d.scale[index * 3];
              target[1] = d.scale[index * 3 + 1];
              target[2] = d.scale[index * 3 + 2];
              return target;
            },
            getOrientation: (_: any, {index, target}: any) => {
              target[0] = 0;
              target[1] = ((index * 2654435761) % 360) >>> 0;
              target[2] = 0;
              return target;
            },
            material: {ambient: 0.58, diffuse: 0.55, shininess: 4, specularColor: [20, 22, 18]},
            pickable: false,
            extensions: [decoTime],
            currentYear: year,
            growYears: d.kind === 4 ? 1.5 : 6,
            shrinkYears: 1
          } as any)
        );
      }
      return layers;
    }
  });
}
