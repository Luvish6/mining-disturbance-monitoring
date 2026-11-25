# Completed blinded Sentinel review integration

2026-11-25. Descriptive human interpretation, not independently verified mining accuracy. Both supplied CSVs were preserved unchanged and copied byte-for-byte into a new private integration directory. ID-based join: exactly30unique matched IDs, no duplicate, foreign or missing roster IDs. The missing response is retained as blank, not inferred. [Aggregate results and input hashes](human-review-consensus.json).

## Agreement

29complete disturbance-review pairs:10YES/YES,4NO/NO,1UNCERTAIN/UNCERTAIN,14disagreements;1incomplete item (RE2F35EF0, A visible_disturbance blank). Of14disagreements,2are YES/NO oppositions and12involve UNCERTAIN. Agreement15/29=51.724%; expected chance agreement0.350773; unweighted three-category Cohen kappa0.256410. Neither reviewer is treated as ground truth. No prevalence, detection-accuracy or independent-sample significance claim follows from this selected sample.

| A rows / B columns | YES | NO | UNCERTAIN |
|---|---:|---:|---:|
| YES |10|1|1|
| NO |1|4|2|
| UNCERTAIN |5|4|1|

| Distribution (all30submitted rows/reviewer) | A | B |
|---|---|---|
| Image quality |GOOD0;LIMITED25;UNUSABLE5|GOOD8;LIMITED17;UNUSABLE5|
| Confidence |HIGH0;MEDIUM20;LOW10|HIGH9;MEDIUM16;LOW5|

Nine distinct items have UNUSABLE imagery reported by at least one reviewer. LIMITED is usable-rated with limitations, not certified independent-reference quality. Distributions preserve the otherwise partially filled missing-disturbance row. Visible categories: A12YES/7NO/10UNCERTAIN/1missing; B17YES/9NO/4UNCERTAIN. Full change-type distributions are in the JSON.

## Mapping and priorities

Original crosswalk hash was authenticated against the frozen25C.1plan. All30items map to their existing candidate keys and canonical5km blocks/seed42 splits:10TRAIN blocks and3VAL blocks. Point locations, frozen AOI guards and split assignments passed metadata checks; no TEST inputs or imagery were opened. This does not create conservative reference polygon interiors or satisfy positional accuracy. Exact candidate mappings stay private.

Five consensus-disturbance items have GOOD/LIMITED imagery and MEDIUM/HIGH confidence from both: R0442ACAF,R0A099D23,R2C582A69,R6947EBA0,RB9952572. They span3TRAIN and2VAL blocks. Four items have at least one excavation_like vote: R0442ACAF,R4E2CCBF3,R6947EBA0,RB9952572. Three are in the priority set. These are attribution-verification leads only. YES/YES means agreement on visible disturbance, not agreement on cause, change subtype, quality or mining. For example R0442ACAF is agriculture for A and excavation_like for B.

## Admission and blockers

**Accepted mining positives0; accepted negatives0.** All30mining_attribution values remain UNKNOWN and reference_label remains empty/null. No unusable item becomes a negative. Existing src/phase3/admission.validate_references rejects the shared-input evidence as non-independent; the original strict review importer is unchanged. The new analysis-only intake accepts valid pseudonymous/partial submissions for statistics, not admission. Submitted identifiers A/B do not authenticate actual people or reviewer independence.

Missing gates: independent dated evidence for both frozen seasons, verified mining/non-mining interpretation, conservative georeferenced polygons, documented positional error<=30m, source/reviewer rights, confirmed independent reviewer identities and adjudication. These chips are Sentinel-only shared model-input imagery per the existing licensing audit; Planet raw imagery restrictions do not affect their source data, but shared-source interpretation cannot serve as independent mining ground truth.

## Private outputs and reproduction

Directory: outputs/phase25/experiments/human-review-integration-v1/.

- original_review_A.csv,original_review_B.csv: unchanged private copies.
- merged_reviews.csv: all30ID-joined records, both original responses, missing fields and mapping.
- consensus_summary.json,interpretation_records.json,receipt.json: statistics, decisions-as-submitted, hashes and blockers.
- adjudication_queue.csv: all30rows, five priority items first; reviewer/adjudicator decisions and evidence fields remain blank. Coordinator-only: do not send unblinded candidate mappings/screening strata to new blinded reviewers.

Reproduce into a NEW ignored output directory with the existing environment:

```powershell
python -B -m scripts.phase25_review_results <original-review-A.csv> <original-review-B.csv> outputs/phase25/experiments/<new-private-run>
```

Thirteen focused tests passed (new analysis plus existing strict review/readiness gates). Publication/privacy audit passed for staged safe code, tests and aggregates. Original CSV hashes were rechecked after integration. No labels, training, imagery downloads, discovery reruns, TEST payload access or dashboard changes. Indian supervised training remains NO-GO; operational alerts remain zero.

**Next action:**complete A's missing RE2F35EF0 response and confirm reviewer identities/independence; obtain independent paired evidence for the five priority items (excavation-like flags first), then adjudicate via the unchanged reference protocol. Keep subtype disagreements and unusable imagery explicit.
