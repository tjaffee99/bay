/** Landmarks (placeholder; reconstructions land in src/landmarks/*). */
import type {Layer, PickingInfo} from '@deck.gl/core';

export type LandmarkSet = {count: number};

export async function loadLandmarks(): Promise<LandmarkSet | null> {
  return null;
}

export function landmarkLayers(_set: LandmarkSet, _year: number, _quality: boolean): Layer[] {
  return [];
}

export function landmarkInfo(_set: LandmarkSet, _info: PickingInfo): {title: string; rows: Record<string, string | number>} | null {
  return null;
}
