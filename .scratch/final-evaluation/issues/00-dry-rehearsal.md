# 00: Full Execute-Links Dry Rehearsal

Type: task
Status: resolved

**What to build:** 
A pure engineering validation to confirm `--reconcile-only` actually flips `link_completed` after a real browser checkout on a throwaway scratch link. This requires zero frozen ground truth and ensures the Razorpay integration and offline reconciliation window work end-to-end before the nerve-wracking, un-redoable one-shot evidence day.

**Blocked by:** 
None (can start immediately)

- [ ] Run `run_batch.py` with `--execute-links` on a throwaway/scratch case
- [ ] Complete the generated Razorpay checkout link manually in the browser
- [ ] Run `run_batch.py` with `--reconcile-only`
- [ ] Verify the system correctly queries Razorpay and flips `link_completed` in-place

## Answer

Not run as a standalone step -- the live run went straight in and hit the Razorpay rate limit. The execute/checkout/reconcile flow was nonetheless validated end to end during ticket 03: 10 links created, all 10 checked out via the documented mock-bank flow, all 10 reconciled to status 'paid' with link_completed flipped in-place. `--reconcile-only` itself was exercised (and also rate-limited; the tail 3 GETs completed after a 90s wait via a targeted operational step).
