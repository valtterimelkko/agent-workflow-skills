/**
 * WatchWakeManager — session-local counterpart of the Internal API watch ledger.
 *
 * The server owns observation. This manager owns one local delivery cursor for
 * each child watch, persists it, and injects bounded wake/state messages into
 * the current Pi host. Server-generation preconditions are capability-gated;
 * legacy acknowledgement remains explicitly weaker than confirmed CAS deletion.
 */

import { createHash } from 'node:crypto';

export interface WatchConditionSpecLocal {
	id?: string;
	type: 'event_type' | 'tool' | 'text' | 'deadline';
	eventType?: string;
	/** Existing server condition language: primitive shallow equality on event.data. */
	dataMatch?: Record<string, string | number | boolean>;
	toolName?: string;
	phase?: 'start' | 'end';
	argIncludes?: string;
	contains?: string;
	pattern?: string;
	patternFlags?: string;
	source?: 'assistant' | 'any';
	/** For type 'deadline': seconds until the server-side timer fires (integer 1..86400). */
	afterSeconds?: number;
	once?: boolean;
}

/** The complete set of condition types the Pi Web UI server can ever match. */
export const KNOWN_CONDITION_TYPES = ['event_type', 'tool', 'text', 'deadline'] as const;

const PRIMITIVE_DATAMATCH = new Set(['string', 'number', 'boolean']);

/**
 * Registration-time validation. A condition whose shape can NEVER match is
 * refused locally, before any API call, with a message spelling out the correct
 * shape — instead of registering, reporting "watching", and stranding the parent
 * forever.
 *
 * Live incident: a parent registered `{ "type": "goal_end" }` (an
 * event name used AS the type) and `{ "type": "text_match" }`; the watch was
 * accepted and the wake never came.
 *
 * The known-type set mirrors the server's own `KNOWN_CONDITION_TYPES`
 * (condition evaluator): `event_type`, `tool`,
 * `text`, `deadline`. The server's shallow `data[k] === v` match is why a dotted
 * key or a nested object value can never fire.
 */
export function validateConditions(conditions: WatchConditionSpecLocal[]): void {
	for (const spec of conditions) {
		const type = (spec as { type?: unknown })?.type;
		if (typeof type !== 'string' || !(KNOWN_CONDITION_TYPES as readonly string[]).includes(type)) {
			const name = typeof type === 'string' ? type : String(type);
			const bare = /^[a-z][a-z0-9_]*$/.test(name);
			throw new Error(
				`unknown condition type "${name}" — valid types are ${KNOWN_CONDITION_TYPES.join(', ')}. ` +
					(bare
						? `If "${name}" is an event name, use {"type":"event_type","eventType":"${name}"} (the event name is the eventType field, not the type). `
						: '') +
					'For text, use {"type":"text","contains":"…"} or {"type":"text","pattern":"…"}.',
			);
		}
		if (type === 'event_type' && (typeof spec.eventType !== 'string' || spec.eventType.trim().length === 0)) {
			throw new Error(
				'event_type conditions require a non-empty string eventType, e.g. {"type":"event_type","eventType":"agent_end"}. ' +
					'Without it the condition can never match.',
			);
		}
		if (type === 'text' && spec.contains === undefined && spec.pattern === undefined) {
			throw new Error('text conditions require contains or pattern — without one the condition can never match');
		}
		if (spec.dataMatch !== undefined) {
			if (spec.dataMatch === null || typeof spec.dataMatch !== 'object' || Array.isArray(spec.dataMatch)) {
				throw new Error('dataMatch must be an object of top-level primitive key/value pairs, e.g. {"status":"paused"}');
			}
			for (const [key, value] of Object.entries(spec.dataMatch)) {
				if (key.includes('.')) {
					throw new Error(
						`dataMatch key "${key}" is dotted, but the server's match is shallow (a top-level event-data key only): ` +
							`it can never match. Use the top-level key (e.g. "${key.split('.').pop()}"), or watch the eventType itself.`,
					);
				}
				if (!PRIMITIVE_DATAMATCH.has(typeof value) || value === null) {
					throw new Error(
						`dataMatch value for "${key}" must be a primitive (string, number or boolean): the server compares ` +
							`event.data[key] === value shallowly, so an object, array or null value can never match.`,
					);
				}
			}
		}
	}
}

export interface RegisterArgs {
	sessionId: string;
	conditions: WatchConditionSpecLocal[];
	message: string;
	sourceSessionId?: string;
	maxWakes?: number;
	label?: string;
	intervalSeconds?: number;
}

export interface AttachArgs {
	sessionId: string;
	message: string;
	maxWakes?: number;
	intervalSeconds?: number;
	sinceIndex?: number;
	wakesSent?: number;
	createdAt?: number;
	id?: string;
	generation?: string;
	serverWatchId?: string;
	serverCreatedAt?: string;
	serverGeneration?: string;
	remoteDeleteGenerationConfirmed?: boolean;
	status?: RegistrationStatus;
	lastError?: string;
	sourceSessionId?: string;
	remoteCleanupPending?: boolean;
	remoteDeleteAcknowledged?: boolean;
	/** Explicit remote mutation authority; false for rejected/stale diagnostic records. */
	remoteDeleteAllowed?: boolean;
	stateNoticeAttempts?: number;
	stateNoticeKinds?: string[];
	/** Current host identity used to validate legacy entries that predate sourceSessionId persistence. */
	expectedOwnerSessionId?: string;
}

export type RegistrationStatus = 'watching' | 'done' | 'stale' | 'cancelled';

export interface Registration {
	id: string;
	sessionId: string;
	message: string;
	maxWakes: number;
	intervalSeconds: number;
	label?: string;
	status: RegistrationStatus;
	sinceIndex: number;
	wakesSent: number;
	createdAt: number;
	/** Locally unique replacement generation; unlike watchId it changes per POST. */
	generation: string;
	/** Server evidence used to reject restoration onto a newer replacement. */
	serverWatchId?: string;
	serverCreatedAt?: string;
	/** Opaque server token, separate from the local replacement generation. */
	serverGeneration?: string;
	remoteDeleteGenerationConfirmed?: boolean;
	lastError?: string;
	sourceSessionId?: string;
	/** Local delivery has stopped, but the server DELETE needs retry/inspection. */
	remoteCleanupPending?: boolean;
	/** DELETE acknowledged; only remoteDeleteGenerationConfirmed proves matching CAS. */
	remoteDeleteAcknowledged?: boolean;
	/** Whether this local record may issue DELETE at the child watch URL. */
	remoteDeleteAllowed: boolean;
	/** Runtime-only cadence. */
	nextPollAt: number;
	/** Runtime-only bounded state-notice accounting. */
	stateNoticeAttempts: number;
	stateNoticeKinds: Set<string>;
}

export interface PersistedRegistrationEntry {
	id?: string;
	sessionId: string;
	message: string;
	maxWakes?: number;
	intervalSeconds?: number;
	label?: string;
	sinceIndex?: number;
	wakesSent?: number;
	createdAt?: number;
	generation?: string;
	serverWatchId?: string;
	serverCreatedAt?: string;
	serverGeneration?: string;
	remoteDeleteGenerationConfirmed?: boolean;
	status?: RegistrationStatus;
	lastError?: string;
	sourceSessionId?: string;
	remoteCleanupPending?: boolean;
	remoteDeleteAcknowledged?: boolean;
	remoteDeleteAllowed?: boolean;
	/** Persisted notice accounting prevents repeated restore/poll notices across reloads. */
	stateNoticeAttempts?: number;
	stateNoticeKinds?: string[];
}

export interface WatchWakeManagerDeps {
	callApi: (method: string, path: string, body?: unknown) => Promise<{ status: number; json?: any }>;
	sendWake: (text: string) => boolean;
	now?: () => number;
	/** Production adapter discovers the exact live capability before mutation. */
	supportsGenerationPreconditions?: () => Promise<boolean>;
}

export function registrationsFingerprint(entries: PersistedRegistrationEntry[]): string {
	const canonical = (entries ?? []).map((entry) => JSON.stringify([
		entry.id ?? null,
		entry.sessionId ?? null,
		entry.message ?? null,
		entry.maxWakes ?? null,
		entry.intervalSeconds ?? null,
		entry.label ?? null,
		entry.sinceIndex ?? null,
		entry.wakesSent ?? null,
		entry.createdAt ?? null,
		entry.generation ?? null,
		entry.serverWatchId ?? null,
		entry.serverCreatedAt ?? null,
		entry.serverGeneration ?? null,
		entry.remoteDeleteGenerationConfirmed ?? null,
		entry.status ?? null,
		entry.lastError ?? null,
		entry.sourceSessionId ?? null,
		entry.remoteCleanupPending ?? null,
		entry.remoteDeleteAcknowledged ?? null,
		entry.remoteDeleteAllowed ?? null,
		entry.stateNoticeAttempts ?? null,
		[...(entry.stateNoticeKinds ?? [])].sort(),
	]));
	return createHash('sha256').update(canonical.join('|')).digest('hex');
}

const DEFAULT_MAX_WAKES = 1;
const DEFAULT_INTERVAL_SECONDS = 30;
const MIN_INTERVAL_SECONDS = 5;
const MAX_WAKE_BUDGET = 10;
const MAX_LOCAL_RECORDS = 100;
const MAX_STATE_NOTICE_ATTEMPTS = 4;

function serverGenerationOf(json: any): string | undefined {
	return typeof json?.generation === 'string' && json.generation.length > 0 && json.generation.length <= 200
		? json.generation : undefined;
}

function interpolate(template: string, firing: { conditionId?: string; eventType?: string; firedAt?: number }, sessionId: string, firingCount: number): string {
	const replaceAll = (s: string, find: string, value: string) => s.split(find).join(value);
	let out = replaceAll(template, '{{sessionId}}', sessionId);
	out = replaceAll(out, '{{conditionId}}', firing.conditionId ?? 'unknown');
	out = replaceAll(out, '{{eventType}}', firing.eventType ?? 'unknown');
	out = replaceAll(out, '{{firedAt}}', firing.firedAt !== undefined ? new Date(firing.firedAt).toISOString() : 'unknown');
	out = replaceAll(out, '{{firingCount}}', String(firingCount));
	return out;
}

export class WatchWakeManager {
	private readonly callApi: WatchWakeManagerDeps['callApi'];
	private readonly sendWake: WatchWakeManagerDeps['sendWake'];
	private readonly now: () => number;
	private readonly supportsGenerationPreconditions: () => Promise<boolean>;
	private readonly registrations = new Map<string, Registration>();
	private readonly currentBySession = new Map<string, string>();
	private readonly polls = new Map<string, Promise<Registration | undefined>>();
	private readonly mutationChains = new Map<string, Promise<unknown>>();
	private seq = 0;

	constructor(deps: WatchWakeManagerDeps) {
		this.callApi = deps.callApi;
		this.sendWake = deps.sendWake;
		this.now = deps.now ?? (() => Date.now());
		this.supportsGenerationPreconditions = deps.supportsGenerationPreconditions ?? (async () => false);
	}

	private nextIdentity(): { id: string; generation: string; createdAt: number } {
		const createdAt = this.now();
		const sequence = ++this.seq;
		return { id: `ww_${sequence}_${createdAt}`, generation: `local-${createdAt}-${sequence}`, createdAt };
	}

	private normalise(maxWakes?: number, intervalSeconds?: number): { maxWakes: number; intervalSeconds: number } {
		return {
			maxWakes: Math.max(1, Math.min(MAX_WAKE_BUDGET, maxWakes ?? DEFAULT_MAX_WAKES)),
			intervalSeconds: Math.max(MIN_INTERVAL_SECONDS, intervalSeconds ?? DEFAULT_INTERVAL_SECONDS),
		};
	}

	private withSessionMutation<T>(sessionId: string, operation: () => Promise<T>): Promise<T> {
		const prior = this.mutationChains.get(sessionId) ?? Promise.resolve();
		const next = prior.catch(() => undefined).then(operation);
		this.mutationChains.set(sessionId, next);
		void next.finally(() => {
			if (this.mutationChains.get(sessionId) === next) this.mutationChains.delete(sessionId);
		}).catch(() => undefined);
		return next;
	}

	private install(reg: Registration): void {
		const previousId = this.currentBySession.get(reg.sessionId);
		if (previousId && previousId !== reg.id) this.registrations.delete(previousId);
		this.registrations.set(reg.id, reg);
		this.currentBySession.set(reg.sessionId, reg.id);
		this.pruneTerminalHistory();
	}

	private pruneTerminalHistory(): void {
		if (this.registrations.size <= MAX_LOCAL_RECORDS) return;
		const removable = [...this.registrations.values()]
			.filter((reg) => reg.status !== 'watching')
			.sort((a, b) => a.createdAt - b.createdAt);
		while (this.registrations.size > MAX_LOCAL_RECORDS && removable.length > 0) {
			const reg = removable.shift()!;
			this.registrations.delete(reg.id);
			if (this.currentBySession.get(reg.sessionId) === reg.id) this.currentBySession.delete(reg.sessionId);
		}
	}

	private async expectedGeneration(args: RegisterArgs, previous?: Registration): Promise<string | null> {
		const response = await this.callApi('GET', `/api/v1/sessions/${encodeURIComponent(args.sessionId)}/watch`);
		if (response.status === 404) return null;
		if (response.status !== 200) throw new Error(`Cannot establish watch precondition: HTTP ${response.status}`);
		const generation = serverGenerationOf(response.json);
		if (!generation) throw new Error('Server advertised watch preconditions but returned no valid generation.');
		if (previous?.serverGeneration && previous.serverGeneration !== generation) throw new Error('WATCH_REPLACED: refusing to overwrite an external generation.');
		const watchSource = response.json?.sourceSessionId;
		if (watchSource && watchSource !== args.sourceSessionId) throw new Error('WATCH_OWNERSHIP_CHANGED: refusing to replace a watch held by another session.');
		const sameTimestamp = previous?.serverCreatedAt && previous.serverCreatedAt === response.json?.createdAt;
		if (!watchSource && !previous?.serverGeneration && !sameTimestamp) throw new Error('WATCH_OWNERSHIP_UNVERIFIED: existing watch cannot be safely replaced.');
		if (previous?.serverCreatedAt && response.json?.createdAt && !sameTimestamp) throw new Error('WATCH_REPLACED: server creation evidence changed.');
		return generation;
	}

	async register(args: RegisterArgs): Promise<Registration & { status: 'watching' }> {
		if (!args.sessionId?.trim()) throw new Error('sessionId is required');
		// The id goes into a URL path: refuse anything that could change the route.
		if (args.sessionId === '.' || args.sessionId === '..' || /[\/\\?#%\s]/.test(args.sessionId)) {
			throw new Error('sessionId is not a valid session id');
		}
		if (!args.conditions?.length) throw new Error('at least one condition is required');
		if (!args.message?.trim()) throw new Error('message is required');
		// Refuse a condition whose shape can never match BEFORE any API call: the
		// server would otherwise accept it and the wake would never come (F1).
		validateConditions(args.conditions);
		return this.withSessionMutation(args.sessionId, async () => {
			const { maxWakes, intervalSeconds } = this.normalise(args.maxWakes, args.intervalSeconds);
			const previousId = this.currentBySession.get(args.sessionId);
			const previous = previousId ? this.registrations.get(previousId) : undefined;
			const generationAware = await this.supportsGenerationPreconditions();
			if (!generationAware && previous?.serverGeneration) throw new Error('Watch CAS capability disappeared; refusing an unconditional replacement.');
			const expectedGeneration = generationAware ? await this.expectedGeneration(args, previous) : undefined;
			const res = await this.callApi('POST', `/api/v1/sessions/${encodeURIComponent(args.sessionId)}/watch`, {
				conditions: args.conditions,
				pin: true,
				label: args.label ?? `watch-wake:${args.sessionId}`,
				sourceSessionId: args.sourceSessionId,
				...(generationAware ? { expectedGeneration } : {}),
			});
			if (res.status !== 201) {
				const detail = res.json?.error ?? res.json?.code ?? `HTTP ${res.status}`;
				throw new Error(`Watch registration failed: ${detail}`);
			}
			const serverGeneration = generationAware ? serverGenerationOf(res.json) : undefined;
			if (generationAware && (!serverGeneration || serverGeneration === expectedGeneration)) {
				throw new Error('Ambiguous watch registration acknowledgement: valid fresh server generation missing. Remote state may exist; reconcile before retrying.');
			}
			const identity = this.nextIdentity();
			// A proved fresh generation has no pre-registration history. Consume
			// events received before its POST acknowledgement rather than losing them.
			const baseline = generationAware ? 0 : (typeof res.json?.firingCount === 'number' ? res.json.firingCount : 0);
			const reg: Registration = {
				...identity,
				sessionId: args.sessionId,
				message: args.message,
				maxWakes,
				intervalSeconds,
				label: args.label,
				status: 'watching',
				sinceIndex: baseline,
				wakesSent: 0,
				serverWatchId: typeof res.json?.watchId === 'string' ? res.json.watchId : undefined,
				serverGeneration,
				remoteDeleteGenerationConfirmed: false,
				serverCreatedAt: typeof res.json?.createdAt === 'string' ? res.json.createdAt : undefined,
				sourceSessionId: args.sourceSessionId,
				remoteCleanupPending: false,
				remoteDeleteAcknowledged: false,
				remoteDeleteAllowed: true,
				nextPollAt: this.now(),
				stateNoticeAttempts: 0,
				stateNoticeKinds: new Set(),
			};
			this.install(reg);
			return { ...reg, status: 'watching' as const };
		});
	}

	async attach(args: AttachArgs): Promise<Registration> {
		const { maxWakes, intervalSeconds } = this.normalise(args.maxWakes, args.intervalSeconds);
		if (args.expectedOwnerSessionId && args.sourceSessionId && args.sourceSessionId !== args.expectedOwnerSessionId) {
			throw new Error('WATCH_LOCAL_OWNER_CHANGED (persisted source session differs from the current host session)');
		}
		const res = await this.callApi('GET', `/api/v1/sessions/${encodeURIComponent(args.sessionId)}/watch`);
		if (res.status !== 200) {
			const detail = res.json?.error ?? res.json?.code ?? `HTTP ${res.status}`;
			throw new Error(`No watch to attach to (${detail}) — register watch_wake first or re-register after a server restart`);
		}
		const currentGeneration = serverGenerationOf(res.json);
		if (args.serverGeneration && currentGeneration !== args.serverGeneration) throw new Error('WATCH_REPLACED: persisted server generation is missing or different.');
		const currentCreatedAt = typeof res.json?.createdAt === 'string' ? res.json.createdAt : undefined;
		if (args.serverCreatedAt && currentCreatedAt && args.serverCreatedAt !== currentCreatedAt) {
			throw new Error('WATCH_REPLACED (server createdAt differs from the persisted generation)');
		}
		const currentOwner = typeof res.json?.sourceSessionId === 'string' ? res.json.sourceSessionId : undefined;
		// The live factory identity is authoritative. Persisted source identity is
		// evidence to validate, never authority that may override a fork/new host.
		const expectedOwner = args.expectedOwnerSessionId ?? args.sourceSessionId;
		if (currentOwner && expectedOwner && currentOwner !== expectedOwner) {
			throw new Error('WATCH_OWNERSHIP_CHANGED (server watch belongs to another source session)');
		}
		if (currentOwner && !expectedOwner) {
			throw new Error('WATCH_OWNERSHIP_UNVERIFIED (legacy local entry cannot adopt a claimed server watch)');
		}
		const identity = this.nextIdentity();
		const currentFiringCount = typeof res.json?.firingCount === 'number' ? res.json.firingCount : 0;
		const baseline = typeof args.sinceIndex === 'number' ? Math.max(0, args.sinceIndex) : currentFiringCount;
		const wakesSent = typeof args.wakesSent === 'number' ? Math.max(0, Math.min(maxWakes, args.wakesSent)) : 0;
		const reg: Registration = {
			...identity,
			id: args.id ?? identity.id,
			generation: args.generation ?? identity.generation,
			createdAt: args.createdAt ?? identity.createdAt,
			sessionId: args.sessionId,
			message: args.message,
			maxWakes,
			intervalSeconds,
			status: wakesSent >= maxWakes ? 'done' : 'watching',
			sinceIndex: baseline,
			wakesSent,
			serverWatchId: typeof res.json?.watchId === 'string' ? res.json.watchId : args.serverWatchId,
			serverCreatedAt: currentCreatedAt ?? args.serverCreatedAt,
			serverGeneration: args.serverGeneration,
			remoteDeleteGenerationConfirmed: args.remoteDeleteGenerationConfirmed ?? false,
			sourceSessionId: currentOwner ?? args.sourceSessionId,
			lastError: args.lastError,
			remoteCleanupPending: args.remoteCleanupPending ?? false,
			remoteDeleteAcknowledged: args.remoteDeleteAcknowledged ?? false,
			remoteDeleteAllowed: true,
			nextPollAt: this.now(),
			stateNoticeAttempts: Math.max(0, args.stateNoticeAttempts ?? 0),
			stateNoticeKinds: new Set(args.stateNoticeKinds ?? []),
		};
		this.install(reg);
		return { ...reg };
	}

	get(id: string): Registration | undefined {
		return this.registrations.get(id);
	}

	list(): Registration[] {
		return [...this.registrations.values()].map((reg) => ({ ...reg }));
	}

	private notifyState(reg: Registration, kind: 'poll-error' | 'terminal', reason: string): void {
		if (reg.stateNoticeKinds.has(kind) || reg.stateNoticeAttempts >= MAX_STATE_NOTICE_ATTEMPTS) return;
		reg.stateNoticeAttempts += 1;
		const delivered = this.sendWake(`Watch-wake state notice for child ${reg.sessionId}: ${reason}`);
		if (delivered) reg.stateNoticeKinds.add(kind);
		else reg.lastError = `${reason}; state notice delivery failed`;
	}

	async pollOnce(id: string): Promise<Registration | undefined> {
		const existing = this.polls.get(id);
		if (existing) return existing;
		const pending = this.pollOnceInternal(id).finally(() => {
			const reg = this.registrations.get(id);
			if (reg) reg.nextPollAt = this.now() + reg.intervalSeconds * 1000;
			if (this.polls.get(id) === pending) this.polls.delete(id);
		});
		this.polls.set(id, pending);
		return pending;
	}

	private async pollOnceInternal(id: string): Promise<Registration | undefined> {
		const reg = this.registrations.get(id);
		if (!reg) return undefined;
		if (this.currentBySession.get(reg.sessionId) !== id || reg.status !== 'watching') return { ...reg };

		let res: { status: number; json?: any };
		try {
			res = await this.callApi('GET', `/api/v1/sessions/${encodeURIComponent(reg.sessionId)}/watch?sinceIndex=${reg.sinceIndex}`);
		} catch (error) {
			if (this.currentBySession.get(reg.sessionId) !== id || reg.status !== 'watching') return { ...reg };
			reg.lastError = `poll failed: ${error instanceof Error ? error.message : String(error)}`;
			this.notifyState(reg, 'poll-error', reg.lastError);
			return { ...reg };
		}
		// Cancellation or replacement may have happened while GET was in flight.
		// The response belongs to the old local authority and must not deliver.
		if (this.currentBySession.get(reg.sessionId) !== id || reg.status !== 'watching') return { ...reg };
		if (res.status === 404) {
			reg.status = 'stale';
			reg.lastError = 'WATCH_NOT_FOUND (server restart or replacement removed this watch; re-register to resume)';
			this.notifyState(reg, 'terminal', reg.lastError);
			return { ...reg };
		}
		if (res.status !== 200) {
			reg.lastError = `poll failed: HTTP ${res.status}`;
			this.notifyState(reg, 'poll-error', reg.lastError);
			return { ...reg };
		}
		if (reg.serverGeneration && serverGenerationOf(res.json) !== reg.serverGeneration) {
			reg.status = 'stale';
			reg.remoteDeleteAllowed = false;
			reg.lastError = 'WATCH_REPLACED: server generation is missing or different.';
			this.notifyState(reg, 'terminal', reg.lastError);
			return { ...reg };
		}
		if (res.json?.status === 'detached') {
			reg.status = 'stale';
			reg.lastError = 'WATCH_DETACHED (server restarted; re-register to resume)';
			this.notifyState(reg, 'terminal', reg.lastError);
			return { ...reg };
		}
		const currentCreatedAt = typeof res.json?.createdAt === 'string' ? res.json.createdAt : undefined;
		if (reg.serverCreatedAt && currentCreatedAt && reg.serverCreatedAt !== currentCreatedAt) {
			reg.status = 'stale';
			reg.remoteDeleteAllowed = false;
			reg.lastError = 'WATCH_REPLACED (server createdAt differs from this local generation)';
			this.notifyState(reg, 'terminal', reg.lastError);
			return { ...reg };
		}
		const currentOwner = typeof res.json?.sourceSessionId === 'string' ? res.json.sourceSessionId : undefined;
		if (currentOwner && currentOwner !== reg.sourceSessionId) {
			reg.status = 'stale';
			reg.remoteDeleteAllowed = false;
			reg.lastError = 'WATCH_OWNERSHIP_CHANGED (server watch belongs to another source session)';
			this.notifyState(reg, 'terminal', reg.lastError);
			return { ...reg };
		}
		const total = typeof res.json?.firingCount === 'number' ? res.json.firingCount : reg.sinceIndex;
		const fresh: Array<{ conditionId?: string; eventType?: string; firedAt?: number }> = Array.isArray(res.json?.firings) ? res.json.firings : [];
		if (fresh.length === 0) {
			reg.sinceIndex = Math.max(reg.sinceIndex, total);
			return { ...reg };
		}

		const last = fresh[fresh.length - 1];
		let delivered = false;
		if (reg.wakesSent < reg.maxWakes) {
			delivered = this.sendWake(interpolate(reg.message, last, reg.sessionId, total));
			if (delivered) {
				reg.wakesSent += 1;
				reg.lastError = undefined;
			} else {
				reg.lastError = 'wake delivery failed (host channel down); will retry next poll';
			}
		}
		if (delivered) reg.sinceIndex = Math.max(reg.sinceIndex, total);
		if (reg.wakesSent >= reg.maxWakes) reg.status = 'done';
		return { ...reg };
	}

	async pollDue(): Promise<void> {
		const now = this.now();
		const due = this.list().filter((reg) => reg.status === 'watching' && reg.nextPollAt <= now);
		await Promise.all(due.map((reg) => this.pollOnce(reg.id)));
	}

	async cancel(id: string, onLocalStop?: () => void): Promise<Registration | undefined> {
		const initial = this.registrations.get(id);
		if (!initial) return undefined;
		// DELETE authority is consumed by acknowledgement. Repeating an old
		// cancellation must not delete a later external replacement at this URL.
		if (initial.status === 'cancelled' && initial.remoteDeleteAcknowledged) return { ...initial };
		// Stop local delivery before any network await or queued mutation. The
		// in-flight poll guard re-checks this status after its GET resolves.
		initial.status = 'cancelled';
		initial.remoteDeleteAcknowledged = false;
		try { onLocalStop?.(); } catch { /* local stop remains effective; caller may retry persistence */ }
		return this.withSessionMutation(initial.sessionId, async () => {
			const reg = this.registrations.get(id);
			if (!reg || this.currentBySession.get(initial.sessionId) !== id) {
				return {
					...initial,
					remoteCleanupPending: false,
					lastError: 'local delivery stopped; remote cleanup skipped because this registration was superseded',
				};
			}
			// Another queued cancel may have completed while this one waited.
			if (reg.remoteDeleteAcknowledged) return { ...reg };
			if (!reg.remoteDeleteAllowed) {
				reg.remoteCleanupPending = false;
				reg.remoteDeleteAcknowledged = false;
				reg.lastError = 'local delivery stopped; remote deletion skipped because this diagnostic record has no remote-delete authority';
				return { ...reg };
			}
			let response: { status: number; json?: any } | undefined;
			let generationAware = false;
			try {
				generationAware = await this.supportsGenerationPreconditions();
				if (reg.serverGeneration && !generationAware) throw new Error('Watch CAS capability disappeared; refusing unconditional DELETE.');
				if (generationAware && !reg.serverGeneration) {
					const observed = await this.expectedGeneration({ sessionId: reg.sessionId, sourceSessionId: reg.sourceSessionId, conditions: [], message: reg.message }, reg);
					if (observed === null) {
						reg.remoteCleanupPending = false;
						reg.remoteDeleteAllowed = false;
						reg.lastError = 'Remote watch is already absent; generation-specific deletion was not confirmed.';
						return { ...reg };
					}
					reg.serverGeneration = observed;
				}
				response = await this.callApi('DELETE', `/api/v1/sessions/${encodeURIComponent(reg.sessionId)}/watch`, generationAware ? { expectedGeneration: reg.serverGeneration } : undefined);
			} catch (error) {
				reg.remoteCleanupPending = true;
				reg.lastError = `local delivery stopped; remote cleanup pending: ${error instanceof Error ? error.message : String(error)}`;
				return { ...reg };
			}
			if (response.status === 409 && response.json?.code === 'WATCH_GENERATION_MISMATCH') {
				reg.remoteCleanupPending = false;
				reg.remoteDeleteAllowed = false;
				reg.remoteDeleteGenerationConfirmed = false;
				reg.lastError = 'WATCH_GENERATION_MISMATCH: this generation is no longer current; remote deletion not confirmed.';
				return { ...reg };
			}
			if (generationAware && response.status === 200 && (response.json?.success !== true || response.json?.generation !== reg.serverGeneration)) {
				reg.remoteCleanupPending = true;
				reg.remoteDeleteGenerationConfirmed = false;
				reg.lastError = 'Ambiguous DELETE acknowledgement: matching deleted generation was not returned. Reconcile before retrying.';
				return { ...reg };
			}
			if (response.status === 200 && response.json?.success !== false) {
				reg.remoteCleanupPending = false;
				reg.remoteDeleteGenerationConfirmed = generationAware;
				reg.remoteDeleteAcknowledged = true;
				reg.remoteDeleteAllowed = false;
				reg.lastError = undefined;
			} else {
				reg.remoteCleanupPending = true;
				const detail = response.json?.error ?? response.json?.code ?? `HTTP ${response.status}`;
				reg.lastError = `local delivery stopped; remote cleanup pending: ${detail}`;
			}
			return { ...reg };
		});
	}

	toEntries(): PersistedRegistrationEntry[] {
		return this.list().map((reg) => ({
			id: reg.id,
			sessionId: reg.sessionId,
			message: reg.message,
			maxWakes: reg.maxWakes,
			intervalSeconds: reg.intervalSeconds,
			label: reg.label,
			sinceIndex: reg.sinceIndex,
			wakesSent: reg.wakesSent,
			createdAt: reg.createdAt,
			generation: reg.generation,
			serverWatchId: reg.serverWatchId,
			serverCreatedAt: reg.serverCreatedAt,
			serverGeneration: reg.serverGeneration,
			remoteDeleteGenerationConfirmed: reg.remoteDeleteGenerationConfirmed,
			status: reg.status,
			lastError: reg.lastError,
			sourceSessionId: reg.sourceSessionId,
			remoteCleanupPending: reg.remoteCleanupPending,
			remoteDeleteAcknowledged: reg.remoteDeleteAcknowledged,
			remoteDeleteAllowed: reg.remoteDeleteAllowed,
			stateNoticeAttempts: reg.stateNoticeAttempts,
			stateNoticeKinds: [...reg.stateNoticeKinds].sort(),
		}));
	}

	private restoreTerminal(entry: PersistedRegistrationEntry): Registration {
		const identity = this.nextIdentity();
		const { maxWakes, intervalSeconds } = this.normalise(entry.maxWakes, entry.intervalSeconds);
		const reg: Registration = {
			...identity,
			id: entry.id ?? identity.id,
			generation: entry.generation ?? identity.generation,
			createdAt: entry.createdAt ?? identity.createdAt,
			sessionId: entry.sessionId,
			message: entry.message,
			maxWakes,
			intervalSeconds,
			label: entry.label,
			status: entry.status ?? 'stale',
			sinceIndex: Math.max(0, entry.sinceIndex ?? 0),
			wakesSent: Math.max(0, Math.min(maxWakes, entry.wakesSent ?? 0)),
			serverWatchId: entry.serverWatchId,
			serverCreatedAt: entry.serverCreatedAt,
			serverGeneration: entry.serverGeneration,
			remoteDeleteGenerationConfirmed: entry.remoteDeleteGenerationConfirmed ?? false,
			lastError: entry.lastError,
			sourceSessionId: entry.sourceSessionId,
			remoteCleanupPending: entry.remoteCleanupPending ?? false,
			remoteDeleteAcknowledged: entry.remoteDeleteAcknowledged ?? false,
			remoteDeleteAllowed: entry.remoteDeleteAllowed ?? false,
			nextPollAt: this.now(),
			stateNoticeAttempts: Math.max(0, entry.stateNoticeAttempts ?? 0),
			stateNoticeKinds: new Set(entry.stateNoticeKinds ?? []),
		};
		this.install(reg);
		return reg;
	}

	async reconcile(entries: PersistedRegistrationEntry[], expectedOwnerSessionId?: string): Promise<{ attached: number; stale: number }> {
		let attached = 0;
		let stale = 0;
		const restoreNoticeCandidates: Registration[] = [];
		const latestBySession = new Map<string, PersistedRegistrationEntry>();
		for (const entry of entries ?? []) {
			if (entry?.sessionId && entry?.message) latestBySession.set(entry.sessionId, entry);
		}
		for (const entry of latestBySession.values()) {
			if (entry.status && entry.status !== 'watching') {
				const sameCurrentOwner = !expectedOwnerSessionId || !entry.sourceSessionId || entry.sourceSessionId === expectedOwnerSessionId;
				const retryableOwnedCancel = entry.status === 'cancelled' && entry.remoteCleanupPending === true && sameCurrentOwner
					&& (entry.remoteDeleteAllowed === true || entry.remoteDeleteAllowed === undefined);
				const terminal = this.restoreTerminal({
					...entry,
					remoteDeleteAllowed: retryableOwnedCancel,
				});
				if (terminal.status === 'stale' && terminal.lastError && !terminal.stateNoticeKinds.has('terminal') && terminal.stateNoticeAttempts < MAX_STATE_NOTICE_ATTEMPTS) {
					restoreNoticeCandidates.push(terminal);
				}
				continue;
			}
			try {
				await this.attach({ ...entry, expectedOwnerSessionId });
				attached += 1;
			} catch (error) {
				stale += 1;
				const terminal = this.restoreTerminal({
					...entry,
					status: 'stale',
					lastError: error instanceof Error ? error.message : String(error),
					remoteDeleteAllowed: false,
				});
				if (!terminal.stateNoticeKinds.has('terminal') && terminal.stateNoticeAttempts < MAX_STATE_NOTICE_ATTEMPTS) {
					restoreNoticeCandidates.push(terminal);
				}
			}
		}
		if (restoreNoticeCandidates.length > 0) {
			const primary = restoreNoticeCandidates[0];
			const others = restoreNoticeCandidates.length - 1;
			const reason = `${primary.lastError ?? 'watch restore failed'}${others > 0 ? `; ${others} other restored watch${others === 1 ? '' : 'es'} also became stale` : ''}`;
			this.notifyState(primary, 'terminal', reason);
			if (primary.stateNoticeKinds.has('terminal')) {
				// One startup notice covers this reconcile batch; persist coverage on
				// every failed record so a reload cannot fan it back out into a storm.
				for (const covered of restoreNoticeCandidates) covered.stateNoticeKinds.add('terminal');
			}
		}
		return { attached, stale };
	}
}
