import json
import tempfile
import time
from pathlib import Path
from unittest import mock

import pytest


def test_meta_schedule_window_is_fail_closed():
    from multi_pc.meta_scheduling import MetaScheduleTimeError, parse_meta_schedule_time

    now = 1_800_000_000
    with pytest.raises(MetaScheduleTimeError) as too_soon:
        parse_meta_schedule_time(now + 600, now_ts=now)
    assert too_soon.value.code == "meta_schedule_too_soon"
    with pytest.raises(MetaScheduleTimeError) as too_far:
        parse_meta_schedule_time(now + 29 * 86400 + 1, now_ts=now)
    assert too_far.value.code == "meta_schedule_too_far"
    assert parse_meta_schedule_time(now + 601, now_ts=now) == now + 601


def test_profile_fallback_is_stable_and_appends_url_once():
    from src.first_comment_profiles import builtin_profiles, profile_first_comment

    store = {"profiles": builtin_profiles(), "default_profile_id": "builtin_sports"}
    url = "https://example.test/story"
    first = profile_first_comment("Fixture", url, store=store)
    assert first == profile_first_comment("Fixture", url, store=store)
    assert first.count(url) == 1


def test_token_reimport_preserves_id_and_generates_unique_new_ids():
    from src.publisher.token_vault import TokenVault

    with tempfile.TemporaryDirectory() as folder:
        vault = TokenVault(Path(folder))
        with mock.patch.object(vault, "verify_token", return_value={"status": "ACTIVE", "pages": [], "owner_name": "Fixture"}):
            first, _ = vault.add_token("Fixture", "token-a", discover_pages=True)
            second, _ = vault.add_token("Fixture", "token-a", discover_pages=True)
            third, _ = vault.add_token("Fixture 2", "token-b", discover_pages=True)
        assert first["id"] == second["id"]
        assert first["id"] != third["id"]
        assert len({item["id"] for item in vault.list_tokens(mask=False)}) == 2
