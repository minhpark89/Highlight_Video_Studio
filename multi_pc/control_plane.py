import json
import sqlite3
import time
import uuid
from functools import wraps
from pathlib import Path

from flask import Flask, g, jsonify, request

from .security import (
    canonical_json,
    find_sensitive_path,
    hash_password,
    new_token,
    redact,
    token_digest,
    verify_password,
)


API_VERSION = "2026-09-28.phase1"
ALLOWED_ACTIONS = {
    "highlight_pipeline": {"source_url", "title", "options", "client_job_ref"},
    "publish_zernio": {"local_output_ref", "destination_ref", "caption", "schedule_at"},
}
JOB_STATES = {"queued", "leased", "running", "succeeded", "failed", "cancelled"}


def _now() -> int:
    return int(time.time())


def _id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex}"


def create_app(config: dict | None = None) -> Flask:
    app = Flask(__name__)
    app.config.update(
        DATABASE=str(Path(app.instance_path) / "highlight_phase1.sqlite3"),
        SESSION_TTL_SECONDS=12 * 60 * 60,
        PAIRING_TTL_SECONDS=5 * 60,
        LEASE_TTL_SECONDS=60,
        ALLOW_REGISTRATION=False,
        TESTING=False,
    )
    if config:
        app.config.update(config)

    Path(app.config["DATABASE"]).parent.mkdir(parents=True, exist_ok=True)

    def db() -> sqlite3.Connection:
        if "db" not in g:
            connection = sqlite3.connect(app.config["DATABASE"], timeout=10, isolation_level=None)
            connection.row_factory = sqlite3.Row
            connection.execute("PRAGMA foreign_keys = ON")
            g.db = connection
        return g.db

    app.get_db = db  # type: ignore[attr-defined]

    @app.teardown_appcontext
    def close_db(_error=None):
        connection = g.pop("db", None)
        if connection is not None:
            connection.close()

    with app.app_context():
        schema = Path(__file__).with_name("schema.sql").read_text(encoding="utf-8")
        db().executescript(schema)

    def bearer() -> str:
        header = request.headers.get("Authorization", "")
        if not header.startswith("Bearer "):
            return ""
        return header[7:].strip()

    def account_required(handler):
        @wraps(handler)
        def wrapped(*args, **kwargs):
            raw = bearer()
            row = db().execute(
                """SELECT accounts.* FROM sessions
                   JOIN accounts ON accounts.id = sessions.account_id
                   WHERE sessions.token_hash=? AND sessions.revoked_at IS NULL AND sessions.expires_at>?""",
                (token_digest(raw), _now()),
            ).fetchone() if raw else None
            if not row:
                return jsonify(error="account authentication required"), 401
            g.account = row
            g.session_token = raw
            return handler(*args, **kwargs)

        return wrapped

    def device_required(handler):
        @wraps(handler)
        def wrapped(*args, **kwargs):
            raw = bearer()
            row = db().execute(
                "SELECT * FROM devices WHERE credential_hash=?",
                (token_digest(raw),),
            ).fetchone() if raw else None
            if not row:
                return jsonify(error="device authentication required"), 401
            g.device = row
            return handler(*args, **kwargs)

        return wrapped

    def public_job(row):
        return {
            "id": row["id"],
            "device_id": row["device_id"],
            "action": row["action"],
            "payload": json.loads(row["payload_json"]),
            "state": row["state"],
            "attempt": row["attempt"],
            "progress": json.loads(row["progress_json"] or "{}"),
            "result": json.loads(row["result_json"]) if row["result_json"] else None,
            "error": json.loads(row["error_json"]) if row["error_json"] else None,
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }

    @app.get("/health")
    def health():
        db().execute("SELECT 1").fetchone()
        return jsonify(ok=True, service="highlight-control-plane", api_version=API_VERSION)

    @app.post("/v1/auth/register")
    def register():
        if not app.config["ALLOW_REGISTRATION"]:
            return jsonify(error="registration is disabled"), 403
        body = request.get_json(silent=True) or {}
        email = str(body.get("email", "")).strip().lower()
        password = str(body.get("password", ""))
        if "@" not in email or len(password) < 10:
            return jsonify(error="valid email and password of at least 10 characters required"), 400
        try:
            account_id = _id("acct")
            db().execute(
                "INSERT INTO accounts(id,email,password_hash,created_at) VALUES(?,?,?,?)",
                (account_id, email, hash_password(password), _now()),
            )
        except sqlite3.IntegrityError:
            return jsonify(error="account already exists"), 409
        return jsonify(id=account_id, email=email), 201

    @app.post("/v1/auth/login")
    def login():
        body = request.get_json(silent=True) or {}
        email = str(body.get("email", "")).strip().lower()
        password = str(body.get("password", ""))
        account = db().execute("SELECT * FROM accounts WHERE email=?", (email,)).fetchone()
        if not account or not verify_password(password, account["password_hash"]):
            return jsonify(error="invalid credentials"), 401
        raw_token = new_token()
        expires_at = _now() + int(app.config["SESSION_TTL_SECONDS"])
        db().execute(
            "INSERT INTO sessions(id,account_id,token_hash,expires_at,created_at) VALUES(?,?,?,?,?)",
            (_id("sess"), account["id"], token_digest(raw_token), expires_at, _now()),
        )
        response = jsonify(token=raw_token, expires_at=expires_at, account={"id": account["id"], "email": email})
        response.headers["Cache-Control"] = "no-store"
        return response

    @app.post("/v1/auth/logout")
    @account_required
    def logout():
        db().execute("UPDATE sessions SET revoked_at=? WHERE token_hash=?", (_now(), token_digest(g.session_token)))
        return "", 204

    @app.post("/v1/devices/pairing-codes")
    @account_required
    def create_pairing_code():
        raw_code = "-".join([new_token(4)[:5].upper(), new_token(4)[:5].upper()])
        expires_at = _now() + int(app.config["PAIRING_TTL_SECONDS"])
        db().execute(
            "INSERT INTO pairing_codes(id,account_id,code_hash,expires_at,created_at) VALUES(?,?,?,?,?)",
            (_id("pair"), g.account["id"], token_digest(raw_code), expires_at, _now()),
        )
        response = jsonify(code=raw_code, expires_at=expires_at)
        response.headers["Cache-Control"] = "no-store"
        return response, 201

    @app.post("/v1/devices/pair")
    def pair_device():
        body = request.get_json(silent=True) or {}
        code = str(body.get("code", "")).strip().upper()
        name = str(body.get("name", "")).strip()[:120]
        fingerprint = str(body.get("fingerprint", "")).strip()[:200]
        if not code or not name or not fingerprint:
            return jsonify(error="code, name, and fingerprint required"), 400
        connection = db()
        connection.execute("BEGIN IMMEDIATE")
        try:
            pairing = connection.execute(
                "SELECT * FROM pairing_codes WHERE code_hash=?", (token_digest(code),)
            ).fetchone()
            if not pairing or pairing["consumed_at"] is not None or pairing["expires_at"] <= _now():
                connection.execute("ROLLBACK")
                return jsonify(error="pairing code is invalid or expired"), 410
            if connection.execute(
                "SELECT 1 FROM devices WHERE account_id=? AND fingerprint=?",
                (pairing["account_id"], fingerprint),
            ).fetchone():
                connection.execute("ROLLBACK")
                return jsonify(error="device is already paired"), 409
            credential = new_token(40)
            device_id = _id("dev")
            connection.execute(
                """INSERT INTO devices(id,account_id,name,fingerprint,credential_hash,created_at)
                   VALUES(?,?,?,?,?,?)""",
                (device_id, pairing["account_id"], name, fingerprint, token_digest(credential), _now()),
            )
            connection.execute("UPDATE pairing_codes SET consumed_at=? WHERE id=?", (_now(), pairing["id"]))
            connection.execute("COMMIT")
        except Exception:
            connection.execute("ROLLBACK")
            raise
        response = jsonify(device_id=device_id, credential=credential)
        response.headers["Cache-Control"] = "no-store"
        return response, 201

    @app.get("/v1/devices")
    @account_required
    def list_devices():
        rows = db().execute(
            "SELECT id,name,fingerprint,status,last_seen_at,created_at FROM devices WHERE account_id=? ORDER BY created_at",
            (g.account["id"],),
        ).fetchall()
        return jsonify(devices=[dict(row) for row in rows])

    @app.post("/v1/device/heartbeat")
    @device_required
    def heartbeat_device():
        body = request.get_json(silent=True) or {}
        capabilities = redact(body.get("capabilities", {}))
        if find_sensitive_path(capabilities):
            return jsonify(error="sensitive capability data rejected"), 400
        db().execute(
            "UPDATE devices SET last_seen_at=?,status='online',capabilities_json=? WHERE id=?",
            (_now(), canonical_json(capabilities), g.device["id"]),
        )
        return jsonify(ok=True, server_time=_now())

    @app.post("/v1/jobs")
    @account_required
    def create_job():
        body = request.get_json(silent=True) or {}
        device_id = str(body.get("device_id", ""))
        action = str(body.get("action", ""))
        payload = body.get("payload", {})
        idempotency_key = request.headers.get("Idempotency-Key", "").strip()
        if not idempotency_key or len(idempotency_key) > 200:
            return jsonify(error="Idempotency-Key header required"), 400
        if action not in ALLOWED_ACTIONS or not isinstance(payload, dict):
            return jsonify(error="unsupported action or invalid payload"), 400
        unknown = set(payload) - ALLOWED_ACTIONS[action]
        if unknown:
            return jsonify(error="payload contains unsupported fields", fields=sorted(unknown)), 400
        sensitive_path = find_sensitive_path(payload)
        if sensitive_path:
            return jsonify(error="sensitive data is not accepted by the control plane", field=sensitive_path), 400
        device = db().execute(
            "SELECT id FROM devices WHERE id=? AND account_id=?", (device_id, g.account["id"])
        ).fetchone()
        if not device:
            return jsonify(error="device not found"), 404
        existing = db().execute(
            "SELECT * FROM jobs WHERE account_id=? AND idempotency_key=?",
            (g.account["id"], idempotency_key),
        ).fetchone()
        if existing:
            return jsonify(job=public_job(existing), idempotent_replay=True), 200
        timestamp = _now()
        job_id = _id("job")
        try:
            db().execute(
                """INSERT INTO jobs(id,account_id,device_id,action,payload_json,state,idempotency_key,created_at,updated_at)
                   VALUES(?,?,?,?,?,'queued',?,?,?)""",
                (job_id, g.account["id"], device_id, action, canonical_json(payload), idempotency_key, timestamp, timestamp),
            )
        except sqlite3.IntegrityError:
            existing = db().execute(
                "SELECT * FROM jobs WHERE account_id=? AND idempotency_key=?",
                (g.account["id"], idempotency_key),
            ).fetchone()
            return jsonify(job=public_job(existing), idempotent_replay=True), 200
        row = db().execute("SELECT * FROM jobs WHERE id=?", (job_id,)).fetchone()
        return jsonify(job=public_job(row), idempotent_replay=False), 201

    @app.get("/v1/jobs/<job_id>")
    @account_required
    def get_job(job_id):
        row = db().execute(
            "SELECT * FROM jobs WHERE id=? AND account_id=?", (job_id, g.account["id"])
        ).fetchone()
        return (jsonify(job=public_job(row)), 200) if row else (jsonify(error="job not found"), 404)

    @app.post("/v1/device/jobs/lease")
    @device_required
    def lease_job():
        connection = db()
        now = _now()
        ttl = int(app.config["LEASE_TTL_SECONDS"])
        connection.execute("BEGIN IMMEDIATE")
        try:
            active = connection.execute(
                """SELECT * FROM jobs WHERE device_id=? AND state IN ('leased','running')
                   AND lease_expires_at>? ORDER BY created_at LIMIT 1""",
                (g.device["id"], now),
            ).fetchone()
            if active:
                connection.execute("COMMIT")
                return jsonify(job=public_job(active), lease_id=active["lease_id"], lease_expires_at=active["lease_expires_at"], replay=True)
            row = connection.execute(
                """SELECT * FROM jobs WHERE device_id=? AND
                   (state='queued' OR (state IN ('leased','running') AND lease_expires_at<=?))
                   ORDER BY created_at LIMIT 1""",
                (g.device["id"], now),
            ).fetchone()
            if not row:
                connection.execute("COMMIT")
                return "", 204
            lease_id = _id("lease")
            expires_at = now + ttl
            connection.execute(
                """UPDATE jobs SET state='leased',lease_id=?,lease_expires_at=?,attempt=attempt+1,updated_at=?
                   WHERE id=?""",
                (lease_id, expires_at, now, row["id"]),
            )
            leased = connection.execute("SELECT * FROM jobs WHERE id=?", (row["id"],)).fetchone()
            connection.execute("COMMIT")
            return jsonify(job=public_job(leased), lease_id=lease_id, lease_expires_at=expires_at, replay=False)
        except Exception:
            connection.execute("ROLLBACK")
            raise

    def leased_job(job_id: str, lease_id: str):
        return db().execute(
            "SELECT * FROM jobs WHERE id=? AND device_id=? AND lease_id=?",
            (job_id, g.device["id"], lease_id),
        ).fetchone()

    @app.post("/v1/device/jobs/<job_id>/progress")
    @device_required
    def job_progress(job_id):
        body = request.get_json(silent=True) or {}
        lease_id = str(body.get("lease_id", ""))
        progress = body.get("progress", {})
        row = leased_job(job_id, lease_id)
        if not row:
            return jsonify(error="job lease not found"), 409
        if row["state"] in ("succeeded", "failed", "cancelled"):
            return jsonify(job=public_job(row), idempotent_replay=True)
        if row["lease_expires_at"] <= _now():
            return jsonify(error="job lease expired"), 409
        sensitive = find_sensitive_path(progress)
        if sensitive:
            return jsonify(error="sensitive progress data rejected", field=sensitive), 400
        new_expiry = _now() + int(app.config["LEASE_TTL_SECONDS"])
        db().execute(
            "UPDATE jobs SET state='running',progress_json=?,lease_expires_at=?,updated_at=? WHERE id=?",
            (canonical_json(redact(progress)), new_expiry, _now(), job_id),
        )
        return jsonify(ok=True, lease_expires_at=new_expiry)

    @app.post("/v1/device/jobs/<job_id>/complete")
    @device_required
    def complete_job(job_id):
        body = request.get_json(silent=True) or {}
        lease_id = str(body.get("lease_id", ""))
        status = str(body.get("status", ""))
        row = leased_job(job_id, lease_id)
        if not row:
            return jsonify(error="job lease not found"), 409
        if row["state"] in ("succeeded", "failed"):
            return jsonify(job=public_job(row), idempotent_replay=True)
        if row["lease_expires_at"] <= _now():
            return jsonify(error="job lease expired"), 409
        if status not in ("succeeded", "failed"):
            return jsonify(error="status must be succeeded or failed"), 400
        result = redact(body.get("result", {}))
        error = redact(body.get("error", {}))
        sensitive = find_sensitive_path(result) or find_sensitive_path(error)
        if sensitive:
            return jsonify(error="sensitive completion data rejected", field=sensitive), 400
        db().execute(
            """UPDATE jobs SET state=?,result_json=?,error_json=?,lease_expires_at=NULL,updated_at=?
               WHERE id=?""",
            (status, canonical_json(result), canonical_json(error), _now(), job_id),
        )
        updated = db().execute("SELECT * FROM jobs WHERE id=?", (job_id,)).fetchone()
        return jsonify(job=public_job(updated), idempotent_replay=False)

    @app.errorhandler(Exception)
    def safe_error(error):
        if app.config["TESTING"]:
            raise error
        app.logger.exception("control-plane request failed")
        return jsonify(error="internal server error"), 500

    return app


if __name__ == "__main__":
    application = create_app()
    application.run(host="127.0.0.1", port=5090, debug=False)
