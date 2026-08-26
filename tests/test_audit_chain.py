import json

from src.audit_log import GENESIS_PREV_HASH, AuditLog, _hash, verify_chain


def _read_lines(path):
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def _write_lines(path, records):
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        for rec in records:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")


def test_clean_chain_verifies(tmp_path):
    path = tmp_path / "audit.jsonl"
    log = AuditLog(path)
    for i in range(5):
        log.append(f"RCV-{i:03d}", "POLICY_DECISION", {"i": i})

    ok, problems = verify_chain(path)
    assert ok is True
    assert problems == []


def test_mutated_payload_detected(tmp_path):
    path = tmp_path / "audit.jsonl"
    log = AuditLog(path)
    for i in range(5):
        log.append(f"RCV-{i:03d}", "POLICY_DECISION", {"i": i})

    records = _read_lines(path)
    records[2]["payload"] = {"i": 999}
    _write_lines(path, records)

    ok, problems = verify_chain(path)
    assert ok is False
    assert any("seq 2" in p for p in problems)


def test_deleted_record_detected(tmp_path):
    path = tmp_path / "audit.jsonl"
    log = AuditLog(path)
    for i in range(5):
        log.append(f"RCV-{i:03d}", "POLICY_DECISION", {"i": i})

    records = _read_lines(path)
    del records[2]
    _write_lines(path, records)

    ok, problems = verify_chain(path)
    assert ok is False


def test_reordered_records_detected(tmp_path):
    path = tmp_path / "audit.jsonl"
    log = AuditLog(path)
    for i in range(5):
        log.append(f"RCV-{i:03d}", "POLICY_DECISION", {"i": i})

    records = _read_lines(path)
    records[1], records[2] = records[2], records[1]
    _write_lines(path, records)

    ok, problems = verify_chain(path)
    assert ok is False


def test_extra_top_level_field_detected(tmp_path):
    path = tmp_path / "audit.jsonl"
    log = AuditLog(path)
    for i in range(3):
        log.append(f"RCV-{i:03d}", "POLICY_DECISION", {"i": i})

    records = _read_lines(path)
    records[1]["approved_by"] = "ops"  # entry_hash left stale, doesn't cover this field
    _write_lines(path, records)

    ok, problems = verify_chain(path)
    assert ok is False
    assert any("seq 1" in p for p in problems)


def test_partial_last_line_reported_not_raised(tmp_path):
    path = tmp_path / "audit.jsonl"
    log = AuditLog(path)
    for i in range(3):
        log.append(f"RCV-{i:03d}", "POLICY_DECISION", {"i": i})

    with open(path, "a", encoding="utf-8", newline="\n") as f:
        f.write('{"seq": 3, "case_id": "RCV-003", "payload": {truncated')

    ok, problems = verify_chain(path)
    assert ok is False
    assert any("line 3" in p for p in problems)


def test_altered_genesis_prev_hash_detected(tmp_path):
    path = tmp_path / "audit.jsonl"
    log = AuditLog(path)
    for i in range(3):
        log.append(f"RCV-{i:03d}", "POLICY_DECISION", {"i": i})

    records = _read_lines(path)
    assert records[0]["prev_hash"] == GENESIS_PREV_HASH
    records[0]["prev_hash"] = "1" * 64
    _write_lines(path, records)

    ok, problems = verify_chain(path)
    assert ok is False
    assert any("seq 0" in p for p in problems)


def test_empty_file_verifies_vacuously(tmp_path):
    path = tmp_path / "audit.jsonl"
    ok, problems = verify_chain(path)
    assert ok is True
    assert problems == []


def test_known_input_produces_known_hash():
    # Pins sort_keys, separators, ensure_ascii=False, UTF-8, float repr, and
    # JSON null/bool spelling together. If canonicalization ever drifts,
    # this fails loudly instead of every historical chain silently
    # invalidating.
    record = {
        "seq": 0,
        "timestamp": "2026-08-27T10:00:00+05:30",
        "case_id": "RCV-004",
        "event_type": "POLICY_DECISION",
        "payload": {
            "customer_reply": "இது தப்பான சார்ஜ்",
            "confidence": 0.91,
            "note": None,
            "flagged": True,
            "nested": {"z": 2, "a": 1},
        },
        "prev_hash": GENESIS_PREV_HASH,
    }
    assert _hash(record) == "992905753566cfe0eb8937fea5349d0739e4c47f9be549fdcf958cebc891b891"


def test_suffix_rewrite_is_not_detectable(tmp_path):
    # Documents the ceiling: no key, no external anchor, so a suffix can be
    # rewritten with recomputed hashes and will verify clean. This is the
    # honest answer to "what stops me regenerating the file?" -- nothing.
    path = tmp_path / "audit.jsonl"
    log = AuditLog(path)
    for i in range(5):
        log.append(f"RCV-{i:03d}", "POLICY_DECISION", {"i": i})

    records = _read_lines(path)
    prev_hash = records[2]["entry_hash"]
    for i in (3, 4):
        rec = {
            "seq": i,
            "timestamp": records[i]["timestamp"],
            "case_id": records[i]["case_id"],
            "event_type": "POLICY_DECISION",
            "payload": {"rewritten": True},
            "prev_hash": prev_hash,
        }
        rec["entry_hash"] = _hash(rec)
        records[i] = rec
        prev_hash = rec["entry_hash"]
    _write_lines(path, records)

    ok, problems = verify_chain(path)
    assert ok is True
    assert problems == []
