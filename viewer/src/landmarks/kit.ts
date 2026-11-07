/**
 * Low-poly geometry kit for landmark reconstructions.
 *
 * Builds non-indexed triangle meshes in a local metric frame:
 *   x = east, y = north, z = up (metres), origin = the landmark's anchor.
 * Shading is flat (SimpleMeshLayer derives face normals in the fragment
 * shader when no normals are supplied), so winding order doesn't matter.
 *
 * A transform stack (translate + rotate about z, compass bearings) lets each
 * landmark be modelled in its own axis-aligned frame and placed on the map.
 */
import {earcut} from '@math.gl/polygon';

export type V2 = [number, number];
export type V3 = [number, number, number];
export type Color = string | [number, number, number];

const M_PER_DEG_LAT = 110_574;

/** Local metres of (lon, lat) relative to an anchor. */
export function lngLatToLocal(anchor: V2, p: V2): V2 {
  const k = 111_320 * Math.cos((anchor[1] * Math.PI) / 180);
  return [(p[0] - anchor[0]) * k, (p[1] - anchor[1]) * M_PER_DEG_LAT];
}

export function localToLngLat(anchor: V2, p: V2): V2 {
  const k = 111_320 * Math.cos((anchor[1] * Math.PI) / 180);
  return [anchor[0] + p[0] / k, anchor[1] + p[1] / M_PER_DEG_LAT];
}

function toRgb(c: Color): [number, number, number] {
  if (Array.isArray(c)) return [c[0] / 255, c[1] / 255, c[2] / 255];
  const h = c.replace('#', '');
  return [parseInt(h.slice(0, 2), 16) / 255, parseInt(h.slice(2, 4), 16) / 255, parseInt(h.slice(4, 6), 16) / 255];
}

type Frame = {tx: number; ty: number; tz: number; cos: number; sin: number};

export class MeshBuilder {
  private pos: number[] = [];
  private col: number[] = [];
  private rgb: [number, number, number] = [1, 1, 1];
  private stack: Frame[] = [{tx: 0, ty: 0, tz: 0, cos: 1, sin: 0}];

  color(c: Color) {
    this.rgb = toRgb(c);
    return this;
  }

  /** Run `fn` in a frame translated to (x, y, z) and rotated so local +y points at `bearing` (deg clockwise from north). */
  frame(x: number, y: number, z: number, bearing: number, fn: () => void) {
    const parent = this.stack[this.stack.length - 1];
    // world = parent.rot * (local) + parent.t ; new frame composes
    const a = (-bearing * Math.PI) / 180; // rotation about z (counter-clockwise radians)
    const ca = Math.cos(a);
    const sa = Math.sin(a);
    const [wx, wy] = [parent.tx + parent.cos * x - parent.sin * y, parent.ty + parent.sin * x + parent.cos * y];
    this.stack.push({
      tx: wx,
      ty: wy,
      tz: parent.tz + z,
      cos: parent.cos * ca - parent.sin * sa,
      sin: parent.sin * ca + parent.cos * sa
    });
    fn();
    this.stack.pop();
    return this;
  }

  private xf(p: V3): V3 {
    const f = this.stack[this.stack.length - 1];
    return [f.tx + f.cos * p[0] - f.sin * p[1], f.ty + f.sin * p[0] + f.cos * p[1], f.tz + p[2]];
  }

  tri(a: V3, b: V3, c: V3) {
    for (const p of [a, b, c]) {
      const w = this.xf(p);
      this.pos.push(w[0], w[1], w[2]);
      this.col.push(this.rgb[0], this.rgb[1], this.rgb[2]);
    }
    return this;
  }

  quad(a: V3, b: V3, c: V3, d: V3) {
    this.tri(a, b, c);
    this.tri(a, c, d);
    return this;
  }

  /** Flat polygon at height z (earcut), optional holes. */
  cap(outer: V2[], z: number, holes: V2[][] = []) {
    const flat: number[] = [];
    const holeIdx: number[] = [];
    for (const p of outer) flat.push(p[0], p[1]);
    for (const h of holes) {
      holeIdx.push(flat.length / 2);
      for (const p of h) flat.push(p[0], p[1]);
    }
    const t = earcut(flat, holeIdx.length ? holeIdx : undefined, 2);
    for (let i = 0; i < t.length; i += 3) {
      const v = (k: number): V3 => [flat[t[k] * 2], flat[t[k] * 2 + 1], z];
      this.tri(v(i), v(i + 1), v(i + 2));
    }
    return this;
  }

  /** Vertical walls of a closed ring between z0 and z1. */
  walls(ring: V2[], z0: number, z1: number) {
    for (let i = 0; i < ring.length; i++) {
      const a = ring[i];
      const b = ring[(i + 1) % ring.length];
      this.quad([a[0], a[1], z0], [b[0], b[1], z0], [b[0], b[1], z1], [a[0], a[1], z1]);
    }
    return this;
  }

  /** Extruded polygon. */
  prism(ring: V2[], z0: number, z1: number, opts: {top?: boolean; bottom?: boolean; holes?: V2[][]} = {}) {
    const {top = true, bottom = false, holes = []} = opts;
    this.walls(ring, z0, z1);
    for (const h of holes) this.walls(h, z0, z1);
    if (top) this.cap(ring, z1, holes);
    if (bottom) this.cap(ring, z0, holes);
    return this;
  }

  /** Axis-aligned box centred at (cx, cy) in the current frame. */
  box(cx: number, cy: number, z0: number, sx: number, sy: number, h: number, opts: {top?: boolean; bottom?: boolean} = {}) {
    return this.prism(rect(cx, cy, sx, sy), z0, z0 + h, opts);
  }

  /** Lofted solid between two rings with equal vertex counts (tapers, twists). */
  loft(rings: V2[][], zs: number[], opts: {top?: boolean; bottom?: boolean} = {}) {
    const {top = true, bottom = false} = opts;
    for (let k = 0; k < rings.length - 1; k++) {
      const A = rings[k];
      const B = rings[k + 1];
      for (let i = 0; i < A.length; i++) {
        const j = (i + 1) % A.length;
        this.quad([A[i][0], A[i][1], zs[k]], [A[j][0], A[j][1], zs[k]], [B[j][0], B[j][1], zs[k + 1]], [B[i][0], B[i][1], zs[k + 1]]);
      }
    }
    if (top) this.cap(rings[rings.length - 1], zs[zs.length - 1]);
    if (bottom) this.cap(rings[0], zs[0]);
    return this;
  }

  /** Pyramid / cone from a ring up to an apex. */
  pyramid(ring: V2[], z0: number, apex: V3) {
    for (let i = 0; i < ring.length; i++) {
      const a = ring[i];
      const b = ring[(i + 1) % ring.length];
      this.tri([a[0], a[1], z0], [b[0], b[1], z0], apex);
    }
    return this;
  }

  cylinder(cx: number, cy: number, r: number, z0: number, z1: number, segs = 16, opts: {top?: boolean} = {}) {
    return this.prism(circle(cx, cy, r, segs), z0, z1, {top: opts.top ?? true});
  }

  frustum(cx: number, cy: number, r0: number, r1: number, z0: number, z1: number, segs = 16, top = true) {
    return this.loft([circle(cx, cy, r0, segs), circle(cx, cy, r1, segs)], [z0, z1], {top});
  }

  /** Spherical-cap dome (rise h) on a circle of radius r at height z0. */
  dome(cx: number, cy: number, r: number, z0: number, h: number, segs = 16, rings = 5) {
    const R = (r * r + h * h) / (2 * h); // sphere radius through rim and apex
    const zc = z0 + h - R;
    const ringsArr: V2[][] = [];
    const zs: number[] = [];
    for (let k = 0; k < rings; k++) {
      const z = z0 + (h * k) / rings;
      const rr = Math.sqrt(Math.max(R * R - (z - zc) * (z - zc), 0));
      ringsArr.push(circle(cx, cy, rr, segs));
      zs.push(z);
    }
    this.loft(ringsArr, zs, {top: false});
    this.pyramid(ringsArr[rings - 1], zs[rings - 1], [cx, cy, z0 + h]);
    return this;
  }

  /** Gabled roof over a rectangle (ridge along the local y axis when `alongY`). */
  gable(cx: number, cy: number, sx: number, sy: number, z0: number, h: number, alongY = true) {
    const hx = sx / 2;
    const hy = sy / 2;
    if (alongY) {
      const r0: V3 = [cx, cy - hy, z0 + h];
      const r1: V3 = [cx, cy + hy, z0 + h];
      this.quad([cx - hx, cy - hy, z0], [cx - hx, cy + hy, z0], r1, r0);
      this.quad([cx + hx, cy - hy, z0], [cx + hx, cy + hy, z0], r1, r0);
      this.tri([cx - hx, cy - hy, z0], [cx + hx, cy - hy, z0], r0);
      this.tri([cx - hx, cy + hy, z0], [cx + hx, cy + hy, z0], r1);
    } else {
      const r0: V3 = [cx - hx, cy, z0 + h];
      const r1: V3 = [cx + hx, cy, z0 + h];
      this.quad([cx - hx, cy - hy, z0], [cx + hx, cy - hy, z0], r1, r0);
      this.quad([cx - hx, cy + hy, z0], [cx + hx, cy + hy, z0], r1, r0);
      this.tri([cx - hx, cy - hy, z0], [cx - hx, cy + hy, z0], r0);
      this.tri([cx + hx, cy - hy, z0], [cx + hx, cy + hy, z0], r1);
    }
    return this;
  }

  /** Hipped roof over a rectangle: ridge length = longer side - shorter side. */
  hip(cx: number, cy: number, sx: number, sy: number, z0: number, h: number) {
    const hx = sx / 2;
    const hy = sy / 2;
    const c = [cx - hx, cy - hy, cx + hx, cy + hy];
    if (sx >= sy) {
      const r0: V3 = [cx - hx + hy, cy, z0 + h];
      const r1: V3 = [cx + hx - hy, cy, z0 + h];
      this.quad([c[0], c[1], z0], [c[2], c[1], z0], r1, r0);
      this.quad([c[0], c[3], z0], [c[2], c[3], z0], r1, r0);
      this.tri([c[0], c[1], z0], [c[0], c[3], z0], r0);
      this.tri([c[2], c[1], z0], [c[2], c[3], z0], r1);
    } else {
      const r0: V3 = [cx, cy - hy + hx, z0 + h];
      const r1: V3 = [cx, cy + hy - hx, z0 + h];
      this.quad([c[0], c[1], z0], [c[0], c[3], z0], r1, r0);
      this.quad([c[2], c[1], z0], [c[2], c[3], z0], r1, r0);
      this.tri([c[0], c[1], z0], [c[2], c[1], z0], r0);
      this.tri([c[0], c[3], z0], [c[2], c[3], z0], r1);
    }
    return this;
  }

  /** Square beam (w × w) from a to b — struts, cables, suspenders. */
  beam(a: V3, b: V3, w: number, hgt = w) {
    const dx = b[0] - a[0];
    const dy = b[1] - a[1];
    const dz = b[2] - a[2];
    const L = Math.hypot(dx, dy, dz);
    if (L < 1e-6) return this;
    // perpendicular basis
    let ux = -dy;
    let uy = dx;
    let uz = 0;
    let ul = Math.hypot(ux, uy, uz);
    if (ul < 1e-6) {
      ux = 1;
      uy = 0;
      uz = 0;
      ul = 1;
    }
    ux /= ul;
    uy /= ul;
    uz /= ul;
    // v = d × u
    let vx = dy * uz - dz * uy;
    let vy = dz * ux - dx * uz;
    let vz = dx * uy - dy * ux;
    const vl = Math.hypot(vx, vy, vz);
    vx /= vl;
    vy /= vl;
    vz /= vl;
    const hw = w / 2;
    const hh = hgt / 2;
    const corners = (p: V3): V3[] => [
      [p[0] - ux * hw - vx * hh, p[1] - uy * hw - vy * hh, p[2] - uz * hw - vz * hh],
      [p[0] + ux * hw - vx * hh, p[1] + uy * hw - vy * hh, p[2] + uz * hw - vz * hh],
      [p[0] + ux * hw + vx * hh, p[1] + uy * hw + vy * hh, p[2] + uz * hw + vz * hh],
      [p[0] - ux * hw + vx * hh, p[1] - uy * hw + vy * hh, p[2] - uz * hw + vz * hh]
    ];
    const A = corners(a);
    const B = corners(b);
    for (let i = 0; i < 4; i++) {
      const j = (i + 1) % 4;
      this.quad(A[i], A[j], B[j], B[i]);
    }
    return this;
  }

  /** Polyline of beams (cables). */
  polyline(pts: V3[], w: number) {
    for (let i = 0; i < pts.length - 1; i++) this.beam(pts[i], pts[i + 1], w);
    return this;
  }

  /** Surface between two matching polylines (e.g. a sloped seating bowl). */
  ribbon(a: V3[], b: V3[], closed = false) {
    const n = a.length;
    for (let i = 0; i < (closed ? n : n - 1); i++) {
      const j = (i + 1) % n;
      this.quad(a[i], a[j], b[j], b[i]);
    }
    return this;
  }

  /** Vertical wall along a path with per-vertex bottom/top heights. */
  wallProfile(path: V2[], z0: number | number[], z1: number | number[], closed = false) {
    const n = path.length;
    const lo = (i: number) => (Array.isArray(z0) ? z0[i] : z0);
    const hi = (i: number) => (Array.isArray(z1) ? z1[i] : z1);
    for (let i = 0; i < (closed ? n : n - 1); i++) {
      const j = (i + 1) % n;
      this.quad([path[i][0], path[i][1], lo(i)], [path[j][0], path[j][1], lo(j)], [path[j][0], path[j][1], hi(j)], [path[i][0], path[i][1], hi(i)]);
    }
    return this;
  }

  get vertexCount() {
    return this.pos.length / 3;
  }

  build() {
    return {
      positions: {value: new Float32Array(this.pos), size: 3},
      colors: {value: new Float32Array(this.col), size: 3}
    };
  }
}

// ------------------------------------------------------------------ shapes

export function rect(cx: number, cy: number, sx: number, sy: number): V2[] {
  return [
    [cx - sx / 2, cy - sy / 2],
    [cx + sx / 2, cy - sy / 2],
    [cx + sx / 2, cy + sy / 2],
    [cx - sx / 2, cy + sy / 2]
  ];
}

/** Rectangle rotated so its local +y axis points at `bearing`. */
export function rotRect(cx: number, cy: number, sx: number, sy: number, bearing: number): V2[] {
  const a = (-bearing * Math.PI) / 180;
  const c = Math.cos(a);
  const s = Math.sin(a);
  return rect(0, 0, sx, sy).map(([x, y]) => [cx + c * x - s * y, cy + s * x + c * y] as V2);
}

export function circle(cx: number, cy: number, r: number, segs = 16, rx = r, ry = r): V2[] {
  void r;
  const out: V2[] = [];
  for (let i = 0; i < segs; i++) {
    const a = (i / segs) * Math.PI * 2;
    out.push([cx + Math.cos(a) * rx, cy + Math.sin(a) * ry]);
  }
  return out;
}

export function ellipse(cx: number, cy: number, rx: number, ry: number, segs = 24): V2[] {
  return circle(cx, cy, rx, segs, rx, ry);
}

/** Rounded rectangle (squircle-ish), `cr` = corner radius, `n` segments per corner. */
export function roundedRect(cx: number, cy: number, sx: number, sy: number, cr: number, n = 4): V2[] {
  const out: V2[] = [];
  const hx = sx / 2 - cr;
  const hy = sy / 2 - cr;
  const corners: [number, number, number][] = [
    [hx, -hy, -Math.PI / 2],
    [hx, hy, 0],
    [-hx, hy, Math.PI / 2],
    [-hx, -hy, Math.PI]
  ];
  for (const [ox, oy, a0] of corners) {
    for (let i = 0; i <= n; i++) {
      const a = a0 + (i / n) * (Math.PI / 2);
      out.push([cx + ox + Math.cos(a) * cr, cy + oy + Math.sin(a) * cr]);
    }
  }
  return out;
}

/** Points along a parabola from p0 to p1 sagging to zMid at the middle. */
export function parabola(p0: V3, p1: V3, zMid: number, n = 16): V3[] {
  const out: V3[] = [];
  for (let i = 0; i <= n; i++) {
    const t = i / n;
    const x = p0[0] + (p1[0] - p0[0]) * t;
    const y = p0[1] + (p1[1] - p0[1]) * t;
    const zl = p0[2] + (p1[2] - p0[2]) * t;
    const sag = (p0[2] + p1[2]) / 2 - zMid;
    out.push([x, y, zl - 4 * sag * t * (1 - t)]);
  }
  return out;
}
