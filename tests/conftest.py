from urllib.parse import urljoin

import pytest
import responses

import pyastrosalt.web

# Prevent accidental real HTTP requests.
# Source: https://blog.jerrycodes.com/no-http-requests/
from pyastrosalt.web import SALT_API_URL


@pytest.fixture(autouse=True)
def no_http_requests(monkeypatch):
    """Do not allow real HTTP requests."""

    def urlopen_mock(self, method, url, *args, **kwargs):
        raise RuntimeError(
            f"The test was about to {method} {self.scheme}://{self.host}{url}"
        )

    monkeypatch.setattr(
        "urllib3.connectionpool.HTTPConnectionPool.urlopen", urlopen_mock
    )


def login(token: str):
    """
    Login to the backend API server.

    Parameters
    ----------
    token: str
        Bearer token. For example, if the value is "secret", the Authorization HTTP
        header should have the value "Bearer secret" for requests requiring
        authentication.
    """
    rsp = responses.Response(
        method="POST",
        url=urljoin(SALT_API_URL, "/token/"),
        json={"access_token": "secret"},
    )
    responses.add(rsp)

    pyastrosalt.web.login("joe", token)
