PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS accounts (
    id TEXT PRIMARY KEY,
    email TEXT NOT NULL UNIQUE COLLATE NOCASE,
    password_hash TEXT NOT NULL,
    created_at INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS sessions (
    id TEXT PRIMARY KEY,
    account_id TEXT NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
    token_hash TEXT NOT NULL UNIQUE,
    expires_at INTEGER NOT NULL,
    created_at INTEGER NOT NULL,
    revoked_at INTEGER
);

CREATE TABLE IF NOT EXISTS pairing_codes (
    id TEXT PRIMARY KEY,
    account_id TEXT NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
    code_hash TEXT NOT NULL UNIQUE,
    expires_at INTEGER NOT NULL,
    created_at INTEGER NOT NULL,
    consumed_at INTEGER
);

CREATE TABLE IF NOT EXISTS devices (
    id TEXT PRIMARY KEY,
    account_id TEXT NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    fingerprint TEXT NOT NULL,
    credential_hash TEXT NOT NULL UNIQUE,
    created_at INTEGER NOT NULL,
    last_seen_at INTEGER,
    status TEXT NOT NULL DEFAULT 'offline',
    capabilities_json TEXT NOT NULL DEFAULT '{}',
    UNIQUE(account_id, fingerprint)
);

CREATE TABLE IF NOT EXISTS jobs (
    id TEXT PRIMARY KEY,
    account_id TEXT NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
    device_id TEXT NOT NULL REFERENCES devices(id) ON DELETE RESTRICT,
    action TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    state TEXT NOT NULL,
    idempotency_key TEXT NOT NULL,
    created_at INTEGER NOT NULL,
    updated_at INTEGER NOT NULL,
    lease_id TEXT,
    lease_expires_at INTEGER,
    attempt INTEGER NOT NULL DEFAULT 0,
    progress_json TEXT NOT NULL DEFAULT '{}',
    result_json TEXT,
    error_json TEXT,
    UNIQUE(account_id, idempotency_key)
);

CREATE INDEX IF NOT EXISTS idx_jobs_device_state ON jobs(device_id, state, created_at);
CREATE INDEX IF NOT EXISTS idx_sessions_token ON sessions(token_hash, expires_at);
