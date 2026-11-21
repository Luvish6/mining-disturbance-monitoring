// Pure helpers for the India discovery view (no DOM) — unit-tested with node --test.
export type Lead = {id: string; state: string; district: string; longitude: number; latitude: number; status: string; common: number; changes: Record<string, number>; source: string};
export type Tier = 'SCREENED_SITE' | 'UNVERIFIED_LEAD' | 'MEGHALAYA_LEAD';

/** Leads with saved Phase 15C/16A site observations in frontend/public/local/india-sites/ (same list the Explorer uses). */
export const SCREENED_SITES = ['gevra', 'bhubaneswari'] as const;
/** Existing river study linked to a lead (Phase 12C/12D Brahmani at Talcher/Angul). */
export const RIVER_STUDY: Record<string, string> = {bhubaneswari: '#rivers-brahmani'};

export const TIERS: Record<Tier, {label: string; text: string}> = {
  SCREENED_SITE: {label: 'Screened site', text: 'Saved Sentinel-1/2 site observations and exploratory unsupervised screening (Phases 15C/16A). Still UNKNOWN: no independent reference.'},
  UNVERIFIED_LEAD: {label: 'Unverified lead', text: 'Location from a public environmental-clearance document with one seasonal S1/S2 screening summary (Phase 11C). Not a detection.'},
  MEGHALAYA_LEAD: {label: 'Meghalaya lead', text: 'Inside the detailed Meghalaya study state; see the Meghalaya analysis for systematic screening.'},
};

export function tierOf(l: Pick<Lead, 'id' | 'state'>): Tier {
  if ((SCREENED_SITES as readonly string[]).includes(l.id)) return 'SCREENED_SITE';
  if (l.state === 'Meghalaya') return 'MEGHALAYA_LEAD';
  return 'UNVERIFIED_LEAD';
}

export function summarise(leads: Lead[]) {
  const by: Record<Tier, number> = {SCREENED_SITE: 0, UNVERIFIED_LEAD: 0, MEGHALAYA_LEAD: 0};
  for (const l of leads) by[tierOf(l)]++;
  return {leads: leads.length, states: new Set(leads.map(l => l.state)).size, tiers: by,
    verified: 0 /* no lead has an independent reference anywhere in the project */};
}

/** India graticule extent (degrees) — a plain lon/lat frame, no boundary layer. */
export const INDIA_FRAME = {west: 68, east: 98, south: 6, north: 37};
export function plot(lon: number, lat: number, w = 600, h = 620, pad = 36) {
  const {west, east, south, north} = INDIA_FRAME;
  return [pad + (lon - west) / (east - west) * (w - 2 * pad), pad + (north - lat) / (north - south) * (h - 2 * pad)] as const;
}
export const inFrame = (lon: number, lat: number) =>
  lon >= INDIA_FRAME.west && lon <= INDIA_FRAME.east && lat >= INDIA_FRAME.south && lat <= INDIA_FRAME.north;
