"""FALCON dispatches to its own Batch job, not the shared methods image."""
from job_server.batch import (
    FALCON_EXIT_MEANINGS,
    failure_detail,
    job_config,
)
from job_server.model import AnalysisMethod


def test_falcon_is_a_selectable_analysis_method():
    assert AnalysisMethod.falcon.value == "falcon"


def test_falcon_goes_to_its_own_queue_and_job_definition():
    cfg = job_config("falcon", "alice", "T2D_EUR")
    assert cfg["jobQueue"] == "falcon-queue"
    assert cfg["jobDefinition"] == "falcon-rs-dataset-job"


def test_falcon_passes_username_and_dataset_but_no_method_selector():
    # Its entrypoint takes --username/--dataset directly; a stray `method`
    # parameter would be substituted into a command that has no slot for it.
    cfg = job_config("falcon", "alice", "T2D_EUR")
    assert cfg["parameters"] == {"username": "alice", "dataset": "T2D_EUR"}


def test_other_methods_still_go_to_the_shared_image():
    for method in ("sldsc", "magma", "pigean", "annot-sldsc"):
        cfg = job_config(method, "alice", "T2D_EUR")
        assert cfg["jobQueue"] == "sldsc-methods-job-queue"
        assert cfg["jobDefinition"] == "dig-sldsc-methods"
        assert cfg["parameters"]["method"] == method


def test_shared_methods_keep_their_exact_previous_shape():
    """Guard against the refactor having changed the existing methods' calls."""
    cfg = job_config("sldsc", "bob", "ds1")
    assert cfg == {
        "jobName": "dig-sldsc-methods",
        "jobQueue": "sldsc-methods-job-queue",
        "jobDefinition": "dig-sldsc-methods",
        "parameters": {"username": "bob", "dataset": "ds1", "method": "sldsc"},
    }


def test_a_declined_dataset_reads_differently_from_a_crash():
    unsupported = failure_detail("falcon", {"exitCode": 10})
    no_variants = failure_detail("falcon", {"exitCode": 11})
    crash = failure_detail("falcon", {"exitCode": 1})
    assert "not supported" in unsupported
    assert "no variants" in no_variants
    assert crash == ""
    assert unsupported != no_variants


def test_failure_detail_is_falcon_only_and_tolerates_a_missing_code():
    assert failure_detail("sldsc", {"exitCode": 10}) == ""
    assert failure_detail("falcon", {}) == ""


def test_contract_codes_avoid_argparse_usage_exit():
    # argparse exits 2 on a bad argument; reusing it would report a harness bug
    # as "this dataset is unsupported".
    assert 2 not in FALCON_EXIT_MEANINGS
