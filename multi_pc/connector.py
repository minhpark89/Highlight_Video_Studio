import logging
import time
from typing import Any

import requests

from .adapter import AdapterError, SafeLocalAdapter
from .security import redact


class ConnectorError(RuntimeError):
    pass


class ControlPlaneClient:
    def __init__(self, base_url: str, device_credential: str, timeout: float = 20):
        if not base_url.lower().startswith("https://") and not base_url.startswith("http://127.0.0.1"):
            raise ConnectorError("control plane must use HTTPS (loopback HTTP allowed for development)")
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({"Authorization": f"Bearer {device_credential}"})

    def _request(self, method: str, path: str, **kwargs):
        response = self.session.request(method, self.base_url + path, timeout=self.timeout, **kwargs)
        if response.status_code == 204:
            return None
        if not response.ok:
            try:
                detail = response.json().get("error", "request rejected")
            except ValueError:
                detail = "request rejected"
            raise ConnectorError(f"control plane HTTP {response.status_code}: {redact(detail)}")
        return response.json()

    def heartbeat(self, capabilities: dict[str, Any]):
        return self._request("POST", "/v1/device/heartbeat", json={"capabilities": capabilities})

    def lease(self):
        return self._request("POST", "/v1/device/jobs/lease", json={})

    def progress(self, job_id: str, lease_id: str, progress: dict):
        return self._request(
            "POST", f"/v1/device/jobs/{job_id}/progress", json={"lease_id": lease_id, "progress": progress}
        )

    def complete(self, job_id: str, lease_id: str, status: str, result=None, error=None):
        return self._request(
            "POST",
            f"/v1/device/jobs/{job_id}/complete",
            json={"lease_id": lease_id, "status": status, "result": result or {}, "error": error or {}},
        )


class Connector:
    def __init__(self, client: ControlPlaneClient, adapter: SafeLocalAdapter, logger=None):
        self.client = client
        self.adapter = adapter
        self.log = logger or logging.getLogger("highlight.connector")

    def poll_once(self) -> bool:
        lease = self.client.lease()
        if not lease:
            return False
        job = lease["job"]
        job_id = job["id"]
        lease_id = lease["lease_id"]

        def report(update):
            self.client.progress(job_id, lease_id, redact(update))

        try:
            report({"stage": "accepted", "percent": 0})
            result = self.adapter.execute(job["action"], job["payload"], report)
        except Exception as exc:
            safe_message = str(redact(str(exc)))[:500]
            try:
                self.client.complete(job_id, lease_id, "failed", error={"message": safe_message})
            except ConnectorError:
                # Fail closed. An unacknowledged job stays leased and can be
                # reclaimed after lease expiry; it is never marked terminal.
                self.log.warning("job failure acknowledgement deferred after connection failure")
            return True

        try:
            self.client.complete(job_id, lease_id, "succeeded", result=result)
        except ConnectorError:
            # Local execution succeeded, but the cloud did not acknowledge it.
            # Do not misreport failure: leave the lease non-terminal so the
            # local idempotency ledger can replay the receipt after reconnect.
            self.log.warning("job success acknowledgement deferred after connection failure")
        return True

    def run_forever(self, poll_seconds: float = 5, max_backoff_seconds: float = 60):
        backoff = poll_seconds
        while True:
            try:
                self.client.heartbeat({"connector": "phase1", "transport": "https-poll"})
                worked = self.poll_once()
                backoff = poll_seconds
                if not worked:
                    time.sleep(poll_seconds)
            except (requests.RequestException, ConnectorError):
                self.log.warning("control plane unavailable; retrying with backoff")
                time.sleep(backoff)
                backoff = min(max_backoff_seconds, max(poll_seconds, backoff * 2))
