from xxcli import feedback


def test_log_signal_appends(tmp_path, monkeypatch):
    monkeypatch.setattr(feedback, "FEEDBACK_FILE", tmp_path / "feedback.jsonl")
    monkeypatch.setattr(feedback, "PREFERENCE_FILE", tmp_path / "preference_rules.json")
    monkeypatch.setattr(feedback, "CONFIG_DIR", tmp_path)

    feedback.log_signal("keep", "123", 8, "adopt", "run-1", "~/Code/xxcli")
    assert feedback.FEEDBACK_FILE.exists()
    assert feedback.load_recent_signals(limit=1)[0]["tweet_id"] == "123"


def test_get_signal_count_counts_explicit_only(tmp_path, monkeypatch):
    monkeypatch.setattr(feedback, "FEEDBACK_FILE", tmp_path / "feedback.jsonl")
    monkeypatch.setattr(feedback, "PREFERENCE_FILE", tmp_path / "preference_rules.json")
    monkeypatch.setattr(feedback, "CONFIG_DIR", tmp_path)

    feedback.log_signal("keep", "123", 8, "adopt", "run-1", "~/Code/xxcli")
    feedback.log_signal("accepted_digest", None, None, None, "run-1", "~/Code/xxcli", items_shown=["123"])
    assert feedback.get_signal_count() == 1


def test_corrupt_or_missing_feedback_file_is_handled(tmp_path, monkeypatch):
    monkeypatch.setattr(feedback, "FEEDBACK_FILE", tmp_path / "feedback.jsonl")
    monkeypatch.setattr(feedback, "PREFERENCE_FILE", tmp_path / "preference_rules.json")
    monkeypatch.setattr(feedback, "CONFIG_DIR", tmp_path)

    assert feedback.load_recent_signals() == []
    feedback.FEEDBACK_FILE.write_text("{bad json}\n", encoding="utf-8")
    assert feedback.load_recent_signals() == []
