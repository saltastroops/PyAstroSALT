from unittest.mock import MagicMock, patch
from urllib.parse import urljoin

import pytest
import requests
import responses

from saltastro.web import (
    DEFAULT_STATUS_CODE_ERRORS,
    SALT_API_URL,
    HttpStatusError,
    SessionHandler,
    check_for_http_errors,
    login,
    logout,
)


@responses.activate
@pytest.mark.parametrize("status_code", [400, 401, 403, 404, 500])
def test_check_for_http_errors_uses_message_from_json_body(status_code: int) -> None:
    """Test that check_for_http_error uses the message property, if it exists."""
    responses.add(
        method="GET",
        url="http://example.com/message-only",
        json={"message": "There is an error!"},
        status=status_code,
    )
    responses.add(
        method="GET",
        url="http://example.com/both-message-and-error",
        json={"error": "There is another error!", "message": "There is an error!"},
        status=status_code,
    )

    resp = requests.get("http://example.com/message-only")

    with pytest.raises(HttpStatusError) as excinfo:
        check_for_http_errors(resp)
    assert excinfo.value.status_code == status_code
    assert excinfo.value.message == "There is an error!"

    resp = requests.get("http://example.com/both-message-and-error")

    with pytest.raises(HttpStatusError) as excinfo:
        check_for_http_errors(resp)
    assert excinfo.value.status_code == status_code
    assert excinfo.value.message == "There is an error!"


@responses.activate
@pytest.mark.parametrize("status_code", [400, 401, 403, 404, 500])
def test_check_for_http_errors_uses_error_from_json_body(status_code: int) -> None:
    """Test that check_for_http_error uses the error property."""
    responses.add(
        method="GET",
        url="http://example.com/message-only",
        json={"error": "There is an error!"},
        status=status_code,
    )

    resp = requests.get("http://example.com/message-only")

    with pytest.raises(HttpStatusError) as excinfo:
        check_for_http_errors(resp)
    assert excinfo.value.status_code == status_code
    assert excinfo.value.message == "There is an error!"


@responses.activate
@pytest.mark.parametrize("status_code", [400, 401, 403, 404, 500])
def test_check_for_http_errors_uses_generic_error_message(status_code: int) -> None:
    """Test that check_for_http_error uses the error property."""
    responses.add(
        method="GET",
        url="http://example.com/json",
        json={"someproperty": "There is an error!"},
        status=status_code,
    )
    responses.add(
        method="GET",
        url="http://example.com/no-json",
        body="There is an error!",
        status=status_code,
    )

    resp = requests.get("http://example.com/json")

    with pytest.raises(HttpStatusError) as excinfo:
        check_for_http_errors(resp)

    assert excinfo.value.status_code == status_code
    assert excinfo.value.message == DEFAULT_STATUS_CODE_ERRORS[status_code]

    resp = requests.get("http://example.com/no-json")

    with pytest.raises(HttpStatusError) as excinfo:
        check_for_http_errors(resp)

    assert excinfo.value.status_code == status_code
    assert excinfo.value.message == DEFAULT_STATUS_CODE_ERRORS[status_code]


@responses.activate
@pytest.mark.parametrize("status_code", [200, 201, 204, 300, 304])
def test_check_for_errors_does_nor_raise_for_non_error_codes(status_code: int) -> None:
    """Test that check_for_http_error uses a generic message if necessary."""
    responses.add(
        method="GET",
        url="http://example.com",
        body="Some response body.",
        status=status_code,
    )

    requests.get("http://example.com")

    assert True


@responses.activate
def test_login() -> None:
    """Test logging in."""
    rsp1 = responses.Response(
        method="POST",
        url=urljoin(SALT_API_URL, "/token/"),
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
        url=urljoin(SALT_API_URL, "/token/"),
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
    with patch("saltastro.web.check_for_http_errors", mock):
        login(username="john", password="secret")
        mock.assert_called()


@responses.activate
def test_logout() -> None:
    """Test logging out."""
    rsp1 = responses.Response(
        method="POST",
        url=urljoin(SALT_API_URL, "/token/"),
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
