# Kiki's bounded improvement loop (v0.1)

Kiki may inspect the code supporting her, propose small improvements, and use authorized development tools to prepare testable GitHub pull requests. This is not a self-modifying model, a second agent, or permission to rewrite the deployed system. Windows SQLite remains the sole task authority.

## What is implemented

The Python 3.10+ standard-library assessor at runtime/improvement/audit.py reads source files in a local checkout, without touching the operational SQLite database, private conversations, credentials, model inference endpoints, or network services. It produces JSON measurements and a Markdown report. It counts source size, conventional tests, maintenance markers, integration patches, and large modules. If an earlier JSON report is supplied, it calculates changes and flags substantial code growth without corresponding test growth.

Run tests: python -m unittest discover -s tests -p test_improvement_audit.py -v

Run report: python runtime/improvement/audit.py --root . --json-out audit-output/snapshot.json --markdown-out audit-output/report.md

Compare prior report: add --baseline previous/snapshot.json to the report command.

The workflow named Kiki complexity review checks the assessor on pull requests, accepts manual dispatch, and requests a weekly Monday 14:00 UTC report. It publishes a job summary and retains its JSON/Markdown artifact for 90 days. It downloads the preceding successful scheduled report, if present, to create a week-to-week comparison. No previous report means no trend claim.

**Important deployment limitation:** GitHub scheduled workflows run only from the default branch. The repository's main currently contains only the original README; the actual prototype lives on a stack of open PRs. This workflow is staged in a feature PR and will NOT start scheduling until it is merged to main. After merge, the workflow is configured to assess feature/animated-presence-browser-voice until the working branches are consolidated. Then change its checkout target to main. Claims of active recurring monitoring before this merge would be false.

## Authorized development cycle

Observe -> measure -> suggest -> prioritize -> prepare scoped change -> test -> review -> merge -> verify live deployment, if relevant -> record outcome. A commit or PR is not deployment evidence.

A proposal must name the observed problem, show its source, propose a bounded change and test, indicate uncertainty, and preserve a rollback path. Reasonable first proposals include adding regression tests, documenting an integration interface, organizing oversized modules, or identifying dead code. Kiki may generate proposed source changes on isolated branches using existing authorized GitHub access. Changes need passing tests and review before merging.

This v0.1 intentionally contains no self-triggered code editor and grants no write permissions to its GitHub workflow. A later improvement executor should submit changes as draft PRs only, with explicit allowlisted files, bounded budgets, independent checks, and no auto-merge. No automatic deployment, credential rotation, student-data access, email sends, calendar edits, new autonomous task authority, or tool-permission expansion.

The optional language model is for interpreting evidence and suggesting source changes, never for determining whether a change is verified. Read-only monitoring works without an LLM. The assessor uses filename and declaration heuristics rather than actual coverage, so it cannot claim correctness or live service health.

## Current architectural debt, verified October 20, 2026

The default branch is a stub. PR #15 adds the Windows-authoritative shared queue but remains a draft with Site patch reconciliation and live activation pending. PR #16 adds animated 2D presence and browser voice on top of PR #15. Several integration patches are still source artifacts, not proof of production deployment. First priority should be consolidation and deployment receipts, followed by an automated regression suite and measured improvements. Do not create another scheduler, separate Telegram poller, or competing database to solve this.

Acceptance for version 0.1 means a reproducible report, test-verified analyzer, evidence-linked proposals, and a reviewable PR. A recurring audit will only be considered running when the workflow appears on main and a scheduled execution receipt is available.
