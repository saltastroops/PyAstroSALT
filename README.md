# pyastrosalt

PyAstroSALT is a wrapper around the RESTful API for observations with the [South African Astronomical Observatory (SALT)](https://www.salt.ac.za/).

It can be used for

* validating proposals
* submitting proposals
* making any API request

## Installation

PyAstroSALT can be installed from PyPI:

```console
pip install pyastrosalt
```

## Validating a proposal

SALT proposals are stored as zip files. If you want to see what such a zip file looks like, you can create a proposal in the [Principal Investigator Proposal Tool (PIPT)](https://astronomers.salt.ac.za/software/pipt/) and export it using the menu item `File | Export as Zip File`.

The following assumes that you have a proposal `proposal.zip` in the working directory and that the proposal code is 2026-1-SCI-042.

You start by creating a session and authenticating with your SALT user credentials. For testing, you can use the playground instead of the production server:

```python
from getpass import getpass
from pyastrosalt.session import Session

username = input("Your SALT username: ")
password = getpass("Your SALT password: ")
session = Session()
session.use_playground()
session.login(username=username, password=password)
```

You can now validate the proposal:

```python
from pyastrosalt.submission import validate

valid, errors = validate(session, "proposal.zip", "2026-1-SCI-042")
if valid:
    print("The proposal is valid.")
else:
    print("Validation failed with the following error(s):")
    for error in errors:
        print(f"- {error}")
```

## Submitting a proposal

As in the previous section, the following example assumes that you have a proposal `proposal.zip` in the working directory and that the proposal code is 2026-1-SCI-042.

If you want to submit the proposal, you start by creating a session and authenticating. For testing, you can use the playground instead of the production server:

```python
from getpass import getpass
from time import sleep

from pyastrosalt.session import Session

username = input("Your SALT username: ")
password = getpass("Your SALT password: ")
session = Session()
session.use_playground()
session.login(username=username, password=password)
```

You can now call the `submit` function. This function returns a `Submission` instance, which yiu can poll for the submission status, proposal code and (if applicable) submission error:

```python
from time import sleep
from pyastrosalt.submission import submit, SubmissionStatus

submission = submit(
    session, "proposal.zip", "2026-1-SCI-042"
)
while submission.status == SubmissionStatus.IN_PROGRESS:
    print("Waiting for submission to finish...")
    sleep(10)
    
if submission.status == SubmissionStatus.SUCCESS:
    print(f"Success! The proposal code is {submission.proposal_code}.")
else:
    print(f"The validation failed with the following error:\n{submission.error}")
```

## Using the SALT API

To make a request to the SALT API, you can create a session, authenticate and issue an HTTP request. Refer to the [Requests documentation](https://requests.readthedocs.io/en/latest/) for details on the available request methods (`get`, `post`, `put`, `patch`, `delete` and `request`).

The following example shows how you can get details about your SALT propoals:

```python
from getpass import getpass

from pyastrosalt.session import Session

# Get a session and authenticate
username = input("Your SALT username: ")
password = getpass("Your SALT password: ")
session = Session()
session.use_playground()
session.login(username=username, password=password)

# Make the API request
response = session.get("/proposals/")
if not response.ok:
    raise Exception("The API request failed.")

# Use the response from the API
proposals = response.json()
for proposal in proposals:
    print(f"{proposal['proposal_code']}: {proposal['title']}")
```

You can find the available API endpoints on the [SALT API documentation page](https://api-playground.salt.ac.za/docs).
