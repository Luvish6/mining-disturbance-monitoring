"""Phase 23I: preregistered human-review workflow for the Phase 22X disturbance clusters (TRAIN/VAL only).

  --sample  deterministic stratified sample -> docs/reports/phase23i-sample-manifest.csv (+ local crosswalk)
  --render  before/after/follow-up chips from cached 22X/22Y composites (0 Earth Engine requests)
  --sheet   blank review sheet + blinded offline HTML interface (local)

No labels are produced here. Reviewers are humans; mining attribution stays UNKNOWN.
"""
import argparse
import csv
import hashlib
import json
from pathlib import Path

import numpy as np

from scripts.phase22p_sar_corroboration import save, sha

OUT = Path("outputs/phase23i_review")
MANIFEST = Path("docs/reports/phase23i-sample-manifest.csv")
DESIGN = Path("docs/reports/phase23i-sample-design.json")
SEED = "23I"
N = dict(PERSISTENT=8, PARTIAL=6, RECOVERING=6, CONTROL=10, PURPOSIVE_TIER1=6)
MIN_SEP_M = 640          # chip width: review sites do not overlap
CHIP = 21                # 21 x 30 m = 630 m
MARK = 3                 # 3 x 3 cell (90 m) neutral marker, identical for detected items and controls
STRETCH = (0.0, 0.30)    # fixed linear reflectance stretch for every chip (as Phase 22N)
VV_RANGE = (-25.0, 0.0)
SCHEMA = dict(
    visible_disturbance=["YES", "NO", "UNCERTAIN"],
    change_type=["vegetation_removal", "exposed_soil", "excavation_like", "construction", "agriculture", "other", "unclear"],
    image_quality=["GOOD", "LIMITED", "UNUSABLE"],
    reviewer_confidence=["HIGH", "MEDIUM", "LOW"],
    mining_attribution=["UNKNOWN"])


def h(*parts):
    return hashlib.sha256(":".join([SEED, *map(str, parts)]).encode()).hexdigest()


def pick(candidates, n, taken, min_sep=MIN_SEP_M):
    """Hash-ordered sequential selection with a spatial-separation rule (same AOI distance in metres).
    candidates: dicts with key, aoi, x, y. Returns selected dicts and the number rejected for separation."""
    out, rejected = [], 0
    for c in sorted(candidates, key=lambda c: h(c["key"])):
        if len(out) >= n:
            break
        if any(t["aoi"] == c["aoi"] and np.hypot(t["x"] - c["x"], t["y"] - c["y"]) < min_sep for t in taken + out):
            rejected += 1
            continue
        out.append(c)
    return out, rejected


def neutral_id(key):
    return "R" + h("neutral", key)[:8].upper()


def load_aois():
    """Frozen 22X/22Y AOI arrays, eligibility, candidates, clusters and background (reuses Phase 22 code)."""
    from scripts.phase22l_temporal import select_candidates
    from scripts.phase22r_product_agreement import BANDS as PBANDS, background_mask, clusters
    from scripts.phase22x_landscape import NODATA, OUT as X_OUT, PREREG as X_PREREG, S2_FIELDS, STEP
    x = json.loads(X_PREREG.read_bytes())
    prod = json.loads((X_OUT / "products.json").read_bytes())["grids"]
    y = json.loads(Path("outputs/phase22y_persistence/clusters.json").read_bytes())
    ycls = {(r["aoi"], r["cluster"]): r["cls"] for r in y}
    aois = {}
    for key in sorted(x["aois"]):
        a = x["aois"][key]
        if a["split"] == "test":
            raise ValueError("TEST AOI in frame")
        stem = key.replace(":", "_")
        names = json.loads((X_OUT / f"{stem}_meta.json").read_bytes())["bands"]
        v = np.load(X_OUT / f"{stem}.npy").astype(float); v[v == NODATA] = np.nan
        g = dict(zip(names, v))
        b = np.stack([g[f"before_{k}"] for k in S2_FIELDS]); af = np.stack([g[f"after_{k}"] for k in S2_FIELDS])
        eligible, cand, _, _ = select_candidates(b, af, np.nan_to_num(g["before_count"]), np.nan_to_num(g["after_count"]), g["slope"])
        p = dict(zip(PBANDS, np.array(prod[key])))
        f = np.load(Path("outputs/phase22y_persistence") / f"{stem}.npy").astype(float); f[f == NODATA] = np.nan
        aois[key] = dict(meta=a, g=g, follow=f, cand=cand, cl=clusters(cand),
                         bg=background_mask(eligible, cand) & (p["datamask"] == 1), step=STEP)
        aois[key]["cls"] = [ycls.get((key, i + 1)) for i in range(len(aois[key]["cl"]))]
    return aois


def cell_xy(a, r, c):
    x0, y1 = a["meta"]["bounds"][0], a["meta"]["bounds"][3]
    return x0 + (c + .5) * a["step"], y1 - (r + .5) * a["step"]


def sample():
    aois = load_aois()
    z = {r["id"]: r for r in json.loads(Path("docs/reports/phase22z-summary.json").read_bytes())["shortlist"]}
    det = []
    for key, a in aois.items():
        for i, cells in enumerate(a["cl"], 1):
            if a["cls"][i - 1] is None:
                continue  # only the SAR-tested 22Y cluster set
            r, c = np.round(cells.mean(axis=0)).astype(int)
            x, y = cell_xy(a, r, c)
            det.append(dict(key=f"{key}/C{i:03d}", aoi=key, split=a["meta"]["split"], stratum=a["cls"][i - 1], row=int(r), col=int(c),
                            x=x, y=y, cells=len(cells), tier=z.get(f"{key}/C{i:03d}", {}).get("tier")))
    bg = []
    for key, a in aois.items():
        rr, cc = np.nonzero(a["bg"])
        for r, c in zip(rr, cc):
            x, y = cell_xy(a, r, c)
            bg.append(dict(key=f"{key}/B{r:02d}{c:02d}", aoi=key, split=a["meta"]["split"], stratum="CONTROL", row=int(r), col=int(c),
                           x=x, y=y, cells=1, tier=None))
    frame = {s: [d for d in det if d["stratum"] == s] for s in ("PERSISTENT", "PARTIAL", "RECOVERING")}
    frame["CONTROL"] = bg
    taken, design = [], {}
    for s in ("PERSISTENT", "PARTIAL", "RECOVERING", "CONTROL"):
        sel, rej = pick(frame[s], N[s], taken)
        for d in sel:
            d.update(design="PROBABILITY", inclusion_prob_nominal=N[s] / len(frame[s]), weight_nominal=len(frame[s]) / N[s])
        taken += sel
        design[s] = dict(frame_size=len(frame[s]), sampled=len(sel), rejected_for_separation=rej)
    purpo = [d for d in det if d["tier"] == 1 and d["key"] not in {t["key"] for t in taken}]
    sel, rej = pick(purpo, N["PURPOSIVE_TIER1"], taken)
    for d in sel:
        d.update(stratum="PURPOSIVE_TIER1", design="PURPOSIVE", inclusion_prob_nominal="", weight_nominal="")
    taken += sel
    design["PURPOSIVE_TIER1"] = dict(frame_size=len(purpo), sampled=len(sel), rejected_for_separation=rej,
                                     note="22Z Tier-1 review shortlist; NOT used for any rate estimate")
    for d in taken:
        d["review_id"] = neutral_id(d["key"])
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    cols = ["review_id", "design", "stratum", "aoi", "split", "cells", "inclusion_prob_nominal", "weight_nominal"]
    with MANIFEST.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore"); w.writeheader(); w.writerows(taken)
    OUT.mkdir(parents=True, exist_ok=True)
    save(OUT / "crosswalk.json", taken)  # exact keys/positions stay local (unblinded coordinator only)
    save(DESIGN, dict(phase="23I", seed=SEED, sizes=N, min_separation_m=MIN_SEP_M, strata=design,
                      frame="Phase 22X AOIs (17 TRAIN + 3 VAL, full-footprint TEST guard), 174 SAR-tested clusters, "
                            "22Y classes; controls = 22X background cells (eligible, > 60 m from candidates, land)",
                      selection="sha256(seed:key) order, sequential, rejecting items < 640 m from an already selected item in the "
                                "same AOI; nominal inclusion probability n_h/N_h (separation rule makes it approximate)",
                      exclusions="TEST blocks/tiles never in frame; non-SAR-tested clusters excluded; purposive items excluded from rates",
                      total=len(taken), manifest_sha256=sha(MANIFEST)))
    print({s: v["sampled"] for s, v in design.items()}, "total", len(taken))


def chip_window(r, c, n=64, size=CHIP):
    r0 = min(max(r - size // 2, 0), n - size)
    c0 = min(max(c - size // 2, 0), n - size)
    return r0, c0


def to_rgb(stack, stretch=STRETCH):
    rgb = np.clip((np.stack(stack, axis=-1) - stretch[0]) / (stretch[1] - stretch[0]), 0, 1)
    rgb[~np.isfinite(rgb).all(axis=-1)] = 0.5  # invalid shown as mid grey, never filled from elsewhere
    return np.nan_to_num(rgb, nan=0.5)


def render():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle
    aois = load_aois()
    items = json.loads((OUT / "crosswalk.json").read_bytes())
    (OUT / "chips").mkdir(parents=True, exist_ok=True)
    (OUT / "adjudication").mkdir(exist_ok=True)
    quality = []
    for it in items:
        a = aois[it["aoi"]]; g, f = a["g"], a["follow"]
        r0, c0 = chip_window(it["row"], it["col"])
        sl = (slice(r0, r0 + CHIP), slice(c0, c0 + CHIP))
        panels = [("2023-24 dry season", to_rgb([g["before_B4"][sl], g["before_B3"][sl], g["before_B2"][sl]]), g["before_count"][sl]),
                  ("2024-25 dry season", to_rgb([g["after_B4"][sl], g["after_B3"][sl], g["after_B2"][sl]]), g["after_count"][sl]),
                  ("2025-26 dry season", to_rgb([f[0][sl], f[1][sl], f[2][sl]]), f[6][sl])]
        vv = [np.clip((g[k][sl] - VV_RANGE[0]) / (VV_RANGE[1] - VV_RANGE[0]), 0, 1) for k in ("before_VV", "after_VV")]
        q = {lab.split()[0]: float(np.mean(np.nan_to_num(cnt) >= 2)) for lab, _, cnt in panels}
        quality.append(dict(review_id=it["review_id"], valid_fraction=q,
                            obs_count_range={lab.split()[0]: [int(np.nanmin(np.nan_to_num(cnt))), int(np.nanmax(np.nan_to_num(cnt)))] for lab, _, cnt in panels}))
        for blinded in (True, False):
            fig, axes = plt.subplots(1, 5, figsize=(12.5, 2.9), layout="constrained")
            for ax, (lab, img, _) in zip(axes[:3], panels):
                ax.imshow(img, interpolation="nearest"); ax.set_title(lab, fontsize=8)
            for ax, img, lab in zip(axes[3:], vv, ("S1 VV 2023-24", "S1 VV 2024-25")):
                ax.imshow(img, cmap="gray", interpolation="nearest"); ax.set_title(lab, fontsize=8)
            mr, mc = it["row"] - r0 - MARK // 2, it["col"] - c0 - MARK // 2
            for ax in axes:
                ax.add_patch(Rectangle((mc - .5, mr - .5), MARK, MARK, fill=False, ec="yellow", lw=1.2))
                if not blinded:  # coordinator/adjudication copy only: all candidate boundaries in the chip
                    cl_mask = np.zeros((64, 64), bool)
                    for cells in a["cl"]:
                        cl_mask[cells[:, 0], cells[:, 1]] = True
                    ax.contour(cl_mask[sl].astype(float), levels=[.5], colors="cyan", linewidths=.8)
                ax.set_xticks([]); ax.set_yticks([])
            fig.suptitle(f"{it['review_id']} | 30 m seasonal median composites (not single scenes); fixed stretch 0-0.30; "
                         f"grey = invalid; box = 90 m review marker", fontsize=8)
            target = OUT / ("chips" if blinded else "adjudication") / f"{it['review_id']}.png"
            fig.savefig(target, dpi=110); plt.close(fig)
    save(OUT / "chip_quality.json", quality)
    print("rendered", len(items), "items x 2 (blinded + adjudication)")


def sheet():
    items = json.loads((OUT / "crosswalk.json").read_bytes())
    cols = ["review_id", "reviewer_id", "review_time_utc", "visible_disturbance", "change_type", "image_quality",
            "reviewer_confidence", "mining_attribution", "notes"]
    for rv, salt in (("A", "orderA"), ("B", "orderB")):
        order = sorted(items, key=lambda it: h(salt, it["review_id"]))
        with (OUT / f"review_sheet_{rv}.csv").open("w", newline="", encoding="utf-8") as fh:
            w = csv.writer(fh); w.writerow(cols)
            for it in order:
                w.writerow([it["review_id"], rv, "", "", "", "", "", "UNKNOWN", ""])
        ids = [it["review_id"] for it in order]
        (OUT / f"review_{rv}.html").write_text(HTML.replace("__IDS__", json.dumps(ids)).replace("__RV__", rv)
                                               .replace("__SCHEMA__", json.dumps(SCHEMA)), encoding="utf-8")
    print("sheets and interfaces written for reviewers A and B")


HTML = """<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width">
<title>Disturbance review __RV__</title><style>body{font:14px system-ui;margin:16px;background:#fff;color:#111}
img{max-width:100%;border:1px solid #ccc}fieldset{margin:6px 0}button{margin:4px}</style></head><body>
<h2>Reviewer __RV__ - independent visual review</h2>
<p>Judge only what is visible. Do not consult other reviewers, model scores or maps. Mining attribution stays UNKNOWN.</p>
<div id="item"></div>
<script>
const IDS=__IDS__, S=__SCHEMA__, K="review___RV__";
let st={}; try{st=JSON.parse(localStorage.getItem(K)||"{}")}catch(e){}
let i=0;
function save(){try{localStorage.setItem(K,JSON.stringify(st))}catch(e){}}
function radios(f,id){return S[f].map(v=>`<label><input type=radio name=${f} value=${v} ${(st[id]||{})[f]===v?'checked':''}> ${v}</label>`).join(' ')}
function show(){const id=IDS[i];document.getElementById('item').innerHTML=`<h3>${i+1}/${IDS.length}: ${id}</h3>
<img src="chips/${id}.png"><form id=f>
${['visible_disturbance','change_type','image_quality','reviewer_confidence'].map(f=>`<fieldset><legend>${f}</legend>${radios(f,id)}</fieldset>`).join('')}
<fieldset><legend>mining_attribution</legend>UNKNOWN (fixed)</fieldset>
<textarea name=notes rows=2 cols=60>${(st[id]||{}).notes||''}</textarea></form>
<button onclick="nav(-1)">Previous</button><button onclick="nav(1)">Next</button><button onclick="exp()">Export CSV</button>`}
function grab(){const id=IDS[i],fd=new FormData(document.getElementById('f'));st[id]=Object.fromEntries(fd);st[id].mining_attribution='UNKNOWN';
st[id].review_time_utc=new Date().toISOString();save()}
function nav(d){grab();i=Math.max(0,Math.min(IDS.length-1,i+d));show()}
function exp(){grab();const c=['review_id','reviewer_id','review_time_utc','visible_disturbance','change_type','image_quality','reviewer_confidence','mining_attribution','notes'];
const rows=[c.join(',')].concat(IDS.map(id=>{const r=st[id]||{};return [id,'__RV__',r.review_time_utc||'',r.visible_disturbance||'',r.change_type||'',r.image_quality||'',r.reviewer_confidence||'','UNKNOWN',JSON.stringify(r.notes||'')].join(',')}));
const a=document.createElement('a');a.href=URL.createObjectURL(new Blob([rows.join('\\n')],{type:'text/csv'}));a.download='review___RV__.csv';a.click()}
show();
</script></body></html>"""


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    g = ap.add_mutually_exclusive_group(required=True)
    for fl in ("--sample", "--render", "--sheet"):
        g.add_argument(fl, action="store_true")
    a = ap.parse_args()
    (sample if a.sample else render if a.render else sheet)()
