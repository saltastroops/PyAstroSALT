from typing import Generator

import pytest
import responses

from pyastrosalt.session import Session
from pyastrosalt.util.time import FakeTimeProvider


@pytest.fixture(autouse=True, scope="session")
def set_base_url():
    Session.PLAYGROUND_BASE_URL = "https://playground.example.org"
    Session.PRODUCTION_BASE_URL = "https://example.org"


@pytest.fixture(autouse=True)
def mocked_responses():
    with responses.RequestsMock() as rsps:
        yield rsps


@pytest.fixture(autouse=True, scope="function")
def base_url() -> Generator[str, None, None]:
    # Store the current base URL.
    current_url = Session.PRODUCTION_BASE_URL

    # Replace the base URL with a fake one.
    url = "https://example.org"
    Session.PRODUCTION_BASE_URL = url

    # Return the (fake) base URL.
    yield url

    # Restore the original base URL.
    Session.PRODUCTION_BASE_URL = current_url


@pytest.fixture(autouse=True, scope="function")
def reset_session():
    Session._session = None


@pytest.fixture(scope="function")
def time_provider(monkeypatch) -> Generator[FakeTimeProvider, None, None]:
    time_provider = FakeTimeProvider()
    monkeypatch.setattr(
        "pyastrosalt.submission.Submission._time_provider", time_provider
    )
    yield time_provider
