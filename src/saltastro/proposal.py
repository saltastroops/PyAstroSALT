import copy
import json
import pathlib
from asyncio import sleep
from datetime import datetime
from enum import Enum
from typing import Any, AsyncGenerator, BinaryIO, Dict, Optional, Union, cast
from urllib.parse import urljoin

import websockets

from saltastro.web import SALT_API_URL, SessionHandler, check_for_http_errors

TIME_BETWEEN_RECONNECTION_ATTEMPTS = 10


class SubmissionStatus(str, Enum):
    """Enumeration of submission status values."""

    FAILED = "Failed"
    IN_PROGRESS = "In progress"
    SUCCESSFUL = "Successful"


class SubmissionLogMessageType(str, Enum):
    """Enumeration of submission log message types."""

    ERROR = "Error"
    INFO = "Info"
    WARNING = "Warning"


def submit(
    proposal: Union[pathlib.Path, str, BinaryIO], proposal_code: Optional[str] = None
) -> str:
    """
    Submit a proposal.

    The proposal must be a zip file in a format understood by the script mapping
    proposals to SALT's Science Database; see the documentation for details. The easiest
    way to create such a file is to export the proposal as a zip file in the Principal
    Investigator Proposal Tool.

    You may optionally specify a proposal code. If you do so and the proposal file
    contains a proposal code, the two proposal codes must be the same.

    This method only checks whether the file exists; any further checks are done by the
    server to which it is submitted. If there is an upfront problem, such as if you are
    not authenticated or you submit a file which isn't a zip file, the HTTP request
    fails and this function raises an `~saltastro.web.HttpStatusError`. Otherwise, a
    unique identifier for the submission is returned.

    The fact that you receive a submission identifier does not imply that the submission
    was successful; it just means that the proposal file has been accepted and an
    attempt to map it to the database is made. As validation checks are done as part of
    the mapping process, your proposal might still be found to be invalid.

    You can use the function `~saltastro.proposal.submission_progress` to monitor the
    progress of the submission.

    Parameters
    ----------
    proposal: path-like, file or file-like
        The proposal file to submit.
    proposal_code: str, optional
        The proposal code of the submitted proposal.

    Returns
    -------
    str
        A unique identifier for the submission.
    """
    # If the proposal isn't a stream in memory, check that it is an existing file.
    is_stream = hasattr(proposal, "read")
    proposal_path = (
        None if is_stream else pathlib.Path(cast(Union[str, pathlib.Path], proposal))
    )
    if proposal_path is not None:
        if not proposal_path.exists():
            raise IOError(f"File does not exist: {proposal_path.absolute()}")
        if not proposal_path.is_file():
            raise IOError(f"Not a file: {proposal_path.absolute()}")

    # Submit the proposal
    url = urljoin(SALT_API_URL, "/submissions/")
    data = {}
    if proposal_code is not None:
        data["proposal_code"] = proposal_code
    proposal_content = proposal if is_stream else open(cast(Any, proposal_path), "rb")
    try:
        files = {"proposal": ("proposal.zip", proposal_content)}
        session = SessionHandler.get_session()
        resp = session.post(url, files=files, data=data)
        check_for_http_errors(resp)
        return str(resp.json()["submission_identifier"])
    finally:
        cast(Any, proposal_content).close()


async def submission_progress(
    submission_identifier: str, max_retries: int = 5
) -> AsyncGenerator[Dict[str, Any], None]:
    """
    Monitor progress of a proposal submission.

    This generator tracks the progress of the submission with the given identifier. You
    must have initiated the submission to track; other users are denied access.

    When the generator connects to the submission server, it receives the current status
    of the submission as well as all the submission log entries. Afterwards it receives
    an update with changes every few seconds. Such an update may contain a changed
    status, new log entries, both of these or, if nothing has changed, none of these. In
    case of a successful submission the proposal code is included as well.

    Whenever a message is received from the server, its content is yielded by the
    generator. Once the connection is closed by the server, any remaining messages are
    yielded and the generator is stopped.

    In case of unexpected errors the generator reconnects (up to ``max_retries`` times,
    asking to omit any log entries received already.

    Parameters
    ----------
    submission_identifier: str
        The unique identifier of the submission.
    max_retries: int, optional, default 5
        Maximum number of attempts the generator will make to reconnect to the server if
        necessary. This number does not include the initial connection.

    Yields
    ------
    `~saltastro.proposal.SubmissionProgressDetails`
         Update on the submission progress.
    """
    received_log_entries = 0
    num_retries = 0
    while num_retries <= max_retries:
        try:
            async for p in _submission_progress_server_input(
                submission_identifier, received_log_entries + 1
            ):
                p = copy.deepcopy(p)
                p["status"] = SubmissionStatus(p["status"])
                for log_entry in p["log_entries"]:
                    log_entry["logged_at"] = datetime.fromisoformat(
                        log_entry["logged_at"]
                    )
                    log_entry["message_type"] = SubmissionLogMessageType(
                        log_entry["message_type"]
                    )
                yield p
                received_log_entries += len(p["log_entries"])
                num_retries = 0
            return
        except Exception:
            await sleep(TIME_BETWEEN_RECONNECTION_ATTEMPTS)
            num_retries += 1
            if num_retries > max_retries:
                raise


async def _submission_progress_server_input(
    submission_identifier: str, from_entry_number: int = 1
) -> AsyncGenerator[Any, None]:
    url = f"ws://localhost:8001/submissions/{submission_identifier}/progress/ws?from_entry_number={int(from_entry_number)}"
    async with websockets.connect(url) as websocket:  # type: ignore
        await websocket.send(SessionHandler._access_token)
        try:
            while True:
                p = await websocket.recv()
                yield json.loads(p)
        except websockets.exceptions.ConnectionClosedOK:  # type: ignore
            pass
