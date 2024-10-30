import json
import pathlib
import zipfile
from datetime import datetime, timedelta, timezone
from io import BytesIO
from typing import Any, BinaryIO, Dict, List

import pytest
import responses
from freezegun import freeze_time
from responses import RequestsMock

from pyastrosalt.submission import (
    Submission,
    SubmissionLogEntry,
    SubmissionMessageType,
    SubmissionStatus,
    submit,
)

_PROPOSAL_FILE = pathlib.Path(__file__).parent / "data" / "proposal.zip"


def _create_zip(contents: list[dict]) -> BytesIO:
    zip_content = BytesIO()
    with zipfile.ZipFile(zip_content, "w") as z:
        for c in contents:
            z.writestr(c["filename"], c["content"])
    zip_content.seek(0)
    return zip_content


@pytest.mark.parametrize(
    "proposal",
    [_PROPOSAL_FILE, str(_PROPOSAL_FILE.absolute()), open(_PROPOSAL_FILE, "rb")],
)
def test_submission(
    proposal: pathlib.Path | str | BinaryIO,
    base_url: str,
    mocked_responses: RequestsMock,
):
    proposal_content = _PROPOSAL_FILE.read_bytes()
    proposal_code = "2024-2-SCI-042"
    req_data = {"proposal_code": proposal_code}
    req_files = {"proposal.zip": proposal_content}
    mocked_responses.post(
        f"{base_url}/submissions/",
        json={"identifier": "abcd"},
        match=[
            responses.matchers.multipart_matcher(files=req_files, data=req_data),
        ],
    )
    submit(proposal, proposal_code=proposal_code)


def test_submission_without_proposal_code(
    base_url: str, mocked_responses: RequestsMock
):
    proposal_content = _PROPOSAL_FILE.read_bytes()
    req_files = {"proposal.zip": proposal_content}
    mocked_responses.post(
        f"{base_url}/submissions/",
        json={"identifier": "abcd"},
        match=[
            responses.matchers.multipart_matcher(files=req_files, data={}),
        ],
    )
    submit(_PROPOSAL_FILE)


@pytest.mark.parametrize("content", ["Proposal", "Blocks", "Block"])
def test_submission_accepts_proposal_blocks_and_block(
    content: str, base_url: str, mocked_responses: RequestsMock
):
    file_content = f"""<?xml version="1.0" encoding="UTF-8" ?>

<{content}/>
"""
    proposal_file = _create_zip(
        [{"filename": f"{content}.xml", "content": file_content}]
    )
    proposal_code = "2024-2-SCI-042"
    req_data = {"proposal_code": proposal_code}
    req_files = {"proposal.zip": proposal_file}
    mocked_responses.post(
        f"{base_url}/submissions/",
        json={"identifier": "abcd"},
        match=[
            responses.matchers.multipart_matcher(files=req_files, data=req_data),
        ],
    )
    submit(proposal_file, proposal_code=proposal_code)


def test_submission_requires_zip_file():
    content = BytesIO(b"PKNot a zip file")
    with pytest.raises(ValueError, match="zip"):
        submit(content)


def test_submission_requires_proposal_or_block_xml():
    file = _create_zip([{"filename": "OtherContent.txt", "content": "other content"}])
    with pytest.raises(ValueError, match="Proposal.xml, Blocks.xml or Block.xml"):
        submit(file)


def test_submission_requires_exactly_one_proposal_or_block_xml():
    file = _create_zip(
        [
            {"filename": "Proposal.xml", "content": "<Proposal/>"},
            {"filename": "Blocks.xml", "content": "<Blocks/>"},
        ]
    )
    with pytest.raises(
        ValueError, match="exactly one of Proposal.xml, Blocks.xml or Block.xml"
    ):
        submit(file)


@pytest.mark.parametrize("content", ["Blocks", "Block"])
def test_submission_of_blocks_requires_proposal_code(content: str):
    file = _create_zip([{"filename": f"{content}.xml", "content": f"<{content}/>"}])
    with pytest.raises(ValueError, match="proposal code is required"):
        submit(file)


def test_submission_accepts_a_consistent_proposal_code(
    base_url: str, mocked_responses: RequestsMock
):
    proposal_code = "2024-2-SCI-042"
    content = """<?xml version="1.0" encoding="UTF-8" ?>

<Proposal xmlns="http://www.salt.ac.za/PIPT/Proposal/Phase2" code="2024-2-SCI-042"/>
"""
    file = _create_zip([{"filename": "Proposal.xml", "content": content}])
    mocked_responses.post(f"{base_url}/submissions/", json={"identifier": "abcd"})

    submit(file, proposal_code=proposal_code)


def test_submission_requires_a_consistent_proposal_code():
    proposal_code = "2024-2-SCI-042"
    proposal_code_argument = "2024-2-SCI-043"
    content = f"""<?xml version="1.0" encoding="UTF-8" ?>

<Proposal xmlns="http://www.salt.ac.za/PIPT/Proposal/Phase2" code="{proposal_code}"/>
"""
    file = _create_zip([{"filename": "Proposal.xml", "content": content}])
    message = (
        f"The proposal code argument \\({proposal_code_argument}\\) does not "
        f"match the proposal code in the submitted Proposal.xml file \\("
        f"{proposal_code}\\)."
    )
    with pytest.raises(ValueError, match=message):
        submit(file, proposal_code=proposal_code_argument)


def _create_progress_response(
    status: str,
    entry_numbers: List[int],
    message_types: List[str],
    proposal_code: str | None,
) -> Dict[str, Any]:
    return {
        "status": status,
        "log_entries": [
            {
                "entry_number": e,
                "logged_at": _time(e).isoformat(),
                "message_type": message_types[index],
                "message": f"Message {e}",
            }
            for index, e in enumerate(entry_numbers)
        ],
        "proposal_code": proposal_code,
    }


def _time(entry_number: int) -> datetime:
    return datetime(2024, 10, 25, 10, 0, 0, 0) + timedelta(seconds=entry_number)


@pytest.mark.parametrize("property", ["log", "status", "error"])
def test_submission_progress_methods_make_correct_queries(
    property: str, base_url: str, mocked_responses: RequestsMock
):
    counter = {"value": 0}

    def request_callback(request):
        counter["value"] += 1
        if counter["value"] == 1:
            response = _create_progress_response(
                "In progress", [1, 2], ["Info", "Warning"], None
            )
        elif counter["value"] == 2:
            response = _create_progress_response("In progress", [], [], None)
        elif counter["value"] == 3:
            response = _create_progress_response(
                "In progress", [3, 4, 5, 6], ["Info", "Info", "Info", "Error"], None
            )
        else:
            response = _create_progress_response(
                "Successful", [7], ["Info"], "2024-2-SCI-055"
            )
        return 200, {}, json.dumps(response)

    identifier = "abcd"
    mocked_responses.add_callback(
        "GET",
        f"{base_url}/submissions/{identifier}/progress",
        match=[responses.matchers.query_string_matcher("from_entry_number=1")],
        callback=request_callback,
        content_type="application/json",
    )
    mocked_responses.add_callback(
        "GET",
        f"{base_url}/submissions/{identifier}/progress",
        match=[responses.matchers.query_string_matcher("from_entry_number=3")],
        callback=request_callback,
        content_type="application/json",
    )
    mocked_responses.add_callback(
        "GET",
        f"{base_url}/submissions/{identifier}/progress",
        match=[responses.matchers.query_string_matcher("from_entry_number=7")],
        callback=request_callback,
        content_type="application/json",
    )

    # As the server is queried only every 10 seconds, we have to explicitly move time
    # forward to make repeated server queries.
    initial_datetime = datetime(2024, 10, 25, 10, 0, 0, 0, tzinfo=timezone.utc)
    one_minute = timedelta(minutes=1)
    with freeze_time(initial_datetime, tz_offset=0) as freezer:
        submission = Submission(identifier)
        getattr(submission, property)
        freezer.move_to(initial_datetime + one_minute)
        getattr(submission, property)
        freezer.move_to(initial_datetime + 2 * one_minute)
        getattr(submission, property)
        freezer.move_to(initial_datetime + 3 * one_minute)
        getattr(submission, property)


@pytest.mark.parametrize(
    "final_status, final_message_type, proposal_code",
    [("Failed", "Error", None), ("Successful", "Info", "2024-2-SCI-055")],
)
def test_submission_progress_properties_return_correct_values(
    final_status: str,
    final_message_type: str,
    proposal_code: str | None,
    base_url: str,
    mocked_responses: RequestsMock,
):
    counter = {"value": 0}

    def request_callback(request):
        counter["value"] += 1
        if counter["value"] == 1:
            response = _create_progress_response(
                "In progress", [1, 2], ["Info", "Warning"], None
            )
        elif counter["value"] == 2:
            response = _create_progress_response("In progress", [], [], None)
        elif counter["value"] == 3:
            response = _create_progress_response("In progress", [3], ["Info"], None)
        else:
            response = _create_progress_response(
                final_status, [4, 5], ["Info", final_message_type], proposal_code
            )
        return 200, {}, json.dumps(response)

    identifier = "abcd"
    mocked_responses.add_callback(
        "GET",
        f"{base_url}/submissions/{identifier}/progress",
        match=[responses.matchers.query_string_matcher("from_entry_number=1")],
        callback=request_callback,
        content_type="application/json",
    )
    mocked_responses.add_callback(
        "GET",
        f"{base_url}/submissions/{identifier}/progress",
        match=[responses.matchers.query_string_matcher("from_entry_number=3")],
        callback=request_callback,
        content_type="application/json",
    )
    mocked_responses.add_callback(
        "GET",
        f"{base_url}/submissions/{identifier}/progress",
        match=[responses.matchers.query_string_matcher("from_entry_number=4")],
        callback=request_callback,
        content_type="application/json",
    )

    expected_full_log = [
        SubmissionLogEntry(
            logged_at=_time(1),
            message_type=SubmissionMessageType.INFO,
            message="Message 1",
        ),
        SubmissionLogEntry(
            logged_at=_time(2),
            message_type=SubmissionMessageType.WARNING,
            message="Message 2",
        ),
        SubmissionLogEntry(
            logged_at=_time(3),
            message_type=SubmissionMessageType.INFO,
            message="Message 3",
        ),
        SubmissionLogEntry(
            logged_at=_time(4),
            message_type=SubmissionMessageType.INFO,
            message="Message 4",
        ),
        SubmissionLogEntry(
            logged_at=_time(5),
            message_type=SubmissionMessageType(final_message_type),
            message="Message 5",
        ),
    ]

    # As the server is queried only every 10 seconds, we have to explicitly move time
    # forward to make repeated server queries.
    initial_datetime = datetime(2024, 10, 25, 10, 0, 0, 0, tzinfo=timezone.utc)
    one_minute = timedelta(minutes=1)
    with freeze_time(initial_datetime) as freezer:
        # Check the submission...
        submission = Submission(identifier)
        assert submission.status == SubmissionStatus.IN_PROGRESS
        assert submission.log == expected_full_log[:2]
        assert submission.error is None
        assert submission.proposal_code is None

        # ... and check it again one minute later...
        freezer.move_to(initial_datetime + one_minute)
        assert submission.status == SubmissionStatus.IN_PROGRESS
        assert submission.log == expected_full_log[:2]
        assert submission.error is None
        assert submission.proposal_code is None

        # ... and check it again another minute later...
        freezer.move_to(initial_datetime + 2 * one_minute)
        assert submission.status == SubmissionStatus.IN_PROGRESS
        assert submission.log == expected_full_log[:3]
        assert submission.error is None
        assert submission.proposal_code is None

        # ... and check it again yet another minute later.
        freezer.move_to(initial_datetime + 3 * one_minute)
        assert submission.status == final_status
        assert submission.log == expected_full_log[:5]
        if final_status == SubmissionStatus.FAILED:
            assert submission.error == "Message 5"
            assert submission.proposal_code is None
        else:
            assert submission.error is None
            assert submission.proposal_code == "2024-2-SCI-055"


def test_submission_progress_queries_every_ten_seconds(
    base_url: str, mocked_responses: RequestsMock
):
    identifier = "abcd"
    url = f"{base_url}/submissions/{identifier}/progress"
    full_url = f"{url}?from_entry_number=1"
    mocked_responses.get(
        url,
        json=_create_progress_response("In progress", [], [], None),
    )

    initial_datetime = datetime(2024, 10, 25, 10, 0, 0, 0, tzinfo=timezone.utc)
    one_second = timedelta(seconds=1)
    with freeze_time(initial_datetime) as freezer:
        # Even though you query all the status details, only one server query is made.
        submission = Submission(identifier)
        submission.status  # noqa (we are testing a "side effect")
        submission.error  # noqa
        submission.log  # noqa
        submission.proposal_code  # noqa
        mocked_responses.assert_call_count(full_url, 1)

        # Re-query the status. No server query is made.
        submission.status  # noqa
        mocked_responses.assert_call_count(full_url, 1)

        # Wait for 9 seconds and query the status again. No server query is made.
        freezer.move_to(initial_datetime + 9 * one_second)
        submission.status  # noqa
        mocked_responses.assert_call_count(full_url, 1)

        # Wait for another 2 seconds and query the status again. This time a server
        # query is made.
        freezer.move_to(initial_datetime + 11 * one_second)
        submission.status  # noqa
        mocked_responses.assert_call_count(full_url, 2)
