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
  getShaders(type: any) {
    const shaders = super.getShaders(type);
    shaders.inject = {
      ...(shaders.inject || {}),
      'vec4 colors = solidPolygon.isWireframe ? lineColors : fillColors;': `
  float roofCode = floor(colors.a * 255.0 + 0.5);
  colors.a = 1.0;
#ifndef IS_SIDE_VERTEX
  if (roofCode > 254.5) colors.rgb = mix(colors.rgb, vec3(0.58, 0.58, 0.57), 0.6);
  else if (roofCode > 253.5) colors.rgb = mix(vec3(0.71, 0.47, 0.38), colors.rgb, 0.2);
  else if (roofCode > 252.5) colors.rgb = mix(colors.rgb, vec3(0.36, 0.36, 0.38), 0.6);
#endif
`
    };
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
