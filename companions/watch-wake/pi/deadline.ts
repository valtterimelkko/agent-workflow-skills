import { randomUUID } from "node:crypto";

export const DEADLINE_RECORD_VERSION = 1;
export const DEFAULT_MAX_DELAY_MS = 24 * 60 * 60 * 1000;
export const MAX_MESSAGE_LENGTH = 2000;

const MAX_LABEL_LENGTH = 128;
const MAX_SESSION_ID_LENGTH = 256;
const MAX_ID_LENGTH = 160;
const MAX_ERROR_LENGTH = 512;
const MAX_RETRY_DELAY_MS = 60_000;
const MAX_RETRY_COUNT = 5;
const DEFAULT_RETRY_DELAYS_MS = [1_000, 5_000, 30_000] as const;

export type DeadlineStatus = "armed" | "pending" | "delivered" | "failed" | "cancelled";

export interface DeadlineRecord {
  version: typeof DEADLINE_RECORD_VERSION;
  id: string;
  ownerSessionId: string;
  message: string;
  waitLabel?: string;
  armedAt: number;
  deadlineAt: number;
  status: DeadlineStatus;
  expiryAttempted: boolean;
  deliveryAttempts: number;
  maxDeliveryAttempts: number;
  lastAttemptAt?: number;
  nextAttemptAt?: number;
  deliveryAcceptedAt?: number;
  lastDeliveryError?: string;
}

export interface DeadlineView extends DeadlineRecord {
  /** True only when the exact current record was synchronously persisted. */
  durable: boolean;
  /** A transient persistence failure for the current in-memory record. */
  persistenceError?: string;
}

export interface DeadlineManagerOptions {
  /** The current host/session identity; restore rejects a different session. */
  ownerSessionId: string;
  /** True means accepted by the local channel, not processed by the recipient. */
  sendWake: (text: string) => boolean;
  /** Pi appendEntry-style synchronous persistence. Thenables are unsupported. */
  persist?: (record: DeadlineRecord) => void;
  now?: () => number;
  schedule?: (callback: () => void, delayMs: number) => unknown;
  cancelSchedule?: (handle: unknown) => void;
  /** Lowerable finite cap; the implementation never permits a value above 24h. */
  maxDelayMs?: number;
  /** Positive finite delays after failed delivery attempts. */
  retryDelaysMs?: readonly number[];
}

export interface ArmDeadlineInput {
  /** Exactly one of delayMs and deadlineAt must be supplied. */
  delayMs?: number;
  deadlineAt?: number;
  message: string;
  waitLabel?: string;
}

export interface DeadlineCancelResult {
  cancelled: boolean;
  reason: "cancelled" | "none" | "already-delivered" | "already-failed" | "already-cancelled";
  deadline: DeadlineView | null;
}

const defaultNow = () => Date.now();
const defaultSchedule = (callback: () => void, delayMs: number) => setTimeout(callback, delayMs);
const defaultCancelSchedule = (handle: unknown) => clearTimeout(handle as never);

class UnsupportedPersistenceError extends Error {
  public constructor() {
    super("asynchronous persistence is unsupported; use synchronous appendEntry");
    this.name = "UnsupportedPersistenceError";
  }
}

function isObject(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function errorText(error: unknown): string {
  if (error instanceof Error && error.message) return error.message;
  return String(error);
}

function boundedError(error: unknown): string {
  const text = errorText(error);
  if (text.length <= MAX_ERROR_LENGTH) return text;
  return `${text.slice(0, MAX_ERROR_LENGTH - 3)}...`;
}

function requireString(value: unknown, name: string, maxLength: number): string {
  if (typeof value !== "string") throw new Error(`${name} must be a string`);
  const trimmed = value.trim();
  if (!trimmed) throw new Error(`${name} must not be empty`);
  if (trimmed.length > maxLength) throw new Error(`${name} exceeds maximum length ${maxLength}`);
  return trimmed;
}

function requireSafeInteger(value: unknown, name: string): number {
  if (!Number.isSafeInteger(value)) throw new Error(`${name} must be a finite safe integer`);
  return value as number;
}

function requireTimestamp(value: unknown, name: string): number {
  const result = requireSafeInteger(value, name);
  if (result < 0) throw new Error(`${name} must not be negative`);
  return result;
}

function optionalTimestamp(value: unknown, name: string): number | undefined {
  if (value === undefined) return undefined;
  return requireTimestamp(value, name);
}

function cloneRecord(record: DeadlineRecord): DeadlineRecord {
  return JSON.parse(JSON.stringify(record)) as DeadlineRecord;
}

function fingerprint(record: DeadlineRecord): string {
  return JSON.stringify(record);
}

function isThenable(value: unknown): boolean {
  if ((typeof value !== "object" || value === null) && typeof value !== "function") return false;
  return typeof (value as { then?: unknown }).then === "function";
}

function validateStoredRecord(value: unknown, ownerSessionId: string, now: number, maxDelayMs: number): DeadlineRecord {
  if (!isObject(value)) throw new Error("stored deadline must be an object");
  if (value.version !== DEADLINE_RECORD_VERSION) throw new Error("stored deadline version is invalid");

  const storedOwner = requireString(value.ownerSessionId, "stored ownerSessionId", MAX_SESSION_ID_LENGTH);
  if (storedOwner !== ownerSessionId) {
    throw new Error(`stored deadline session identity mismatch: expected ${ownerSessionId}, got ${storedOwner}`);
  }

  const id = requireString(value.id, "stored id", MAX_ID_LENGTH);
  const message = requireString(value.message, "stored message", MAX_MESSAGE_LENGTH);
  let waitLabel: string | undefined;
  if (value.waitLabel !== undefined) waitLabel = requireString(value.waitLabel, "stored waitLabel", MAX_LABEL_LENGTH);

  const armedAt = requireTimestamp(value.armedAt, "stored armedAt");
  const deadlineAt = requireTimestamp(value.deadlineAt, "stored deadlineAt");
  if (deadlineAt < armedAt) throw new Error("stored deadlineAt precedes armedAt");
  if (deadlineAt - armedAt > maxDelayMs) throw new Error("stored original deadline interval exceeds maximum delay");
  if (deadlineAt > now && deadlineAt - now > maxDelayMs) {
    throw new Error("stored future deadline exceeds scheduling horizon");
  }

  const statusValues: DeadlineStatus[] = ["armed", "pending", "delivered", "failed", "cancelled"];
  if (typeof value.status !== "string" || !statusValues.includes(value.status as DeadlineStatus)) {
    throw new Error("stored deadline status is invalid");
  }
  const status = value.status as DeadlineStatus;
  if (typeof value.expiryAttempted !== "boolean") throw new Error("stored expiryAttempted is invalid");

  const deliveryAttempts = requireSafeInteger(value.deliveryAttempts, "stored deliveryAttempts");
  const maxDeliveryAttempts = requireSafeInteger(value.maxDeliveryAttempts, "stored maxDeliveryAttempts");
  if (maxDeliveryAttempts < 1 || maxDeliveryAttempts > MAX_RETRY_COUNT + 1) {
    throw new Error("stored maxDeliveryAttempts is out of bounds");
  }
  if (deliveryAttempts < 0 || deliveryAttempts > maxDeliveryAttempts) {
    throw new Error("stored deliveryAttempts is out of bounds");
  }

  const lastAttemptAt = optionalTimestamp(value.lastAttemptAt, "stored lastAttemptAt");
  const nextAttemptAt = optionalTimestamp(value.nextAttemptAt, "stored nextAttemptAt");
  const deliveryAcceptedAt = optionalTimestamp(value.deliveryAcceptedAt, "stored deliveryAcceptedAt");
  let lastDeliveryError: string | undefined;
  if (value.lastDeliveryError !== undefined) {
    if (typeof value.lastDeliveryError !== "string" || value.lastDeliveryError.length > MAX_ERROR_LENGTH) {
      throw new Error("stored lastDeliveryError is invalid");
    }
    lastDeliveryError = value.lastDeliveryError;
  }
  const retryHorizonMs = Math.max(maxDelayMs, MAX_RETRY_DELAY_MS);
  if (nextAttemptAt !== undefined && nextAttemptAt > now && nextAttemptAt - now > retryHorizonMs) {
    throw new Error("stored future retry exceeds scheduling horizon");
  }

  if (status === "armed" && (value.expiryAttempted !== false || deliveryAttempts !== 0 || nextAttemptAt !== undefined || deliveryAcceptedAt !== undefined)) {
    throw new Error("stored armed deadline has inconsistent delivery state");
  }
  if (status === "pending" && (value.expiryAttempted !== true || deliveryAcceptedAt !== undefined)) {
    throw new Error("stored pending deadline has inconsistent delivery state");
  }
  if (status === "delivered" && (value.expiryAttempted !== true || deliveryAttempts < 1 || deliveryAcceptedAt === undefined || nextAttemptAt !== undefined)) {
    throw new Error("stored delivered deadline has inconsistent delivery state");
  }
  if (status === "failed" && (value.expiryAttempted !== true || deliveryAttempts !== maxDeliveryAttempts || deliveryAcceptedAt !== undefined || nextAttemptAt !== undefined)) {
    throw new Error("stored failed deadline has inconsistent delivery state");
  }
  if (status === "cancelled" && (deliveryAcceptedAt !== undefined || nextAttemptAt !== undefined)) {
    throw new Error("stored cancelled deadline has inconsistent delivery state");
  }

  const result: DeadlineRecord = {
    version: DEADLINE_RECORD_VERSION,
    id,
    ownerSessionId: storedOwner,
    message,
    armedAt,
    deadlineAt,
    status,
    expiryAttempted: value.expiryAttempted,
    deliveryAttempts,
    maxDeliveryAttempts,
  };
  if (waitLabel !== undefined) result.waitLabel = waitLabel;
  if (lastAttemptAt !== undefined) result.lastAttemptAt = lastAttemptAt;
  if (nextAttemptAt !== undefined) result.nextAttemptAt = nextAttemptAt;
  if (deliveryAcceptedAt !== undefined) result.deliveryAcceptedAt = deliveryAcceptedAt;
  if (lastDeliveryError !== undefined) result.lastDeliveryError = lastDeliveryError;
  return result;
}

/** One active, host-owned deadline with synchronous Pi-style persistence. */
export class DeadlineManager {
  private readonly ownerSessionId: string;
  private readonly sendWake: (text: string) => boolean;
  private readonly persist?: (record: DeadlineRecord) => void;
  private readonly now: () => number;
  private readonly schedule: (callback: () => void, delayMs: number) => unknown;
  private readonly cancelSchedule: (handle: unknown) => void;
  private readonly maxDelayMs: number;
  private readonly retryDelaysMs: readonly number[];

  private state: DeadlineRecord | null = null;
  private timer: unknown = undefined;
  private timerActive = false;
  private epoch = 0;
  private disposed = false;
  private deliveryEpoch: number | null = null;
  private persistedFingerprint: string | undefined;
  private persistenceError: string | undefined;

  public constructor(options: DeadlineManagerOptions) {
    if (!isObject(options)) throw new Error("deadline manager options are required");
    this.ownerSessionId = requireString(options.ownerSessionId, "ownerSessionId", MAX_SESSION_ID_LENGTH);
    if (typeof options.sendWake !== "function") throw new Error("sendWake must be a function");
    this.sendWake = options.sendWake;
    if (options.persist !== undefined && typeof options.persist !== "function") throw new Error("persist must be a function");
    this.persist = options.persist;
    this.now = options.now ?? defaultNow;
    this.schedule = options.schedule ?? defaultSchedule;
    this.cancelSchedule = options.cancelSchedule ?? defaultCancelSchedule;
    if (typeof this.now !== "function" || typeof this.schedule !== "function" || typeof this.cancelSchedule !== "function") {
      throw new Error("now, schedule and cancelSchedule must be functions");
    }

    const maxDelayMs = options.maxDelayMs ?? DEFAULT_MAX_DELAY_MS;
    if (!Number.isSafeInteger(maxDelayMs) || maxDelayMs < 0 || maxDelayMs > DEFAULT_MAX_DELAY_MS) {
      throw new Error(`maxDelayMs must be a finite safe integer between 0 and ${DEFAULT_MAX_DELAY_MS}`);
    }
    this.maxDelayMs = maxDelayMs;

    const retryDelays = options.retryDelaysMs === undefined ? [...DEFAULT_RETRY_DELAYS_MS] : [...options.retryDelaysMs];
    if (retryDelays.length > MAX_RETRY_COUNT) throw new Error("too many retry delays");
    for (const delay of retryDelays) {
      if (!Number.isSafeInteger(delay) || delay < 1 || delay > MAX_RETRY_DELAY_MS) {
        throw new Error(`retry delays must be finite safe integers between 1 and ${MAX_RETRY_DELAY_MS}`);
      }
    }
    this.retryDelaysMs = retryDelays;
  }

  public async arm(input: ArmDeadlineInput): Promise<DeadlineView> {
    this.ensureOpen();
    if (!isObject(input)) throw new Error("deadline input is required");
    const message = requireString(input.message, "message", MAX_MESSAGE_LENGTH);
    const hasDelay = input.delayMs !== undefined;
    const hasDeadline = input.deadlineAt !== undefined;
    if (hasDelay === hasDeadline) throw new Error("supply exactly one of delayMs or deadlineAt");

    const now = this.readNow();
    let deadlineAt: number;
    if (hasDelay) {
      const delayMs = requireSafeInteger(input.delayMs, "delayMs");
      if (delayMs < 0 || delayMs > this.maxDelayMs) throw new Error(`delayMs must be between 0 and ${this.maxDelayMs}`);
      deadlineAt = now + delayMs;
      if (!Number.isSafeInteger(deadlineAt)) throw new Error("deadlineAt exceeds safe bounds");
    } else {
      deadlineAt = requireTimestamp(input.deadlineAt, "deadlineAt");
      if (deadlineAt < now) throw new Error("deadlineAt cannot already be overdue when armed");
      if (deadlineAt - now > this.maxDelayMs) throw new Error(`deadlineAt exceeds maximum delay ${this.maxDelayMs}`);
    }

    let waitLabel: string | undefined;
    if (input.waitLabel !== undefined && input.waitLabel.trim() !== "") {
      waitLabel = requireString(input.waitLabel, "waitLabel", MAX_LABEL_LENGTH);
    }

    const candidate: DeadlineRecord = {
      version: DEADLINE_RECORD_VERSION,
      id: `deadline-${randomUUID()}`,
      ownerSessionId: this.ownerSessionId,
      message,
      armedAt: now,
      deadlineAt,
      status: "armed",
      expiryAttempted: false,
      deliveryAttempts: 0,
      maxDeliveryAttempts: this.retryDelaysMs.length + 1,
    };
    if (waitLabel !== undefined) candidate.waitLabel = waitLabel;

    const token = this.invalidateRuntime();
    this.setState(candidate);
    try {
      this.persistIfChanged(candidate, true);
    } catch (error) {
      if (error instanceof UnsupportedPersistenceError) {
        this.state = null;
        this.invalidateRuntime();
        throw error;
      }
      throw error;
    }
    if (this.isCurrent(token) && this.state?.id === candidate.id) this.scheduleAt(token, candidate.deadlineAt);
    return this.inspect() as DeadlineView;
  }

  public inspect(): DeadlineView | null {
    if (this.state === null) return null;
    const result: DeadlineView = {
      ...cloneRecord(this.state),
      durable: this.persistedFingerprint === fingerprint(this.state) && this.persistenceError === undefined,
    };
    if (this.persistenceError !== undefined) result.persistenceError = this.persistenceError;
    return result;
  }

  public list(): DeadlineView[] {
    const current = this.inspect();
    return current === null ? [] : [current];
  }

  public async cancel(): Promise<DeadlineCancelResult> {
    this.ensureOpen();
    const current = this.state;
    if (current === null) return { cancelled: false, reason: "none", deadline: null };
    if (current.status === "delivered") return { cancelled: false, reason: "already-delivered", deadline: this.inspect() };
    if (current.status === "failed") return { cancelled: false, reason: "already-failed", deadline: this.inspect() };
    if (current.status === "cancelled") return { cancelled: false, reason: "already-cancelled", deadline: this.inspect() };

    this.invalidateRuntime();
    const cancelled = cloneRecord(current);
    cancelled.status = "cancelled";
    delete cancelled.nextAttemptAt;
    delete cancelled.lastDeliveryError;
    this.setState(cancelled);
    this.persistIfChanged(cancelled);
    return { cancelled: true, reason: "cancelled", deadline: this.inspect() };
  }

  public async restore(stored: unknown): Promise<DeadlineView | null> {
    this.ensureOpen();
    if (stored === null || stored === undefined) {
      this.invalidateRuntime();
      this.state = null;
      this.persistedFingerprint = undefined;
      this.persistenceError = undefined;
      return null;
    }

    // Complete validation happens before invalidating a currently valid timer.
    const now = this.readNow();
    const record = validateStoredRecord(stored, this.ownerSessionId, now, this.maxDelayMs);
    const storedFingerprint = fingerprint(record);
    if (this.state !== null && this.state.id === record.id) return this.inspect();

    const token = this.invalidateRuntime();
    this.state = record;
    this.persistedFingerprint = storedFingerprint;
    this.persistenceError = undefined;

    if (record.status === "armed") {
      if (record.deadlineAt <= now) {
        this.setState({ ...record, status: "pending", expiryAttempted: true });
        delete this.state.nextAttemptAt;
        this.persistIfChanged(this.state);
        await this.handleTimer(token);
      } else {
        this.scheduleAt(token, record.deadlineAt);
      }
    } else if (record.status === "pending") {
      if (record.nextAttemptAt !== undefined && record.nextAttemptAt > now) {
        this.scheduleAt(token, record.nextAttemptAt, Math.max(this.maxDelayMs, MAX_RETRY_DELAY_MS));
      } else await this.handleTimer(token);
    }
    return this.inspect();
  }

  /** Runtime shutdown, intentionally distinct from user cancellation. */
  public dispose(): void {
    if (this.disposed) return;
    this.disposed = true;
    this.invalidateRuntime();
  }

  private ensureOpen(): void {
    if (this.disposed) throw new Error("deadline manager is disposed");
  }

  private readNow(): number {
    const value = this.now();
    if (!Number.isSafeInteger(value) || value < 0) throw new Error("clock must return a finite safe timestamp");
    return value;
  }

  private setState(next: DeadlineRecord): void {
    this.state = next;
    if (this.persistedFingerprint !== fingerprint(next)) this.persistenceError = undefined;
  }

  private invalidateRuntime(): number {
    this.epoch += 1;
    this.clearTimer();
    return this.epoch;
  }

  private clearTimer(): void {
    if (!this.timerActive) return;
    try {
      this.cancelSchedule(this.timer);
    } finally {
      this.timer = undefined;
      this.timerActive = false;
    }
  }

  private isCurrent(token: number): boolean {
    return !this.disposed && token === this.epoch;
  }

  private scheduleAt(token: number, at: number, horizonMs = this.maxDelayMs): void {
    if (!this.isCurrent(token) || this.state === null) return;
    const delayMs = Math.max(0, at - this.readNow());
    if (!Number.isSafeInteger(delayMs) || delayMs > horizonMs) throw new Error("scheduled deadline exceeds finite delay cap");
    this.clearTimer();
    this.timer = this.schedule(() => {
      // A queued callback from an old epoch must not hide a replacement timer.
      if (!this.isCurrent(token)) return;
      this.timerActive = false;
      void this.handleTimer(token).catch((error) => {
        if (this.isCurrent(token) && this.state !== null) {
          this.state.lastDeliveryError = boundedError(error);
          this.persistenceError = boundedError(error);
        }
      });
    }, delayMs);
    this.timerActive = true;
  }

  private async handleTimer(token: number): Promise<void> {
    if (!this.isCurrent(token) || this.state === null) return;
    if (this.deliveryEpoch === token) return;
    this.deliveryEpoch = token;
    try {
      if (this.state.status === "armed") {
        this.setState({ ...cloneRecord(this.state), status: "pending", expiryAttempted: true });
        delete this.state.nextAttemptAt;
        this.persistIfChanged(this.state);
      }
      if (!this.isCurrent(token) || this.state === null || this.state.status !== "pending") return;
      if (this.state.nextAttemptAt !== undefined && this.state.nextAttemptAt > this.readNow()) {
        this.scheduleAt(token, this.state.nextAttemptAt, Math.max(this.maxDelayMs, MAX_RETRY_DELAY_MS));
        return;
      }
      await this.attemptDelivery(token);
    } finally {
      if (this.deliveryEpoch === token) this.deliveryEpoch = null;
    }
  }

  private async attemptDelivery(token: number): Promise<void> {
    if (!this.isCurrent(token) || this.state === null || this.state.status !== "pending") return;
    const before = this.state;
    const attempt = Math.min(before.deliveryAttempts + 1, before.maxDeliveryAttempts);
    this.setState({ ...cloneRecord(before), deliveryAttempts: attempt, lastAttemptAt: this.readNow() });
    delete this.state.nextAttemptAt;
    this.persistIfChanged(this.state);
    if (!this.isCurrent(token) || this.state === null || this.state.status !== "pending") return;

    let accepted = false;
    let failure: string | undefined;
    try {
      accepted = this.sendWake(this.formatWake(this.state)) === true;
      if (!accepted) failure = "wake channel rejected delivery";
    } catch (error) {
      failure = boundedError(error);
    }
    if (!this.isCurrent(token) || this.state === null || this.state.status !== "pending") return;

    if (accepted) {
      this.setState({ ...cloneRecord(this.state), status: "delivered", deliveryAcceptedAt: this.readNow() });
      delete this.state.nextAttemptAt;
      delete this.state.lastDeliveryError;
      this.persistIfChanged(this.state);
      return;
    }

    const message = boundedError(failure ?? "wake channel rejected delivery");
    if (attempt < this.state.maxDeliveryAttempts) {
      const retryDelay = this.retryDelaysMs[attempt - 1] ?? this.retryDelaysMs.at(-1) ?? 1;
      const nextAttemptAt = this.readNow() + retryDelay;
      if (!Number.isSafeInteger(nextAttemptAt)) throw new Error("retry deadline exceeds safe bounds");
      this.setState({ ...cloneRecord(this.state), nextAttemptAt, lastDeliveryError: message });
      this.persistIfChanged(this.state);
      if (this.isCurrent(token) && this.state?.status === "pending") {
        this.scheduleAt(token, nextAttemptAt, Math.max(this.maxDelayMs, MAX_RETRY_DELAY_MS));
      }
      return;
    }

    this.setState({ ...cloneRecord(this.state), status: "failed", lastDeliveryError: message });
    delete this.state.nextAttemptAt;
    this.persistIfChanged(this.state);
  }

  private formatWake(record: DeadlineRecord): string {
    const wait = record.waitLabel === undefined ? "" : ` wait=${record.waitLabel}`;
    return `[deadline ${record.id}${wait}] ${record.message} — deadline expired; expiry is NOT completion.`;
  }

  private persistIfChanged(record: DeadlineRecord, rejectUnsupportedAsync = false): void {
    const snapshot = cloneRecord(record);
    const recordFingerprint = fingerprint(snapshot);
    if (recordFingerprint === this.persistedFingerprint && this.persistenceError === undefined) return;
    if (this.persist === undefined) {
      if (this.state !== null && fingerprint(this.state) === recordFingerprint) this.persistenceError = "no persistence adapter configured";
      return;
    }

    try {
      const result = this.persist(cloneRecord(snapshot));
      if (isThenable(result)) {
        const error = new UnsupportedPersistenceError();
        if (rejectUnsupportedAsync) throw error;
        if (this.state !== null && fingerprint(this.state) === recordFingerprint) this.persistenceError = error.message;
        return;
      }
      this.persistedFingerprint = recordFingerprint;
      if (this.state !== null && fingerprint(this.state) === recordFingerprint) this.persistenceError = undefined;
    } catch (error) {
      if (rejectUnsupportedAsync && error instanceof UnsupportedPersistenceError) throw error;
      if (this.state !== null && fingerprint(this.state) === recordFingerprint) this.persistenceError = boundedError(error);
    }
  }
}
