"""demo.py is a thin readable wrapper over run_batch's decision path;
this just pins that it stays runnable and routes a known case the same
way the batch runner does."""

from scripts.demo import BY_ID, main, show
from src.rules_interpreter import interpret


def test_known_opt_out_routes_stop():
    assert show(BY_ID["RCV-011"], interpret) == "STOP"


def test_default_trio_runs_clean():
    assert main([]) == 0


def test_unknown_id_errors():
    assert main(["RCV-999"]) == 1
