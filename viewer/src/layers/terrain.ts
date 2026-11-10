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
import {Geometry, Model} from '@luma.gl/engine';
import type {ShaderModule} from '@luma.gl/shadertools';
import {decoLayers, setVisibleDeco, type DecoBatch} from './deco-layer';
import {TILE_ZOOM_DETAIL, gridIndices, loadTerrainTile, type TerrainMesh, type TileContent} from './terrain-tile';

export {loadTerrainTile};
export type {TerrainMesh, TileContent};

// cover codes — keep in sync with pipeline/terrain_tiles.py
const PALETTE: [number, number, number][] = [
  [0.56, 0.71, 0.79], // 0 deep water
  [0.66, 0.79, 0.84], // 1 shallow water
  [0.56, 0.56, 0.5], // 2 tidal flat (wet mud)
  [0.52, 0.58, 0.38], // 3 tidal marsh
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
  [0.52, 0.6, 0.55], // 14 salt pond (evaporator colours in the shader)
  [0.6, 0.61, 0.45], // 15 diked wetland
  [0.8, 0.78, 0.73], // 16 urban (city ground: streets, pavement, small yards)
  [0.62, 0.73, 0.47], // 17 park
  [0.68, 0.64, 0.58], // 18 rock
  [0.44, 0.57, 0.35], // 19 riparian
  [0.75, 0.71, 0.63], // 20 fill
  [0.56, 0.63, 0.47], // 21 freshwater wetland
  [0.62, 0.76, 0.83], // 22 reservoir / lake
  [0.32, 0.25, 0.21], // 23 burned (1906)
  [0.66, 0.69, 0.56] // 24 suburban (houses in yards and trees)
];


type TerrainUniforms = {year: number; exaggeration: number; latScale: number; latBase: [number, number]};
const terrainModule: ShaderModule<TerrainUniforms> = {
  name: 'terrain',
  vs: `layout(std140) uniform terrainUniforms {
  float year;
  float exaggeration;
  float latScale;
  vec2 latBase;
} terrain;
`,
  fs: `layout(std140) uniform terrainUniforms {
  float year;
  float exaggeration;
  float latScale;
  vec2 latBase;
} terrain;
`,
  uniformTypes: {year: 'f32', exaggeration: 'f32', latScale: 'f32', latBase: 'vec2<f32>'}
};


// How the land cover is drawn. Covers live on the grid vertices (30 m in SF, 60 m
// elsewhere). Interpolating their colours across triangles looked like blurry
// 30 m pixels; snapping to the nearest vertex showed the grid's staircase. Instead,
// each tile's current cover colours go into a small texture (one texel per vertex,
// alpha = water), refreshed when the year changes. The fragment shader takes a
// smooth B-spline sample of it (a 4×4 neighbourhood) and snaps that to the nearest
// of the surrounding real covers, with a little noise: crisp edges that follow
// rounded, natural curves instead of grid steps. Hills are smooth-shaded.
const vs = `#version 300 es
#define SHADER_NAME terrain-tile-vs
in vec3 positions;
in vec4 covers;
in float cover4;
in vec4 years;
in float skirt;
in float fade;
in vec3 normals;
in vec2 uv;
out vec2 vUv;
out float vSkirt;
out float vFade;
out vec3 vNormal;
out vec3 vCommon;
out vec3 vCamera;
out vec2 vLngLat;
float coverZ(float c, float z) {
  if (c < 1.5) return 0.0;                         // bay / ocean surface
  if (abs(c - 22.0) < 0.5) return z;               // reservoir surface
  if (abs(c - 2.0) < 0.5) return 0.25;             // tidal flat
  if (abs(c - 3.0) < 0.5) return 0.6;              // tidal marsh
  if (abs(c - 14.0) < 0.5) return 0.35;            // salt pond
  return max(z, 0.9);                              // land
}
float waterness(float c) { return (c < 1.5 || abs(c - 22.0) < 0.5 || abs(c - 14.0) < 0.5) ? 1.0 : 0.0; }
// bay, tidal flat, salt pond, reservoir: what a building must not stand on
float openWater(float c) { return (c < 2.5 || abs(c - 22.0) < 0.5 || abs(c - 14.0) < 0.5) ? 1.0 : 0.0; }
void main(void) {
  float y = terrain.year;
  float c = covers.x;
  float prev = covers.x;
  float t0 = -100000.0;
  if (years.x > 0.0 && y >= years.x) { prev = c; c = covers.y; t0 = years.x; }
  if (years.y > 0.0 && y >= years.y) { prev = c; c = covers.z; t0 = years.y; }
  if (years.z > 0.0 && y >= years.z) { prev = c; c = covers.w; t0 = years.z; }
  if (years.w > 0.0 && y >= years.w) { prev = c; c = cover4; t0 = years.w; }
  float dur = abs(c - 23.0) < 0.5 ? 0.04 : 2.5;
  // made land is there within half a year (a 2.5-year fade left buildings standing on
  // half-blue ground for a year or two after their fill date)
  if (openWater(prev) > 0.5 && openWater(c) < 0.5) dur = 0.5;
  float k = smoothstep(0.0, 1.0, clamp((y - t0) / dur, 0.0, 1.0));
  float wet = mix(waterness(prev), waterness(c), k);
  float z = mix(coverZ(prev, positions.z), coverZ(c, positions.z), k) * terrain.exaggeration;
  if (skirt > 0.5) z -= 80.0;
  vUv = uv;
  vSkirt = skirt;
  vFade = fade;
  // water lies flat; land uses the elevation grid's normal
  vNormal = project_normal(normalize(mix(normals, vec3(0.0, 0.0, 1.0), wet)));
  vec4 commonPos;
  gl_Position = project_position_to_clipspace(vec3(positions.xy, z), vec3(0.0), vec3(0.0), commonPos);
  geometry.position = commonPos;
  DECKGL_FILTER_GL_POSITION(gl_Position, geometry);
  vCommon = commonPos.xyz;
  vCamera = project.cameraPosition;
  vLngLat = positions.xy + project.coordinateOrigin.xy;
}
`;

const fs = `#version 300 es
#define SHADER_NAME terrain-tile-fs
precision highp float;
uniform sampler2D coverTex;
in vec2 vUv;
in float vSkirt;
in float vFade;
in vec3 vNormal;
in vec3 vCommon;
in vec3 vCamera;
in vec2 vLngLat;
out vec4 fragColor;
float hash(vec2 p) { return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453); }
float vnoise(vec2 p) {
  vec2 i = floor(p);
  vec2 f = fract(p);
  f = f * f * (3.0 - 2.0 * f);
  return mix(mix(hash(i), hash(i + vec2(1.0, 0.0)), f.x), mix(hash(i + vec2(0.0, 1.0)), hash(i + vec2(1.0, 1.0)), f.x), f.y);
}
// cubic B-spline sample from 4 bilinear taps
vec4 bspline(vec2 st, vec2 size) {
  vec2 i = floor(st);
  vec2 f = st - i;
  vec2 f2 = f * f;
  vec2 f3 = f2 * f;
  vec2 w0 = (-f3 + 3.0 * f2 - 3.0 * f + 1.0) / 6.0;
  vec2 w1 = (3.0 * f3 - 6.0 * f2 + 4.0) / 6.0;
  vec2 w2 = (-3.0 * f3 + 3.0 * f2 + 3.0 * f + 1.0) / 6.0;
  vec2 w3 = f3 / 6.0;
  vec2 g0 = w0 + w1;
  vec2 g1 = w2 + w3;
  vec2 h0 = (i - 1.0 + w1 / g0 + 0.5) / size;
  vec2 h1 = (i + 1.0 + w3 / g1 + 0.5) / size;
  return g0.y * (g0.x * texture(coverTex, vec2(h0.x, h0.y)) + g1.x * texture(coverTex, vec2(h1.x, h0.y)))
       + g1.y * (g0.x * texture(coverTex, vec2(h0.x, h1.y)) + g1.x * texture(coverTex, vec2(h1.x, h1.y)));
}
// ---- farm patterns (procedural; cover code in the texel alpha, see coverColors)
// L = position in z13 lattice cells (76 m) local to the tile (precise), B = the tile's
// lattice origin (integer, a multiple of 4) for field ids. Orchard crowns stand on a
// 1/9-cell grid (8.5 m) offset by half a step; the 3D orchard trees on every 3rd of them.
// integer hash shared with pipeline/terrain_tiles.py (block_hash): which 4x4-cell
// orchard blocks are other fields, so the 3D orchard trees skip the same blocks
float blockHash(vec2 b) {
  uvec2 v = uvec2(ivec2(b));
  uint h = v.x * 1664525u + v.y * 1013904223u;
  h ^= h >> 16;
  h *= 2246822519u;
  h ^= h >> 13;
  h *= 3266489917u;
  h ^= h >> 16;
  return float(h & 65535u) / 65535.0;
}
float ih(vec2 p) {
  uvec2 v = uvec2(ivec2(floor(p)) + ivec2(1 << 20));
  uint h = v.x * 1664525u + v.y * 1013904223u;
  h ^= h >> 16; h *= 2246822519u; h ^= h >> 13; h *= 3266489917u; h ^= h >> 16;
  return float(h & 65535u) / 65535.0;
}
float inoise(vec2 p) {
  vec2 i = floor(p);
  vec2 f = fract(p);
  f = f * f * (3.0 - 2.0 * f);
  return mix(mix(ih(i), ih(i + vec2(1.0, 0.0)), f.x), mix(ih(i + vec2(0.0, 1.0)), ih(i + vec2(1.0, 1.0)), f.x), f.y);
}
// antialiased line coverage: thinner than a pixel, it fades to its area share
float lineCover(float d, float halfW, float px) {
  px = max(px, 1e-5);
  return clamp((halfW - d) / px + 0.5, 0.0, 1.0) * min(1.0, 2.0 * halfW / px);
}
vec3 farmPattern(vec3 base, int code, vec2 L, vec2 B, float px) {
  vec2 blk = floor(L / 4.0);
  vec2 bid = B / 4.0 + blk;
  vec2 bp = L / 4.0 - blk;                 // 0..1 inside a 4x4-cell block (306 m)
  float h0 = hash(bid + 0.37);
  float h1 = hash(bid + 17.3);
  // each block is split in two fields, across x or y
  bool splitX = h0 < 0.5;
  float cut = 0.3 + 0.4 * h1;
  float side = splitX ? step(cut, bp.x) : step(cut, bp.y);
  float hf = hash(bid * 1.7 + side * 5.3 + 2.1);
  float hr = hash(bid * 2.3 + side * 3.1 + 7.7);
  // distance to field edges in cells
  vec2 eb = min(bp, 1.0 - bp) * 4.0;
  float dEdge = min(min(eb.x, eb.y), abs((splitX ? bp.x : bp.y) - cut) * 4.0);
  float rowsAlongX = step(0.5, hr);
  float hb = blockHash(bid);
  if (code == 2 && hb < 0.2) code = 1;            // not every block of an orchard district is orchard
  if (code == 1) {
    // farmland: fields in staggered rows (each row of 4-cell fields shifted, so the
    // boundaries don't line up into a grid), each field one crop — grain gold, green
    // crop, ploughed, stubble, hay — with faint crop rows and soft edges
    vec2 P = L + B;
    float rowi = floor(P.y / 3.0);
    float off = ih(vec2(rowi, 17.0)) * 4.0;
    float wfield = 3.0 + 3.0 * ih(vec2(rowi, 29.0));
    float fx = (P.x + off) / wfield;
    vec2 fid = vec2(floor(fx), rowi);
    float hf1 = ih(fid * 1.13 + 3.0);
    float hr1 = ih(fid * 2.71 + 8.0);
    vec2 fp = vec2(fract(fx) * wfield, fract(P.y / 3.0) * 3.0);
    float dE = min(min(fp.x, wfield - fp.x), min(fp.y, 3.0 - fp.y));
    vec3 f = hf1 < 0.3 ? vec3(0.86, 0.77, 0.5) : hf1 < 0.5 ? vec3(0.63, 0.68, 0.43) : hf1 < 0.66 ? vec3(0.66, 0.56, 0.43)
           : hf1 < 0.85 ? vec3(0.85, 0.8, 0.62) : vec3(0.76, 0.74, 0.5);
    vec3 c = mix(base, f, 0.6);
    float per = 0.08;                                  // crop rows, ~6 m
    float u = (hr1 > 0.5 ? L.y : L.x) / per;
    c *= 1.0 + (abs(fract(u) - 0.5) * 2.0 - 0.5) * 0.05 * smoothstep(2.0, 5.0, per / px);
    return mix(c, vec3(0.58, 0.56, 0.42), lineCover(dE, 0.015, px) * 0.45);
  }
  if (code == 2) {
    // orchard: crowns on the 8.5 m grid over a grassy floor; blocks of different ages
    // prunes (dark), apricots / cherries (lighter), walnuts (big crowns); tilled or grassy floor
    vec3 crown = hb < 0.55 ? vec3(0.36, 0.5, 0.27) : hb < 0.85 ? vec3(0.46, 0.6, 0.31) : vec3(0.4, 0.53, 0.33);
    crown *= 0.94 + 0.12 * hf;
    vec3 soil = hr < 0.5 ? vec3(0.78, 0.74, 0.55) : vec3(0.72, 0.78, 0.5);
    float r = hb >= 0.85 ? 0.43 : 0.3 + 0.1 * hf;   // young blocks have smaller crowns
    // no trees on the lanes along the block edges
    float lane = smoothstep(0.03, 0.06, dEdge);
    vec2 q = fract(L * 9.0 + 0.5) - 0.5;          // crowns at (k + 0.5) / 9 cells
    float d = length(q);
    float aa = px * 9.0 * 0.75 + 1e-4;
    float k = (1.0 - smoothstep(r - aa, r + aa, d)) * lane;
    float avg = 3.14159 * r * r;
    float vis = smoothstep(1.5, 4.0, 1.0 / (9.0 * px));
    float cov = mix(avg * mix(1.0, lane, 0.5), k, vis);
    vec3 c = mix(soil, crown, cov);
    c = mix(base, c, 0.85);
    return mix(c, vec3(0.6, 0.58, 0.42), lineCover(dEdge, 0.015, px) * 0.6);
  }
  if (code == 3) {
    // vineyard: rows ~2.8 m apart, across the block's long axis
    float u = (rowsAlongX > 0.5 ? L.y : L.x) * 27.0;
    float k = 1.0 - smoothstep(0.25, 0.45, abs(fract(u) - 0.5));
    float vis = smoothstep(1.5, 4.0, 1.0 / (27.0 * px));
    vec3 c = mix(vec3(0.72, 0.64, 0.46), vec3(0.47, 0.56, 0.3), mix(0.45, k, vis));
    c = mix(base, c, 0.8);
    return mix(c, vec3(0.6, 0.58, 0.42), lineCover(dEdge, 0.015, px) * 0.6);
  }
  if (code == 4) {
    // pasture: paddocks of slightly different grass
    vec3 c = base * (0.95 + 0.1 * hf);
    return mix(c, base * 0.85, lineCover(dEdge, 0.01, px) * 0.5);
  }
  return base;
}
int coverCode(vec4 t) { return t.a < 0.25 ? int(floor(t.a * 255.0 / 8.0 + 0.5)) : 0; }
// ---- bay shore (procedural detail on real covers): value noise on an integer hash,
// in global lattice cells (P = tile lattice + its origin), stable at any coordinate
// thin meandering lines where a two-octave noise crosses 0.5 (tidal channels)
float channels(vec2 P, float scale, float halfW, float px) {
  float n = inoise(P * scale) * 0.65 + inoise(P * scale * 2.3 + 7.1) * 0.35;
  float d = abs(n - 0.5);
  float w = fwidth(n) + 1e-5;
  return (1.0 - smoothstep(halfW - w, halfW + w, d)) * smoothstep(0.004, 0.02, halfW / max(px * scale, 1e-5));
}
vec3 shorePattern(vec3 base, int code, vec2 P, float px) {
  if (code == 5) {
    // tidal marsh: pickleweed and cordgrass, darker patches, sloughs and channels
    vec3 c = base * (0.92 + 0.16 * inoise(P * 1.7));
    c = mix(c, vec3(0.44, 0.5, 0.36), 0.35 * smoothstep(0.55, 0.8, inoise(P * 0.6 + 3.3)));
    float ch = channels(P, 0.55, 0.016, px);
    return mix(c, vec3(0.42, 0.52, 0.54), ch);
  }
  if (code == 6) {
    // tidal flat: wet grey mud, mottled, with water-filled rills
    vec3 c = mix(vec3(0.5, 0.51, 0.47), vec3(0.62, 0.6, 0.54), inoise(P * 1.3) * 0.7 + inoise(P * 4.1) * 0.3);
    float ch = channels(P + 11.0, 1.1, 0.02, px);
    return mix(c, vec3(0.5, 0.62, 0.66), ch * 0.85);
  }
  if (code == 7) {
    // diked baylands: seasonal wetland / pasture, fields along the levees
    return base * (0.94 + 0.12 * inoise(P * 0.9));
  }
  return base;
}
// salt ponds: a complex of evaporators — irregular polygons (~0.5-1 km) between
// straight dikes (Voronoi cells), each a muted colour by salinity: mostly
// blue-green and olive, a few khaki and rust
vec3 saltPond(vec2 P, float px) {
  vec2 q = P / 11.0;
  vec2 iq = floor(q);
  float d1 = 1e9, d2 = 1e9;
  vec2 best = vec2(0.0);
  for (int j = -1; j <= 1; j++)
    for (int i = -1; i <= 1; i++) {
      vec2 cc = iq + vec2(float(i), float(j));
      vec2 fpnt = cc + vec2(0.15 + 0.7 * ih(cc * 1.31 + 2.0), 0.15 + 0.7 * ih(cc * 2.17 + 9.0));
      float d = distance(q, fpnt);
      if (d < d1) { d2 = d1; d1 = d; best = cc; }
      else if (d < d2) { d2 = d; }
    }
  float h = ih(best * 1.37 + 5.0);
  vec3 c = h < 0.4 ? vec3(0.45, 0.56, 0.55) : h < 0.7 ? vec3(0.52, 0.58, 0.49) : h < 0.85 ? vec3(0.58, 0.58, 0.48)
         : h < 0.95 ? vec3(0.62, 0.53, 0.46) : vec3(0.56, 0.48, 0.46);
  c = mix(vec3(0.5, 0.58, 0.54), c, 0.7) * (0.97 + 0.06 * inoise(P * 0.7));
  float edge = (d2 - d1) * 0.5 * 11.0;                // lattice cells to the dike
  return mix(c, vec3(0.7, 0.67, 0.58), lineCover(edge, 0.05, px));
}
void main(void) {
  vec2 size = vec2(textureSize(coverTex, 0));
  vec2 st = vUv * size - 0.5;
  vec4 smoothC = bspline(st, size);
  vec4 C = smoothC;
  vec4 dom = texelFetch(coverTex, clamp(ivec2(floor(st + 0.5)), ivec2(0), ivec2(size) - 1), 0);
  // snap to a real cover where texels are big enough on screen to see the edge
  vec2 dst = fwidth(st);
  float texelPx = 1.0 / max(max(dst.x, dst.y), 1e-4);
  float sel = smoothstep(2.0, 5.0, texelPx) * (1.0 - step(0.01, vSkirt));
  if (sel > 0.0) {
    ivec2 i0 = ivec2(floor(st));
    ivec2 mx = ivec2(size) - 1;
    vec4 t[4] = vec4[4](
      texelFetch(coverTex, clamp(i0, ivec2(0), mx), 0),
      texelFetch(coverTex, clamp(i0 + ivec2(1, 0), ivec2(0), mx), 0),
      texelFetch(coverTex, clamp(i0 + ivec2(0, 1), ivec2(0), mx), 0),
      texelFetch(coverTex, clamp(i0 + ivec2(1, 1), ivec2(0), mx), 0));
    // nearest real cover A, then the nearest *different* cover B
    int a = 0;
    float da = 1e9;
    for (int k = 0; k < 4; k++) { float d = distance(smoothC, t[k]); if (d < da) { da = d; a = k; } }
    int bb = -1;
    float db = 1e9;
    for (int k = 0; k < 4; k++) {
      if (distance(t[k], t[a]) < 0.01) continue;
      float d = distance(smoothC, t[k]);
      if (d < db) { db = d; bb = k; }
    }
    vec4 picked = t[a];
    if (bb >= 0) {
      vec4 A = t[a];
      vec4 B = t[bb];
      vec4 AB = B - A;
      float s = dot(smoothC - A, AB) / max(dot(AB, AB), 1e-6);
      // organic edge: ~25 m and ~9 m noise on the threshold
      vec2 q = (vLngLat - vec2(-122.0, 37.5)) * vec2(3500.0, 4400.0) * 1.1;
      float nz = (vnoise(q) * 0.62 + vnoise(q * 2.7 + 13.1) * 0.38 - 0.5) * 0.22;
      float e = s + nz - 0.5;
      float aa = fwidth(s) * 0.75 + 1e-4;
      picked = mix(A, B, smoothstep(-aa, aa, e));
      dom = e > 0.0 ? B : A;
    } else {
      dom = t[a];
    }
    C = mix(smoothC, picked, sel);
  }
  vec3 color = C.rgb;
  float wet = clamp((C.a - 0.3) / 0.7, 0.0, 1.0);
  int code = coverCode(dom);
  bool salt = abs(dom.a * 255.0 - 250.0) < 2.5;
  if ((code > 0 || salt) && vSkirt < 0.01) {
    vec2 L = st * terrain.latScale;
    vec2 P = L + terrain.latBase;
    float px = max(length(vec2(dFdx(L.x), dFdy(L.x))), length(vec2(dFdx(L.y), dFdy(L.y))));
    if (salt) color = mix(color, saltPond(P, px), smoothstep(0.6, 0.95, C.a));
    else if (code <= 4) color = farmPattern(color, code, L, terrain.latBase, px);
    else color = shorePattern(color, code, P, px);
    if (code == 6) wet = max(wet, 0.3);                // wet mud: flat, with a sheen
  }
  vec3 n = normalize(vNormal);
  if (n.z < 0.2) n = normalize(cross(dFdx(vCommon), dFdy(vCommon)));
  // steep natural slopes read as rock (cliffs)
  float steep = 1.0 - n.z;
  vec3 land = mix(color, vec3(0.64, 0.6, 0.54), smoothstep(0.45, 0.75, steep) * 0.75 * (1.0 - wet));
  vec3 lit = lighting_getLightColor(land, vCamera, vCommon, n);
  // water: calm and flat-bright
  fragColor = vec4(mix(lit, color * 1.02, wet * 0.85), 1.0);
  // the edge of the map: land and water fade into parchment over the last few km,
  // with a ragged, organic line (old game map)
  if (vFade < 0.999) {
    vec2 q = (vLngLat - vec2(-122.0, 37.5)) * vec2(88.0, 111.0);
    float n = inoise(q * 0.35) * 0.6 + inoise(q * 1.3 + 4.0) * 0.4;
    float f = smoothstep(0.15, 0.85, vFade + (n - 0.5) * 0.45);
    fragColor.rgb = mix(vec3(0.925, 0.9, 0.84), fragColor.rgb, f);
  }
  DECKGL_FILTER_COLOR(fragColor, geometry);
}
`;

const WATERISH = new Uint8Array(64);
for (const c of [0, 1, 14, 22]) WATERISH[c] = 1;
const OPEN_WATER = new Uint8Array(64);
for (const c of [0, 1, 2, 14, 22]) OPEN_WATER[c] = 1;
// farm pattern codes in the texel alpha for land (water: alpha 255); see farmPattern()
const FARM_CODE = new Uint8Array(64);
for (const [c, code] of Object.entries({10: 1, 11: 2, 12: 3, 13: 4, 3: 5, 21: 5, 2: 6, 15: 7})) FARM_CODE[+c] = code;
/**
 * Current cover colour (rgb) and wetness (a) of each grid vertex — same rules as the vertex
 * shader. Returns the span of years [from, to) over which the result stays the same (no
 * cover change pending or blending in it), so a tile whose ground isn't changing is not
 * recomputed and re-uploaded on every frame while the year runs.
 */
function coverColors(m: TerrainMesh, year: number, out: Uint8Array): [number, number] {
  const nn = m.n * m.n;
  let from = -Infinity;
  let to = Infinity;
  for (let v = 0; v < nn; v++) {
    let c = m.covers[v * 4];
    let prev = c;
    let t0 = -100000;
    for (let k = 0; k < 4; k++) {
      const yk = m.years[v * 4 + k];
      if (yk > 0) {
        if (year >= yk) {
          prev = c;
          c = k < 3 ? m.covers[v * 4 + k + 1] : m.cover4[v];
          t0 = yk;
        } else if (yk < to) to = yk;
      }
    }
    // (same rule as the vertex shader: the burn is instant, made land comes in half a year)
    const dur = c === 23 ? 0.04 : OPEN_WATER[prev] && !OPEN_WATER[c] ? 0.5 : 2.5;
    const x = Math.min(1, Math.max(0, (year - t0) / dur));
    if (x < 1) from = Infinity; // a change is blending in: every year differs
    else if (t0 + dur > from) from = t0 + dur;
    const kk = x * x * (3 - 2 * x);
    const p0 = PALETTE[prev] ?? PALETTE[0];
    const p1 = PALETTE[c] ?? PALETTE[0];
    const w = WATERISH[prev] * (1 - kk) + WATERISH[c] * kk;
    out[v * 4] = Math.round((p0[0] + (p1[0] - p0[0]) * kk) * 255);
    out[v * 4 + 1] = Math.round((p0[1] + (p1[1] - p0[1]) * kk) * 255);
    out[v * 4 + 2] = Math.round((p0[2] + (p1[2] - p0[2]) * kk) * 255);
    const cur = kk >= 0.5 ? c : prev;
    const code = FARM_CODE[cur];
    // salt ponds: alpha 250 (still water to the shader), patterned as evaporators
    out[v * 4 + 3] = w > 0 ? (cur === 14 && w > 0.99 ? 250 : Math.round(w * 255)) : code * 8;
  }
  return [from, to];
}

type TerrainMeshLayerProps = {
  mesh: TerrainMesh;
  currentYear: number;
  exaggeration: number;
  material: any;
};

const meshDefaults: DefaultProps<TerrainMeshLayerProps> = {
  mesh: {type: 'object', value: null as any, compare: true},
  currentYear: 2026,
  exaggeration: 1,
  material: {
    ambient: 0.62,
    diffuse: 0.55,
    shininess: 4,
    specularColor: [20, 20, 20]
  }
};

/** One terrain tile mesh. */
class TerrainMeshLayer extends Layer<TerrainMeshLayerProps> {
  static layerName = 'TerrainMeshLayer';
  static defaultProps = meshDefaults;
  state!: {model?: Model; texture?: any; texYear?: number; texSpan?: [number, number]; texData?: Uint8Array};

  getShaders() {
    return super.getShaders({
      vs,
      fs,
      modules: [project32, phongMaterial, terrainModule]
    });
  }

  initializeState(_: LayerContext) {
    this.setState({});
  }

  updateState(params: UpdateParameters<this>) {
    super.updateState(params);
    if (params.props.mesh !== params.oldProps.mesh || params.changeFlags.extensionsChanged) {
      this.state.model?.destroy();
      this.state.texture?.destroy();
      const m = this.props.mesh;
      const texture = m
        ? this.context.device.createTexture({
            width: m.n,
            height: m.n,
            format: 'rgba8unorm',
            sampler: {minFilter: 'linear', magFilter: 'linear', addressModeU: 'clamp-to-edge', addressModeV: 'clamp-to-edge'}
          })
        : undefined;
      this.setState({model: this._getModel(), texture, texYear: undefined, texSpan: undefined, texData: m ? new Uint8Array(m.n * m.n * 4) : undefined});
    }
  }

  finalizeState(context: LayerContext) {
    super.finalizeState(context);
    this.state.model?.destroy();
    this.state.texture?.destroy();
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
          skirt: {size: 1, value: m.skirt},
          fade: {size: 1, value: m.fade},
          uv: {size: 2, value: m.uv},
          normals: {size: 3, value: m.normals}
        },
        indices: {size: 1, value: m.indices}
      }),
      isInstanced: false
    });
  }

  draw() {
    const {model, texture, texData} = this.state;
    if (!model || !texture || !texData) return;
    // refresh the cover texture when the year moved — and only if this tile's ground
    // changes between the year it was built for and now (most tiles, most years: no)
    const span = this.state.texSpan;
    if (
      this.state.texYear === undefined ||
      (Math.abs(this.state.texYear - terrainYear) > 0.01 && !(span && terrainYear >= span[0] && terrainYear < span[1]))
    ) {
      this.state.texSpan = coverColors(this.props.mesh, terrainYear, texData);
      texture.writeData(texData);
      this.state.texYear = terrainYear;
      model.setBindings({coverTex: texture});
    }
    model.shaderInputs.setProps({
      terrain: {
        year: terrainYear,
        exaggeration: this.props.exaggeration,
        latScale: this.props.mesh.latScale,
        latBase: this.props.mesh.latBase
      }
    });
    model.draw(this.context.renderPass);
  }
}

// ------------------------------------------------------------------ tile decoding

let onDecoChange: (() => void) | null = null;
/** Called when the merged decorations change (the visible tiles settled): re-render. */
export function setTerrainChangeCallback(fn: () => void) {
  onDecoChange = fn;
}

// ---- tiles are decoded in workers (terrain-worker.ts); on the main thread only if
// workers are not available
type Pending = {resolve: (c: TileContent) => void; reject: (e: unknown) => void; z: number; x: number; y: number};
const pending = new Map<number, Pending>();
let workers: Worker[] | null = null;
let nextJob = 0;
function tileWorkers(): Worker[] {
  if (workers) return workers;
  workers = [];
  try {
    const n = Math.max(1, Math.min(4, (navigator.hardwareConcurrency || 4) - 1));
    for (let i = 0; i < n; i++) {
      // (the name carries the page's base URL: data paths in the worker resolve against it)
      const w = new Worker(new URL('./terrain-worker.ts', import.meta.url), {type: 'module', name: document.baseURI});
      w.onmessage = (e: MessageEvent<{id: number; content?: TileContent; error?: string}>) => {
        const job = pending.get(e.data.id);
        if (!job) return;
        pending.delete(e.data.id);
        if (e.data.error) {
          // a worker that cannot decode: do this tile here
          loadTerrainTile(job.z, job.x, job.y).then(job.resolve, job.reject);
          return;
        }
        const c = e.data.content ?? null;
        if (c) c.mesh.indices = gridIndices(c.mesh.n);
        job.resolve(c);
      };
      w.onerror = () => {
        // the worker script failed to start: give its jobs to the main thread, stop using workers
        workers = [];
        for (const [id, job] of pending) {
          pending.delete(id);
          loadTerrainTile(job.z, job.x, job.y).then(job.resolve, job.reject);
        }
      };
      workers.push(w);
    }
  } catch {
    workers = [];
  }
  return workers;
}
function loadTileOffThread(z: number, x: number, y: number): Promise<TileContent> {
  const ws = tileWorkers();
  if (!ws.length) return loadTerrainTile(z, x, y);
  return new Promise((resolve, reject) => {
    const id = nextJob++;
    pending.set(id, {resolve, reject, z, x, y});
    ws[id % ws.length].postMessage({id, z, x, y});
  });
}

// the live TileLayer (deck moves state onto the newest instance passed to setProps)
let liveTiles: TileLayer<TileContent> | null = null;
let decoTimer = 0;
let decoWaiting = false;
let decoBusy: (() => boolean) | null = null;
/** Tells the terrain when the camera is travelling (decorations are then merged less often). */
export function setDecoBusy(fn: () => boolean) {
  decoBusy = fn;
}
/** Re-merge the decorations of the tiles currently displayed (debounced). */
export function refreshDecoSoon(delay = 120) {
  // while the camera is travelling (a story flight, a long zoom) tiles come and go all the
  // time: merging the trees of the visible tiles on every change copies and re-uploads up
  // to a million instances each time — once the journey is over, or every 0.9 s, is enough
  if (decoBusy?.()) {
    if (decoTimer && decoWaiting) return;
    delay = 900;
    decoWaiting = true;
  }
  clearTimeout(decoTimer);
  decoTimer = window.setTimeout(() => {
    decoWaiting = false;
    decoTimer = 0;
    const ts = (liveTiles as any)?.state?.tileset;
    if (!ts) return;
    const tiles = (ts.tiles as any[]).filter(t => t.isVisible && t.content?.deco?.length);
    if (
      setVisibleDeco(
        tiles.map(t => ({
          key: t.id as string,
          batches: t.content.deco as DecoBatch[]
        }))
      )
    )
      onDecoChange?.();
  }, delay);
}

// The year is read at draw time (not a prop), so changing it doesn't rebuild the
// ~50 tile sublayers every frame while the timeline plays.
let terrainYear = 2026;

export function terrainLayer(year: number, extent: [number, number, number, number], zoom = 13) {
  terrainYear = year;
  liveTiles = new TileLayer<TileContent>({
    id: 'terrain',
    minZoom: 8,
    maxZoom: TILE_ZOOM_DETAIL,
    tileSize: 256,
    extent,
    zRange: [-80, 1300],
    maxRequests: 12,
    // while a zoom level loads, show the cached parent OR children, never both: opaque
    // meshes of two zoom levels on top of each other z-fight (flicker) and double the
    // decorations
    refinementStrategy: 'no-overlap',
    getTileData: ({index}: any) => loadTileOffThread(index.z, index.x, index.y),
    // decorations of the tiles in view are drawn together (deco-layer.ts)
    onTileLoad: () => refreshDecoSoon(),
    onViewportLoad: () => refreshDecoSoon(0),
    renderSubLayers: (props: any) => {
      const content = props.data as TileContent;
      if (!content) return null;
      const {mesh} = content;
      return new TerrainMeshLayer({
        id: `${props.id}-mesh`,
        mesh,
        exaggeration: 1,
        // receives shadows but doesn't cast them: one shadow-pass draw per tile would
        // cost more than the hill shading it adds
        shadowEnabled: false,
        coordinateSystem: COORDINATE_SYSTEM.LNGLAT_OFFSETS,
        coordinateOrigin: [mesh.origin[0], mesh.origin[1], 0]
      } as any);
    }
  });
  return [liveTiles, ...decoLayers(year, zoom)];
}
