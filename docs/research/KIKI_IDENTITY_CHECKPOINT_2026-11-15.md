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

## Follow-up verification: 2026-11-15 11:03 America/Chicago (17:03 UTC, scheduled checkpoint context)
- GitHub Actions run 43733093752, job 132869668426: **completed/success**, all six API requests executed, artifact ID 14169581344 uploaded at 2026-11-15T16:09:57Z. Artifact ZIP SHA-256 from GitHub: `a948d568e4132262b17764777dfdde0036ff994732b432d6c3711e637258e40d`. Model GGUF SHA-256 from runner log: `bdde4346e5e0ecc8b679dd6ca43d4e66d85c50227cda5287428d65489fad0c59`.
- Downloaded artifact ZIP and parsed `jan_edge_results.json` locally. Raw results contain six nonempty replies. **All six finished with `finish_reason=length` at `completion_tokens=220`**, so none establishes a complete final user-facing answer. This is a harness validity failure for character evaluation, not a successful identity test.
- The model repeatedly exposed self-directed planning prose in the `content` channel despite `chat_template_kwargs.enable_thinking=false`. Some replies include literal `</think>`. The bounded-history case invented a previous favorite-song exchange that was never supplied, which is a negative observation about unsupported autobiographical claims in this specific configuration, not evidence of Kiki's actual history.
- Critical next action: repair the test harness on this isolated branch to capture distinct reasoning/final fields if available, inspect the model's supported chat template and thinking controls, increase token budget, and assert `finish_reason=stop` plus a complete user-facing answer before evaluating personality. Preserve this failed/limited run as baseline, never promote generated preferences to Kiki's canonical identity.
- Original 39 conventions and actual Jay-hosted Jan model identifier remain unverified. No production runtime, local canonical SQLite, or private archive was changed.

## Corrective harness change: 2026-11-15 12:00 America/Chicago (18:00 UTC, scheduled run)
- Inspected the prior six-response failure and the exact `tests/jan_edge_smoke.py` source. The initial harness used `max_tokens=220` and only captured `message.content`, with no completion validity gate.
- On the isolated experiment branch, updated the test harness in commit `d5507ba7af9c809b643757ab544de8c285ea6bd2`: raised `max_tokens` to 1024, preserved `reasoning_content` separately when exposed, recorded available message fields, and added per-case `complete_user_answer` and thinking-marker checks. Incomplete or thinking-leaking responses remain recorded as negative results, not valid personality evidence.
- This change does **not** prove thinking is suppressed, does not establish that any responses are complete, and does not identify Jay's local Jan model. A new branch-triggered Actions run must be inspected and its raw artifact checked before claiming improvement.
- Next: verify the new run and artifact, then evaluate whether the server template supports a clean final answer. Original K1-K1 instructions and 39 linguistic conventions are still unavailable through the installed skills listing. Do not publish or infer private persona data.
