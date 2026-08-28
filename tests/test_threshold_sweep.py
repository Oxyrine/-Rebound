import json
from pathlib import Path
from unittest.mock import patch
import pytest

from scripts import threshold_sweep

def test_threshold_sweep_report_generation(tmp_path):
    # Setup mock development_cases.json
    cases = [
        {
            "case_id": "test-dispute-1",
            "bucket": "DISPUTE_REFUND",
            "expected_outcome": "HARD_STOP",
            "razorpay_context": {"order_id": "order_1", "payment_id": "pay_1"},
            "customer_reply": "refund my money"
        },
        {
            "case_id": "test-benign-1",
            "bucket": "BENIGN",
            "expected_outcome": "RECOVERY_ELIGIBLE",
            "razorpay_context": {"order_id": "order_2", "payment_id": "pay_2"},
            "customer_reply": "will pay tomorrow"
        }
    ]
    
    # Setup mock dev_interpretations.json
    cache = {
        "test-dispute-1": {
            "customer_state": "dispute",
            "stop_signals": ["DISPUTE_OR_COMPLAINT_RAISED"],
            "confidence": 0.95,
            "evidence_refs": [],
            "requires_human_review": False,
            "suspected_injection": False
        },
        "test-benign-1": {
            "customer_state": "benign",
            "stop_signals": [],
            "confidence": 0.80,
            "evidence_refs": [],
            "requires_human_review": False,
            "suspected_injection": False
        }
    }

    mock_fixtures_dir = tmp_path / "fixtures"
    mock_fixtures_dir.mkdir()
    (mock_fixtures_dir / "development_cases.json").write_text(json.dumps(cases), encoding="utf-8")
    
    mock_cache_path = tmp_path / "dev_interpretations.json"
    mock_cache_path.write_text(json.dumps(cache), encoding="utf-8")
    
    mock_report_path = tmp_path / "threshold_sweep_report.md"
    
    with patch("scripts.threshold_sweep.FIXTURES_DIR", mock_fixtures_dir), \
         patch("scripts.threshold_sweep.CACHE_PATH", mock_cache_path), \
         patch("scripts.threshold_sweep.REPORT_PATH", mock_report_path):
             
        threshold_sweep.main()
        
        # Verify the report was written
        assert mock_report_path.exists()
        
        content = mock_report_path.read_text(encoding="utf-8")
        assert "confidence threshold sweep" in content
        
        # Check that it has the required sections
        assert "Automation rate" in content
        assert "Recall" in content
        assert "Precision" in content
        
        # Check that disclosures are printed
        assert "calibrated probabilities" in content
        assert "coarse" in content
