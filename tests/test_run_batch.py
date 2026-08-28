import pytest
from unittest.mock import patch
from scripts.run_batch import main

def test_cli_seam_accepts_argv():
    """
    Proves that main(argv=...) can be called directly in tests without monkeypatching sys.argv.
    """
    with patch("scripts.run_batch.run") as mock_run, \
         patch("scripts.run_batch._load_cases") as mock_load, \
         patch("scripts.run_batch.verify_chain", return_value=(True, [])):
        
        mock_load.return_value = []
        
        # Call the CLI using our new testability seam
        main(["--interpreter=rules", "--execute-links"])
        
        assert mock_load.called
        assert mock_run.called
        
        # The execute_links flag should be passed down to run()
        _, kwargs = mock_run.call_args
        assert kwargs["execute_links"] is True
