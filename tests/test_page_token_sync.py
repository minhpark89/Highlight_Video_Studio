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
import collections
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
            "submitAddToken",
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

    def test_submit_add_token_posts_batch_and_refreshes_token_page_state(self):
        body = self._function_body("submitAddToken")
        self.assertIn("/api/tokens", body)
        self.assertIn("tokens_input", body)
        self.assertIn("loadTokensOnly", body)
        self.assertIn("loadTokensAndPages", body)
        self.assertIn("closeAddTokenModal", body)

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

    def test_token_group_ui_explains_snapshot_and_offers_rebind(self):
        body = self._function_body("loadTokenGroupsList")
        rebind = self._function_body("rebindTokenGroupPages")
        self.assertIn("snapshot", self.html)
        self.assertIn("Cập nhật Page set", body)
        self.assertIn("/rebind-pages", rebind)
        self.assertIn("method: 'POST'", rebind)

    def test_group_ui_exposes_snapshot_label_and_rebind_action(self):
        body = self._function_body("loadTokenGroupsList")
        self.assertIn("snapshot", body)
        self.assertIn("rebindTokenGroupPages", body)
        rebind = self._function_body("rebindTokenGroupPages")
        self.assertIn("/rebind-pages", rebind)
        self.assertNotIn("/refresh-pages", rebind)
        hint = self.html[self.html.find('id="tgrp-page-source-token"'):]
        self.assertIn("snapshot", hint[:1200].lower())


# --------------------------------------------------------------------------- #
# Backend behaviour of the Page / Token / Group / Sync APIs
# --------------------------------------------------------------------------- #
class BackendApiTests(unittest.TestCase):
    def test_page_manager_filters_invalid_json_entries(self):
        from src.publisher.page_manager import PageManager

        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "pages.json").write_text(json.dumps(["stale", 42, {"page_id": "PAGE_A"}]), encoding="utf-8")
            (root / "page_groups.json").write_text(json.dumps(["stale", {"id": "grp"}]), encoding="utf-8")
            manager = PageManager(root)
            self.assertEqual(manager.list_pages(), [{"page_id": "PAGE_A"}])
            self.assertEqual(manager.list_groups(), [{"id": "grp"}])

    def test_preflight_invalid_page_entry_fails_closed(self):
        from src.publisher.meta_preflight import preflight_pages

        verdict = preflight_pages(["stale-record"], mock.Mock(), mock.Mock())
        self.assertFalse(verdict["ok"])
        self.assertEqual(verdict["blocked"]["code"], "missing_page")
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
        identity = {"status": "ACTIVE", "error": "", "pages": [], "owner_name": "Owner"}
        with mock.patch.object(self.vault, "verify_identity", return_value=identity), mock.patch.object(
            self.vault, "discover_pages", return_value=verify
        ):
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
            self.assertEqual(p["token_name"], "MyToken")
            self.assertTrue(p["page_token"].startswith("EAAB_page_"))

        response_text = resp.get_data(as_text=True)
        self.assertNotIn("EAAB_secret", response_text)
        self.assertNotIn("EAAB_page_a", response_text)
        self.assertNotIn("EAAB_page_b", response_text)

    def test_multi_token_bindings_are_exact_and_survive_restart(self):
        first = {"id": "tok_a", "name": "A", "token": "token-a", "status": "ACTIVE"}
        second = {"id": "tok_b", "name": "B", "token": "token-b", "status": "ACTIVE"}
        pages = self.pages.sync_pages_from_token(first, [
            {"id": "PAGE_A", "name": "A", "access_token": "page-a", "tasks": ["CREATE_CONTENT"]},
            {"id": "PAGE_SHARED", "name": "Shared", "access_token": "page-shared-a", "tasks": ["CREATE_CONTENT"]},
        ])
        self.pages.sync_pages_from_token(second, [
            {"id": "PAGE_B", "name": "B", "access_token": "page-b", "tasks": ["CREATE_CONTENT"]},
            {"id": "PAGE_SHARED", "name": "Shared", "access_token": "page-shared-b", "tasks": ["CREATE_CONTENT"]},
        ])
        restarted = self.PageManager(self.dir)
        resolved, reason = restarted.resolve_verified_mapping("PAGE_SHARED", second)
        self.assertIsNone(reason)
        self.assertEqual(resolved["page_token"], "page-shared-b")
        self.assertEqual(resolved["token_id"], "tok_b")
        page_b, reason = restarted.resolve_verified_mapping("PAGE_B", second)
        self.assertIsNone(reason)
        self.assertEqual(page_b["page_token"], "page-b")

    def test_refresh_prunes_only_the_refreshed_credential_binding(self):
        first = {"id": "tok_a", "name": "A", "token": "token-a", "status": "ACTIVE"}
        second = {"id": "tok_b", "name": "B", "token": "token-b", "status": "ACTIVE"}
        self.pages.sync_pages_from_token(first, [{"id": "PAGE_X", "access_token": "page-x-a", "tasks": ["CREATE_CONTENT"]}])
        self.pages.sync_pages_from_token(second, [{"id": "PAGE_X", "access_token": "page-x-b", "tasks": ["CREATE_CONTENT"]}])
        self.pages.sync_pages_from_token(first, [])
        current = self.pages.list_pages()[0]
        self.assertNotIn("tok_a", current.get("token_bindings", {}))
        self.assertIn("tok_b", current.get("token_bindings", {}))
        self.assertEqual(current.get("token_id"), "tok_b")

    def test_cross_bound_mapping_is_rejected(self):
        first = {"id": "tok_a", "name": "A", "token": "token-a", "status": "ACTIVE"}
        second = {"id": "tok_b", "name": "B", "token": "token-b", "status": "ACTIVE"}
        self.pages.sync_pages_from_token(first, [{"id": "PAGE_A", "access_token": "page-a", "tasks": ["CREATE_CONTENT"]}])
        import src.publisher.meta_preflight as preflight
        verdict = preflight.resolve_page_token(
            {"page_id": "PAGE_A", "token_id": "tok_b"},
            mock.Mock(get_token_by_id=lambda _id: second),
            self.pages,
        )
        self.assertFalse(verdict["ok"])
        self.assertEqual(verdict["code"], "missing_mapping")

    def test_batch_import_syncs_pages_only_from_first_representative_token(self):
        first_pages = self._graph_pages()
        identity = {"status": "ACTIVE", "error": "", "pages": [], "owner_name": "Owner"}
        discovered = {"status": "ACTIVE", "error": "", "pages": first_pages, "owner_name": "Owner"}
        with mock.patch.object(self.vault, "discover_pages", return_value=discovered) as full, mock.patch.object(self.vault, "verify_identity", return_value=identity) as light:
            resp = self.client.post("/api/tokens", json={
                "tokens_input": "T1|EAAB_one\nT2|EAAB_two\nT3|EAAB_three",
                "page_sync_mode": "representative",
            })
        body = resp.get_json()
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(body["synced_pages"], 2)
        # The batch is validated with /me first, then exactly one /me/accounts Page walk.
        self.assertEqual(light.call_count, 3)
        self.assertEqual(full.call_count, 1)
        self.assertEqual([item["page_sync"] for item in body["results"]], ["synced", "skipped", "skipped"])
        self.assertEqual([item["is_representative"] for item in body["results"]], [True, False, False])
        self.assertEqual(body["representative"]["name"], "T1")
        self.assertNotIn("EAAB_", resp.get_data(as_text=True))

    def test_representative_sync_falls_back_to_second_valid_token(self):
        identity = {"status": "ACTIVE", "error": "", "pages": [], "owner_name": "Owner"}
        failed = {"status": "ERROR", "error": "Page permission denied", "pages": []}
        succeeded = {"status": "ACTIVE", "error": "", "pages": self._graph_pages()[:1]}
        with mock.patch.object(self.vault, "verify_identity", return_value=identity) as light, mock.patch.object(
            self.vault, "discover_pages", side_effect=[failed, succeeded]
        ) as full:
            resp = self.client.post("/api/tokens", json={
                "tokens_input": "First|EAAB_one\nSecond|EAAB_two\nThird|EAAB_three",
                "page_sync_mode": "representative",
            })
        body = resp.get_json()
        self.assertEqual(light.call_count, 3)
        self.assertEqual(full.call_count, 2)
        self.assertEqual(body["representative"]["name"], "Second")
        self.assertEqual(body["representative"]["label"], "#2 Second")
        self.assertEqual([item["status"] for item in body["results"]], ["ACTIVE", "ACTIVE", "ACTIVE"])
        self.assertEqual([item["page_sync"] for item in body["results"]], ["failed", "synced", "skipped"])
        self.assertTrue(body["results"][1]["is_representative"])
        self.assertFalse(body["results"][0]["is_representative"])
        self.assertNotIn("EAAB_", resp.get_data(as_text=True))

    def test_all_representative_page_syncs_can_fail_without_invalidating_tokens(self):
        identity = {"status": "ACTIVE", "error": "", "pages": [], "owner_name": "Owner"}
        failed = {"status": "ERROR", "error": "Page permission denied", "pages": []}
        with mock.patch.object(self.vault, "verify_identity", return_value=identity), mock.patch.object(
            self.vault, "discover_pages", side_effect=[failed, failed]
        ):
            resp = self.client.post("/api/tokens", json={
                "tokens_input": "First|EAAB_one\nSecond|EAAB_two",
                "page_sync_mode": "representative",
            })
        body = resp.get_json()
        self.assertIsNone(body["representative"])
        self.assertEqual([item["status"] for item in body["results"]], ["ACTIVE", "ACTIVE"])
        self.assertEqual([item["page_sync"] for item in body["results"]], ["failed", "failed"])
        self.assertEqual([item["is_representative"] for item in body["results"]], [False, False])
        self.assertEqual([item["status"] for item in self.vault.list_tokens(mask=False)], ["ACTIVE", "ACTIVE"])
        self.assertNotIn("EAAB_", resp.get_data(as_text=True))

    def test_representative_sync_skips_invalid_token_without_page_fetch(self):
        identity_bad = {"status": "ERROR", "error": "[190] invalid token", "pages": [], "owner_name": ""}
        identity_ok = {"status": "ACTIVE", "error": "", "pages": [], "owner_name": "Owner"}
        succeeded = {"status": "ACTIVE", "error": "", "pages": self._graph_pages(), "owner_name": "Owner"}
        with mock.patch.object(self.vault, "verify_identity", side_effect=[identity_bad, identity_ok]), \
                mock.patch.object(self.vault, "discover_pages", return_value=succeeded) as full:
            resp = self.client.post("/api/tokens", json={
                "tokens_input": "Bad|EAAB_bad\nGood|EAAB_good",
                "page_sync_mode": "representative",
            })
        body = resp.get_json()
        self.assertEqual(full.call_count, 1)
        self.assertEqual(body["representative"]["label"], "#2 Good")
        self.assertEqual([item["status"] for item in body["results"]], ["ERROR", "ACTIVE"])
        self.assertEqual([item["page_sync"] for item in body["results"]], ["skipped", "synced"])
        self.assertNotIn("EAAB_", resp.get_data(as_text=True))

    def test_token_group_rebind_refreshes_snapshot_without_graph_call(self):
        tokens = [
            {"id": "tok_1", "name": "Representative", "token": "EAAB_one", "status": "ACTIVE"},
        ]
        self.vault._save(tokens)
        self.pages.save_pages([{"page_id": "PAGE_A", "token_id": "tok_1"}])
        self.appmod.save_token_groups([{"id": "seed", "name": "Seed", "token_ids": []}])
        with mock.patch.object(self.vault, "verify_token") as full:
            created = self.client.post("/api/token-groups", json={
                "name": "Pool", "token_ids": ["tok_1"], "page_source_token_id": "tok_1",
            }).get_json()
        self.assertEqual(created["group"]["page_ids"], ["PAGE_A"])
        gid = created["group"]["id"]
        # A later sync adds a Page for the same source token; the stored binding stays a snapshot.
        self.pages.save_pages([
            {"page_id": "PAGE_A", "token_id": "tok_1"},
            {"page_id": "PAGE_B", "token_id": "tok_1"},
        ])
        stale = next(g for g in self.client.get("/api/token-groups").get_json()["groups"] if g["id"] == gid)
        self.assertEqual(stale["page_ids"], ["PAGE_A"])
        with mock.patch.object(self.vault, "verify_token") as full:
            rebound = self.client.post(f"/api/token-groups/{gid}/rebind-pages")
        self.assertEqual(rebound.status_code, 200)
        self.assertEqual(rebound.get_json()["page_ids"], ["PAGE_A", "PAGE_B"])
        self.assertEqual(full.call_count, 0)

    def test_group_save_uses_cached_bindings_and_rejects_duplicate_name(self):
        self._seed_token()
        self.pages.save_pages([{"page_id": "PAGE_A", "token_bindings": {"tok_test_1": {"status": "VERIFIED"}}}])
        with mock.patch.object(self.vault, "refresh_token_pages") as graph:
            first = self.client.post("/api/token-groups", json={
                "name": "Pool", "token_ids": ["tok_test_1"], "sync_pages": False,
            })
            second = self.client.post("/api/token-groups", json={
                "name": " pool ", "token_ids": ["tok_test_1"], "sync_pages": False,
            })
        self.assertEqual(first.status_code, 200)
        self.assertEqual(first.get_json()["group"]["page_ids"], ["PAGE_A"])
        self.assertEqual(second.status_code, 409)
        self.assertEqual(len(self.appmod.load_token_groups()), 1)
        graph.assert_not_called()

    def test_bulk_delete_refuses_assigned_tokens_and_cleans_groups(self):
        self._seed_token()
        self.vault._save(self.vault.list_tokens(mask=False) + [{"id": "tok_other", "name": "Other", "token": "EAAB_other", "status": "ACTIVE"}])
        self.pages.save_pages([{"page_id": "PAGE_A", "token_id": "tok_test_1", "token_bindings": {"tok_test_1": {}, "tok_other": {}}}])
        self.appmod.save_token_groups([{"id": "g", "name": "Pool", "token_ids": ["tok_test_1", "tok_other"], "page_source_token_id": "tok_other"}])
        refused = self.client.post("/api/tokens/bulk-delete", json={"token_ids": ["tok_test_1", "tok_other"]})
        self.assertEqual(refused.status_code, 409)
        self.assertEqual(len(self.vault.list_tokens(mask=False)), 2)
        deleted = self.client.post("/api/tokens/bulk-delete", json={"token_ids": ["tok_other"]})
        self.assertEqual(deleted.status_code, 200)
        self.assertEqual(self.appmod.load_token_groups()[0]["token_ids"], ["tok_test_1"])
        self.assertEqual(self.appmod.load_token_groups()[0]["page_source_token_id"], "")
        self.assertNotIn("tok_other", self.pages.list_pages()[0]["token_bindings"])

    def test_token_group_rebind_rejects_unbound_group(self):
        self._seed_token()
        self.appmod.save_token_groups([{"id": "seed", "name": "Seed", "token_ids": []}])
        created = self.client.post("/api/token-groups", json={
            "name": "NoSource", "token_ids": ["tok_test_1"],
        }).get_json()
        gid = created["group"]["id"]
        resp = self.client.post(f"/api/token-groups/{gid}/rebind-pages")
        self.assertEqual(resp.status_code, 400)
        self.assertFalse(resp.get_json()["success"])

    def test_token_group_rebind_reports_missing_cached_pages(self):
        self.vault._save([{"id": "tok_1", "name": "Rep", "token": "EAAB_one", "status": "ACTIVE"}])
        self.pages.save_pages([{"page_id": "PAGE_A", "token_id": "tok_1"}])
        self.appmod.save_token_groups([{"id": "seed", "name": "Seed", "token_ids": []}])
        created = self.client.post("/api/token-groups", json={
            "name": "Pool", "token_ids": ["tok_1"], "page_source_token_id": "tok_1",
        }).get_json()
        gid = created["group"]["id"]
        self.pages.save_pages([])
        resp = self.client.post(f"/api/token-groups/{gid}/rebind-pages")
        self.assertEqual(resp.status_code, 409)
        self.assertFalse(resp.get_json()["success"])

    def test_manual_refresh_syncs_one_token_pages(self):
        token = self._seed_token()
        verify = {"status": "ACTIVE", "error": "", "pages": self._graph_pages(), "owner_name": "Owner"}
        with mock.patch.object(self.vault, "verify_token", return_value=verify) as full:
            resp = self.client.post(f"/api/tokens/{token['id']}/refresh-pages")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.get_json()["synced_pages"], 2)
        self.assertEqual(full.call_count, 1)
        self.assertEqual({p["token_id"] for p in self.pages.list_pages()}, {token["id"]})

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
    def test_update_binding_rejects_unverified_token_but_keeps_group_unchanged(self):
        self._seed_token()
        self.pages.save_pages([{"page_id": "PAGE_A", "page_name": "A", "group_ids": [], "group_name": "Chưa nhóm"}])
        self.pages.save_groups([{"id": "grp_1", "name": "BM 1", "page_ids": []}])

        resp = self.client.post("/api/pages/update_binding", json={
            "page_id": "PAGE_A", "group_id": "grp_1", "token_id": "tok_test_1",
        })
        self.assertEqual(resp.status_code, 409)
        self.assertFalse(resp.get_json()["success"])

        p = self.pages.list_pages()[0]
        self.assertNotEqual(p.get("token_id"), "tok_test_1")

    def test_update_binding_unknown_page_404(self):
        resp = self.client.post("/api/pages/update_binding", json={"page_id": "NOPE"})
        self.assertEqual(resp.status_code, 404)

    # -- token assignment -------------------------------------------------- #
    def test_single_token_assign_rejects_unverified_mapping(self):
        token = self._seed_token()
        self.pages.save_pages([{"page_id": "PAGE_A", "page_name": "A", "token_id": ""}])
        resp = self.client.post("/api/pages/assign_token", json={"page_id": "PAGE_A", "token_id": token["id"]})
        self.assertEqual(resp.status_code, 409)
        page = self.pages.list_pages()[0]
        self.assertNotEqual(page.get("token_id"), token["id"])

    def test_single_token_assign_unknown_page(self):
        token = self._seed_token()
        self.pages.save_pages([{"page_id": "PAGE_A", "page_name": "A"}])
        resp = self.client.post("/api/pages/assign_token", json={"page_id": "MISSING", "token_id": token["id"]})
        self.assertEqual(resp.status_code, 404)

    def test_single_token_assign_rejects_unknown_vault_token(self):
        self.pages.save_pages([{"page_id": "PAGE_A", "page_name": "A"}])
        resp = self.client.post("/api/pages/assign_token", json={"page_id": "PAGE_A", "token_id": "missing"})
        self.assertEqual(resp.status_code, 404)

    def test_batch_assign_round_robin_rejects_unverified_mappings(self):
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
        self.assertFalse(body["success"])
        self.assertEqual(resp.status_code, 409)
        self.assertEqual(len(body["blocked"]), 2)
        pages = {p["page_id"]: p for p in self.pages.list_pages()}
        self.assertFalse(any(p.get("token_id") for p in pages.values()))

    def test_batch_assign_single_token_to_many_rejects_unverified_mapping(self):
        token = self._seed_token()
        self.pages.save_pages([
            {"page_id": "PAGE_A"}, {"page_id": "PAGE_B"}, {"page_id": "PAGE_C"},
        ])
        resp = self.client.post("/api/pages/batch_assign_token", json={
            "token_id": token["id"], "page_ids": ["PAGE_A", "PAGE_C"],
        })
        self.assertEqual(resp.status_code, 409)
        pages = {p["page_id"]: p for p in self.pages.list_pages()}
        self.assertNotEqual(pages["PAGE_A"].get("token_id"), token["id"])
        self.assertNotEqual(pages["PAGE_C"].get("token_id"), token["id"])
        self.assertEqual(pages["PAGE_B"].get("token_id", ""), "")

    def test_batch_assign_requires_token_or_assignments(self):
        resp = self.client.post("/api/pages/batch_assign_token", json={"page_ids": ["PAGE_A"]})
        self.assertEqual(resp.status_code, 400)

    # -- token groups ------------------------------------------------------ #
    def test_token_group_create_and_read(self):
        # Seed a non-empty file so load_token_groups() does not inject its default group.
        self._seed_token()
        self.appmod.save_token_groups([{"id": "seed", "name": "Seed", "token_ids": []}])
        r = self.client.post("/api/token-groups", json={"name": "Pool 1", "token_ids": ["tok_test_1"]})
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.get_json()["success"])
        groups = self.client.get("/api/token-groups").get_json()["groups"]
        names = {g["name"]: g for g in groups}
        self.assertIn("Pool 1", names)
        self.assertEqual(names["Pool 1"]["token_ids"], ["tok_test_1"])

    def test_token_group_reuses_representative_page_set_without_graph_fetch(self):
        tokens = [
            {"id": "tok_1", "name": "Representative", "token": "EAAB_one", "status": "ACTIVE"},
            {"id": "tok_2", "name": "Pool member", "token": "EAAB_two", "status": "ACTIVE"},
        ]
        self.vault._save(tokens)
        self.pages.save_pages([
            {"page_id": "PAGE_A", "token_id": "tok_1"},
            {"page_id": "PAGE_B", "token_id": "tok_1"},
            {"page_id": "PAGE_OTHER", "token_id": "tok_other"},
        ])
        self.appmod.save_token_groups([{"id": "seed", "name": "Seed", "token_ids": []}])
        with mock.patch.object(self.vault, "verify_token") as full:
            r = self.client.post("/api/token-groups", json={
                "name": "Shared Page Pool",
                "token_ids": ["tok_1", "tok_2", "tok_2"],
                "page_source_token_id": "tok_1",
            })
        self.assertEqual(r.status_code, 200)
        self.assertEqual(full.call_count, 0)
        group = next(g for g in self.client.get("/api/token-groups").get_json()["groups"] if g["name"] == "Shared Page Pool")
        self.assertEqual(group["token_ids"], ["tok_1", "tok_2"])
        self.assertEqual(group["page_source_token_id"], "tok_1")
        self.assertEqual(group["page_ids"], ["PAGE_A", "PAGE_B"])

    def test_token_group_rebind_refreshes_cached_snapshot_without_graph_fetch(self):
        self.vault._save([{"id": "tok_1", "name": "Source", "token": "EAAB_one", "status": "ACTIVE"}])
        self.pages.save_pages([{"page_id": "PAGE_NEW", "token_id": "tok_1"}])
        self.appmod.save_token_groups([{
            "id": "pool_1", "name": "Pool", "token_ids": ["tok_1"],
            "page_source_token_id": "tok_1", "page_ids": ["PAGE_OLD"],
        }])
        with mock.patch.object(self.vault, "verify_token") as full, mock.patch.object(self.vault, "discover_pages") as discover:
            resp = self.client.post("/api/token-groups/pool_1/rebind-pages")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.get_json()["page_ids"], ["PAGE_NEW"])
        full.assert_not_called()
        discover.assert_not_called()

    def test_token_group_rebind_rejects_deleted_source_token(self):
        self.appmod.save_token_groups([{
            "id": "pool_1", "name": "Pool", "token_ids": [],
            "page_source_token_id": "missing", "page_ids": ["PAGE_OLD"],
        }])
        resp = self.client.post("/api/token-groups/pool_1/rebind-pages")
        self.assertEqual(resp.status_code, 404)
        self.assertEqual(self.appmod.load_token_groups()[0]["page_ids"], ["PAGE_OLD"])

    def test_token_group_requires_name(self):
        self.appmod.save_token_groups([{"id": "seed", "name": "Seed", "token_ids": []}])
        r = self.client.post("/api/token-groups", json={"name": "", "token_ids": []})
        self.assertEqual(r.status_code, 400)

    def test_token_group_delete(self):
        self.appmod.save_token_groups([{"id": "tgrp_1", "name": "Pool 1", "token_ids": []}])
        self.client.delete("/api/token-groups/tgrp_1")
        groups = self.client.get("/api/token-groups").get_json()["groups"]
        self.assertNotIn("tgrp_1", [g["id"] for g in groups])

    def test_fast_token_group_creates_distinct_manageable_groups(self):
        token = self._seed_token()
        self.appmod.save_token_groups([])
        first = self.client.post("/api/token-groups", json={"name": "Pool A", "token_ids": [token["id"]]}).get_json()
        second = self.client.post("/api/token-groups", json={"name": "Pool B", "token_ids": [token["id"]]}).get_json()
        self.assertNotEqual(first["group"]["id"], second["group"]["id"])
        groups = self.client.get("/api/token-groups").get_json()["groups"]
        self.assertEqual({g["name"] for g in groups}, {"Pool A", "Pool B"})

    def test_token_list_reports_current_page_binding_count(self):
        token = self._seed_token()
        self.pages.save_pages([{"page_id": "PAGE_A", "token_id": token["id"]}, {"page_id": "PAGE_B"}])
        listed = self.client.get("/api/tokens").get_json()["tokens"]
        self.assertEqual(listed[0]["pages_count"], 1)

    def test_page_list_reports_scheduled_and_published_without_stale_group(self):
        self.pages.save_pages([{"page_id": "PAGE_A", "group_ids": ["deleted"], "group_name": "BM 1", "total_posted": 0}])
        self.pages.save_groups([{"id": "group-live", "name": "Live Group", "page_ids": ["PAGE_A"]}])
        posts = [
            {"page_id": "PAGE_A", "status": "published"},
            {"page_id": "PAGE_A", "status": "scheduled"},
        ]
        with mock.patch.object(self.appmod, "load_posts", return_value=posts):
            response = self.client.get("/api/pages")
        page = response.get_json()["pages"][0]
        self.assertEqual(page["published_count"], 1)
        self.assertEqual(page["scheduled_count"], 1)
        self.assertEqual(page["group_name"], "Live Group")
        self.assertEqual(page["group_ids"], ["group-live"])

    def test_group_allocation_assigns_only_verified_one_page_one_token(self):
        token = {"id": "tok_1", "name": "T1", "token": "EAAB_one", "status": "ACTIVE"}
        self.vault._save([token])
        self.pages.sync_pages_from_token(token, [{"id": "PAGE_A", "name": "A", "access_token": "page-a"}])
        self.appmod.save_token_groups([{"id": "pool_1", "name": "Pool", "token_ids": ["tok_1"], "page_ids": ["PAGE_A"]}])
        resp = self.client.post("/api/pages/batch_assign_token", json={"token_group_id": "pool_1", "page_ids": ["PAGE_A"]})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.get_json()["count"], 1)
        self.assertEqual(self.pages.list_pages()[0]["token_id"], "tok_1")

    def test_31_tokens_balance_100_pages_as_three_or_four_each(self):
        from src.publisher.meta_preflight import preflight_pages
        tokens = [{"id": f"tok_{i}", "name": "Imported label", "owner_name": f"Autopost {i}",
                   "token": f"EAAB_fixture_{i}", "status": "ACTIVE"} for i in range(31)]
        self.vault._save(tokens)
        pages = []
        for index in range(100):
            page_id = f"PAGE_{index}"
            bindings = {token["id"]: {
                "token_id": token["id"], "token_name": "Imported label",
                "page_token": f"page_{index}_{token['id']}", "verified_page_id": page_id,
                "credential_fingerprint": self.pages.credential_fingerprint(token["token"]),
                "tasks": ["CREATE_CONTENT"], "status": "VERIFIED",
            } for token in tokens}
            pages.append({"page_id": page_id, "token_id": "old_deleted_id", "token_name": "Bm1",
                          "token_bindings": bindings, "group_ids": []})
        self.pages.save_pages(pages)
        self.appmod.save_token_groups([{"id": "new", "name": "NEW", "token_ids": [t["id"] for t in tokens],
                                        "page_ids": [p["page_id"] for p in pages]}])
        response = self.client.post("/api/pages/batch_assign_token", json={
            "token_group_id": "new", "max_pages_per_token": 3,
        })
        self.assertEqual(response.status_code, 200, response.get_json())
        body = response.get_json()
        self.assertEqual(body["count"], 100)
        self.assertEqual(body["requested_limit"], 3)
        self.assertEqual(body["effective_limit"], 4)
        self.assertEqual(collections.Counter(body["loads"].values()), {3: 24, 4: 7})
        assigned = self.pages.list_pages()
        self.assertEqual({p["token_name"] for p in assigned}, {t["owner_name"] for t in tokens})
        self.assertTrue(preflight_pages(assigned, self.vault, self.pages)["ok"])

    def test_group_allocation_respects_page_limit_without_partial_write(self):
        token = {"id": "tok_1", "name": "T1", "token": "EAAB_one", "status": "ACTIVE"}
        self.vault._save([token])
        self.pages.sync_pages_from_token(token, [
            {"id": "PAGE_A", "access_token": "page-a"},
            {"id": "PAGE_B", "access_token": "page-b"},
        ])
        before = self.pages.list_pages()
        response = self.client.post("/api/pages/batch_assign_token", json={
            "auto_verified": True, "max_pages_per_token": 1,
        })
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.get_json()["code"], "token_capacity")
        self.assertEqual(self.pages.list_pages(), before)

    def test_group_save_syncs_each_token_and_balances_verified_pages(self):
        tokens = [
            {"id": f"tok_{i}", "name": f"Token {i}", "token": f"EAAB_{i}", "status": "ACTIVE"}
            for i in range(3)
        ]
        self.vault._save(tokens)
        all_pages = [{"id": f"PAGE_{i}", "name": f"Page {i}", "access_token": f"page-{i}"} for i in range(10)]

        def refresh(token_id):
            token = next(t for t in tokens if t["id"] == token_id)
            return token, all_pages

        with mock.patch.object(self.vault, "refresh_token_pages", side_effect=refresh):
            created = self.client.post("/api/token-groups", json={
                "name": "Balanced", "token_ids": [t["id"] for t in tokens], "sync_pages": True,
            })
        self.assertEqual(created.status_code, 200)
        group = created.get_json()["group"]
        self.assertEqual(len(group["page_ids"]), 10)
        assigned = self.client.post("/api/pages/batch_assign_token", json={"token_group_id": group["id"]})
        self.assertEqual(assigned.status_code, 200)
        self.assertEqual(sorted(assigned.get_json()["loads"].values()), [3, 3, 4])
        self.assertEqual(assigned.get_json()["over_four"], {})

    def test_group_allocation_ignores_stale_binding_and_fails_closed(self):
        token = {"id": "tok_1", "name": "T1", "token": "fresh-token", "status": "ACTIVE"}
        self.vault._save([token])
        self.pages.save_pages([{
            "page_id": "PAGE_A", "page_name": "A", "token_id": "tok_1",
            "token_bindings": {"tok_1": {"verified_page_id": "PAGE_A", "status": "VERIFIED", "page_token": "old-page-token", "credential_fingerprint": "wrong"}},
        }])
        self.appmod.save_token_groups([{"id": "pool_1", "name": "Pool", "token_ids": ["tok_1"], "page_ids": ["PAGE_A"]}])
        resp = self.client.post("/api/pages/batch_assign_token", json={"token_group_id": "pool_1", "page_ids": ["PAGE_A"]})
        self.assertEqual(resp.status_code, 409)
        self.assertEqual(resp.get_json()["blocked"][0]["page_id"], "PAGE_A")

    def test_group_allocation_explains_unverified_page_mapping(self):
        token = {"id": "tok_1", "name": "T1", "token": "EAAB_one", "status": "ACTIVE"}
        self.vault._save([token])
        self.pages.save_pages([{"page_id": "PAGE_A", "page_name": "A"}])
        self.appmod.save_token_groups([{"id": "pool_1", "name": "Pool", "token_ids": ["tok_1"], "page_ids": ["PAGE_A"]}])
        resp = self.client.post("/api/pages/batch_assign_token", json={"token_group_id": "pool_1", "page_ids": ["PAGE_A"]})
        self.assertEqual(resp.status_code, 409)
        self.assertIn("verified", resp.get_json()["error"])
        self.assertEqual(resp.get_json()["blocked"][0]["page_id"], "PAGE_A")


if __name__ == "__main__":
    unittest.main()
