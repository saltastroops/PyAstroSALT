import copy
import io
import pathlib
from contextlib import contextmanager
from datetime import datetime
from typing import Any, Dict, Generator, List
from unittest.mock import patch
from urllib.parse import urljoin

import pytest
import responses
from responses import matchers

from saltastro.proposal import (
    SubmissionLogMessageType,
    SubmissionStatus,
    submission_progress,
    submit,
)
from saltastro.web import SALT_API_URL, HttpStatusError, login


def test_submitted_proposal_file_must_exist() -> None:
    """Test that the submitted proposal file must exist."""
    with pytest.raises(IOError) as excinfo:
        submit("thereisnofilehere")

    assert "exist" in str(excinfo.value)
    assert "thereisnofilehere" in str(excinfo.value)


def test_submitted_proposal_file_must_be_a_file(tmp_path: pathlib.Path) -> None:
    """Test that the submitted proposal file must not be a directory."""
    with pytest.raises(IOError) as excinfo:
        submit(tmp_path)

    assert "file" in str(excinfo.value)
    assert str(tmp_path) in str(excinfo)


@responses.activate
def test_submitted_proposal_raises_http_errors():
    """Test that submit raises an exception if there is an HTTP error."""
    rsp = responses.Response(
        method="POST", url=urljoin(SALT_API_URL, "/submissions/"), status=400
    )
    responses.add(rsp)

    with pytest.raises(HttpStatusError):
        submit(io.BytesIO(b"Some content"))


@responses.activate
def test_submit_works_correctly_for_memory_stream():
    """Test that submit works correctly for a proposal from an in-memory-stream."""
    rsp1 = responses.Response(
        method="POST",
        url=urljoin(SALT_API_URL, "/token/"),
        json={"access_token": "secret"},
    )
    responses.add(rsp1)

    rsp2 = responses.Response(
        method="POST",
        url=urljoin(SALT_API_URL, "/submissions/"),
        json={"submission_identifier": "submissionid"},
        match=[
            matchers.header_matcher({"Authorization": "Bearer secret"}),
            matchers.multipart_matcher(
                files={"proposal": ("proposal.zip", b"some content")},
                data={"proposal_code": "2022-1-SCI-042"},
            ),
        ],
    )
    responses.add(rsp2)

    login("john", "topsecret")
    proposal = io.BytesIO(b"some content")
    submission_identifier = submit(proposal, "2022-1-SCI-042")

    assert submission_identifier == "submissionid"


@responses.activate
def test_submit_works_correctly_for_real_file(tmp_path: pathlib.Path) -> None:
    """Test that submit works correctly for a proposal from a file."""
    rsp1 = responses.Response(
        method="POST",
        url=urljoin(SALT_API_URL, "/token/"),
        json={"access_token": "secret"},
    )
    responses.add(rsp1)

    rsp2 = responses.Response(
        method="POST",
        url=urljoin(SALT_API_URL, "/submissions/"),
        json={"submission_identifier": "submissionid"},
        match=[
            matchers.header_matcher({"Authorization": "Bearer secret"}),
            matchers.multipart_matcher(
                files={"proposal": ("proposal.zip", b"fake proposal zip")},
                data={"proposal_code": "2022-1-SCI-042"},
            ),
        ],
    )
    responses.add(rsp2)

    proposal = tmp_path / "proposal.zip"
    proposal.write_bytes(b"fake proposal zip")

    login("john", "topsecret")
    submission_identifier = submit(proposal, "2022-1-SCI-042")

    assert submission_identifier == "submissionid"


def _mock_submission_progress_data():
    dates = [
        "2022-05-04T16:08:16+00:00",
        "2022-05-04T16:08:18+00:00",
        "2022-05-04T16:08:22+00:00",
        "2022-05-04T16:08:25+00:00",
        "2022-05-04T16:08:30+00:00",
    ]
    raw_data: List[Dict[str, Any]] = [
        {
            "status": "In progress",
            "log_entries": [
                {
                    "entry_number": 1,
                    "logged_at": dates[0],
                    "message_type": "Info",
                    "message": "Message 1",
                },
                {
                    "entry_number": 2,
                    "logged_at": dates[1],
                    "message_type": "Warning",
                    "message": "Message 2",
                },
            ],
        },
        {
            "status": "In progress",
            "log_entries": [
                {
                    "entry_number": 3,
                    "logged_at": dates[2],
                    "message_type": "Info",
                    "message": "Message 3",
                },
            ],
        },
        {"status": "In progress", "log_entries": []},
        {
            "status": "Failed",
            "log_entries": [
                {
                    "entry_number": 4,
                    "logged_at": dates[3],
                    "message_type": "Info",
                    "message": "Message 3",
                },
                {
                    "entry_number": 5,
                    "logged_at": dates[4],
                    "message_type": "Error",
                    "message": "Message 5",
                },
            ],
        },
    ]
    expected_data = copy.deepcopy(raw_data)
    for d in expected_data:
        d["status"] = SubmissionStatus(d["status"])
        for log_entry in d["log_entries"]:
            log_entry["logged_at"] = datetime.fromisoformat(log_entry["logged_at"])
            log_entry["message_type"] = SubmissionLogMessageType(
                log_entry["message_type"]
            )

    return raw_data, expected_data


@pytest.mark.asyncio
async def test_submission_progress_works():
    """Test that the correct submission progress data is returned."""
    raw_data, expected_data = _mock_submission_progress_data()

    async def _mock_submission_progress_server_input(
        submission_identifier: str, from_entry_number: int = 1
    ) -> Generator[Any, None, None]:
        for r in raw_data:
            yield r

    with patch(
        "saltastro.proposal._submission_progress_server_input",
        _mock_submission_progress_server_input,
    ):
        # There should be no reconnection in this test, but we avoid waiting, just in
        # case things go pear-shaped and reconnection does happen.
        with patch("saltastro.proposal.TIME_BETWEEN_RECONNECTION_ATTEMPTS", 0):
            received_data = []
            async for r in submission_progress("abc"):
                received_data.append(r)

    assert received_data == expected_data


@pytest.mark.asyncio
async def test_submission_progress_reconnects():
    """Test that a reconnection happens if there is a problem."""
    raw_data, expected_data = _mock_submission_progress_data()

    # ignore empty log entry list, as we'll simulate reconnection
    raw_data = raw_data[:2] + raw_data[3:]
    expected_data = expected_data[:2] + expected_data[3:]

    async def _mock_submission_progress_server_input(
        submission_identifier: str, from_entry_number: int = 1
    ) -> Generator[Any, None, None]:
        # We call this function with the values 1 and 4 for from_entry_number. The
        # latter value implies that the first two items of raw_data must be ignored.
        for i, r in enumerate(raw_data if from_entry_number != 4 else raw_data[2:]):
            if from_entry_number == 1 and i == 2:
                raise Exception("Boom!")
            yield r

    with patch(
        "saltastro.proposal._submission_progress_server_input",
        _mock_submission_progress_server_input,
    ):
        with patch("saltastro.proposal.TIME_BETWEEN_RECONNECTION_ATTEMPTS", 0):
            received_data = []
            async for r in submission_progress("abc"):
                received_data.append(r)

    assert len(received_data) == len(expected_data)


@contextmanager
def _does_not_raise() -> Generator[Any, None, None]:
    yield


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "retries,expectation", [(6, _does_not_raise()), (7, pytest.raises(Exception))]
)
async def test_submission_progression_retries_max_retries_times(retries, expectation):
    """Test that there are max_retries attempts to reconnect if there is a problem."""
    counter_dict = {"counter": 0}

    async def _mock_submission_progress_server_input(
        submission_identifier: str, from_entry_number: int = 1
    ) -> Generator[Any, None, None]:
        # Keep track on how often this function has been called
        counter_dict["counter"] += 1

        # Fail retries - 1 times
        if counter_dict["counter"] < retries:
            raise Exception("There is a failure.")

        # Success!
        yield {
            "status": "Successful",
            "log_entries": [],
            "proposal_code": "2022-1-SCI-042",
        }

    with expectation:
        with patch(
            "saltastro.proposal._submission_progress_server_input",
            _mock_submission_progress_server_input,
        ):
            with patch("saltastro.proposal.TIME_BETWEEN_RECONNECTION_ATTEMPTS", 0):
                async for _ in submission_progress("abc", max_retries=5):
                    pass


@pytest.mark.asyncio
async def test_submission_progress_resets_num_of_retries():
    """Test that the number of retries is reset to 0 if data is returned."""
    counter_dict = {"counter": 0}
    max_retries = 3

    async def _mock_submission_progress_server_input(
        submission_identifier: str, from_entry_number: int = 1
    ) -> Generator[Any, None, None]:
        # Keep track on how often this function has been called
        counter_dict["counter"] += 1

        # Fail max_retries times
        if counter_dict["counter"] < max_retries:
            raise Exception("This is a failure.")
        elif counter_dict["counter"] == max_retries:
            # Finally! Data is returned!
            yield {
                "status": "In progress",
                "log_entries": [],
            }

            # But again we fail...
            raise Exception("This is a failure.")

        # ... and fail more often...
        if max_retries <= counter_dict["counter"] < 2 * max_retries:
            raise Exception("This is a failure.")
        else:
            # ... until finally we get some data again.
            yield {
                "status": "Successful",
                "log_entries": [],
                "proposal_code": "2022-1-SCI-042",
            }

    expected_data = [
        {"status": SubmissionStatus.IN_PROGRESS, "log_entries": []},
        {
            "status": SubmissionStatus.SUCCESSFUL,
            "log_entries": [],
            "proposal_code": "2022-1-SCI-042",
        },
    ]

    with patch(
        "saltastro.proposal._submission_progress_server_input",
        _mock_submission_progress_server_input,
    ):
        with patch("saltastro.proposal.TIME_BETWEEN_RECONNECTION_ATTEMPTS", 0):
            received_data = []
            async for p in submission_progress("abc", max_retries):
                received_data.append(p)

    assert received_data == expected_data
