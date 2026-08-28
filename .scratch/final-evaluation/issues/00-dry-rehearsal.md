# 00: Full Execute-Links Dry Rehearsal

Type: task
Status: claimed

**What to build:** 
A pure engineering validation to confirm `--reconcile-only` actually flips `link_completed` after a real browser checkout on a throwaway scratch link. This requires zero frozen ground truth and ensures the Razorpay integration and offline reconciliation window work end-to-end before the nerve-wracking, un-redoable one-shot evidence day.

**Blocked by:** 
None (can start immediately)

- [ ] Run `run_batch.py` with `--execute-links` on a throwaway/scratch case
- [ ] Complete the generated Razorpay checkout link manually in the browser
- [ ] Run `run_batch.py` with `--reconcile-only`
- [ ] Verify the system correctly queries Razorpay and flips `link_completed` in-place
