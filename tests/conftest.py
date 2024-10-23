from typing import Generator

import pytest
import responses

from pyastrosalt.session import Session


@pytest.fixture(autouse=True)
def mocked_responses():
    with responses.RequestsMock() as rsps:
        yield rsps


@pytest.fixture(autouse=True, scope="function")
def base_url() -> Generator[str, None, None]:
    # Store the current base URL.
    session = Session.get_instance()
    current_url = session.base_url

    # Replace the base URL with a fake one.
    url = "https://example.org"
    session.base_url = url

    # Return the (fake) base URL.
    yield url

    # Restore the original base URL.
    session.base_url = current_url


@pytest.fixture(autouse=True, scope="function")
def reset_session():
    Session._session = None
