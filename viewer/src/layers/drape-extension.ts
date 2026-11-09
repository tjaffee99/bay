/**
 * DrapeExtension — keeps flat things lying on the terrain (golf courses, pitches,
 * plazas, runways, aprons) visible at every zoom and pitch.
 *
 * Their heights come from an elevation lookup and their big triangles span many
 * terrain cells, so they sit a little above or below the terrain mesh here and there;
 * with depth precision falling off with distance, they z-fought or vanished under the
 * ground as the view zoomed out (and only on the far half of a pitched view). Instead of
 * lifting them (which shifts them on screen), each vertex's DEPTH is taken from a point
 * pulled toward the camera by a fixed share of its distance — the screen position is
 * unchanged (the point moves along its own view ray). The layer does not write depth,
 * so buildings, trees and roads drawn after it still cover it exactly; hills in front
 * still hide it (only ground within that share of the distance shows through).
 * Overlapping polygons of one layer then stack in draw order (pipeline sorts them).
 */
import {LayerExtension} from '@deck.gl/core';
import type {Layer} from '@deck.gl/core';

export class DrapeExtension extends LayerExtension<{pull: number}> {
  static extensionName = 'DrapeExtension';

  constructor(opts: {pull?: number} = {}) {
    super({pull: opts.pull ?? 0.004});
  }

  getShaders(this: Layer, extension: this) {
    return {
      inject: {
        'vs:DECKGL_FILTER_GL_POSITION': /* glsl */ `
          {
            vec3 drapeToCam = project.cameraPosition - geometry.position.xyz;
            vec4 drapePulled = project_common_position_to_clipspace(vec4(geometry.position.xyz + drapeToCam * ${extension.opts.pull.toFixed(5)}, 1.0));
            position.z = drapePulled.z / drapePulled.w * position.w;
          }
        `
      }
    };
  }
}

/** depth test against the terrain, but never write depth (see above) */
export const DRAPE_PARAMETERS = {depthWriteEnabled: false, depthCompare: 'less-equal'} as const;
