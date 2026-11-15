# MineNetCD256 label-blind validation audit

The pinned official validation shard, from the [publisher dataset](https://huggingface.co/datasets/HZDR-FWGEL/MineNetCD256), contains 4,613 patches across ten mines. The scan read the complete site column and matched publisher counts. The first four rows per site were frozen before masks or predictions were opened. This equal-site sample is label-blind, with potential within-site spatial clustering. Frozen train and validation mine IDs were disjoint. Exact training-image duplicates and duplicate sampled pairs were checked by decoded hashes. The cropped data do not provide reliable coordinates for auditing near-overlap. Some validation sites informed the prior models. No previous test cache was accessed and no fitting, calibration or threshold changes were made.

The model artifact hashes and validation selection were checked against prior receipts. The 40 patches included 2,621,440 binary-mask pixels, 207,471 positives (7.91%). No pixels were excluded. None of the selected row IDs overlapped the local paired development caches. The successful run read 122,446,272 Parquet range bytes and took 88 seconds wall time on CPU.

| Validation site | Available patches | Positives in sample | U-Net P / R / F1 / IoU | U-Net predicted + / FPR | RF P / R / F1 / IoU | RF predicted + / FPR |
| --- | ---: | ---: | --- | --- | --- | --- |
| Brazil_01 | 132 | 0 | 0.000 / — / — / — | 22,463 / 8.57% | 0.000 / — / — / — | 88,256 / 33.67% |
| Chile_01 | 1001 | 2,330 | 0.000 / 0.000 / 0.000 / 0.000 | 6,027 / 2.32% | 0.031 / 0.444 / 0.058 / 0.030 | 33,383 / 12.45% |
| Congo_01 | 1122 | 46,751 | 0.460 / 0.135 / 0.209 / 0.117 | 13,769 / 3.45% | 0.061 / 0.042 / 0.050 / 0.025 | 32,044 / 13.97% |
| Germany_05 | 104 | 95,798 | 0.553 / 0.063 / 0.112 / 0.060 | 10,835 / 2.91% | 0.308 / 0.273 / 0.290 / 0.169 | 84,781 / 35.25% |
| Russia_08 | 240 | 0 | 0.000 / — / — / — | 7,513 / 2.87% | 0.000 / — / — / — | 18,237 / 6.96% |
| Serbia_01 | 182 | 0 | 0.000 / — / — / — | 7,582 / 2.89% | 0.000 / — / — / — | 17,818 / 6.80% |
| SouthAfrica_05 | 240 | 0 | 0.000 / — / — / — | 11,374 / 4.34% | 0.000 / — / — / — | 32,571 / 12.42% |
| SouthAfrica_08 | 304 | 62,592 | 0.408 / 0.062 / 0.108 / 0.057 | 9,521 / 2.82% | 0.143 / 0.292 / 0.192 / 0.106 | 127,906 / 54.93% |
| SouthAfrica_11 | 448 | 0 | 0.000 / — / — / — | 16,874 / 6.44% | 0.000 / — / — / — | 1,366 / 0.52% |
| Tanzania_01 | 840 | 0 | 0.000 / — / — / — | 7,735 / 2.95% | 0.000 / — / — / — | 28,250 / 10.78% |
| pooled | 4613 | 207,471 | 0.143 / 0.078 / 0.101 / 0.053 | 113,693 / 4.04% | 0.102 / 0.229 / 0.141 / 0.076 | 464,612 / 17.28% |

Zero-positive sites are reported individually. Recall, positive F1 and IoU are withheld there; they are excluded from the positive-site ranges. Precision is zero when those sites have predicted positives and undefined when there are no positive predictions.

At the frozen thresholds (U-Net .50 and RF .75), U-Net has lower FPR on nine of ten sites, with a worst case of 8.57% at Brazil_01 (22,463 false-positive pixels). RF has higher pooled recall and F1, with worst FPR 54.93% at SouthAfrica_08 (109,604 false-positive pixels). Among the four sites with foreground support, U-Net F1 spans .000–.209, RF .050–.290. There is a precision/recall and false-positive tradeoff.

Pooled Brier/ECE (ten equal-width score bins) are .234/.402 for U-Net and .300/.439 for RF; a constant score equal to the observed sample prevalence has descriptive Brier .073. Neither score is calibrated. At .35 the U-Net predicts every pixel positive; at .65 it predicts none. RF's best sampled diagnostic F1 is .156 at .50, with 44.59% FPR. At .90 FPR falls to 4.50% and F1 to .070. These diagnostics do not replace the frozen operating points.

Next experiment: score spatially spaced, label-blind windows in additional development AOIs with documented patch geometry, and preregister a site-level false-positive cap before comparing calibration or operating points. These RGB results do not validate the Indian Sentinel pipeline.

Reproduce with the existing environment and frozen local checkpoints. Pick a new output directory.

```powershell
python -B -m scripts.minenetcd256_validation_audit outputs/external_minenetcd256 outputs/external_minenetcd256/new_validation_audit
```

The ignored output holds sampled row IDs, source hashes, all per-site metrics, reliability bins and the fixed diagnostic threshold grid.
