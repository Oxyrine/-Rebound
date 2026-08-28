Status: ready-for-agent

## Problem Statement

The REBOUND codebase is functionally complete and fully tested, but the official offline evaluation metrics have not yet been produced. The project requires a rigorous, blinded manual labeling process of the held-out cases to freeze the ground truth, followed by a final evidence run that integrates with Razorpay to prove functionality and calculate the final §23 and §25 metrics for the README.

## Solution

Execute a structured, two-pass manual labeling process separated by a 48-hour cool-down period to ensure high-fidelity ground truth. Once reconciled and frozen, execute the batch evaluation pipeline (`run_batch.py`) against all 59 cases, generating live Razorpay test links, reconciling them, and generating the final `metrics_report.md` to populate the project README.

## User Stories

1. As an AI Builder candidate, I want to perform a blind pass of manual labeling on the 22 held-out test cases, so that I establish a baseline for my evaluation data without being influenced by previous exposure.
2. As an AI Builder candidate, I want to wait 48 hours and perform a second blind pass of manual labeling, so that I can reconcile both passes into a high-confidence frozen ground truth dataset.
3. As a project evaluator, I want the final evaluation run to hit the real Razorpay API to generate checkout links, so that I can verify the system handles real-world API interactions.
4. As a project evaluator, I want the final metrics report to accurately reflect the system's performance on the frozen ground truth, so that I can evaluate the project's success.
5. As an open-source reader, I want the project README to reflect the final performance numbers, so that I understand the effectiveness of the REBOUND system.

## Implementation Decisions

- **Manual Labeling:** The labeling will be conducted manually in `fixtures/labeling_pass1_worksheet.json` by the user, followed by a second pass and a final reconciliation step to freeze the labels.
- **Evidence Run:** The final evidence run will use `scripts/run_batch.py --execute-links` against all 59 cases to generate the real Razorpay payment links, followed by manual checkout and `--reconcile-only`.
- **Metrics Generation:** The final step will automatically generate the §23 and §25 tables via `scripts/generate_metrics.py`, producing `evidence/metrics_report.md`.
- **Documentation:** The numbers generated in `evidence/metrics_report.md` will be manually extracted and copied into `README.md`.

## Testing Decisions

- **Seams**: Since the codebase is fully written and tested (117/117 passing), no new code or testing seams are required. The execution of the final evidence run against the live Razorpay API acts as the ultimate end-to-end integration test of the system.

## Out of Scope

- Modifying the underlying agent logic or rules engine based on the evaluation results (the code is frozen).
- Adding new test cases beyond the 59 existing cases in the fixture.

## Further Notes

- This spec tracks the non-code, operational phase of the Buildathon project submission.
