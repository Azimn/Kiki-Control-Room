# Kiki Control Room hosted Site

Private deployment: https://kiki-control-room.cherrylarch3.chatgpt.site

The deployable source and original image are preserved in the Sites-managed source repository. This folder mirrors the application, MCP service, schema and tests for review alongside existing development branches. Sites runtime scripts and supplied artwork remain in that complete checkout. Do not deploy this review mirror alone without the Sites starter helpers and original public/kiki.png.

D1 binding DB is the authoritative hosted interaction receipt ledger. Future Telegram and PC adapters must use secure owner mapping and this ledger, rather than make their local database authoritative. Kiki-Mind historical admission remains separate.

Implemented: online tasks, completion and snooze; paginated source-attributed interaction history; authenticated MCP prepare/commit; browser dictation with provider consent; browser speech playback and voice selection; plaintext portable export; golden-android responsive UI.

Validation: nine hosted SQLite tests, six donor MCP tests, six shared-history contract tests, TypeScript and production build passed. Deployment succeeded with MCP capability enabled. Browser visual testing and live connected-plugin calls have not been verified. The plugin is reported installed by Sites, but its tools were not callable from the authoring session.

Pending: Telegram/PC synchronization, website inference, calendar/email adapters, proactive delivery, encrypted independent backups and tested restoration, retention/deletion workflow and live cross-interface acceptance. This is a functioning private hosted foundation, not a claim that every integration in the brief is production-ready.

Run node --test tests/sites-tools.test.mjs under Node 22 or later. Apply versioned migrations via Sites; preserve DB on updates. No private records or runtime credentials belong in GitHub.
