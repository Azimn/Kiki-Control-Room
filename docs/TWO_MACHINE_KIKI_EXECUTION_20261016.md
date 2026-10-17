# Two-machine Kiki execution plan (2026-10-16)

## Existing low-power computer
Keep Jan/Ollama, Python/SQLite operational task authority, local Kiki Telegram poller, and outbound Control Room history synchronization unchanged. Do not stop any service or extract its secrets during laptop preflight. One Telegram poller per bot at any time.

## Powerful Windows laptop
Target OpenClaw's current supported native CLI/Gateway and signed Windows Hub, with existing Kiki personality/operating contract loaded into a clean workspace only. Do not install Hermes or OpenClaw as multiple competing live Kiki schedulers. Preserve installed Hermes as an inactive fallback. Windows Hub connects to the existing native gateway through Advanced setup rather than creating a separate app-owned WSL Gateway. The Windows execution node must be explicitly paired and its command surface approved.

New bootstrap script: [Bootstrap-Kiki.ps1](../integrations/openclaw/setup-windows/Bootstrap-Kiki.ps1). It supports a mutation-free -AuditOnly preflight, backs up existing config locally, stages canonical identity files without overwrite, installs only the missing OpenClaw CLI from the official script, delegates model sign-in to official onboarding, and downloads the signed Windows Hub. The companion conversation also contains a downloadable ZIP for a double-click setup launcher. These artifacts have not been run on Jay's physical laptop.

## Ownership and reconciliation
OpenClaw is an execution worker, not a new identity authority. Keep Kiki-Mind as identity, Control Room D1 for attributed interactions, and old PC SQLite for operational tasks until a deliberately tested migration. The laptop cannot assume it can call the private Kiki plugin from outside ChatGPT. Build an authenticated narrow read/write adapter and verify the same turn appears from Telegram and ChatGPT with source/provenance before shifting Telegram ownership. Do not paste bot tokens, access keys, email contents or sensitive personal/state data into the public repository.

## Autonomous behavior
Activate OpenClaw native owner-DM heartbeat only after one live Telegram delivery with a provider receipt and a single poller. Use OpenClaw native automations, not duplicate custom loops or additional ChatGPT task slots. Allow routine read-only and reversible actions under standard host permissions; require specific approval for privileged installs, deletion, account changes, spending, external third-party publication, or protected university data. Verify every command and reminder by provider/device receipt.

## Required production demonstrations
A Kiki-initiated check-in without ChatGPT being opened, actual Telegram delivery, attributed shared-history visibility across platforms, local file action with receipt, deduplicated synthetic calendar event with provider readback, resumption after interruption and Windows reboot, denial handling, and no damage to the old Jan/Telegram environment. Track initiation success, user inputs required, false completion claims and task progress.

Status: Work in progress, not a remotely completed installation. Acceptance gate: [Issue #13](https://github.com/Azimn/Kiki-Control-Room/issues/13). Draft deployment PR: [#12](https://github.com/Azimn/Kiki-Control-Room/pull/12).