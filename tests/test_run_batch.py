import pytest
from unittest.mock import patch
from scripts.run_batch import main

def test_cli_seam_accepts_argv(tmp_path):
    """
    Proves that main(argv=...) can be called directly in tests without monkeypatching sys.argv.
    """
    log_path = tmp_path / "test_audit.jsonl"
    with patch("scripts.run_batch.run") as mock_run, \
         patch("scripts.run_batch._load_cases") as mock_load, \
         patch("scripts.run_batch.verify_chain", return_value=(True, [])):
        
        mock_load.return_value = []
        
        # Call the CLI using our new testability seam
        main(["--interpreter=rules", "--execute-links", "--audit-path", str(log_path), "--first-run"])
        
        assert mock_load.called
        assert mock_run.called
        
        # The execute_links flag should be passed down to run()
        _, kwargs = mock_run.call_args
        assert kwargs["execute_links"] is True


def test_execute_links_requires_audit_path(capsys):
    with pytest.raises(SystemExit):
        main(['--interpreter=rules', '--execute-links'])
    out, err = capsys.readouterr()
    assert '--audit-path is required when --execute-links or --reconcile-only is used' in err

def test_first_run_missing_when_audit_file_missing(tmp_path, capsys):
    log_path = tmp_path / 'new_log.jsonl'
    with pytest.raises(SystemExit):
        main(['--interpreter=rules', '--audit-path', str(log_path)])
    out, err = capsys.readouterr()
    assert 'does not exist. Pass --first-run' in err

def test_first_run_present_when_audit_file_exists(tmp_path, capsys):
    log_path = tmp_path / 'existing_log.jsonl'
    log_path.write_text('')
    with pytest.raises(SystemExit):
        main(['--interpreter=rules', '--audit-path', str(log_path), '--first-run'])
    out, err = capsys.readouterr()
    assert 'already exists. Omit the flag to append' in err

@patch('scripts.run_batch.run')
@patch('scripts.run_batch._load_cases')
@patch('scripts.run_batch.verify_chain', return_value=(True, []))
def test_first_run_present_when_audit_file_missing(mock_verify, mock_load, mock_run, tmp_path):
    mock_load.return_value = []
    log_path = tmp_path / 'new_log.jsonl'
    # Should not raise SystemExit
    main(['--interpreter=rules', '--audit-path', str(log_path), '--first-run'])
    assert mock_run.called

@patch('scripts.run_batch.run')
@patch('scripts.run_batch._load_cases')
@patch('scripts.run_batch.verify_chain', return_value=(True, []))
def test_first_run_missing_when_audit_file_exists(mock_verify, mock_load, mock_run, tmp_path):
    mock_load.return_value = []
    log_path = tmp_path / 'existing_log.jsonl'
    log_path.write_text('')
    # Should not raise SystemExit
    main(['--interpreter=rules', '--audit-path', str(log_path)])
    assert mock_run.called

import json

@patch('scripts.run_batch.reconcile_created_links')
@patch('scripts.run_batch.AuditLog')
@patch('scripts.run_batch.RazorpayClient')
def test_reconcile_only_updates_evidence(mock_client, mock_auditlog, mock_reconcile, tmp_path):
    mock_reconcile.return_value = [{'case_id': 'c1', 'status': 'paid'}]
    
    evidence_dir = tmp_path / 'evidence'
    evidence_dir.mkdir()
    evidence_file = evidence_dir / 'run_results_rules_dev.json'
    evidence_file.write_text('{"c1": {"link_completed": false}, "c2": {"link_completed": false}}')
    
    audit_log_path = tmp_path / 'some_log.jsonl'
    audit_log_path.touch()
    
    with patch('scripts.run_batch.Path') as MockPath:
        def side_effect(path_str):
            if str(path_str) == 'evidence':
                return evidence_dir
            from pathlib import Path
            return Path(path_str)
        MockPath.side_effect = side_effect
        
        main(['--interpreter=rules', '--reconcile-only', '--audit-path', str(audit_log_path)])
        
    updated = json.loads(evidence_file.read_text())
    assert updated['c1']['link_completed'] is True
    assert updated['c2']['link_completed'] is False
