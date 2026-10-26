"""The sifter run's API-side sequencing, and the batch.py split it relies on.

run_sifter_pipeline runs the `full` sifter job and the S-LDSC decision side by
side, then the global-enrichment job only when both came good. Every Batch, S3
and workflow_jobs seam is stubbed, so nothing here touches AWS or sleeps. The
failure semantics under test come from the spec: S-LDSC trouble never fails the
run; a failed `full` or global-enrichment job does.
"""
import asyncio
import inspect
import io
import json
from unittest.mock import ANY, AsyncMock, MagicMock, patch

import pytest
from botocore.exceptions import ClientError

from job_server import api, batch, database_utils, variant_sifter
from job_server.model import User

USERNAME = "alice"
DS = "orch_ds"
GUID = database_utils.get_dataset_hash(DS, USERNAME)
SLDSC_PATH = f"userdata/{USERNAME}/genetic/{DS}/sldsc/sldsc"
SLDSC_FILE = "tissue.output.tsv"
RAW_PATH = f"userdata/{USERNAME}/genetic/{DS}/raw"
GE = variant_sifter.GE_MODE

RUNNABLE = {"name": DS, "col_map": {"beta": "BETA", "n": "N"}}
NOT_RUNNABLE = {"name": DS, "col_map": {"beta": "BETA"}}  # no N column, no effective_n


def _job(status, log, exit_code=0):
    return {"status": status, "log": log, "container": {"exitCode": exit_code}}


def _rows(sldsc_status):
    """A workflow_jobs listing as the pipeline really sees it: its own
    variant-sifter row is always RUNNING, which must not read as S-LDSC."""
    return [{"method": variant_sifter.SIFTER_METHOD, "status": "RUNNING"},
            {"method": "sldsc", "status": sldsc_status}]


def _next(answers):
    """Pop the next canned answer; the last one repeats."""
    return answers.pop(0) if len(answers) > 1 else answers[0]


def _bound(real_fn, mock):
    call = mock.await_args
    return inspect.signature(real_fn).bind(*call.args, **call.kwargs).arguments


class Run:
    """One run_sifter_pipeline call with Batch, S3 and the DB stubbed.

    `exists` is what s3.results_exist answers on each call and `listings` what
    get_workflow_jobs_for_dataset answers; in both the last answer repeats.
    `sldsc` is the side effect of the S-LDSC submit_and_await_job.
    """

    def __init__(self, *, exists, metadata=RUNNABLE, listings=([],), full=None, ge=None,
                 sldsc=None, metadata_error=None, record_error=None):
        self.exists = list(exists)
        self.listings = list(listings)
        self.metadata = metadata
        self.metadata_error = metadata_error
        self.record_error = record_error
        self.sldsc = sldsc
        # A job outcome dict, or an exception for await_job to raise.
        self.jobs = {"full": full or _job("SUCCEEDED", "full log"),
                     GE: ge or _job("SUCCEEDED", "ge log")}
        self.events = []

    async def _await_job(self, job_config):
        mode = job_config["parameters"]["mode"]
        self.events.append(("start", mode))
        await asyncio.sleep(0)  # a real suspension: the caller must await it
        self.events.append(("end", mode))
        if isinstance(self.jobs[mode], Exception):
            raise self.jobs[mode]
        return self.jobs[mode]

    async def _record(self, *args, **kwargs):
        self.events.append(("record",))
        if self.record_error:
            raise self.record_error
        return "recorded"

    def _get_results(self, path, file):
        if self.metadata_error:
            raise self.metadata_error
        return {"Body": io.BytesIO(json.dumps(self.metadata).encode())}

    def run(self):
        # The real functions, taken before patching, name the mocked calls' arguments.
        self.real_submit, self.real_record = batch.submit_and_await_job, batch.record_job_end
        with patch("job_server.batch.await_job", new=AsyncMock(side_effect=self._await_job)) as self.await_job, \
             patch("job_server.batch.submit_and_await_job", new=AsyncMock(side_effect=self.sldsc)) as self.submit, \
             patch("job_server.batch.record_job_end", new=AsyncMock(side_effect=self._record)) as self.record, \
             patch("job_server.s3.results_exist", side_effect=lambda p, f: _next(self.exists)) as self.results_exist, \
             patch("job_server.s3.get_results", side_effect=self._get_results) as self.get_results, \
             patch("job_server.database_utils.get_workflow_jobs_for_dataset",
                   side_effect=lambda db, dataset_id: _next(self.listings)) as self.workflow_jobs, \
             patch("job_server.database_utils.log_job_start") as self.log_job_start, \
             patch("job_server.database_utils.log_job_end") as self.log_job_end, \
             patch("job_server.api.SLDSC_POLL_SECONDS", 0):
            # Bounded, so a poll loop that never ends fails the test instead of hanging it.
            asyncio.run(asyncio.wait_for(api.run_sifter_pipeline(User(username=USERNAME), DS, GUID), 5))
        return self

    @property
    def modes(self):
        """The sifter modes awaited, in order."""
        return [c.args[0]["parameters"]["mode"] for c in self.await_job.await_args_list]

    @property
    def record_call(self):
        """The arguments the run's end was recorded with (exactly one recording)."""
        assert self.record.await_count == 1
        return _bound(self.real_record, self.record)

    @property
    def recorded(self):
        return self.record_call["result"]

    @property
    def sldsc_call(self):
        return _bound(self.real_submit, self.submit)


# ---- run_sifter_pipeline -----------------------------------------------------

def test_existing_sldsc_results_are_reused():
    r = Run(exists=[True]).run()
    r.results_exist.assert_any_call(SLDSC_PATH, SLDSC_FILE)
    r.submit.assert_not_awaited()
    r.log_job_start.assert_not_called()
    r.get_results.assert_not_called()
    assert r.modes == ["full", GE]
    assert r.recorded["status"] == "SUCCEEDED"


def test_missing_results_run_sldsc_off_the_dataset_stream_then_index():
    r = Run(exists=[False, True], listings=[_rows("FAILED")]).run()
    r.get_results.assert_called_once_with(RAW_PATH, "metadata")
    r.log_job_start.assert_called_once_with(ANY, USERNAME, DS, "RUNNING sldsc")
    r.submit.assert_awaited_once()
    call = r.sldsc_call
    assert call["job_config"] == batch.job_config("sldsc", USERNAME, DS)
    assert (call["user"], call["dataset"], call["method"]) == (USERNAME, DS, "sldsc")
    # Its SUCCEEDED/FAILED would otherwise end the dataset's SSE stream early.
    assert call["job_queues"] == {} and call["job_queues"] is not api.job_queues
    assert r.modes == ["full", GE]
    assert r.recorded["status"] == "SUCCEEDED"


def test_unrunnable_upload_skips_sldsc_and_global_enrichment():
    r = Run(exists=[False], metadata=NOT_RUNNABLE).run()
    r.submit.assert_not_awaited()
    r.log_job_start.assert_not_called()
    assert r.modes == ["full"]
    assert r.recorded["status"] == "SUCCEEDED"
    assert variant_sifter.sldsc_skip_reason(NOT_RUNNABLE) in r.recorded["log"]


def test_running_sldsc_is_waited_on_not_resubmitted():
    r = Run(exists=[False, True],
            listings=[_rows("RUNNING"), _rows("RUNNING"), _rows("SUCCEEDED")]).run()
    r.submit.assert_not_awaited()
    r.log_job_start.assert_not_called()
    assert r.workflow_jobs.call_count == 3
    r.workflow_jobs.assert_called_with(ANY, GUID)
    assert r.modes == ["full", GE]
    assert r.recorded["status"] == "SUCCEEDED"


def test_running_sldsc_that_leaves_no_results_skips_global_enrichment():
    r = Run(exists=[False], listings=[_rows("RUNNING"), _rows("FAILED")]).run()
    r.submit.assert_not_awaited()
    assert r.modes == ["full"]
    assert r.recorded["status"] == "SUCCEEDED"


def test_sldsc_poll_interval_is_a_minute():
    assert api.SLDSC_POLL_SECONDS == 60


def test_sldsc_that_leaves_no_results_skips_global_enrichment():
    r = Run(exists=[False, False]).run()
    r.submit.assert_awaited_once()
    assert r.modes == ["full"]
    assert r.recorded["status"] == "SUCCEEDED"
    assert "global enrichment" in r.recorded["log"].lower()


def test_sldsc_past_the_wait_cap_is_marked_failed_and_the_run_succeeds():
    async def hang(*args, **kwargs):
        await asyncio.Event().wait()

    with patch("job_server.variant_sifter.SLDSC_WAIT_CAP_SECONDS", 0.05):
        r = Run(exists=[False], sldsc=hang).run()
    r.submit.assert_awaited_once()
    r.log_job_end.assert_called_once_with(ANY, USERNAME, DS, "sldsc FAILED", ANY)
    note = r.log_job_end.call_args.args[4]
    assert note and note in r.recorded["log"]
    assert r.modes == ["full"]
    assert r.recorded["status"] == "SUCCEEDED"


def test_sldsc_batch_error_ends_its_row_failed_and_the_run_succeeds():
    """A Batch error submitting or polling the S-LDSC this run started must end
    its `sldsc` row: left RUNNING, the next run would wait the full cap on it."""
    r = Run(exists=[False], sldsc=RuntimeError("submit_job throttled")).run()
    r.log_job_start.assert_called_once_with(ANY, USERNAME, DS, "RUNNING sldsc")
    r.submit.assert_awaited_once()
    r.log_job_end.assert_called_once_with(ANY, USERNAME, DS, "sldsc FAILED", ANY)
    assert "submit_job throttled" in r.log_job_end.call_args.args[4]
    assert r.modes == ["full"]
    assert r.recorded["status"] == "SUCCEEDED"
    assert "submit_job throttled" in r.recorded["log"]


def test_failed_full_job_fails_the_run_without_global_enrichment():
    full = _job("FAILED", "full broke", exit_code=1)
    r = Run(exists=[True], full=full).run()
    assert r.modes == ["full"]
    assert r.recorded["status"] == "FAILED"
    assert r.recorded["container"] == full["container"]
    assert "full broke" in r.recorded["log"]


def test_failed_full_job_is_recorded_without_waiting_for_sldsc():
    """Only global enrichment needs the S-LDSC outcome. A failed `full` job must
    not read RUNNING (Run disabled, credible-set uploads blocked) for the hours a
    first-run S-LDSC can take."""
    full = _job("FAILED", "full broke", exit_code=1)
    r = Run(exists=[False, True], full=full)

    async def sldsc(*args, **kwargs):  # still running when the full job fails
        for _ in range(5):
            await asyncio.sleep(0)
        r.events.append(("end", "sldsc"))

    r.sldsc = sldsc
    r.run()
    assert r.record.await_count == 1
    assert r.recorded["status"] == "FAILED"
    assert r.recorded["container"] == full["container"]
    assert r.modes == ["full"]
    # Recorded before S-LDSC finished, and S-LDSC was not cancelled: it ran to
    # its own end (it logged `RUNNING sldsc`, so only its poller can end that row).
    r.submit.assert_awaited_once()
    assert r.events.index(("record",)) < r.events.index(("end", "sldsc"))


def test_failed_global_enrichment_job_fails_the_run():
    ge = _job("FAILED", "ge broke", exit_code=1)
    r = Run(exists=[True], ge=ge).run()
    assert r.modes == ["full", GE]
    assert r.recorded["status"] == "FAILED"
    assert r.recorded["container"] == ge["container"]
    assert "full log" in r.recorded["log"] and "ge broke" in r.recorded["log"]


def test_end_is_recorded_once_and_only_after_global_enrichment_finished():
    r = Run(exists=[True]).run()
    assert r.record.await_count == 1
    assert r.events[-1] == ("record",)
    assert r.events.index(("end", GE)) < r.events.index(("record",))
    call = r.record_call
    assert (call["user"], call["dataset"], call["method"]) == (USERNAME, DS, variant_sifter.SIFTER_METHOD)
    assert call["job_queues"] is api.job_queues
    log = call["result"]["log"]
    assert log.index("full log") < log.index("ge log")


def test_full_job_raising_records_one_failure_and_leaves_sldsc_running():
    """A Batch API error is not a FAILED job, but it must still end the run:
    a variant-sifter row left RUNNING blocks credible-set indexing for good."""
    r = Run(exists=[False, True], full=RuntimeError("describe_jobs throttled"))

    async def sldsc(*args, **kwargs):  # still running when the full job blows up
        for _ in range(5):
            await asyncio.sleep(0)
        r.events.append(("end", "sldsc"))

    r.sldsc = sldsc
    r.run()
    assert r.record.await_count == 1
    assert r.recorded["status"] == "FAILED"
    assert "describe_jobs throttled" in r.recorded["log"]
    assert r.recorded["container"] == {}
    assert r.modes == ["full"]
    # S-LDSC had logged `RUNNING sldsc`: cancelling it would strand that row, so
    # it runs to its end, and the failure is recorded without waiting for it.
    r.submit.assert_awaited_once()
    assert r.events.index(("record",)) < r.events.index(("end", "sldsc"))


def test_global_enrichment_job_raising_records_one_failure():
    err = ClientError({"Error": {"Code": "500", "Message": "logs unavailable"}}, "GetLogEvents")
    r = Run(exists=[True], ge=err)
    r.run()
    assert r.record.await_count == 1
    assert r.recorded["status"] == "FAILED"
    assert "logs unavailable" in r.recorded["log"]
    assert "full log" in r.recorded["log"]
    assert r.recorded["container"] == {}
    assert r.modes == ["full", GE]


def test_a_failing_record_is_not_retried():
    r = Run(exists=[True], record_error=RuntimeError("db down"))
    with pytest.raises(RuntimeError, match="db down"):
        r.run()
    assert r.record.await_count == 1


def test_error_deciding_sldsc_means_not_ready_not_failed():
    err = ClientError({"Error": {"Code": "500", "Message": "boom"}}, "GetObject")
    r = Run(exists=[False], metadata_error=err).run()
    r.submit.assert_not_awaited()
    assert r.modes == ["full"]
    assert r.recorded["status"] == "SUCCEEDED"
    assert "boom" in r.recorded["log"]


# ---- batch.py: submit_and_await_job split into await_job + record_job_end ----

def _batch_client(*statuses):
    """One mock for both the batch and the logs boto3 clients."""
    client = MagicMock()
    client.submit_job.return_value = {"jobId": "job-1"}
    client.describe_jobs.side_effect = [
        {"jobs": [{"status": s, "container": {"logStreamName": "stream", "exitCode": 0}}]}
        for s in statuses]
    client.get_log_events.return_value = {"events": [{"message": "line 1"}, {"message": "line 2"}]}
    return client


def test_await_job_returns_the_outcome_without_db_writes():
    client = _batch_client("RUNNING", "SUCCEEDED")
    with patch("job_server.batch.boto3.client", return_value=client), \
         patch("job_server.batch.asyncio.sleep", new=AsyncMock()) as sleep, \
         patch("job_server.database_utils.log_job_end") as log_job_end:
        result = asyncio.run(batch.await_job({"jobName": "j", "jobQueue": "q"}))
    assert result == {"status": "SUCCEEDED", "log": "line 1\nline 2",
                      "container": {"logStreamName": "stream", "exitCode": 0}}
    client.submit_job.assert_called_once_with(jobName="j", jobQueue="q")
    sleep.assert_awaited_once_with(60)
    log_job_end.assert_not_called()


def test_submit_and_await_job_still_records_the_end_status():
    client = _batch_client("SUCCEEDED")
    key = database_utils.get_dataset_hash("ds", "bob")

    async def go():
        queues = {key: asyncio.Queue()}
        await batch.submit_and_await_job({"jobName": "j"}, "bob", "ds", "sldsc", queues, "")
        return queues[key].get_nowait()

    with patch("job_server.batch.boto3.client", return_value=client), \
         patch("job_server.database_utils.log_job_end") as log_job_end:
        message = asyncio.run(go())
    log_job_end.assert_called_once_with(ANY, "bob", "ds", "sldsc SUCCEEDED", "line 1\nline 2", prefix="")
    assert message == {"status": "sldsc SUCCEEDED", "dataset": "ds", "method": "sldsc"}


def test_record_job_end_returns_the_status_and_appends_extra_log():
    result = {"status": "FAILED", "log": "out", "container": {"exitCode": 11}}
    with patch("job_server.database_utils.log_job_end") as log_job_end:
        status = asyncio.run(batch.record_job_end("bob", "ds", "falcon", result, {}, extra_log="note"))
    assert status == "falcon FAILED" + batch.failure_detail("falcon", {"exitCode": 11})
    args = log_job_end.call_args.args
    assert args[3] == status
    assert args[4].index("out") < args[4].index("note")
