"""Targeted regression tests for Page / Token / Token-Group / Sync management.

Covers the reported non-functional features:
  * token add + page sync persists pages with correct schema (page_id, group_ids)
  * page <-> group binding (update_binding) and group CRUD
  * single + batch token assignment
  * frontend invariants: no duplicate top-level function definitions, no fetches
    pointing at non-existent Flask routes, and no shadowed stale handlers.

No real Meta Graph API calls are made (token verification is stubbed) and no real
tokens are written or printed.
"""

import re
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

BASE_DIR = Path(__file__).resolve().parent.parent


# --------------------------------------------------------------------------- #
# Frontend static invariants (pure text analysis of web/templates/index.html)
# --------------------------------------------------------------------------- #
class FrontendInvariantTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html = (BASE_DIR / "web" / "templates" / "index.html").read_text(encoding="utf-8")

    def _functions(self):
        return re.findall(r"(?m)^[ \t]*(?:async[ \t]+)?function[ \t]+([A-Za-z_$][\w$]*)[ \t]*\(", self.html)

    def _function_body(self, name):
        """Return the full body of a top-level function, up to the next
        top-level function/async function definition (or end of file)."""
        matches = list(re.finditer(
            r"(?m)^[ \t]*(?:async[ \t]+)?function[ \t]+([A-Za-z_$][\w$]*)[ \t]*\(", self.html
        ))
        target = next((m for m in matches if m.group(1) == name), None)
        self.assertIsNotNone(target, f"{name} not found")
        following = next((m for m in matches if m.start() > target.start()), None)
        return self.html[target.start():] if following is None else self.html[target.start():following.start()]

    def test_no_duplicate_function_definitions(self):
        names = self._functions()
        seen = {}
        for n in names:
            seen[n] = seen.get(n, 0) + 1
        dups = {n: c for n, c in seen.items() if c > 1}
        self.assertEqual(dups, {}, f"Duplicate top-level function definitions shadow each other: {dups}")

    def test_required_handlers_defined_once(self):
        names = self._functions()
        for fn in (
            "openAddGroupModal",
            "closeAddGroupModal",
            "openScheduleRulesModal",
            "closeScheduleRulesModal",
            "executeBatchDistribute",
            "openAssignSingleTokenModal",
            "loadScheduleRulesConfig",
            "renderFilteredPages",
        ):
            self.assertEqual(names.count(fn), 1, f"{fn} must be defined exactly once (found {names.count(fn)})")

    def test_no_code_reference_to_stale_distribute_dom_ids(self):
        # The removed stale handler referenced these DOM ids directly. A descriptive
        # comment mentioning them is fine; live code must not touch them.
        for stale in ("dist-select-group", "dist-start-time", "btn-batch-distribute"):
            for pat in (f"getElementById('{stale}')", f'getElementById("{stale}")',
                        f"querySelector('#{stale}')", f'querySelector("#{stale}")'):
                self.assertNotIn(pat, self.html, f"Stale DOM id '{stale}' still referenced in code")

    def test_ui_fetches_resolve_to_real_routes(self):
        app_src = (BASE_DIR / "web" / "app.py").read_text(encoding="utf-8")
        routes = set(re.findall(r"@app\.route\(\s*['\"]([^'\"]+)['\"]", app_src))
        fetches = set(re.findall(r"fetch\(\s*[`'\"]([^`'\"?]+)", self.html))

        def norm(u):
            u = re.sub(r"\$\{[^}]*\}", "<X>", u)
            return re.split(r"['\"]\s*\+", u)[0].strip()

        missing = []
        for u in fetches:
            n = norm(u)
            base_u = n.split("<")[0].rstrip("/")
            if not any(
                rt == n or (rt.split("<")[0].rstrip("/") == base_u and base_u)
                for rt in routes
            ):
                missing.append(u)
        self.assertEqual(missing, [], f"UI fetches with no matching route: {missing}")

    def test_group_filter_uses_correct_schema_keys(self):
        # The Pages view filter must key off group_ids / group_name (backend schema),
        # and must not depend on a non-existent p.groups array.
        body = self._function_body("renderFilteredPages")
        self.assertIn("group_ids", body)
        self.assertNotIn("p.groups", body)

    def test_schedule_rules_config_uses_groups_endpoint(self):
        body = self._function_body("loadScheduleRulesConfig")
        self.assertIn("/api/groups", body)
        self.assertNotIn("/api/pages/groups", body)

    def test_single_token_assign_opens_vault_selector(self):
        body = self._function_body("openAssignSingleTokenModal")
        self.assertIn("openQuickAssignModal", body)
        self.assertNotIn("prompt(", body)

    def test_quick_assign_sends_token_id(self):
        body = self._function_body("saveQuickAssign")
        self.assertIn("/api/pages/update_binding", body)
        self.assertIn("token_id", body)


# --------------------------------------------------------------------------- #
# Backend behaviour of the Page / Token / Group / Sync APIs
# --------------------------------------------------------------------------- #
class BackendApiTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)

        # Import managers and rebind them to an isolated temp data dir.
        from src.publisher.token_vault import TokenVault
        from src.publisher.page_manager import PageManager

        self.TokenVault = TokenVault
        self.PageManager = PageManager
        self.vault = TokenVault(self.dir)
        self.pages = PageManager(self.dir)

        import web.app as appmod
        self.appmod = appmod
        self._orig_vault = appmod.token_vault
        self._orig_pages = appmod.page_manager
        self._orig_tg_file = appmod.TOKEN_GROUPS_FILE
        appmod.token_vault = self.vault
        appmod.page_manager = self.pages
        appmod.TOKEN_GROUPS_FILE = self.dir / "token_groups.json"
        appmod.app.config["TESTING"] = True
        self.client = appmod.app.test_client()

    def tearDown(self):
        self.appmod.token_vault = self._orig_vault
        self.appmod.page_manager = self._orig_pages
        self.appmod.TOKEN_GROUPS_FILE = self._orig_tg_file
        self.tmp.cleanup()

    # -- helpers ----------------------------------------------------------- #
    def _seed_token(self, name="System Token", tok="EAAB_test_token_value_123456"):
        entry = {
            "id": "tok_test_1",
            "name": name,
            "token": tok,
            "status": "ACTIVE",
            "pages_count": 2,
            "rate_status": "NORMAL",
            "app_usage_pct": 0,
            "call_count_hour": 0,
        }
        self.vault._save([entry])
        return entry

    def _graph_pages(self):
        return [
            {"page_id": "PAGE_A", "page_name": "Page A", "category": "Media",
             "page_token": "EAAB_page_a", "avatar": ""},
            {"page_id": "PAGE_B", "page_name": "Page B", "category": "Media",
             "page_token": "EAAB_page_b", "avatar": ""},
        ]

    # -- token add + sync -------------------------------------------------- #
    def test_add_token_syncs_pages_with_correct_schema(self):
        verify = {"status": "ACTIVE", "error": "", "pages": self._graph_pages(), "owner_name": "Owner"}
        with mock.patch.object(self.vault, "verify_token", return_value=verify):
            resp = self.client.post("/api/tokens", json={"tokens_input": "MyToken|EAAB_secret", "name": ""})
        self.assertEqual(resp.status_code, 200)
        body = resp.get_json()
        self.assertTrue(body["success"])
        self.assertEqual(body["synced_pages"], 2)

        pages = self.pages.list_pages()
        self.assertEqual(len(pages), 2)
        ids = {p["page_id"] for p in pages}
        self.assertEqual(ids, {"PAGE_A", "PAGE_B"})
        for p in pages:
            self.assertIn("group_ids", p)
            self.assertEqual(p["token_id"], body["results"][0]["id"])

    def test_add_token_duplicate_is_deduped(self):
        verify = {"status": "ACTIVE", "error": "", "pages": [], "owner_name": ""}
        with mock.patch.object(self.vault, "verify_token", return_value=verify):
            self.client.post("/api/tokens", json={"tokens_input": "EAAB_same_token"})
            self.client.post("/api/tokens", json={"tokens_input": "EAAB_same_token"})
        self.assertEqual(len(self.vault.list_tokens(mask=False)), 1)

    def test_add_token_rejects_empty(self):
        resp = self.client.post("/api/tokens", json={"tokens_input": "   "})
        self.assertEqual(resp.status_code, 400)

    def test_tokens_list_is_masked(self):
        self._seed_token()
        body = self.client.get("/api/tokens").get_json()
        self.assertTrue(body["success"])
        for t in body["tokens"]:
            self.assertNotIn("token", t, "raw token must not be returned by list API")
            self.assertIn("token_masked", t)

    # -- groups ------------------------------------------------------------ #
    def test_group_create_list_delete(self):
        r = self.client.post("/api/groups", json={"name": "BM 1", "page_ids": ["PAGE_A"]})
        self.assertEqual(r.status_code, 200)
        groups = self.client.get("/api/groups").get_json()["groups"]
        self.assertEqual(len(groups), 1)
        self.assertEqual(groups[0]["page_ids"], ["PAGE_A"])

        gid = groups[0]["id"]
        d = self.client.delete(f"/api/groups/{gid}")
        self.assertEqual(d.status_code, 200)
        self.assertEqual(self.client.get("/api/groups").get_json()["groups"], [])

    def test_save_group_updates_existing(self):
        r1 = self.client.post("/api/groups", json={"name": "G1", "page_ids": []}).get_json()
        gid = r1.get("group", {}).get("id") or self.pages.list_groups()[0]["id"]
        self.client.post("/api/groups", json={"id": gid, "name": "G1-renamed", "page_ids": ["PAGE_B"]})
        groups = self.pages.list_groups()
        names = [g["name"] for g in groups]
        self.assertIn("G1-renamed", names)
        self.assertEqual(len(groups), 1)

    # -- page binding ------------------------------------------------------ #
    def test_update_binding_assigns_group_and_token(self):
        self._seed_token()
        self.pages.save_pages([{"page_id": "PAGE_A", "page_name": "A", "group_ids": [], "group_name": "Chưa nhóm"}])
        self.pages.save_groups([{"id": "grp_1", "name": "BM 1", "page_ids": []}])

        resp = self.client.post("/api/pages/update_binding", json={
            "page_id": "PAGE_A", "group_id": "grp_1", "token_id": "tok_test_1",
        })
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.get_json()["success"])

        p = self.pages.list_pages()[0]
        self.assertEqual(p["group_ids"], ["grp_1"])
        self.assertEqual(p["group_name"], "BM 1")
        self.assertEqual(p["token_id"], "tok_test_1")
        # group back-reference updated
        self.assertIn("PAGE_A", self.pages.list_groups()[0]["page_ids"])

    def test_update_binding_unknown_page_404(self):
        resp = self.client.post("/api/pages/update_binding", json={"page_id": "NOPE"})
        self.assertEqual(resp.status_code, 404)

    # -- token assignment -------------------------------------------------- #
    def test_single_token_assign(self):
        token = self._seed_token()
        self.pages.save_pages([{"page_id": "PAGE_A", "page_name": "A", "token_id": ""}])
        resp = self.client.post("/api/pages/assign_token", json={"page_id": "PAGE_A", "token_id": token["id"]})
        self.assertEqual(resp.status_code, 200)
        page = self.pages.list_pages()[0]
        self.assertEqual(page["token_id"], token["id"])
        self.assertEqual(page["token_name"], token["name"])
        self.assertEqual(page["page_token"], token["token"])

    def test_single_token_assign_unknown_page(self):
        token = self._seed_token()
        self.pages.save_pages([{"page_id": "PAGE_A", "page_name": "A"}])
        resp = self.client.post("/api/pages/assign_token", json={"page_id": "MISSING", "token_id": token["id"]})
        self.assertEqual(resp.status_code, 404)

    def test_single_token_assign_rejects_unknown_vault_token(self):
        self.pages.save_pages([{"page_id": "PAGE_A", "page_name": "A"}])
        resp = self.client.post("/api/pages/assign_token", json={"page_id": "PAGE_A", "token_id": "missing"})
        self.assertEqual(resp.status_code, 404)

    def test_batch_assign_round_robin(self):
        tokens = [
            {"id": "tok_1", "name": "T1", "token": "EAAB_page_token_1", "status": "ACTIVE"},
            {"id": "tok_2", "name": "T2", "token": "EAAB_page_token_2", "status": "ACTIVE"},
        ]
        self.vault._save(tokens)
        self.pages.save_pages([
            {"page_id": "PAGE_A", "page_name": "A"},
            {"page_id": "PAGE_B", "page_name": "B"},
        ])
        resp = self.client.post("/api/pages/batch_assign_token", json={
            "assignments": [
                {"page_id": "PAGE_A", "token_id": "tok_1"},
                {"page_id": "PAGE_B", "token_id": "tok_2"},
            ]
        })
        body = resp.get_json()
        self.assertTrue(body["success"])
        self.assertEqual(body["count"], 2)
        pages = {p["page_id"]: p for p in self.pages.list_pages()}
        self.assertEqual({pid: p["token_id"] for pid, p in pages.items()}, {"PAGE_A": "tok_1", "PAGE_B": "tok_2"})
        self.assertEqual(pages["PAGE_A"]["page_token"], "EAAB_page_token_1")
        self.assertEqual(pages["PAGE_B"]["token_name"], "T2")

    def test_batch_assign_single_token_to_many(self):
        token = self._seed_token()
        self.pages.save_pages([
            {"page_id": "PAGE_A"}, {"page_id": "PAGE_B"}, {"page_id": "PAGE_C"},
        ])
        resp = self.client.post("/api/pages/batch_assign_token", json={
            "token_id": token["id"], "page_ids": ["PAGE_A", "PAGE_C"],
        })
        self.assertEqual(resp.get_json()["count"], 2)
        pages = {p["page_id"]: p for p in self.pages.list_pages()}
        self.assertEqual(pages["PAGE_A"]["token_id"], token["id"])
        self.assertEqual(pages["PAGE_C"]["page_token"], token["token"])
        self.assertEqual(pages["PAGE_B"].get("token_id", ""), "")

    def test_batch_assign_requires_token_or_assignments(self):
        resp = self.client.post("/api/pages/batch_assign_token", json={"page_ids": ["PAGE_A"]})
        self.assertEqual(resp.status_code, 400)

    # -- token groups ------------------------------------------------------ #
    def test_token_group_create_and_read(self):
        # Seed a non-empty file so load_token_groups() does not inject its default group.
        self.appmod.save_token_groups([{"id": "seed", "name": "Seed", "token_ids": []}])
        r = self.client.post("/api/token-groups", json={"name": "Pool 1", "token_ids": ["tok_test_1"]})
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.get_json()["success"])
        groups = self.client.get("/api/token-groups").get_json()["groups"]
        names = {g["name"]: g for g in groups}
        self.assertIn("Pool 1", names)
        self.assertEqual(names["Pool 1"]["token_ids"], ["tok_test_1"])

    def test_token_group_requires_name(self):
        self.appmod.save_token_groups([{"id": "seed", "name": "Seed", "token_ids": []}])
        r = self.client.post("/api/token-groups", json={"name": "", "token_ids": []})
        self.assertEqual(r.status_code, 400)

    def test_token_group_delete(self):
        self.appmod.save_token_groups([{"id": "tgrp_1", "name": "Pool 1", "token_ids": []}])
        self.client.delete("/api/token-groups/tgrp_1")
        groups = self.client.get("/api/token-groups").get_json()["groups"]
        self.assertNotIn("tgrp_1", [g["id"] for g in groups])


if __name__ == "__main__":
    unittest.main()
