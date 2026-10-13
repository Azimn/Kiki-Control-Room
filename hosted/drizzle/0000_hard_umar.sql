CREATE TABLE `interaction_events` (
	`seq` integer PRIMARY KEY AUTOINCREMENT NOT NULL,
	`event_id` text NOT NULL,
	`thread_id` text NOT NULL,
	`turn_id` text NOT NULL,
	`event_kind` text NOT NULL,
	`source_channel` text NOT NULL,
	`source_native_id` text,
	`actor_id` text NOT NULL,
	`actor_kind` text NOT NULL,
	`idempotency_key` text NOT NULL,
	`content_json` text NOT NULL,
	`provenance_json` text NOT NULL,
	`parent_event_id` text,
	`recorded_at` text DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')) NOT NULL,
	FOREIGN KEY (`thread_id`) REFERENCES `conversation_threads`(`thread_id`) ON UPDATE no action ON DELETE no action
);
--> statement-breakpoint
CREATE UNIQUE INDEX `interaction_events_event_id_unique` ON `interaction_events` (`event_id`);--> statement-breakpoint
CREATE UNIQUE INDEX `event_retry` ON `interaction_events` (`source_channel`,`idempotency_key`);--> statement-breakpoint
CREATE TABLE `tasks` (
	`id` text PRIMARY KEY NOT NULL,
	`owner_id` text NOT NULL,
	`title` text NOT NULL,
	`status` text DEFAULT 'open' NOT NULL,
	`snoozed_until` text,
	`created_at` text DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')) NOT NULL
);
--> statement-breakpoint
CREATE TABLE `conversation_threads` (
	`thread_id` text PRIMARY KEY NOT NULL,
	`owner_id` text NOT NULL,
	`subject_id` text DEFAULT 'kiki' NOT NULL,
	`created_at` text DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')) NOT NULL
);
--> statement-breakpoint
CREATE TABLE `conversation_turns` (
	`turn_id` text PRIMARY KEY NOT NULL,
	`thread_id` text NOT NULL,
	`user_event_id` text NOT NULL,
	`assistant_event_id` text,
	`state` text DEFAULT 'prepared' NOT NULL,
	`created_at` text DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')) NOT NULL,
	FOREIGN KEY (`thread_id`) REFERENCES `conversation_threads`(`thread_id`) ON UPDATE no action ON DELETE no action,
	FOREIGN KEY (`user_event_id`) REFERENCES `interaction_events`(`event_id`) ON UPDATE no action ON DELETE no action,
	FOREIGN KEY (`assistant_event_id`) REFERENCES `interaction_events`(`event_id`) ON UPDATE no action ON DELETE no action
);
--> statement-breakpoint
CREATE UNIQUE INDEX `conversation_turns_user_event_id_unique` ON `conversation_turns` (`user_event_id`);--> statement-breakpoint
CREATE UNIQUE INDEX `conversation_turns_assistant_event_id_unique` ON `conversation_turns` (`assistant_event_id`);
--> statement-breakpoint
CREATE TRIGGER interaction_events_no_update BEFORE UPDATE ON interaction_events BEGIN SELECT RAISE(ABORT,'interaction_events is append-only'); END;
--> statement-breakpoint
CREATE TRIGGER interaction_events_no_delete BEFORE DELETE ON interaction_events BEGIN SELECT RAISE(ABORT,'interaction_events is append-only'); END;
--> statement-breakpoint
CREATE INDEX ix_interaction_events_thread_seq ON interaction_events(thread_id,seq);
