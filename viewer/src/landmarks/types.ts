import type {MeshBuilder, V2} from './kit';

export type Landmark = {
  id: string;
  name: string;
  kind: 'bridge' | 'building' | 'tower' | 'stadium' | 'park' | 'monument';
  /** Construction start (the model rises from here) and completion/opening. */
  built: [number, number];
  /** Removal year (9999 if standing). */
  end: number;
  /** lon, lat of the local origin. */
  anchor: V2;
  /** Model in local metres (x east, y north, z up) around the anchor. */
  build: (b: MeshBuilder) => void;
  /** Local-metre polygons whose generic footprint extrusions this model replaces. */
  replaces?: V2[][];
  /** Shown in the click popup. */
  facts: Record<string, string>;
  sources: string[];
};
