# Kiki Slack master repair guide

The Slack listener sends messages to the live Dodaios BrainManager, the same
instance that serves Kiki's desktop chat. It builds the configured identity,
persona and memory layers and uses the main local model. Slack conversations
keep their own transcript and support shared recall by topic. The Slack entry
point can read memory and return a reply. Desktop actions stay on the desktop
entry point. The listener requires a main-agent receipt before posting.

## Restore after a Dodaios update

1. Keep the current working Dodaios install and Kiki Slack checkout available for
   rollback. Record both Git revisions and stop upgrading if the update would
   replace private workspace data. Use the known working install for live Slack
   while checking an update on a separate checkout.
2. Restore the existing Dodaios identity and continuity setup first. Verify
   Kiki's name, `SOUL.md`, effective custom prompt, and the existing
   `kiki-continuity` bridge from regular Dodaios. If an update replaced a local
   modification, use the private repair snapshot to review it against the new
   files. Apply changes individually if Git reports a conflict.
3. From the Kiki Control Room checkout, run
   `./integrations/slack/dodaios/Install-KikiSlackPrompt.ps1 -DodaiosPath <editable-checkout>`.
   It checks the source patch against the candidate checkout and stops if the
   hook changed or the installed module contains unrecognized edits. Re-run it after
   an update that replaces the editable source or after changing Slack session IDs.
   It reads the Slack policy and writes only the model and session IDs into
   Dodaios's own checkout, so the desktop process can find them even when
   Windows redirects Codex's app data. Use `-SlackPolicyPath` to supply the
   backed-up policy if needed. A packaged release may need
   to be run from an editable checkout for this hook to load.
4. Confirm the Windows account still has its existing files under
   `%LOCALAPPDATA%\KikiSlack`. The Slack policy is `slack.json`. It
   references two distinct Dodaios session IDs used for Slack transport and
   their transport model. Replies use the main BrainManager's configured local
   model. Keep the Slack installation and DPAPI files under the Windows account
   that encrypted them. If that account or machine changes,
   re-enter the credentials securely. The SQLite inbox holds replay and
   delivery receipts. Preserve it across restores and restarts.
5. Restart Dodaios through its desktop UI. Run the listener with
   `%LOCALAPPDATA%\KikiSlack\Start-KikiSlack.ps1` if it is stopped.
   The listener's local health endpoint is `http://127.0.0.1:8766/health`.

## Verify before switching to an updated install

- From regular Dodaios, verify Kiki's configured personality and shared recall.
- From the owner's Slack DM, ask `recall Calibos email`. Confirm the reply
  describes the saved ChatGPT exchange in Kiki's voice. An unavailable bridge
  or no matching receipts should be reported clearly. Only an explicit topic
  lookup sends the topic to the existing memory bridge. Slack turns are not
  written to the shared bridge by this hook.
- In the private Calibos channel, ask Kiki about recent channel messages.
  Confirm it uses channel context. Then ask `recall Calibos email` and verify
  it can summarize the matching shared receipt in that channel. Correlate the
  turn ID with the Dodaios log entry "Kiki main BrainManager completed Slack".
  A generic side-chat response will be rejected by the listener.
  Check one channel-level mention and one threaded mention. Keep the DM and
  channel session IDs distinct.
- Restart both processes and repeat the DM and channel checks. Confirm one
  listener owns port 8766 and a retry does not create another Slack reply.

## Rollback and backup

The installer patches the main BrainManager, its continuity wrapper, and the
chat API dispatcher. It also installs the Slack route module. With the listener idle, run `git apply --reverse --check` against
`integrations/slack/dodaios/main-agent.patch` from the Dodaios checkout
before reversing the patch with `git apply --reverse`. Restart Dodaios
normally. Keep the Slack inbox and DPAPI files in place. After an upstream
upgrade, switching back to the prior working checkout is safer than replacing
changed application files by hand.

The private snapshot keeps the pre-hook Dodaios working changes, selected
local integration files, the Slack launchers and policy, and an online SQLite
backup of the inbox. Treat the snapshot as private. The installer and this
guide contain no account credentials. Back up encrypted credentials separately
under your Windows account. Changes to voice, custom MCP bridges, and local
configuration have their own dependencies. Restore those from the snapshot
after checking their paths and current versions.
