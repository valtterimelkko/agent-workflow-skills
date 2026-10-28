/**
 * Watch Wake — be woken by an Internal API watch on another session.
 *
 * The Pi Web UI Internal API's long-horizon watch is a durable server-side
 * observer, and (Internal API contract 1.22.0) it can wake a *managed* session
 * on fire. A bare `pi` CLI process is not managed by the server, so this
 * extension provides the same "watch the child, wake the parent" primitive
 * locally:
 *
 *   watch_wake_register   — register a watch on a child session (pure
 *                           observer; no onFire) and remember the baseline
 *   watch_wake_list       — list local registrations
 *   watch_wake_cancel     — delete the watch and stop waking
 *
 * A process-local timer polls the durable ledger
 * (`GET /sessions/:id/watch?sinceIndex=N`) — one cheap request per interval;
 * the server did the watching. On a new firing the extension steers the wake
 * into a busy host at the next tool boundary, or starts an idle host with a
 * follow-up. A steer that races the turn boundary falls back once to follow-up.
 *
 * Tokens are never configured here: the socket and token file are read from
 * PI_WEB_UI_WATCH_WAKE_SOCKET / PI_WEB_UI_WATCH_WAKE_TOKEN_FILE or the
 * standard ~/.pi-web-ui defaults on each call.
 */

import * as fs from "node:fs";
import * as http from "node:http";
import * as os from "node:os";
import * as path from "node:path";
import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";
import { Type } from "typebox";
import { WatchWakeManager, registrationsFingerprint, type PersistedRegistrationEntry } from "./manager.ts";
import { registerDeadlineHost } from "./deadline-host.ts";

const ENTRY_TYPE = "watch-wake-registrations";

function configFromEnv(): { socketPath: string; tokenPath: string } {
	return {
		socketPath: process.env.PI_WEB_UI_WATCH_WAKE_SOCKET ?? path.join(os.homedir(), ".pi-web-ui", "internal-api.sock"),
		tokenPath: process.env.PI_WEB_UI_WATCH_WAKE_TOKEN_FILE ?? path.join(os.homedir(), ".pi-web-ui", "internal-api-token"),
	};
}

function readToken(tokenPath: string): string {
	const token = fs.readFileSync(tokenPath, "utf8").trim();
	if (!token) throw new Error(`Internal API token file is empty: ${tokenPath}`);
	return token;
}

/** One token-authenticated call over the Internal API Unix socket. */
function callApi(method: string, requestPath: string, body?: unknown, hostSessionId?: string | null): Promise<{ status: number; json?: any }> {
	const { socketPath, tokenPath } = configFromEnv();
	const token = readToken(tokenPath);
	const payload = body === undefined ? undefined : JSON.stringify(body);
	return new Promise((resolve, reject) => {
		let settled = false;
		let req: http.ClientRequest;
		const fail = (reason: string) => {
			if (settled) return;
			settled = true;
			req.setTimeout(0);
			reject(new Error(`Internal API ${method} ${requestPath} failed: ${reason}`));
		};
		const succeed = (result: { status: number; json?: any }) => {
			if (settled) return;
			settled = true;
			req.setTimeout(0);
			resolve(result);
		};
		req = http.request(
			{
				socketPath,
				path: requestPath,
				method,
				headers: {
					authorization: `Bearer ${token}`,
					...(payload !== undefined ? { "content-type": "application/json", "content-length": Buffer.byteLength(payload) } : {}),
					// Contract 1.34.0 child surfacing: identify the calling (parent)
					// session so the server can link dispatched children and watches.
					...(hostSessionId ? { "x-parent-session": hostSessionId } : {}),
				},
			},
			(res) => {
				const chunks: Buffer[] = [];
				let bytes = 0;
				let ended = false;
				const maxResponseBytes = 256 * 1024;
				res.once("aborted", () => fail("response aborted before the complete body arrived"));
				res.once("error", (error) => fail(`response error: ${error.message}`));
				res.once("close", () => {
					if (!ended && !res.complete) fail("response closed before the complete body arrived");
				});
				res.on("data", (c: Buffer) => {
					if (settled) return;
					bytes += c.length;
					if (bytes > maxResponseBytes) {
						fail(`response exceeded ${maxResponseBytes} bytes`);
						res.destroy();
						return;
					}
					chunks.push(c);
				});
				res.once("end", () => {
					if (settled) return;
					ended = true;
					const text = Buffer.concat(chunks).toString("utf8");
					let json: any;
					try {
						json = JSON.parse(text);
					} catch {
						json = { error: text.slice(0, 400) };
					}
					succeed({ status: res.statusCode ?? 0, json });
				});
			},
		);
		req.once("error", (error) => fail(error.message));
		req.setTimeout(30_000, () => req.destroy(new Error("Internal API request timed out")));
		if (payload !== undefined) req.write(payload);
		req.end();
	});
}

function renderRegistration(reg: ReturnType<WatchWakeManager["get"]> & {}): string {
	const parts = [
		`id: ${reg.id}`,
		`child_session: ${reg.sessionId}`,
		`status: ${reg.status}`,
		`wakes_sent: ${reg.wakesSent}/${reg.maxWakes}`,
		`interval_s: ${reg.intervalSeconds}`,
		`baseline_firings: ${reg.sinceIndex}`,
	];
	if (reg.serverGeneration) parts.push(`server_generation: ${reg.serverGeneration}`);
	if (reg.serverCreatedAt) parts.push(`server_created_at: ${reg.serverCreatedAt}`);
	if (reg.status === "cancelled") {
		parts.push("local_delivery: stopped");
		parts.push(`remote_delete: ${reg.remoteCleanupPending ? "cleanup-pending" : reg.remoteDeleteAcknowledged ? (reg.remoteDeleteGenerationConfirmed ? "generation-confirmed" : "acknowledged (legacy, not generation-confirmed)") : reg.remoteDeleteAllowed ? "not-confirmed" : "not-authorised"}`);
	}
	if (reg.lastError) parts.push(`last_error: ${reg.lastError}`);
	return parts.join("\n");
}

const ConditionSchema = Type.Object({
	id: Type.Optional(Type.String({ description: "Stable condition id (auto c0, c1… when omitted)" })),
	type: Type.Union([Type.Literal("event_type"), Type.Literal("tool"), Type.Literal("text"), Type.Literal("deadline")], {
		description: "event_type (match a NormalizedEvent.type, e.g. agent_end) | tool (toolName/phase/argIncludes) | text (contains or pattern) | deadline (server-side timer). An event name must go in eventType, never in type.",
	}),
	eventType: Type.Optional(Type.String({ description: "For event_type: the event type to match" })),
	dataMatch: Type.Optional(Type.Record(Type.String(), Type.Union([Type.String(), Type.Number(), Type.Boolean()]), {
		description: "For event_type: primitive shallow equality filters on the event data (passed through unchanged)",
	})),
	toolName: Type.Optional(Type.String({ description: "For tool: tool name" })),
	phase: Type.Optional(Type.Union([Type.Literal("start"), Type.Literal("end")], { description: "For tool: phase (default start)" })),
	argIncludes: Type.Optional(Type.String({ description: "For tool: substring required in args/result" })),
	contains: Type.Optional(Type.String({ description: "For text: substring to match" })),
	pattern: Type.Optional(Type.String({ description: "For text: regex source (tested case-insensitively by default)" })),
	patternFlags: Type.Optional(Type.String({ description: "For text: regex flags (default 'i')" })),
	source: Type.Optional(Type.Union([Type.Literal("assistant"), Type.Literal("any")], { description: "For text: assistant output (default) or any text" })),
	afterSeconds: Type.Optional(Type.Integer({ description: "For deadline: seconds until the server-side timer fires (integer 1..86400)", minimum: 1, maximum: 86400 })),
	once: Type.Optional(Type.Boolean({ description: "Fire only on first match (default true)" })),
});

const RegisterParams = Type.Object({
	session_id: Type.String({ description: "The CHILD session to observe (any runtime managed by Pi Web UI). Must not be this session." }),
	conditions: Type.Array(ConditionSchema, { description: "Watch conditions (same spec as POST /sessions/:id/watch)" }),
	message: Type.String({
		description: "Wake message injected here when a condition fires. Placeholders: {{sessionId}}, {{conditionId}}, {{eventType}}, {{firedAt}}, {{firingCount}}. E.g. 'Your child {{sessionId}} finished ({{conditionId}}) — inspect and continue.'",
		maxLength: 4000,
	}),
	max_wakes: Type.Optional(Type.Integer({ description: "Max local wake deliveries (1-10, default 1)", minimum: 1, maximum: 10 })),
	interval_seconds: Type.Optional(Type.Integer({ description: "Poll interval seconds (>=5, default 30)", minimum: 5, maximum: 3600 })),
	label: Type.Optional(Type.String({ description: "Optional label for the server-side watch", maxLength: 200 })),
});

const ListParams = Type.Object({});
const CancelParams = Type.Object({
	id: Type.String({ description: "Registration id from watch_wake_register" }),
});

export default function (pi: ExtensionAPI) {
	let hostRef: ExtensionAPI | null = pi;
	let hostContext: { isIdle(): boolean } | null = null;
	// Contract 1.34.0: this session's id, sent as X-Parent-Session on API calls.
	let hostSessionId: string | null = null;
	let pollTimer: ReturnType<typeof setInterval> | undefined;
	let pollCycle: Promise<void> | null = null;

	const sendWake = (text: string): boolean => {
		if (!hostRef) return false;
		if (hostContext?.isIdle() ?? true) {
			try {
				hostRef.sendUserMessage(text, { deliverAs: "followUp", triggerTurn: true });
				return true;
			} catch {
				return false;
			}
		}
		try {
			hostRef.sendUserMessage(text, { deliverAs: "steer" });
			return true;
		} catch {
			// The active turn may have ended between isIdle() and delivery.
			try {
				hostRef.sendUserMessage(text, { deliverAs: "followUp", triggerTurn: true });
			} catch {
				return false;
			}
			try {
				pi.appendEntry("watch-wake-delivery", { delivery: "followUp-fallback", at: Date.now() });
			} catch {
				// Delivery succeeded; fallback audit persistence is best-effort.
			}
			return true;
		}
	};

	const deadlines = registerDeadlineHost(pi, sendWake);
	const callOwnedApi = (method: string, requestPath: string, body?: unknown) => {
		if (!hostRef) throw new Error('Host session ended; refusing further watch API calls.');
		return callApi(method, requestPath, body, hostSessionId);
	};
	const manager = new WatchWakeManager({
		// Recheck ownership before EACH request, including after capability/GET awaits.
		callApi: callOwnedApi,
		supportsGenerationPreconditions: async () => {
			const response = await callOwnedApi('GET', '/api/v1/capabilities');
			if (response.status !== 200) throw new Error(`Watch capability discovery failed: HTTP ${response.status}`);
			const capability = response.json?.features?.watchGenerationPreconditions;
			if (capability === undefined) return false;
			if (capability?.generationField === 'generation' && capability?.registerField === 'expectedGeneration' && capability?.deleteBodyField === 'expectedGeneration') return true;
			throw new Error('Watch generation capability has an unsupported field contract; refusing mutation.');
		},
		sendWake,
	});

	// Persist only when the snapshot actually changes (cursor advance, wake budget
	// consumption, registration add/cancel). An unchanged poll writes nothing —
	// the host session file must not grow while the session idles (an earlier
	// design appended one identical entry per poll, growing an idle session file
	// by megabytes of duplicate entries).
	let lastPersistedFingerprint: string | null = null;
	const persistRegistrations = () => {
		try {
			const registrations = manager.toEntries();
			const fingerprint = registrationsFingerprint(registrations);
			if (fingerprint === lastPersistedFingerprint) return;
			pi.appendEntry(ENTRY_TYPE, { registrations });
			// Advance only after append succeeds. A transient append failure must leave
			// the same snapshot retryable on the next poll/mutation.
			lastPersistedFingerprint = fingerprint;
		} catch {
			// Best-effort persistence; the server-side watch survives regardless.
		}
	};

	const startTimer = () => {
		if (pollTimer) return;
		// A fixed minimum-cadence tick lets the manager honour each registration's
		// own due time, including watches added after this timer starts.
		pollTimer = setInterval(() => {
			if (pollCycle) return;
			pollCycle = manager.pollDue()
				.then(persistRegistrations)
				.catch(() => undefined)
				.finally(() => { pollCycle = null; });
		}, 5_000);
		pollTimer.unref?.();
	};

	pi.on("session_start", async (_event, ctx) => {
		hostContext = ctx;
		hostSessionId = ctx.sessionManager.getSessionId();
		// Local deadline recovery must not wait for remote watch I/O.
		await deadlines.start(ctx);
		if (!hostRef) return; // Shutdown can occur while overdue recovery yields.
		// Reconcile persisted registrations: attach (never re-register — the
		// server ledger must survive) and resume from the persisted firing cursor.
		try {
			const entries = ctx.sessionManager.getBranch();
			const registrations = [...entries]
				.reverse()
				.find((entry) => entry.type === "custom" && "customType" in entry && entry.customType === ENTRY_TYPE) as
				| { data?: { registrations?: PersistedRegistrationEntry[] } }
				| undefined;
			const restored = registrations?.data?.registrations ?? [];
			if (restored.length > 0) await manager.reconcile(restored, hostSessionId ?? undefined);
			const restoredFingerprint = registrationsFingerprint(restored);
			const reconciledFingerprint = registrationsFingerprint(manager.toEntries());
			if (restoredFingerprint === reconciledFingerprint) {
				// Exact restore: unchanged polls must not rewrite the same entry.
				lastPersistedFingerprint = reconciledFingerprint;
			} else {
				// Attach failure, generation enrichment, or state repair changed truth.
				// Persist it now; do not seed a fingerprint for bytes never appended.
				persistRegistrations();
			}
		} catch {
			// Best-effort restore.
		}
		if (manager.list().some((r) => r.status === "watching")) startTimer();
	});

	pi.on("session_shutdown", async () => {
		deadlines.dispose();
		// Pi creates a fresh extension factory for quit, reload, new, resume and
		// fork. Every old instance must relinquish timers and stale send handles.
		if (pollTimer) clearInterval(pollTimer);
		pollTimer = undefined;
		pollCycle = null;
		hostContext = null;
		hostRef = null;
		hostSessionId = null;
	});

	pi.registerTool({
		name: "watch_wake_register",
		label: "Watch Wake Register",
		description: [
			"Register a durable Internal API watch on a CHILD session and get woken here when it fires — the cross-session parent-wake for this bare CLI process.",
			"Use when you dispatched long-horizon work to another session (any runtime: pi, claude, opencode, antigravity, commandcode) via the Pi Web UI Internal API and want to go idle instead of polling for news.",
			"Condition choice: event_type agent_end is the safe default — it fires exactly once per child turn (a prompt with five tasks wakes you once, after all five finish; it also fires when the child stops early to ask). Text sentinels wake mid-turn but only if the child emits the exact string — name the sentinel in the child's task prompt. Tool conditions match a specific tool result (phase end + argIncludes), not prose.",
			"The server-side watch is a pure observer; this extension polls its durable ledger on an interval (cheap), steers a busy host, and starts an idle host. Firings that predate a new registration never re-wake you.",
			"After a Pi Web UI server restart the watch reloads detached: poll marks the registration stale; re-register to resume. The child session id is the internal id from the create/dispatch response.",
		].join(" "),
		parameters: RegisterParams,
		async execute(_toolCallId, params) {
			if (!hostRef) throw new Error("Host session ended; refusing a new watch registration.");
			if (params.session_id === hostSessionId) {
				throw new Error("Refusing to watch this session itself: an idle session produces no events to act on. Watch the child, wake yourself from the child's watch.");
			}
			const reg = await manager.register({
				sessionId: params.session_id,
				conditions: params.conditions as never,
				message: params.message,
				maxWakes: params.max_wakes,
				intervalSeconds: params.interval_seconds,
				label: params.label,
				sourceSessionId: hostSessionId ?? undefined,
			});
			if (!hostRef) {
				throw new Error("Host session ended before registration completed. The remote watch may exist; local delivery is inactive. Reconcile before retrying.");
			}
			persistRegistrations();
			startTimer();
			return {
				content: [
					{
						type: "text",
						text: [
							"Watching — you will be woken here when a condition fires. Go idle; do not poll.",
							renderRegistration(reg),
							"The wake arrives as a user message in this conversation. One wake per new firing batch (bounded by max_wakes).",
						].join("\n"),
					},
				],
				details: { id: reg.id, sessionId: reg.sessionId, status: reg.status, maxWakes: reg.maxWakes, intervalSeconds: reg.intervalSeconds, serverGeneration: reg.serverGeneration },
			};
		},
	});

	pi.registerTool({
		name: "watch_wake_list",
		label: "Watch Wake List",
		description: "List this session's local watch-wake registrations (child session, status, wakes sent, baseline). A registration is 'stale' when its server-side watch disappeared (e.g. Pi Web UI restart) — re-register to resume.",
		parameters: ListParams,
		async execute() {
			const regs = manager.list();
			if (regs.length === 0) {
				return { content: [{ type: "text", text: "No watch-wake registrations. Use watch_wake_register to watch a child session." }] };
			}
			return {
				content: [{ type: "text", text: regs.map(renderRegistration).join("\n\n") }],
				details: { count: regs.length },
			};
		},
	});

	pi.registerTool({
		name: "watch_wake_cancel",
		label: "Watch Wake Cancel",
		description: "Cancel a watch-wake registration: deletes the server-side watch (releasing its residency claim) and stops waking this session.",
		parameters: CancelParams,
		async execute(_toolCallId, params) {
			if (!hostRef) throw new Error("Host session ended; refusing remote watch cancellation.");
			const reg = await manager.cancel(params.id, persistRegistrations);
			if (!reg) throw new Error(`No authoritative watch-wake registration found for id "${params.id}" (it may have been superseded)`);
			persistRegistrations();
			const remote = reg.remoteCleanupPending
				? `Local delivery stopped. Remote deletion was NOT confirmed; cleanup remains retryable. ${reg.lastError ?? ""}`
				: reg.remoteDeleteAcknowledged
					? reg.remoteDeleteGenerationConfirmed
						? `Local delivery stopped. Remote deletion of generation ${reg.serverGeneration} confirmed.`
						: "Local delivery stopped. Legacy DELETE acknowledged; this is not generation-atomic confirmation."
					: `Local delivery stopped without deleting a replacement. ${reg.lastError ?? "Remote deletion not confirmed."}`;
			return {
				content: [{ type: "text", text: `Cancelled local watch on ${reg.sessionId} (registration ${reg.id}).\n${remote}` }],
				details: { id: reg.id, status: reg.status, localDeliveryStopped: true, remoteCleanupPending: reg.remoteCleanupPending, remoteDeleteAcknowledged: reg.remoteDeleteAcknowledged, remoteDeleteGenerationConfirmed: reg.remoteDeleteGenerationConfirmed, serverGeneration: reg.serverGeneration, remoteDeleteAllowed: reg.remoteDeleteAllowed },
			};
		},
	});
}
