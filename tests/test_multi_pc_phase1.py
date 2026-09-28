import tempfile
import unittest
from pathlib import Path

from multi_pc.adapter import SafeLocalAdapter
from multi_pc.connector import Connector, ConnectorError
from multi_pc.control_plane import create_app


class Phase1ApiTestCase(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.db_path = str(Path(self.temp.name) / "control.sqlite3")
        self.app = create_app({
            "TESTING": True,
            "DATABASE": self.db_path,
            "ALLOW_REGISTRATION": True,
            "PAIRING_TTL_SECONDS": 30,
            "LEASE_TTL_SECONDS": 30,
        })
        self.client = self.app.test_client()

    def tearDown(self):
        self.temp.cleanup()

    def account(self, email):
        password = "correct-horse-battery"
        response = self.client.post("/v1/auth/register", json={"email": email, "password": password})
        self.assertEqual(response.status_code, 201)
        response = self.client.post("/v1/auth/login", json={"email": email, "password": password})
        self.assertEqual(response.status_code, 200)
        return response.get_json()["token"]

    @staticmethod
    def auth(token):
        return {"Authorization": f"Bearer {token}"}

    def pair(self, account_token, name="Renderer", fingerprint="machine-a"):
        code_response = self.client.post("/v1/devices/pairing-codes", headers=self.auth(account_token))
        self.assertEqual(code_response.status_code, 201)
        code = code_response.get_json()["code"]
        response = self.client.post(
            "/v1/devices/pair", json={"code": code, "name": name, "fingerprint": fingerprint}
        )
        self.assertEqual(response.status_code, 201)
        return response.get_json()

    def create_job(self, account_token, device_id, key="job-key", payload=None):
        return self.client.post(
            "/v1/jobs",
            headers={**self.auth(account_token), "Idempotency-Key": key},
            json={
                "device_id": device_id,
                "action": "highlight_pipeline",
                "payload": payload or {"source_url": "https://www.youtube.com/watch?v=abcdefghijk"},
            },
        )

    def test_account_and_device_isolation(self):
        alice = self.account("alice@example.test")
        bob = self.account("bob@example.test")
        alice_device = self.pair(alice, fingerprint="alice-pc")
        bob_device = self.pair(bob, fingerprint="bob-pc")

        denied = self.create_job(alice, bob_device["device_id"], key="wrong-device")
        self.assertEqual(denied.status_code, 404)

        created = self.create_job(alice, alice_device["device_id"])
        self.assertEqual(created.status_code, 201)
        job_id = created.get_json()["job"]["id"]

        hidden = self.client.get(f"/v1/jobs/{job_id}", headers=self.auth(bob))
        self.assertEqual(hidden.status_code, 404)
        bob_lease = self.client.post("/v1/device/jobs/lease", headers=self.auth(bob_device["credential"]), json={})
        self.assertEqual(bob_lease.status_code, 204)

    def test_expired_and_consumed_pairing_codes_fail_closed(self):
        token = self.account("pairing@example.test")
        response = self.client.post("/v1/devices/pairing-codes", headers=self.auth(token))
        code = response.get_json()["code"]
        with self.app.app_context():
            self.app.get_db().execute("UPDATE pairing_codes SET expires_at=0")
        expired = self.client.post(
            "/v1/devices/pair", json={"code": code, "name": "PC", "fingerprint": "expired"}
        )
        self.assertEqual(expired.status_code, 410)

        paired = self.pair(token, fingerprint="one-time")
        devices = self.client.get("/v1/devices", headers=self.auth(token)).get_json()["devices"]
        self.assertEqual(devices[0]["id"], paired["device_id"])

    def test_job_idempotency_duplicate_lease_and_reconnect_reclaim(self):
        token = self.account("jobs@example.test")
        device = self.pair(token, fingerprint="jobs-pc")
        first = self.create_job(token, device["device_id"], key="stable-key")
        second = self.create_job(token, device["device_id"], key="stable-key")
        self.assertEqual(first.status_code, 201)
        self.assertEqual(second.status_code, 200)
        self.assertTrue(second.get_json()["idempotent_replay"])
        self.assertEqual(first.get_json()["job"]["id"], second.get_json()["job"]["id"])

        headers = self.auth(device["credential"])
        lease1 = self.client.post("/v1/device/jobs/lease", headers=headers, json={}).get_json()
        lease2 = self.client.post("/v1/device/jobs/lease", headers=headers, json={}).get_json()
        self.assertTrue(lease2["replay"])
        self.assertEqual(lease1["lease_id"], lease2["lease_id"])
        self.assertEqual(lease1["job"]["attempt"], 1)

        with self.app.app_context():
            self.app.get_db().execute(
                "UPDATE jobs SET lease_expires_at=0 WHERE id=?", (lease1["job"]["id"],)
            )
        reclaimed = self.client.post("/v1/device/jobs/lease", headers=headers, json={}).get_json()
        self.assertNotEqual(reclaimed["lease_id"], lease1["lease_id"])
        self.assertEqual(reclaimed["job"]["attempt"], 2)

    def test_secret_fields_rejected_and_secret_values_redacted(self):
        token = self.account("secrets@example.test")
        device = self.pair(token, fingerprint="secret-pc")
        rejected = self.create_job(
            token, device["device_id"], key="secret-job", payload={"source_url": "https://safe.test", "api_key": "never"}
        )
        self.assertEqual(rejected.status_code, 400)
        self.assertNotIn("never", rejected.get_data(as_text=True))

        created = self.create_job(token, device["device_id"], key="redact-job")
        lease = self.client.post(
            "/v1/device/jobs/lease", headers=self.auth(device["credential"]), json={}
        ).get_json()
        completed = self.client.post(
            f"/v1/device/jobs/{created.get_json()['job']['id']}/complete",
            headers=self.auth(device["credential"]),
            json={
                "lease_id": lease["lease_id"],
                "status": "failed",
                "error": {"message": "upstream rejected Bearer top-secret-value"},
            },
        )
        self.assertEqual(completed.status_code, 200)
        serialized = completed.get_data(as_text=True)
        self.assertNotIn("top-secret-value", serialized)
        self.assertIn("REDACTED", serialized)


class ConnectorBehaviorTests(unittest.TestCase):
    def test_connector_runs_allowlisted_adapter_and_reports_local_reference(self):
        calls = []

        class Client:
            def lease(self):
                return {
                    "lease_id": "lease-1",
                    "job": {"id": "job-1", "action": "highlight_pipeline", "payload": {"source_url": "https://safe"}},
                }

            def progress(self, job_id, lease_id, progress):
                calls.append(("progress", job_id, lease_id, progress))

            def complete(self, job_id, lease_id, status, result=None, error=None):
                calls.append(("complete", job_id, lease_id, status, result, error))

        def handler(payload, progress):
            progress({"stage": "render", "percent": 50})
            return {"local_output_ref": "D:\\outputs\\job-1.mp4", "bytes": 1234}

        connector = Connector(Client(), SafeLocalAdapter({"highlight_pipeline": handler}))
        self.assertTrue(connector.poll_once())
        self.assertEqual(calls[-1][3], "succeeded")
        self.assertEqual(calls[-1][4]["local_output_ref"], "D:\\outputs\\job-1.mp4")

    def test_completion_connection_failure_never_reports_success(self):
        calls = []

        class Client:
            def lease(self):
                return {"lease_id": "lease-1", "job": {"id": "job-1", "action": "highlight_pipeline", "payload": {}}}

            def progress(self, *_args):
                return None

            def complete(self, _job_id, _lease_id, status, result=None, error=None):
                calls.append(status)
                raise ConnectorError("offline")

        adapter = SafeLocalAdapter({"highlight_pipeline": lambda payload, progress: {"local_output_ref": "local.mp4"}})
        self.assertTrue(Connector(Client(), adapter).poll_once())
        self.assertEqual(calls, ["succeeded"])


if __name__ == "__main__":
    unittest.main()
