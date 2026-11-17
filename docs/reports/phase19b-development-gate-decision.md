# Phase 19B — EuroMineNet development gate decision

**NO-GO.** The frozen development split remains uncertified. No imagery was downloaded, no TEST payload was opened, and no roster, threshold, transfer ledger or Phase 19A receipt was changed.

## Metadata and site evidence

The author methods describe Sentinel-2 Level-2A annual observations, a preference for clear peak-vegetation imagery and ten optical bands on a common nominal 10 m grid. The official loader computes footprint change by differencing binarized annual masks. The public materials checked did not establish the exact contributing scene IDs, UTC dates, single-scene versus compositing details or applied snow/cloud rules for Czechia_2 or Czechia_3. Neither local image pair contains a usable sensing date or QA sidecar. The archive index from the feasibility check listed four auxiliary XML members, none for either Czech site. The EGU abstract identifies the benchmark tasks. Its linked full supplement exceeded the metadata reader's size limit. [Author methods](https://arxiv.org/html/2510.14661v1#S3.SS2) · [Official loader](https://github.com/AI4RS/EuroMineNet/blob/main/datasets/cd_dataset.py) · [EGU abstract](https://meetingorganizer.copernicus.org/EGU26/EGU26-13973.html)

The Czech Ministry report distinguishes Nástup Tušimice, Bílina, ČSA and Vršany/Šverma and lists separate mining-area maps. The paper illustrates Nástup–Tušimice and names Bílina in another figure. Neither source verified a crosswalk from these names to both released Czechia IDs and all operations represented in their cutouts. The bounded Czech Geological Survey lease-polygon requests timed out. Nonintersecting imagery envelopes at approximately 2.23 km separation therefore leave shared-complex risk **unresolved**. The record provides no basis to assert that both cutouts depict one complex. [Czech Ministry mining report](https://www.mpo.gov.cz/assets/dokumenty/55488/63564/653919/priloha001.pdf) · [Czech Geological Survey lease register](https://mapy.geology.cz/arcgis/rest/services/Suroviny/Surovinovy_informacni_system/MapServer/0)

## Label-blind visibility and alignment review

Rechecked hashes and the paired CRS, affine and dimensions from all 32 cached development image TIFFs. Reviewed all sites in a fixed B4/B3/B2 0–3500 display with identical orientation and jointly inspected the two Czech pairs at larger scale. The contact sheet displays no label contours. Looked for persistent roads, settlement edges, field patterns and water boundaries, broader tonal shifts and obscuration. This establishes coarse visual consistency only. It gives no pixel-level positional error, quantitative visibility mask or clearance of every window.

| Site | Image-only observation and remaining issue |
| --- | --- |
| Sweden_9 | Broad roads and worked-looking terrain align visually. Local dark terrain remains uncertain. |
| Czechia_3 | Persistent field and settlement context is recognizable. Site-complex independence from Czechia_2 remains unresolved. |
| Spain_15 | Broad pit context is recognizable. Water appearance and surrounding tone differ. |
| Slovakia_2 | Broad road and relief context is recognizable. Dark slopes retain possible shadow effects. |
| Romania_8 | Field divisions and roads are recognizable. Local surface tone differs. |
| Finland_4 | Broad industrial and forest context is recognizable. Dark areas retain illumination uncertainty. |
| Portuga_3 | Roads and bright quarry context are recognizable. Strong terrain and surface contrast varies. |
| Poland_9 | Coarse scene context persists. The 109-row raster provides no full unpadded window. |
| Hungary_1 | Broad shapes persist. The 2023 image looks more subdued and locally lower contrast. Visibility there is uncertain. |
| Austria_1 | Broad bench and road context persists. Terrain shadow is unresolved. |
| Germany_14 | Road and settlement context is recognizable. Water and local tone differ. |
| Italy_1 | Settlement and quarry context are recognizable. Local tonal differences remain. |
| Sweden_2 | Broad industrial context persists. Local bright areas require visibility confirmation. |
| Czechia_2 | In 2023 bright streaks and patches follow benches, fields and built surfaces. Snow or frost is visually plausible, but cloud, bright exposed substrate and illumination cannot be separated reliably without dated QA. Bright cover obscures parts of the stable context. No snow/cloud mask was inferred. |
| Romania_4 | Field divisions and settlements broadly persist. Seasonal tone differs. |
| Finland_7 | Roads and broad terrain remain recognizable. Dark terrain and surface tone vary. |

The existing Czech overlays were consulted separately to confirm how the file pairs are displayed. Mask content did not determine visual exclusions. The earlier window support remains provisional at 132 TRAIN windows with nine positive mines and 64 VALIDATION windows with four positive mines. **Certified support is zero windows and zero certified positive mines in both splits** because the frozen gate still fails. No training manifest or command was released. The label-blind contact sheet and grid checks are private under `outputs/external_eurominenet/phase19b/`.

## Draft request to authors — unsent

> We are checking the fixed EuroMineNet 2023→2024 development split. Could you provide, for Czechia_2 and Czechia_3 in both years, the Sentinel-2 product IDs and sensing UTC times, or the constituent scene list and annual compositing rule? Please include any original cloud, shadow, snow or valid-data masks or QA criteria, particularly for bright cover in Czechia_2 Year2023. Please also confirm how the annual TIFF masks are aligned to the imagery and provide the mine/lease identifiers or footprints for all operations represented by each cutout, including whether the two IDs share a mine complex or associated workings. We will keep the published split and withhold fitting until these checks are resolved.

Four focused acquisition and window-support tests passed. Indian supervised status is unaffected.
