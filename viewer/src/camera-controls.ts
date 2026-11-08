/**
 * Camera controls on top of MapLibre's defaults:
 *  - shift + drag rotates (horizontal) and tilts (vertical) — instead of
 *    MapLibre's shift-drag box zoom, which isn't useful here;
 *  - right-drag / ctrl-drag keep MapLibre's own rotate behaviour.
 */
import type maplibregl from 'maplibre-gl';

export function installCameraControls(map: maplibregl.Map) {
  map.boxZoom.disable();
  const canvas = map.getCanvasContainer();
  let dragging = false;
  let lastX = 0;
  let lastY = 0;

  canvas.addEventListener(
    'pointerdown',
    e => {
      if (!e.shiftKey || e.button !== 0) return;
      dragging = true;
      lastX = e.clientX;
      lastY = e.clientY;
      map.dragPan.disable();
      canvas.setPointerCapture(e.pointerId);
      e.preventDefault();
      e.stopPropagation();
    },
    true
  );
  canvas.addEventListener(
    'pointermove',
    e => {
      if (!dragging) return;
      const dx = e.clientX - lastX;
      const dy = e.clientY - lastY;
      lastX = e.clientX;
      lastY = e.clientY;
      map.jumpTo({
        bearing: map.getBearing() + dx * 0.35,
        pitch: Math.max(0, Math.min(map.getMaxPitch(), map.getPitch() - dy * 0.25))
      });
      e.preventDefault();
      e.stopPropagation();
    },
    true
  );
  const end = (e: PointerEvent) => {
    if (!dragging) return;
    dragging = false;
    map.dragPan.enable();
    try {
      canvas.releasePointerCapture(e.pointerId);
    } catch {
      /* already released */
    }
    map.fire('moveend');
  };
  canvas.addEventListener('pointerup', end, true);
  canvas.addEventListener('pointercancel', end, true);
}
