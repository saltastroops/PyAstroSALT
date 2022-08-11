import copy
import io
import pathlib
import zipfile
from datetime import datetime
from typing import Any, Dict, Generator, List, Tuple
from unittest.mock import patch

import pytest
import responses
from responses import matchers

from pyastrosalt.proposal import (
    SubmissionLogMessageType,
    SubmissionStatus,
    download_zip,
    submission_progress,
    submit,
)
from pyastrosalt.web import api_url, HttpStatusError
from tests.conftest import does_not_raise, login


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
def test_submitted_proposal_raises_http_errors() -> None:
    """Test that submit raises an exception if there is an HTTP error."""
    rsp = responses.Response(
        method="POST", url=api_url("/submissions/"), status=400
    )
    responses.add(rsp)

    with pytest.raises(HttpStatusError):
        submit(io.BytesIO(b"Some content"))


@responses.activate
def test_submit_works_correctly_for_memory_stream() -> None:
    """Test that submit works correctly for a proposal from an in-memory-stream."""
    rsp = responses.Response(
        method="POST",
        url=api_url("/submissions/"),
        json={"submission_identifier": "submissionid"},
        match=[
            matchers.header_matcher({"Authorization": "Bearer secret"}),
            matchers.multipart_matcher(
                files={"proposal": ("proposal.zip", b"some content")},
                data={"proposal_code": "2022-1-SCI-042"},
            ),
        ],
    )
    responses.add(rsp)

    login("secret")
    proposal = io.BytesIO(b"some content")
    submission_identifier = submit(proposal, "2022-1-SCI-042")

    assert submission_identifier == "submissionid"


@responses.activate
def test_submit_works_correctly_for_real_file(tmp_path: pathlib.Path) -> None:
    """Test that submit works correctly for a proposal from a file."""
    rsp = responses.Response(
        method="POST",
        url=api_url("/submissions/"),
        json={"submission_identifier": "submissionid"},
        match=[
            matchers.header_matcher({"Authorization": "Bearer secret"}),
            matchers.multipart_matcher(
                files={"proposal": ("proposal.zip", b"fake proposal zip")},
                data={"proposal_code": "2022-1-SCI-042"},
            ),
        ],
    )
    responses.add(rsp)

    proposal = tmp_path / "proposal.zip"
    proposal.write_bytes(b"fake proposal zip")

    login("secret")
    submission_identifier = submit(proposal, "2022-1-SCI-042")

    assert submission_identifier == "submissionid"


def _mock_submission_progress_data() -> Tuple[List[Any], List[Any]]:
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
async def test_submission_progress_works() -> None:
    """Test that the correct submission progress data is returned."""
    raw_data, expected_data = _mock_submission_progress_data()

    async def _mock_submission_progress_server_input(
        submission_identifier: str, from_entry_number: int = 1
    ) -> Generator[Any, None, None]:
        for r in raw_data:
            yield r

    with patch(
        "pyastrosalt.proposal._submission_progress_server_input",
        _mock_submission_progress_server_input,
    ):
        # There should be no reconnection in this test, but we avoid waiting, just in
        # case things go pear-shaped and reconnection does happen.
        with patch("pyastrosalt.proposal.TIME_BETWEEN_RECONNECTION_ATTEMPTS", 0):
            received_data = []
            async for r in submission_progress("abc"):
                received_data.append(r)

    assert received_data == expected_data


@pytest.mark.asyncio
async def test_submission_progress_reconnects() -> None:
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
        "pyastrosalt.proposal._submission_progress_server_input",
        _mock_submission_progress_server_input,
    ):
        with patch("pyastrosalt.proposal.TIME_BETWEEN_RECONNECTION_ATTEMPTS", 0):
            received_data = []
            async for r in submission_progress("abc"):
                received_data.append(r)

    assert len(received_data) == len(expected_data)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "retries,expectation", [(6, does_not_raise()), (7, pytest.raises(Exception))]
)
async def test_submission_progression_retries_max_retries_times(
    retries, expectation
) -> None:
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
            "pyastrosalt.proposal._submission_progress_server_input",
            _mock_submission_progress_server_input,
        ):
            with patch("pyastrosalt.proposal.TIME_BETWEEN_RECONNECTION_ATTEMPTS", 0):
                async for _ in submission_progress("abc", max_retries=5):
                    pass


@pytest.mark.asyncio
async def test_submission_progress_resets_num_of_retries() -> None:
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
        "pyastrosalt.proposal._submission_progress_server_input",
        _mock_submission_progress_server_input,
    ):
        with patch("pyastrosalt.proposal.TIME_BETWEEN_RECONNECTION_ATTEMPTS", 0):
            received_data = []
            async for p in submission_progress("abc", max_retries):
                received_data.append(p)

    assert received_data == expected_data


def _proposal_xml(proposal_zip: bytes) -> bytes:
    with zipfile.ZipFile(io.BytesIO(proposal_zip), "r") as zip_in:
        return zip_in.read("Proposal.xml")


@responses.activate
def test_download_zip_into_file(tmp_path: pathlib.Path) -> None:
    """Test downloading a proposal zip file into a file."""
    proposal_code = "2022-1-SCI-005"
    rsp = responses.Response(
        method="GET",
        url=api_url(f"/proposals/{proposal_code}.zip"),
        content_type="application/zip",
        body=_fake_zip_file(proposal_code, "This is a proposal."),
        match=[
            matchers.header_matcher({"Authorization": "Bearer secret"}),
        ],
    )
    responses.add(rsp)

    login("secret")
    proposal_file = tmp_path / f"{proposal_code}.zip"
    download_zip(proposal_code, proposal_file)

    downloaded_content = proposal_file.read_bytes()
    assert b"This is a proposal." in _proposal_xml(downloaded_content)


def _fake_zip_file(proposal_code: str, text: str) -> bytes:
    xml = f"""\
<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Proposal xmlns="http://www.salt.ac.za/PIPT/Proposal/Phase2/4.8" code="{proposal_code}">
    {text}
</Proposal>
    """
    proposal_content = io.BytesIO()
    with zipfile.ZipFile(proposal_content, "w") as z:
        z.writestr("Proposal.xml", xml)

    return proposal_content.getvalue()


@responses.activate
def test_download_zip_into_in_memory_stream() -> None:
    """Test downloading a proposal zip file into an in-memory stream."""
    proposal_code = "2022-1-SCI-005"
    rsp = responses.Response(
        method="GET",
        url=api_url(f"/proposals/{proposal_code}.zip"),
        content_type="application/zip",
        body=_fake_zip_file(proposal_code, "This is a proposal."),
        match=[
            matchers.header_matcher({"Authorization": "Bearer secret"}),
        ],
    )
    responses.add(rsp)

    login("secret")
    out = io.BytesIO()
    download_zip(proposal_code, out)

    downloaded_content = out.getvalue()
    assert b"This is a proposal." in _proposal_xml(downloaded_content)


@responses.activate
@pytest.mark.parametrize("status_code", [400, 401, 403, 404, 500])
def test_download_zip_raises_http_error(status_code) -> None:
    """Test downloading a proposal zip file into an in-memory stream."""
    proposal_code = "idontexist"
    rsp = responses.Response(
        method="GET",
        url=api_url(f"/proposals/{proposal_code}.zip"),
        status=status_code,
        content_type="application/zip",
        body=b"Something is wrong.",
        match=[
            matchers.header_matcher({"Authorization": "Bearer secret"}),
        ],
    )
    responses.add(rsp)

    login("secret")
    out = io.BytesIO()
    with pytest.raises(HttpStatusError) as excinfo:
        download_zip(proposal_code, out)

    assert excinfo.value.status_code == status_code


@responses.activate
def test_download_zip_updates_proposal_code():
    """Test that the proposal code is updated in the downloaded zip file."""
    proposal_code = "2022-1-SCI-042"
    rsp = responses.Response(
        method="GET",
        url=api_url(f"/proposals/{proposal_code}.zip"),
        content_type="application/zip",
        body=_fake_zip_file("Unsubmitted-002", "This is a proposal."),
        match=[
            matchers.header_matcher({"Authorization": "Bearer secret"}),
        ],
    )
    responses.add(rsp)

    login("secret")

    proposal_content = io.BytesIO()
    download_zip(proposal_code, proposal_content)

    with zipfile.ZipFile(proposal_content, "r") as z:
        xml = z.read("Proposal.xml")
        code_attribute = f'code="{proposal_code}"'.encode("UTF-8")
        assert code_attribute in xml
