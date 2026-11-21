// Node built-in tests for the India discovery helpers (run from frontend/: npm test).
import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync, existsSync} from 'node:fs';
import {INDIA_FRAME, RIVER_STUDY, SCREENED_SITES, TIERS, inFrame, plot, summarise, tierOf} from '../frontend/src/india-data.ts';

const lead = (id, state, lon = 85, lat = 21) => ({id, state, district: '', longitude: lon, latitude: lat, status: 'UNKNOWN', common: 1024, changes: {}, source: ''});

test('tiers separate screened sites, Meghalaya leads and unverified leads', () => {
  assert.equal(tierOf(lead('gevra', 'Chhattisgarh')), 'SCREENED_SITE');
  assert.equal(tierOf(lead('bhubaneswari', 'Odisha')), 'SCREENED_SITE');
  assert.equal(tierOf(lead('R008', 'Meghalaya')), 'MEGHALAYA_LEAD');
  assert.equal(tierOf(lead('nigahi', 'Madhya Pradesh')), 'UNVERIFIED_LEAD');
  for (const t of Object.values(TIERS)) assert.doesNotMatch(t.text, /confirmed|verified detection/i);
});

test('summary never reports verified detections', () => {
  const s = summarise([lead('gevra', 'Chhattisgarh'), lead('kusmunda', 'Chhattisgarh'), lead('R008', 'Meghalaya')]);
  assert.deepEqual(s.tiers, {SCREENED_SITE: 1, UNVERIFIED_LEAD: 1, MEGHALAYA_LEAD: 1});
  assert.equal(s.states, 2);
  assert.equal(s.verified, 0);
});

test('graticule projection keeps India inside the frame, north up', () => {
  const [x0, y0] = plot(INDIA_FRAME.west, INDIA_FRAME.north), [x1, y1] = plot(INDIA_FRAME.east, INDIA_FRAME.south);
  assert.ok(x0 < x1 && y0 < y1 && x0 >= 0 && y1 <= 620);
  assert.ok(inFrame(92.2, 25.7) && !inFrame(120, 25));
  assert.deepEqual([...SCREENED_SITES], ['gevra', 'bhubaneswari']);
  assert.equal(RIVER_STUDY.bhubaneswari, '#rivers-brahmani');
});

test('local snapshot (if present) has six UNKNOWN Phase 11C leads with two screened sites', () => {
  const p = new URL('../frontend/public/local/india-candidates.json', import.meta.url);
  if (!existsSync(p)) return;
  const leads = JSON.parse(readFileSync(p, 'utf8')).data;
  const s = summarise(leads);
  assert.equal(s.leads, 6);
  assert.equal(s.tiers.SCREENED_SITE, 2);
  assert.ok(leads.every(l => l.status === 'UNKNOWN'));
});

test('state filter and screening lookup are pure and never invent sites', async () => {
  const {byState, statesOf, siteFor, ANALYSED_REGION} = await import('../frontend/src/india-data.ts');
  const ls = [lead('gevra', 'Chhattisgarh'), lead('kusmunda', 'Chhattisgarh'), lead('nigahi', 'Madhya Pradesh')];
  assert.deepEqual(statesOf(ls), ['Chhattisgarh', 'Madhya Pradesh']);
  assert.equal(byState(ls, 'Chhattisgarh').length, 2);
  assert.equal(byState(ls, '').length, 3);
  assert.equal(siteFor(undefined, 'gevra'), undefined);
  assert.equal(siteFor({sites: [{id: 'gevra'}]}, 'nigahi'), undefined);
  assert.doesNotMatch(ANALYSED_REGION.text, /confirmed/i);
});

test('Phase 24B snapshot (if present) claims no detections or national coverage', () => {
  const p = new URL('../frontend/public/local/india-screening.json', import.meta.url);
  if (!existsSync(p)) return;
  const r = JSON.parse(readFileSync(p, 'utf8')).data;
  assert.equal(r.claims.verified_detections, 0);
  assert.equal(r.coverage.national_coverage, false);
  assert.ok(r.sites.every(s => s.status === 'UNKNOWN' && s.attribution === 'UNKNOWN'));
});
