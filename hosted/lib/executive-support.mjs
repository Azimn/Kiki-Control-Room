/**
 * Small, deterministic executive-function scaffolding for the Site.
 * No model guesses, fabricated due dates, task mutation, or provider actions.
 * A work session is a separate commitment, never proof its source task is done.
 */
export const SESSION_STATES = Object.freeze(["idle","active","paused","completed"]);
const PLAYBOOKS = Object.freeze({
  email: [
    "Open one relevant message in your approved email account.",
    "Identify the single decision or reply this message needs.",
    "Draft or discuss the reply in your approved work environment.",
    "Check whether it was actually sent; record the remaining action if not."
  ],
  course: [
    "Open the relevant course or university system.",
    "Find the single item that needs a decision or update.",
    "Work on that item for five minutes, without switching to another task.",
    "Verify the result or write down the exact next action."
  ],
  meeting: [
    "Open the relevant calendar or meeting request.",
    "Identify the scheduling decision or information needed.",
    "Prepare one appropriate response or calendar change for review.",
    "Confirm the actual outcome or save the remaining step."
  ],
  general: [
    "Open the document, page, or materials for this task.",
    "Locate the first concrete action, without planning the entire project.",
    "Work on that one action for five minutes.",
    "Verify what changed and record the next action."
  ]
});
export function playbookFor(title) {
  if (/\b(email|mailbox|inbox|reply|respond|outlook|message)\b/i.test(title)) return "email";
  if (/\b(canvas|grade|grading|class|course|student|syllabus|university|faculty|lecture)\b/i.test(title)) return "course";
  if (/\b(meeting|calendar|appointment|schedule|rsvp)\b/i.test(title)) return "meeting";
  return "general";
}
export function nextAction(title, previous = null) {
  const steps = PLAYBOOKS[playbookFor(title)];
  if (previous == null) return steps[0];
  const position = steps.indexOf(previous);
  return steps[position + 1] || null;
}
export function suggestWork(hostedTasks = [], pcSnapshot = null, now = new Date()) {
  const pcTasks = Array.isArray(pcSnapshot?.tasks) ? pcSnapshot.tasks : [];
  const pcObserved = pcSnapshot?.observed_at && Date.parse(pcSnapshot.observed_at);
  // PC is the authority for PC tasks. A stale read is explicitly labeled stale.
  const source = pcTasks.length ? "pc_snapshot" : "hosted";
  const sourceTasks = source === "pc_snapshot" ? pcTasks : hostedTasks;
  const candidates = sourceTasks.filter(t => t && t.status === "open" &&
    (!t.snoozed_until || Date.parse(t.snoozed_until) <= now.getTime()));
  candidates.sort((a,b) => {
    // Only explicit task metadata is used. No fabricated urgency or priority.
    const at = Date.parse(a.created_at || "") || 0;
    const bt = Date.parse(b.created_at || "") || 0;
    return at - bt || String(a.id || "").localeCompare(String(b.id || ""));
  });
  const task = candidates[0];
  if (!task || typeof task.title !== "string" || !task.title.trim()) return null;
  return {
    task_id: task.id, title: task.title, source,
    source_observed_at: source === "pc_snapshot" ? pcSnapshot.observed_at : null,
    snapshot_is_recent: source === "pc_snapshot" && Number.isFinite(pcObserved)
      ? now.getTime() - pcObserved <= 300000 && now.getTime() >= pcObserved : null,
    next_action: nextAction(task.title)
  };
}
export function applySessionCommand(current, command, offer = null, detail = "") {
  const old = current || {status:"idle",objective:"",next_action:"",last_outcome:""};
  const state = old.status || "idle";
  if (!SESSION_STATES.includes(state)) throw Error("Unsupported work-session state.");
  const output = {objective:old.objective || "", next_action:old.next_action || "",
    last_outcome:old.last_outcome || "", status:state};
  if (command === "begin") {
    if (state === "active" || state === "paused") throw Error("Resume or finish the existing session before selecting a new task.");
    if (!offer || !offer.title || !offer.next_action) throw Error("No eligible task to offer.");
    output.objective = offer.title;
    output.next_action = offer.next_action;
    output.last_outcome = "Session started. No task actions have been verified.";
    output.status = "active";
  } else if (command === "pause" || command === "defer") {
    if (state !== "active") throw Error("Only an active session can be paused.");
    output.status = "paused";
    output.last_outcome = "Paused with the exact next action retained; no task completion claimed.";
  } else if (command === "resume") {
    if (state !== "paused") throw Error("Only a paused session can be resumed.");
    output.status = "active";
  } else if (command === "step") {
    if (state !== "active") throw Error("Resume the session before recording progress.");
    const next = nextAction(output.objective, output.next_action);
    if (!next) throw Error("No further suggested step. Record the outcome or finish the session.");
    output.last_outcome = "User reported completing: " + output.next_action +
      " External outcome not independently verified.";
    output.next_action = next;
  } else if (command === "next") {
    if (state !== "active" && state !== "paused") throw Error("Start a session first.");
    if (typeof detail !== "string" || !detail.trim() || detail.length > 1000) throw Error("Next action must contain 1 to 1000 characters.");
    output.next_action = detail.trim();
    output.last_outcome = "Next action recorded by the user; external outcome not verified.";
  } else if (command === "finish") {
    if (state !== "active" && state !== "paused") throw Error("No unfinished session to end.");
    output.status = "completed";
    output.last_outcome = "Work session ended by user; source task has NOT been marked complete.";
  } else {
    throw Error("Unsupported session operation.");
  }
  for (const field of ["objective","next_action","last_outcome"]) {
    if (output[field].length > 1000) throw Error("Session field exceeds 1000 characters.");
  }
  return output;
}
