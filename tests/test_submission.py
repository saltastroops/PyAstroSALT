import pathlib
import zipfile
from io import BytesIO
from typing import BinaryIO

import pytest
import responses
from responses import RequestsMock

from pyastrosalt.submission import submit

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
    mocked_responses.post(f"{base_url}/submissions/")

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
