# §25 confidence threshold sweep

All cells `[from run]` -- recomputed offline from `dev_interpretations.json`, zero API calls.

| Threshold | Automation rate | Recall | Precision |
|---|---|---|---|
| 0.50 | 92% | 8/9 | 8/8 |
| 0.65 | 92% | 8/9 | 8/8 |
| 0.75 | 92% | 8/9 | 8/8 |
| 0.85 | 89% | 8/9 | 8/8 |

**Selected: 0.9**, frozen before held-out evaluation (`CONFIDENCE_THRESHOLD` in `src/policy_engine.py`).

> With ~5–7 dev hard-stop cases the sweep is coarse — a step function with a handful of points, not a smooth curve and not a knee.

> This is a model-reported confidence operating threshold, not a calibrated probability threshold. We do not claim these scores are calibrated probabilities; the sweep is a pragmatic method for choosing a review boundary on development data.