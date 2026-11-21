// Node built-in test runner for the dashboard's pure geo helpers.
// Run from frontend/: npm test  (node --experimental-strip-types --test ../tests/frontend_geo_utils.test.js)
import {test} from 'node:test';
import assert from 'node:assert/strict';
import {boundsOf, clampK, densityClass, filterAois, fitView, lineOf, linesOf, projector, ringsOf, zoomAt, MAX_K} from '../frontend/src/geo-utils.ts';

const B = [92.0, 25.0, 92.8, 25.8];

test('projection maps corners inside the canvas, north up, west left', () => {
  const p = projector(B, 1000, 760);
  const [nwx, nwy] = p([92.0, 25.8]), [sex, sey] = p([92.8, 25.0]);
  assert.ok(nwx < sex && nwy < sey);
  for (const v of [nwx, nwy, sex, sey]) assert.ok(v >= -0.001 && v <= 1000.001);
});

test('geometry helpers handle Polygon, MultiPolygon and lines', () => {
  const ring = [[92.1, 25.1], [92.2, 25.1], [92.2, 25.2], [92.1, 25.1]];
  assert.equal(ringsOf({type: 'Polygon', coordinates: [ring]}).length, 1);
  assert.equal(ringsOf({type: 'MultiPolygon', coordinates: [[ring], [ring]]}).length, 2);
  assert.equal(ringsOf({type: 'Point', coordinates: [0, 0]}).length, 0);
  assert.deepEqual(boundsOf([ring]), [92.1, 25.1, 92.2, 25.2]);
  assert.equal(linesOf({type: 'MultiLineString', coordinates: [ring, ring]}).length, 2);
  assert.match(lineOf(ring, projector(B)), /^M[\d.]+,[\d.]+L/);
});

test('zoom keeps the anchor point fixed and is clamped', () => {
  const v = zoomAt({k: 1, tx: 0, ty: 0}, 2, 300, 200);
  assert.equal(v.k, 2);
  assert.ok(Math.abs((300 - v.tx) / v.k - 300) < 1e-9 && Math.abs((200 - v.ty) / v.k - 200) < 1e-9);
  assert.equal(clampK(99), MAX_K);
  assert.equal(zoomAt({k: 1, tx: 0, ty: 0}, 0.1, 0, 0).k, 1);
});

test('fitView centres the target bounds', () => {
  const v = fitView([100, 100, 300, 200], 1000, 760, 0);
  assert.ok(Math.abs(v.k * 200 + v.tx - 500) < 1e-9 && Math.abs(v.k * 150 + v.ty - 380) < 1e-9);
});

test('district filter and fixed density classes', () => {
  const a = (district, density) => ({aoi: 'x', district, split: 'train', ring: [], density, clusters: 0, candidate_cells: 0});
  const all = [a('East Jaintia Hills', 0), a('West Jaintia Hills', 1.2), a('East Jaintia Hills', 6.7)];
  assert.equal(filterAois(all, 'All districts').length, 3);
  assert.equal(filterAois(all, 'East Jaintia Hills').length, 2);
  assert.deepEqual(all.map(x => densityClass(x.density)), [0, 2, 4]);
});
