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
