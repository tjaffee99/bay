/** Street trees (placeholder until the pipeline's tree file exists). */
import type {Layer} from '@deck.gl/core';

export type TreeSet = {count: number};

export async function loadTrees(): Promise<TreeSet | null> {
  return null;
}

export function treesLayer(_trees: TreeSet, _year: number): Layer[] {
  return [];
}
