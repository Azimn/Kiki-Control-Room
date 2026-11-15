# Kiki identity research checkpoint: 2026-11-15 10:04 America/Chicago

## Current highest-impact work
Controlled public-safe smoke test of Jan's official `janhq/Jan-v1-edge-gguf` Q4_K_M model. This is an experimental candidate, **not** confirmed as the actual model on Jay's Jan installation and **not** a substitute for original K1-K1 historical evidence.

## Verified receipts
- Isolated branch: `experiment/kiki-jan-edge-smoke-20261115`.
- Test harness commit: `612cf33569807ffee00a67c762903d966447ea32`, `tests/jan_edge_smoke.py`. Read back with GitHub contents API.
- Workflow commit: `aa4b7e41aedef0948b87d4c550781b03aefd0bfa`, `.github/workflows/jan-edge-smoke.yml`.
- GitHub Actions run: https://github.com/Azimn/Kiki-Control-Room/actions/runs/43733093752, job `132869668426`. At checkpoint inspection, the runner was still compiling llama.cpp. **No inference results verified yet**.
- The connected skills listing returned no installed skills; original K1-K1 MyGPT instructions and the 39 linguistic conventions have **not** been recovered in this run. Do not manufacture or paraphrase them as exact text.

## Scope and safeguards
Six public-safe, generic prompts test aesthetic preferences, repeat consistency, principled disagreement, resistance to fabricated memories, reasoned preference revision, and temperature variation. These do not contain Jay's private conversations, Kiki's private history, or the original instruction text. Raw responses must be examined before any interpretation. Never promote these test outputs to canonical preferences.

## Next action
Inspect the Actions job and artifact. If failed, read actual failure log and repair on this isolated branch; rerun. If successful, record raw outputs, model hash and test parameters, assess limitations, then separately plan a private historical-context comparison with verified Jan model identification and original K1-K1 instructions. Keep canonical local SQLite unchanged.

## Negative findings
Direct local Hugging Face download was blocked in the prior interactive attempt. Remote Hugging Face Jobs returned HTTP 402, so no inference was executed there. No historical character claim is established by this smoke test.
