from multi_pc.posting_schedule import paced_offsets_by_token, posting_schedule_recommendation


def test_ten_lanes_spread_100_pages_over_about_150_minutes():
    rec = posting_schedule_recommendation(threads=10, pages=100, window_minutes=15)
    assert rec["seconds_between_lanes"] == 90.0
    assert rec["estimated_minutes"] == 148.5


def test_same_token_keeps_a_fifteen_minute_gap():
    offsets = paced_offsets_by_token(["a", "a", "b", "b"], global_seconds=90, token_seconds=900)
    assert offsets[1] - offsets[0] >= 900
    assert offsets[3] - offsets[2] >= 900
