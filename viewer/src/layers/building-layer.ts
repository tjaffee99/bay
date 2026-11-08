/**
 * BuildingLayer — SolidPolygonLayer fed with pre-triangulated binary data.
 *
 * The pipeline writes closed rings (outer + holes) back to back, plus earcut
 * triangle indices and a per-vertex "vertexValid" array (0 at the last vertex of
 * every ring). Stock SolidPolygonLayer only honours a binary vertexValid on
 * WebGPU; without it, holes (courtyards) would get a bogus wall joining the
 * outer ring to the hole. This subclass uses the supplied array on WebGL too.
 */
import {SolidPolygonLayer} from '@deck.gl/layers';

export class BuildingLayer<DataT = any, ExtraProps extends {} = {}> extends SolidPolygonLayer<DataT, ExtraProps> {
  static layerName = 'BuildingLayer';

  // Roofs: the fill colour's alpha carries a roof code (palette.ts buildingColor); top
  // faces get real-world roofing (white / grey membranes, tar, gravel, clay tile,
  // shingle). Walls get storeys of windows — glass set into the facade, curtain-wall
  // bands on towers — that fade out when too small to see (no shimmer when zoomed out),
  // and a little darkening near the ground.
  getShaders(type: any) {
    const shaders = super.getShaders(type);
    const inject: Record<string, string> = {...(shaders.inject || {})};
    const add = (key: string, code: string) => (inject[key] = (inject[key] || '') + code);
    add('vs:#decl', 'out vec3 vWin;\nout float vSide;\nout float vBuild;\n');
    add('fs:#decl', 'in vec3 vWin;\nin float vSide;\nin float vBuild;\n');
    add('vs:#main-start', 'vWin = vec3(0.0); vSide = 0.0;\n');
    // TimeExtension('polygon'): 1 while the building is under construction
    add('vs:#main-end', 'vBuild = time_building;\n');
    add(
      'props.elevations = elevations * positions.y;',
      `
  {
    vec2 dCommon = (nextPos.xy - pos.xy) * project.commonUnitsPerWorldUnit.xy;
    float edgeM = length(dCommon / project.commonUnitsPerMeter.xy);
    vWin = vec3(positions.x * edgeM, positions.y * elevations, elevations);
    vSide = 1.0;
  }
`
    );
    add(
      'vec4 colors = solidPolygon.isWireframe ? lineColors : fillColors;',
      `
  float roofCode = floor(colors.a * 255.0 + 0.5);
  colors.a = 1.0;
#ifndef IS_SIDE_VERTEX
  {
    float rh = fract(sin(dot(colors.rgb, vec3(12.9898, 78.233, 37.719))) * 43758.5453);
    vec3 flatRoof = rh < 0.3 ? vec3(0.84, 0.84, 0.82) : rh < 0.55 ? vec3(0.68, 0.68, 0.66) : rh < 0.75 ? vec3(0.54, 0.54, 0.53) : rh < 0.88 ? vec3(0.36, 0.36, 0.37) : vec3(0.64, 0.6, 0.53);
    if (roofCode > 254.5) colors.rgb = mix(flatRoof, colors.rgb, 0.15);
    else if (roofCode > 253.5) colors.rgb = mix(vec3(0.66, 0.38, 0.29), colors.rgb, 0.1);
    else if (roofCode > 252.5) colors.rgb = mix(vec3(0.33, 0.32, 0.33), colors.rgb, 0.2);
  }
#endif
`
    );
    add(
      'fs:DECKGL_FILTER_COLOR',
      `
  if (vSide > 0.5 && !bool(picking.isActive)) {
    float H = vWin.z;
    float tower = step(40.0, H);
    float storey = mix(3.3, 3.8, tower);
    float bay = mix(2.6, 1.6, tower);
    vec2 g = vec2(vWin.x / bay, (vWin.y - 0.4) / storey);
    vec2 fw = fwidth(g);
    float vis = 1.0 - smoothstep(0.25, 0.6, max(fw.x, fw.y));
    vec2 f = fract(g);
    float wx = mix(0.62, 0.86, tower);
    float wy = mix(0.55, 0.72, tower);
    float win = smoothstep(0.5 - wx * 0.5 - fw.x, 0.5 - wx * 0.5, f.x) * (1.0 - smoothstep(0.5 + wx * 0.5, 0.5 + wx * 0.5 + fw.x, f.x))
              * smoothstep(0.5 - wy * 0.5 - fw.y, 0.5 - wy * 0.5, f.y) * (1.0 - smoothstep(0.5 + wy * 0.5, 0.5 + wy * 0.5 + fw.y, f.y));
    // not on the parapet / roofline, and fewer at street level for small buildings
    win *= step(0.9, vWin.y) * step(vWin.y, H - 0.7);
    vec3 glass = vec3(0.2, 0.25, 0.3) + 0.25 * vec3(0.55, 0.62, 0.7) * f.y;
    float avg = wx * wy * 0.55;
    color.rgb = mix(color.rgb * (1.0 - avg * 0.35), mix(color.rgb, glass, 0.78), win * vis);
    // grounding: slightly darker towards the street
    color.rgb *= mix(0.82, 1.0, smoothstep(0.0, 4.0, vWin.y));
  }
  // under construction: the frame only — timber studs and joists for small buildings,
  // a concrete / steel frame with floor slabs for big ones; solid when too far to see
  if (vBuild > 0.5) {
    float H = vWin.z;
    float timber = 1.0 - step(14.0, H);
    float steel = step(40.0, H) * step(0.5, fract(sin(dot(color.rgb, vec3(7.13, 3.71, 9.17))) * 4375.85));
    vec3 frame = timber > 0.5 ? vec3(0.76, 0.64, 0.46) : steel > 0.5 ? vec3(0.5, 0.33, 0.26) : vec3(0.7, 0.68, 0.64);
    if (vSide > 0.5) {
      vec2 g = vec2(vWin.x / mix(4.5, 1.2, timber), vWin.y / mix(mix(3.6, 3.9, step(40.0, H)), 3.0, timber));
      vec2 fw = fwidth(g);
      float detail = 1.0 - smoothstep(0.2, 0.45, max(fw.x, fw.y));
      vec2 f = abs(fract(g + 0.5) - 0.5);
      float tx = mix(0.06, 0.07, timber);
      float ty = mix(0.07, 0.04, timber);
      float beam = max(1.0 - smoothstep(tx, tx + fw.x, f.x), 1.0 - smoothstep(ty, ty + fw.y, f.y));
      beam = max(beam, step(H - 0.4, vWin.y));
      if (beam < 0.5 && detail > 0.5 && vWin.y > 0.25) discard;
      if (!bool(picking.isActive)) color.rgb = frame * mix(0.9, 1.0, beam);
    } else if (!bool(picking.isActive)) {
      // top deck: plywood / concrete slab
      color.rgb = timber > 0.5 ? vec3(0.78, 0.68, 0.5) : vec3(0.62, 0.61, 0.58);
    }
  }
`
    );
    shaders.inject = inject;
    return shaders;
  }

  calculateVertexValid(attribute: any) {
    const supplied = (this.props.data as any)?.attributes?.ringEndMarkers;
    if (supplied && this.context.device.type !== 'webgpu') {
      attribute.value = supplied;
      return;
    }
    // @ts-ignore protected in typings
    super.calculateVertexValid(attribute);
  }
}
