import asyncio
import xml.etree.ElementTree as ET
import zipfile
from getpass import getpass
from io import BytesIO
from uuid import uuid4

from pyastrosalt.auth import login
from pyastrosalt.proposal import download_zip, submission_progress, submit


def authenticate() -> None:
    """Login."""
    username = input("Your SALT username: ")
    password = getpass("Your SALT password: ")
    login(username, password)


def update_block(block: ET.Element) -> None:
    """Update a block."""
    # Rename the block.
    name_element = block.find("./{*}Name")
    name_element.text = name_element.text.strip() + " (v2)"  # type: ignore

    # Change the block code. This effectively creates a new block.
    block_code_element = block.find("./{*}BlockCode")
    block_code_element.text = str(uuid4())  # type: ignore


def updated_proposal(content: BytesIO) -> BytesIO:
    """Update a proposal and return the updated proposal content."""
    updated_content = BytesIO()

    with zipfile.ZipFile(content, "r") as zip_in:
        with zipfile.ZipFile(updated_content, "w") as zip_out:
            for path in zip_in.namelist():
                if path == "Proposal.xml":
                    # Modify the proposal XML...
                    with zip_in.open(path, "r") as f:
                        tree = ET.parse(f)
                        root = tree.getroot()
                        for block in root.findall(".//{*}Block"):
                            update_block(block)

                    # ... and save the new content
                    with zip_out.open("Proposal.xml", "w") as g:
                        tree.write(g)
                else:
                    # Copy all additional files without change
                    data = zip_in.read(path)
                    zip_out.writestr(path, data)

    # "Rewind" the stream. Otherwise, you would only get an empty byte string when
    # reading from the stream.
    updated_content.seek(0)

    return updated_content


async def watch_progress(submission_identifier: str) -> None:
    """Watch the progress of a submission."""
    progress = submission_progress(submission_identifier)
    async for p in progress:
        if len(p["log_entries"]) > 0:
            for log_message in p["log_entries"]:
                print(  # noqa
                    f"[{log_message['message_type'].value}] "
                    f"{log_message['message']}"
                )


async def main() -> None:
    """Download, update and resubmit a proposal."""
    try:
        authenticate()
        original_proposal = BytesIO()
        download_zip("2022-1-SCI-042", original_proposal)
        proposal = updated_proposal(original_proposal)
        submission_identifier = submit(proposal)
        await watch_progress(submission_identifier)
    except Exception as e:
        print(e)  # noqa


if __name__ == "__main__":
    asyncio.run(main())
