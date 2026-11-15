# Downstream river degradation monitoring and evidence limits

Downstream monitoring is a core research contribution alongside Indian land-disturbance screening. The contribution is a reproducible, quality-gated design for testing whether downstream reaches support comparable spectral observations. It includes a supported Brahmani contrast and explicitly withheld Lukha and Myntdu contrasts. Degradation and mine-specific effects remain unverified.

## Reproduced seasonal results

The frozen windows are 1 November 2023–31 March 2024 and 1 November 2024–31 March 2025. Sentinel-2 harmonized Level-2A reflectance is joined to the cloud-probability collection. The water screen applies existing cloud, shadow and edge masks, SCL water, positive green–NIR NDWI and 20 m clearance from the closest failing-mask pixel centre. The gate requires at least 25 connected common-valid 10 m cells and pairs in at least two calendar months. NDTI is the unitless red–green difference (B4 − B3)/(B4 + B3) on admitted water support. SCL is natively 20 m. The 10 m output does not increase SCL resolution or guarantee pure water.

Brahmani SW3 and 2416 have 93 and 75 connected 10 m cells, respectively. There are 16 matched before/after pairs across five months on dates shared by both reaches. The retained source observations span 3 November 2023 through 27 March 2024 and 2 November 2024 through 27 March 2025. Source scenes and dates remain in the Phase 12C receipt and Phase 12D table.

| Statistic | Before | After | After minus before |
| --- | ---: | ---: | ---: |
| Upstream SW3 median NDTI | −.1008 | −.0872 | +.0136 |
| Far downstream 2416 median NDTI | −.0377 | −.1008 | −.0630 |
| Median of same-date downstream minus upstream differences | +.0644 | −.0162 | −.0806 |

Same-date reach differences ranged from −.0016 to +.1220 before and −.0656 to +.0222 after. The last row is the median of within-date contrasts in each season. It does not subtract the two station-level medians. Samal had 20 pairs and no fixed common support. The use of shared UTC dates reduces date mismatch between sites, though the same date does not identify a shared parcel of water.

CHIRPS has complete 1-, 3- and 7-day antecedent sums for the 32 dates at both station cells. The seven-day maximum at SW3 was 74.59 mm before and 13.98 mm after, and at 2416 it was 64.78 and 19.28 mm. Seasonal station-cell sums were 131.48/74.11 mm at SW3 and 120.87/84.34 mm at 2416. These local coarse-cell estimates contextualize differences in weather before observations. Catchment rainfall, discharge, dam operations, adjacency, glint, suspended solids and other source contributions were not resolved. The spectral contrast does not establish improvement or degradation.

At the four original Meghalaya stations, Khaddum had no screened water, Sunapur lacked after-season interior observations, and Mihmyntdu had no screened interior dates. At Leshka, five matched pairs spanning three months had only 12 fixed connected cells, below 25, with potential impoundment influence. All five nearby Phase 12B alternatives also failed. One Lukha alternative had two matched pairs and zero common cells. Retain these exclusions and withhold seasonal NDTI. [Phase 4A](phase4a-river-feasibility.md) · [Phase 4B](phase4b-leshka-spectral-pilot.md)

## Candidate-to-reach linkage

| Region | Supported relationship | Missing evidence |
| --- | --- | --- |
| Brahmani and Bhubaneswari | HydroSHEDS reciprocal links establish mapped main-stem order Samal → SW3 → 2416. The mine plan names Bangaru Jhor on the northern boundary and describes its drainage to the Brahmani. Monitoring records document a Bhubaneswari sedimentation outlet to that tributary in 2013 and 2014. These support a plausible route. [Mine plan](https://forestsclearance.nic.in/writereaddata/Compliancereport/UaComplianceFull_FPORMIN1550172022_1905251648365478.pdf) · [Historical outlet records, table 5.9](https://www.niti.gov.in/sites/default/files/2019-01/Report%20on%20Coal%20Mining%2C%20Displacement%20and%20Rural%20Livelihoods%20A%20Study%20in%20Mahanadi%20Coalfield%20Odisha.pdf) | Study-period outlet identity and activity, its downstream route and confluence location relative to the retained SW3/2416 footprints. A planned diversion or historical outlet cannot establish recent discharge. |
| Lunar–Lukha | MSPCB documents mining-area tributaries and a stream from the Lumshnong area feeding the Lunar before its confluence with the Lukha at Khaddum. The Phase 12B reach links describe local flow direction. [Lukha action plan](https://megspcb.gov.in/documents/Revised_and_Action_Plan_of_Lukha_River2020.pdf) | No individual candidate-to-outlet trace verifies KORPET, Sumon Pohduna or the Lumshnong candidate polygon as connected to a sampled reach. The monitored Sentinel windows also failed the spectral gate. |
| Myntdu–Leshka | Phase 12B links adjacent main-stem reaches. MeECL documents dam releases, and Leshka's window may be influenced by storage or backwater. [Release guidance](https://meecl.nic.in/index.php/2022/06/07/guidelines-for-release-of-water-through-the-gates-of-the-myntdu-leshka-stage-i-concrete-dam/) | Candidate outlet paths, release/discharge timing and usable matched interior support. |
| Gevra | The three exploratory polygons are in the Gevra window in Chhattisgarh. | This project has no verified routed connection from those features to the monitored Brahmani, Lukha or Myntdu reaches. They cannot be paired with these river contrasts. |

**Smallest next step.** Request one dated, georeferenced Bhubaneswari as-built drainage map or verified outfall/confluence survey from MCL or the Odisha pollution control board. It should identify the actual outfall, Bangaru flow direction and Brahmani junction, and indicate whether the outlet operated in the two study windows. Trace the junction on the Phase 12C network and confirm whether the sampled footprints bracket it. This checks exposure geometry only. Time-matched discharge and field measurements would be needed to interpret sediment or chemistry, and other sources and controls would still matter for attribution.

## Verification and reproduction

Phase 12D replay from the frozen Phase 12C receipt and masks reproduced its CSV byte-for-byte. Phase 12A replay from Phase 4A/4B similarly reproduced the station and daily coverage tables. Fresh outputs were kept in an ignored audit directory. The portal adapters rebuilt the river snapshots from these frozen sources. Production build and browser checks exercised Brahmani season changes and Leshka's insufficient-support gate. No Earth Engine retrieval, edits to frozen outputs, or alert changes were made.

```powershell
New-Item -ItemType Directory outputs/river_replay
python -B scripts/phase12d_matched_brahmani.py --source outputs/phase12c_brahmani --output outputs/river_replay/brahmani.csv
python -B scripts/phase12a_river.py --screen outputs/phase4a_river_feasibility --pilot Myntdu-Leshka-3379 outputs/phase4b_leshka_spectral_pilot --output outputs/river_replay/meghalaya
```
