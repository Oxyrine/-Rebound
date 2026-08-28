Status: ready-for-agent

## Problem Statement

To complete the REBOUND AI Buildathon project, we need a clean evidence run that generates precise metrics and video assets. Currently, the batch runner lacks structural safety around idempotency (risking accidental depletion of the Razorpay Test Mode link budget if run parameters drift) and executes reconciliation inline (giving a human no time to complete a checkout, thereby breaking the "completed link" metrics funnel). Additionally, the ground truth evaluation metrics are not properly segregated from the live execution, which makes reporting murky.

## Solution

We will enforce a structurally safe evidence run by pinning the audit log to a specific evidence path and strictly guarding the CLI against accidental overwrites. We will separate link creation from status reconciliation into distinct, offline steps using an intermediate JSON results file, allowing a manual checkout window. Finally, we will clearly separate ground truth labels from execution routing so metrics correctly distinguish between "intra-rater agreement" and "fixture validity."

## User Stories

1. As a developer running the evaluation, I want the batch runner to require an explicit audit path when executing links, so that I don't accidentally spend API quota on a misnamed scratch file.
2. As a developer, I want the batch runner to hard-fail if I specify a first-run flag but the audit log already exists, so that I don't accidentally overwrite or append duplicate data to the pinned evidence.
3. As a developer preparing for a video demo, I want the batch runner to run in a "reconcile-only" mode, so that I can manually check out a payment link in the browser before recording the reconciliation metrics.
4. As a system evaluator, I want the batch runner to persist case results and interpretation fields as a simple dictionary in a JSON file, so that downstream metrics scripts can read them cleanly without parsing an append-only log.
5. As a system evaluator, I want the metrics script to access both the frozen pass-2 labels and the original day-1 fixture labels directly from the results file, so that I can report accurate metrics on fixture validity versus intra-rater agreement.
6. As a developer concerned with API rate limits, I want the LLM interpretation loop to pause for 1 second per case, so that I don't hit the 20 requests/day free-tier limits aggressively.
7. As a reviewer, I want the combined two-arm evaluation table and final metrics report to be emitted to a single markdown file in the evidence directory, so that the entire run output is self-contained and easily readable on GitHub.
8. As a developer writing tests, I want the CLI parser to accept an optional argument list, so that I can unit test flag combinations without monkeypatching system arguments.

## Implementation Decisions

- **Idempotency Guard**: Idempotency will be enforced via a pinned audit log path rather than SQLite. The CLI will enforce this by requiring an audit path when links are executed, and requiring a first-run flag when creating a new log.
- **Offline Reconciliation**: The batch runner will be split into creation and reconciliation phases. The creation phase will persist output to a JSON results dictionary (keyed by case ID). The `--reconcile-only` phase will read this dictionary, update the payment status by querying Razorpay, and overwrite the JSON dictionary in place.
- **Ground Truth Loading**: The function responsible for loading cases will fetch the frozen pass-2 labels. The runner will attach both the frozen label and the original fixture label to each case result so the metrics generator can diff them directly.
- **Rate Limiting**: A simple 1-second pause will be added inside the LLM interpretation loop.
- **Metrics Emission**: The metrics generator script will output its final report as a markdown file inside the evidence directory to keep artifacts consolidated.
- **CLI Testability**: The main function of the batch runner will accept an optional arguments list (`def main(argv=None): ... parser.parse_args(argv)`) to pass directly to the argument parser, avoiding the need for `sys.argv` monkeypatching.

## Testing Decisions

- A good test for these changes will assert the boundaries of the CLI flags without depending on global state or network calls.
- **Unit Test Seam**: The batch runner's CLI will be tested by calling its main function directly with mocked argument lists, asserting that conflicting flags raise system exits.
- **Integration Test Seam**: An end-to-end dress rehearsal of the batch runner will be performed with link execution disabled to ensure it parses cases, reads the JSON dictionary, and generates a valid report without crashing.
- **Data Integrity Seam**: Existing structural scripts (like the fixture manifest checker and the audit log verifier) will act as invariant checks to ensure the generated evidence remains uncorrupted.

## Out of Scope

- Retrofitting SQLite to manage idempotency.
- Forced caching or determinism work for the LLM non-determinism (it will just be documented).
- Pass 2 labeling and reconciliation (that will happen after the 48-hour clock expires).

## Further Notes

- An ADR documenting the trade-off of using a pinned audit log instead of SQLite for idempotency will be added to the architecture docs later.
