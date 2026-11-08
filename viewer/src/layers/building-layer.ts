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
  // faces get flat grey roofing, clay tile or dark shingle, walls keep the facade colour.
  // While a building is under construction (TimeExtension 'polygon') it is drawn as its
  // frame: timber studs and joists for small buildings, a concrete / steel frame with
  // floor slabs for big ones (solid when too far away to resolve).
  getShaders(type: any) {
    const shaders = super.getShaders(type);
    const inject: Record<string, string> = {...(shaders.inject || {})};
    const add = (key: string, code: string) => (inject[key] = (inject[key] || '') + code);
    add('vs:#decl', 'out vec3 vWin;\nout float vSide;\nout float vBuild;\n');
    add('fs:#decl', 'in vec3 vWin;\nin float vSide;\nin float vBuild;\n');
    add('vs:#main-start', 'vWin = vec3(0.0); vSide = 0.0;\n');
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
  if (roofCode > 254.5) colors.rgb = mix(colors.rgb, vec3(0.58, 0.58, 0.57), 0.6);
  else if (roofCode > 253.5) colors.rgb = mix(vec3(0.71, 0.47, 0.38), colors.rgb, 0.2);
  else if (roofCode > 252.5) colors.rgb = mix(colors.rgb, vec3(0.36, 0.36, 0.38), 0.6);
#endif
`
    );
    add(
      'fs:DECKGL_FILTER_COLOR',
      `
  if (vBuild > 0.5) {
    float H = vWin.z;
    float timber = 1.0 - step(14.0, H);
    float steel = step(40.0, H) * step(0.5, fract(sin(dot(color.rgb, vec3(7.13, 3.71, 9.17))) * 4375.85));
    vec3 frame = timber > 0.5 ? vec3(0.76, 0.64, 0.46) : steel > 0.5 ? vec3(0.46, 0.47, 0.49) : vec3(0.7, 0.68, 0.64);
    if (vSide > 0.5) {
      vec2 g = vec2(vWin.x / mix(4.5, 1.2, timber), vWin.y / mix(mix(3.6, 3.9, step(40.0, H)), 3.0, timber));
      vec2 fw = fwidth(g);
      float detail = 1.0 - smoothstep(0.07, 0.13, max(fw.x, fw.y));
      vec2 f = abs(fract(g + 0.5) - 0.5);
      float tx = 0.08;
      float ty = mix(0.09, 0.06, timber);
      float beam = max(1.0 - smoothstep(tx, tx + fw.x, f.x), 1.0 - smoothstep(ty, ty + fw.y, f.y));
      beam = max(beam, step(H - 0.4, vWin.y));
      if (beam < 0.5 && detail > 0.5 && vWin.y > 0.25) discard;
      if (!bool(picking.isActive)) color.rgb = frame * mix(0.72, 1.0, beam);
    } else if (!bool(picking.isActive)) {
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
