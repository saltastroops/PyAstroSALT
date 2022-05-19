import copy
import json
import pathlib
import zipfile
from asyncio import sleep
from datetime import datetime
from enum import Enum
from io import BytesIO
from tempfile import TemporaryFile
from typing import Any, AsyncGenerator, BinaryIO, Dict, Optional, Union, cast
from urllib.parse import urljoin
from xml.etree import ElementTree as ET

import websockets

from pyastrosalt.web import SALT_API_URL, SessionHandler, check_for_http_errors

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
    proposals to SALT's Science Database. The easiest way to create such a file is to
    export the proposal as a zip file in the Principal Investigator Proposal Tool.

    You may optionally specify a proposal code. If you do so and the proposal file
    contains a proposal code, the two proposal codes must be the same.

    This method only checks whether the file exists; any further checks are done by the
    server to which it is submitted. If there is an upfront problem, such as if you are
    not authenticated or you submit a file which isn't a zip file, the HTTP request
    fails and this function raises an `~pyastrosalt.web.HttpStatusError`. Otherwise, a
    unique identifier for the submission is returned.

    The fact that you receive a submission identifier does not imply that the submission
    was successful; it just means that the proposal file has been accepted and an
    attempt to map it to the database is made. As validation checks are done as part of
    the mapping process, your proposal might still be found to be invalid.

    You can use the function `~pyastrosalt.proposal.submission_progress` to monitor the
    progress of the submission.

    Parameters
    ----------
    proposal : path-like, file or file-like
        The proposal file to submit.
    proposal_code : str, optional
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
    Monitor the progress of a proposal submission.

    This generator tracks the progress of the submission with the given identifier. You
    must have initiated the submission to track it; other users are denied access.

    When the generator connects to the submission server, it receives the current status
    of the submission as well as all the submission log entries. Afterwards it receives
    an update with changes every few seconds. Such an update may contain a changed
    status, new log entries, both of these or, if nothing has changed, none of these. In
    case of a successful submission the proposal code is included as well.

    Whenever a message is received from the server, its content is yielded by the
    generator. Once the connection is closed by the server, any remaining messages are
    yielded and the generator is stopped.

    The items yielded by the generator are dictionaries with the following content:

    .. list-table::

       * - Key
         - Value
       * - ``status``
         - The submission status. This is an instance of `SubmissionStatus`.
       * - ``log_entries``
         - A list of the (new) log entries. See below for their content.
       * - ``proposal_code``
         - The proposal code for the submitted proposal. It is only included in the
           dictionary if the submission has been successful.

    Each log entry is a dictionary with the following content:

    .. list-table::

       * - Key
         - Value
       * - ``logged_at``
         - The date and time when the log entry was made. This is a timezone-aware
           `~datetime.datetime` object.
       * - ``message_type``
         - The type of log message. This is a `SubmissionLogMessageType` instance.
       * - ``message``
         - The log message.

    In case of unexpected errors the generator reconnects (up to ``max_retries`` times),
    asking the API server to omit any log entries received already.

    Parameters
    ----------
    submission_identifier : str
        The unique identifier of the submission.
    max_retries : int, optional, default 5
        Maximum number of attempts the generator will make to reconnect to the server if
        necessary. This number does not include the initial connection.

    Yields
    ------
    `dict`
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
                # Pass on the previously caught exception
                raise


async def _submission_progress_server_input(
    submission_identifier: str, from_entry_number: int = 1
) -> AsyncGenerator[Any, None]:
    api_url_no_protocol = SALT_API_URL.split("://", 1)[1]
    url = (
        f"ws://{api_url_no_protocol}/submissions/{submission_identifier}/progress/ws"
        f"?from_entry_number={int(from_entry_number)}"
    )
    async with websockets.connect(url) as websocket:  # type: ignore
        await websocket.send(SessionHandler.get_access_token())
        try:
            while True:
                p = await websocket.recv()
                yield json.loads(p)
        except websockets.exceptions.ConnectionClosedOK:  # type: ignore
            pass


def download_zip(proposal_code: str, out: Union[pathlib.Path, str, BinaryIO]) -> None:
    """
    Download a proposal zip file.

    The downloaded zip file is stored in the file or file-like object specified with the
    ``out`` parameter. An existing file will be overwritten.

    If ``out`` specifies a real file, that file is closed after the zip file has been
    downloaded. However, an in-memory stream is not closed; it is rewound instead.

    Parameters
    ----------
    proposal_code : str
        Proposal code of the proposal to download.
    out : path-like, file or file-like
        File or file-like object in which to store the downloaded file.
    """
    with TemporaryFile() as tmp_file:
        _download_zip(proposal_code, cast(Any, tmp_file))

        is_stream = hasattr(out, "write")
        f = cast(Any, out if is_stream else open(cast(Any, out), "wb"))
        try:
            # Loop over all files in the downloaded zip file and store them in a new zip
            # file. In case of the proposal XML file the proposal code is updated (as it
            # might be of the form "Unsubmitted-..."), but should be the correct
            # proposal code.
            with zipfile.ZipFile(tmp_file, "r") as zip_in:
                with zipfile.ZipFile(f, "w") as zip_out:
                    for name in zip_in.namelist():
                        if name == "Proposal.xml":
                            original_data = zip_in.read(name)
                            data = _update_proposal_code(original_data, proposal_code)
                        else:
                            data = zip_in.read(name)
                        zip_out.writestr(name, data)
        finally:
            if not is_stream:
                f.close()
            else:
                f.seek(0)


def _download_zip(proposal_code: str, f: BinaryIO) -> None:
    session = SessionHandler.get_session()
    url = urljoin(SALT_API_URL, f"/proposals/{proposal_code}.zip")
    response = session.get(url, stream=True)
    check_for_http_errors(response)
    for chunk in response.iter_content(chunk_size=1024):
        f.write(chunk)

    # "Rewind" the stream, as otherwise only an empty string would be returned when the
    # stream is read.
    f.seek(0)


def _update_proposal_code(proposal_xml: bytes, proposal_code: str) -> bytes:
    # Replace the proposal code in the XML with the given one.
    tree = ET.parse(BytesIO(proposal_xml))
    root = tree.getroot()
    root.set("code", proposal_code)
    out = BytesIO()
    tree.write(out)

    # "Rewind" the stream, as otherwise only an empty string would be returned when the
    # stream is read.
    out.seek(0)

    return out.getvalue()
