// Pure geographic helpers for the offline dashboard map (no DOM, no React) — unit-tested with node --test.
export type LonLat = [number, number];
export type Bounds = [number, number, number, number]; // west, south, east, north
export type View = {k: number; tx: number; ty: number};
export type Aoi = {aoi: string; district: string; split: string; ring: LonLat[]; density: number; clusters: number; candidate_cells: number};

export const W = 1000, H = 760;
export const MIN_K = 1, MAX_K = 12;

/** Equirectangular projection fitted to bounds, with cos(mid-latitude) x-scaling to keep shapes true. */
export function projector(b: Bounds, w = W, h = H) {
  const [west, south, east, north] = b;
  const kx = Math.cos(((south + north) / 2) * Math.PI / 180);
  const sx = w / ((east - west) * kx), sy = h / (north - south);
  const s = Math.min(sx, sy);
  const ox = (w - (east - west) * kx * s) / 2, oy = (h - (north - south) * s) / 2;
  return ([lon, lat]: LonLat): [number, number] => [ox + (lon - west) * kx * s, oy + (north - lat) * s];
}

export function pathOf(rings: LonLat[][], p: (c: LonLat) => [number, number]) {
  return rings.map(r => r.map((c, i) => (i ? 'L' : 'M') + p(c).map(v => v.toFixed(1)).join(',')).join('') + 'Z').join('');
}

export function lineOf(coords: LonLat[], p: (c: LonLat) => [number, number]) {
  return coords.map((c, i) => (i ? 'L' : 'M') + p(c).map(v => v.toFixed(1)).join(',')).join('');
}

/** Rings of a GeoJSON Polygon / MultiPolygon. */
export function ringsOf(g: {type: string; coordinates: unknown}): LonLat[][] {
  if (g.type === 'Polygon') return g.coordinates as LonLat[][];
  if (g.type === 'MultiPolygon') return (g.coordinates as LonLat[][][]).flat();
  return [];
}

/** Line parts of a GeoJSON LineString / MultiLineString. */
export function linesOf(g: {type: string; coordinates: unknown}): LonLat[][] {
  if (g.type === 'LineString') return [g.coordinates as LonLat[]];
  if (g.type === 'MultiLineString') return g.coordinates as LonLat[][];
  return [];
}

export function boundsOf(rings: LonLat[][]): Bounds {
  let w = Infinity, s = Infinity, e = -Infinity, n = -Infinity;
  for (const r of rings) for (const [x, y] of r) { w = Math.min(w, x); e = Math.max(e, x); s = Math.min(s, y); n = Math.max(n, y); }
  return [w, s, e, n];
}

export const clampK = (k: number) => Math.min(MAX_K, Math.max(MIN_K, k));

/** Zoom by factor about a screen point, keeping that point fixed. */
export function zoomAt(v: View, factor: number, cx: number, cy: number): View {
  const k = clampK(v.k * factor), f = k / v.k;
  return {k, tx: cx - (cx - v.tx) * f, ty: cy - (cy - v.ty) * f};
}

/** View that fits projected screen bounds [x0,y0,x1,y1] with padding. */
export function fitView([x0, y0, x1, y1]: [number, number, number, number], w = W, h = H, pad = 40): View {
  const k = clampK(Math.min((w - 2 * pad) / Math.max(1, x1 - x0), (h - 2 * pad) / Math.max(1, y1 - y0)));
  return {k, tx: w / 2 - k * (x0 + x1) / 2, ty: h / 2 - k * (y0 + y1) / 2};
}

export function filterAois(aois: Aoi[], district: string) {
  return district === 'All districts' ? aois : aois.filter(a => a.district === district);
}

/** Fixed, data-independent density classes (ha per 100 ha) so colours never imply false precision. */
export const DENSITY_BREAKS = [0.0001, 0.5, 1.5, 3] as const;
export function densityClass(d: number) {
  if (d < DENSITY_BREAKS[0]) return 0;
  if (d < DENSITY_BREAKS[1]) return 1;
  if (d < DENSITY_BREAKS[2]) return 2;
  if (d < DENSITY_BREAKS[3]) return 3;
  return 4;
}
