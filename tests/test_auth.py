from unittest.mock import MagicMock, patch

import pytest
import requests
import responses

from pyastrosalt.auth import login, logout
from pyastrosalt.web import api_url, SessionHandler


@responses.activate
def test_login() -> None:
    """Test logging in."""
    rsp1 = responses.Response(
        method="POST",
        url=api_url("/token/"),
        json={"access_token": "sometoken"},
        status=200,
        match=[
            responses.matchers.urlencoded_params_matcher(
                {"username": "john", "password": "secret"}
            )
        ],
    )
    rsp2 = responses.Response(
        method="GET",
        url="http://example.com",
        status=200,
        match=[
            responses.matchers.header_matcher({"Authorization": "Bearer sometoken"})
        ],
    )

    responses.add(rsp1)
    responses.add(rsp2)

    login(username="john", password="secret")
    SessionHandler.get_session().get("http://example.com")

    assert rsp1.call_count == 1
    assert rsp2.call_count == 1


@responses.activate
def test_login_checks_for_http_errors() -> None:
    """Test that login raises an exception if there is an HTTP error."""
    rsp = responses.Response(
        method="POST",
        url=api_url("/token/"),
        json={"access_token": "sometoken"},
        status=400,
        match=[
            responses.matchers.urlencoded_params_matcher(
                {"username": "john", "password": "secret"}
            )
        ],
    )
    responses.add(rsp)

    mock = MagicMock()
    with patch("pyastrosalt.auth.check_for_http_errors", mock):
        login(username="john", password="secret")
        mock.assert_called()


@responses.activate
def test_logout() -> None:
    """Test logging out."""
    rsp1 = responses.Response(
        method="POST",
        url=api_url("/token/"),
        json={"access_token": "sometoken"},
        status=200,
        match=[
            responses.matchers.urlencoded_params_matcher(
                {"username": "john", "password": "secret"}
            )
        ],
    )
    rsp2 = responses.Response(
        method="GET",
        url="http://example.com",
        status=200,
        match=[
            responses.matchers.header_matcher({"Authorization": "Bearer sometoken"})
        ],
    )

    responses.add(rsp1)
    responses.add(rsp2)

    login(username="john", password="secret")
    SessionHandler.get_session().get("http://example.com")

    assert rsp1.call_count == 1
    assert rsp2.call_count == 1

    logout()
    with pytest.raises(requests.exceptions.ConnectionError):
        # The connection should fail as no Authorization header is sent any longer,
        # and hence no route for the mock responses is matched.
        SessionHandler.get_session().get("http://example.com/")
