/**
 * Minimal Site runtime adapter contract.
 *
 * Sites may generate its own MCP transport and authorization middleware.
 * Bind these functions to that supported transport. NEVER trust an owner ID
 * provided by an MCP tool argument; resolve it from the verified session.
 */
import { createKikiToolService, KIKI_SITE_TOOL_DEFINITIONS } from "./kiki-tools.mjs";

export function createSiteToolHandlers({ db, resolveVerifiedIdentity }) {
  if (typeof resolveVerifiedIdentity !== "function") {
    throw new Error("Verified session identity resolver is required.");
  }
  const tools = createKikiToolService(db);
  const implementations = {
    kiki_get_brief: tools.getBrief,
    kiki_get_history: tools.getHistory,
    kiki_prepare_turn: tools.prepareTurn,
    kiki_commit_turn: tools.commitTurn
  };
  return KIKI_SITE_TOOL_DEFINITIONS.map(def => ({
    name: def.name,
    description: def.description,
    readonly: def.readonly,
    inputSchema: def.input,
    async invoke({ arguments: args = {}, requestContext } = {}) {
      // The site or plugin host supplies a VERIFIABLE auth context here.
      // A visitor-supplied ownerId or a website cookie string isn't proof.
      const verified = await resolveVerifiedIdentity(requestContext);
      if (!verified || typeof verified.ownerId !== "string") {
        throw new Error("Not signed in to Kiki.");
      }
      const allowed = new Set(Object.keys(def.input.properties || {}));
      if (!args || typeof args !== "object" || Array.isArray(args) ||
          Object.keys(args).some(key => !allowed.has(key))) {
        throw new Error("Unexpected tool arguments.");
      }
      const result = await implementations[def.name](verified, args);
      return { ...result, tool: def.name };
    }
  }));
}
