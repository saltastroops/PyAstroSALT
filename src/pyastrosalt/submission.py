"""This module allows submissions of proposals and blocks."""

from pathlib import Path
from typing import IO, Any, BinaryIO, Union
from zipfile import ZipFile, is_zipfile

import defusedxml.ElementTree as ET

from pyastrosalt.session import Session


class Submission:
    pass


def submit(
    file: Union[Path, str, BinaryIO], proposal_code: str | None = None
) -> Submission:
    """Submit a proposal file.

    The submitted file must be a zip file containing files in a format understood by the
    SALT API. It has to contain an XML file with the whole proposal, blocks or a single
    block, as well as the required attachments.

    A file path or a file-like object may be passed as the file. In case of a file-like
    object it must support the seek method.

    If you submit a new proposal, the proposal code must be None. Conversely, if you
    resubmit an existing proposal, the proposal code must be that of the proposal.

    The function returns a Submission object, which you can use to track the submission
    progress.

    Args:
        file: The zip file containing the submitted content.
        proposal_code: The proposal code or None if this is a new submission.

    Returns:
        A Submission object for tracking the submission progress.
    """
    if not _is_file_like(file):
        with open(file, "rb") as f:  # type:ignore
            return _submit(f, proposal_code)
    else:
        return _submit(file, proposal_code)  # type:ignore


def _submit(file: IO[Any], proposal_code: str | None) -> Submission:
    # Do some sanity checks on the submitted content.
    _check_submitted_content(file, proposal_code)

    # Submit the file.
    session = Session.get_instance()
    data = {"proposal_code": proposal_code} if proposal_code is not None else {}
    session.post(
        "/submissions/",
        data=data,
        files={"proposal.zip": file},
    )
    return Submission()


def _check_submitted_content(file: IO[Any], proposal_code: str | None) -> None:
    # Make sure a zip file is submitted.
    if not is_zipfile(file):
        raise ValueError("The submitted file must be a zip file.")
    file.seek(0)

    # Get the files in the zip file.
    with ZipFile(file, "r") as z:
        filenames = z.namelist()
        file.seek(0)

        # Check that exactly one proposal or block file is present.
        required_filenames = [
            f for f in filenames if f in ("Proposal.xml", "Blocks.xml", "Block.xml")
        ]
        if len(required_filenames) == 0:
            raise ValueError(
                "The submitted zip file must contain a file Proposal.xml, Blocks.xml or Block.xml."
            )
        if len(required_filenames) > 1:
            raise ValueError(
                "The submitted zip file must contain exactly one of Proposal.xml, Blocks.xml or Block.xml."
            )

        # Check that a proposal code is present, if necessary.
        if "Blocks.xml" in required_filenames or "Block.xml" in required_filenames:
            if proposal_code is None:
                raise ValueError("A proposal code is required for a block submission.")

        # Check that the proposal code is consistent, if necessary.
        filename = required_filenames[0]
        if filename == "Proposal.xml":
            with z.open("Proposal.xml", "r") as p:
                tree = ET.parse(p)
                code = tree.getroot().attrib.get("code")
                if code and proposal_code != code:
                    raise ValueError(
                        f"The proposal code argument ({proposal_code}) does not match "
                        f"the proposal code in the submitted Proposal.xml file "
                        f"({code})."
                    )
        file.seek(0)


def _is_file_like(obj: Any):
    # Check whether the given object is file-like.
    # Taken from Pandas (https://github.com/pandas-dev/pandas/blob/v2.2.3/pandas/core/dtypes/inference.py).
    if not (hasattr(obj, "read") or hasattr(obj, "write")):
        return False

    return bool(hasattr(obj, "__iter__"))
