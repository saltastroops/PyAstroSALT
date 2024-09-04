import json
from itertools import product
from typing import Any, Callable, Optional, Type
from unittest import mock

import pytest
from pyastrosalt.exceptions import (
    APIError,
    BadRequestError,
    ForbiddenError,
    NotAuthenticatedError,
    NotFoundError,
    ServerError,
)
from pyastrosalt.session import Session
from requests_mock import Mocker

HTTP_METHODS = ("get", "post", "put", "patch", "delete")


def test_session_is_a_singleton() -> None:
    instance_1 = Session.get_instance()
    instance_2 = Session.get_instance()

    assert instance_1 is not None
    assert instance_1 is instance_2


def test_request_makes_the_correct_request(
    base_url: str, requests_mock: Mocker
) -> None:
    data = {"some": "data"}
    _json = {"start": "now"}
    headers = {"X-SomeHeader": "abc"}
    params = {"filter": "value"}
    passed_kwargs = {"data": data, "json": _json, "headers": headers, "params": params}
    with mock.patch("pyastrosalt.session.RequestsSession"):
        # The session must only be instantiated after the requests session is patched
        session = Session.get_instance()
        try:
            session.request("GET", "/status", **passed_kwargs)
        except Exception:
            pass  # The error is caused by the mocking.

        session._requests_session.request.assert_called()  # type: ignore
        used_args = session._requests_session.request.call_args.args  # type: ignore
        used_kwargs = session._requests_session.request.call_args.kwargs  # type: ignore
        assert list(used_args) == ["GET", f"{base_url}/status"]
        assert used_kwargs == passed_kwargs


@pytest.mark.parametrize("http_method", HTTP_METHODS)
def test_http_method_makes_the_correct_request(http_method: str, base_url: str) -> None:
    data = {"some": "data"}
    _json = {"start": "now"}
    headers = {"X-SomeHeader": "abc"}
    params = {"filter": "value"}
    passed_kwargs = {"data": data, "json": _json, "headers": headers, "params": params}
    with mock.patch("pyastrosalt.session.RequestsSession"):
        # The session must only be instantiated after the requests session is patched
        session = Session.get_instance()
        try:
            getattr(session, http_method)("/status", **passed_kwargs)
        except Exception:
            pass  # The error is caused by the mocking.

        session._requests_session.request.assert_called()  # type: ignore
        used_args = session._requests_session.request.call_args.args  # type: ignore
        used_kwargs = session._requests_session.request.call_args.kwargs  # type: ignore
        assert list(used_args) == [http_method.upper(), f"{base_url}/status"]
        assert used_kwargs == passed_kwargs


@pytest.mark.parametrize(
    "url",
    ("http://example.org/status", "https://example.org/status"),
)
def test_request_rejects_full_urls(url: str) -> None:
    with pytest.raises(ValueError, match="base URL"):
        session = Session.get_instance()
        session.request("GET", url)
    assert True


@pytest.mark.parametrize(
    "http_method, url",
    product(HTTP_METHODS, ("http://example.org/status", "https://example.org/status")),
)
def test_http_method_rejects_full_urls(http_method: str, url: str) -> None:
    with pytest.raises(ValueError, match="base URL"):
        session = Session.get_instance()
        getattr(session, http_method)(url)
    assert True


@pytest.mark.parametrize("endpoint", ("status", "//status"))
def test_request_requires_single_leading_slash_for_endpoint(endpoint: str) -> None:
    with pytest.raises(ValueError, match="must start with a single slash"):
        session = Session.get_instance()
        session.request("GET", endpoint)
    assert True


@pytest.mark.parametrize(
    "http_method, endpoint", product(HTTP_METHODS, ("status", "//status"))
)
def test_http_method_requires_single_leading_slash_for_endpoint(
    http_method: str, endpoint: str
) -> None:
    with pytest.raises(ValueError, match="must start with a single slash"):
        session = Session.get_instance()
        getattr(session, http_method)(endpoint)
    assert True


def test_request_uses_set_base_url(requests_mock: Mocker) -> None:
    session = Session.get_instance()
    current_url = session.base_url
    session.base_url = "https://new.base.url"
    requests_mock.post("https://new.base.url/status")
    response = session.request("POST", "/status")
    session.base_url = current_url
    assert response.status_code == 200


@pytest.mark.parametrize("http_method", HTTP_METHODS)
def test_http_method_uses_set_base_url(http_method: str, requests_mock: Mocker) -> None:
    session = Session.get_instance()
    current_url = session.base_url
    session.base_url = "https://new.base.url"
    getattr(requests_mock, http_method)("https://new.base.url/status")
    response = getattr(session, http_method)("/status")
    session.base_url = current_url
    assert response.status_code == 200


def test_trailing_slashes_are_forbidden_for_the_base_url():
    session = Session.get_instance()
    with pytest.raises(ValueError, match="trailing slash"):
        session.base_url = "https://slashes.example.org/"
    assert True


@pytest.mark.parametrize(
    "status_code, exception_class",
    [
        (400, BadRequestError),
        (401, NotAuthenticatedError),
        (403, ForbiddenError),
        (404, NotFoundError),
        (500, ServerError),
        (418, APIError),
    ],
)
def test_request_raises_api_exceptions(
    status_code: int,
    exception_class: Type[APIError],
    base_url: str,
    requests_mock: Mocker,
) -> None:
    message = "Something is wrong."
    response_payload = {"message": message}
    requests_mock.get(
        f"{base_url}/status",
        status_code=status_code,
        text=json.dumps(response_payload),
    )
    with pytest.raises(exception_class, match=message):
        session = Session.get_instance()
        session.request("GET", "/status")


@pytest.mark.parametrize(
    "http_method, status_code, exception_class",
    [
        ("get", 400, BadRequestError),
        ("post", 401, NotAuthenticatedError),
        ("put", 403, ForbiddenError),
        ("patch", 404, NotFoundError),
        ("delete", 500, ServerError),
        ("get", 418, APIError),
    ],
)
def test_http_method_raises_api_exceptions(
    http_method: str,
    status_code: int,
    exception_class: Type[APIError],
    base_url: str,
    requests_mock: Mocker,
) -> None:
    message = "Something is wrong."
    response_payload = {"message": message}
    getattr(requests_mock, http_method)(
        f"{base_url}/status",
        status_code=status_code,
        text=json.dumps(response_payload),
    )
    with pytest.raises(exception_class, match=message):
        session = Session.get_instance()
        getattr(session, http_method)("/status")


@pytest.mark.parametrize("response_payload", ["no valid JSON", "{}"])
def test_request_handles_errors_without_message(
    response_payload: str, base_url: str, requests_mock: Mocker
) -> None:
    requests_mock.get(
        f"https://example.org/status", status_code=400, text=response_payload
    )
    with pytest.raises(BadRequestError, match="API request error."):
        session = Session.get_instance()
        session.request("GET", "/status")


@pytest.mark.parametrize(
    "http_method, response_payload", product(HTTP_METHODS, ["no valid JSON", "{}"])
)
def test_http_method_handles_errors_without_message(
    http_method: str, response_payload: str, base_url: str, requests_mock: Mocker
) -> None:
    getattr(requests_mock, http_method)(
        f"{base_url}/status", status_code=400, text=response_payload
    )
    with pytest.raises(BadRequestError, match="API request error."):
        session = Session.get_instance()
        getattr(session, http_method)("/status")


def test_logging_in(base_url: str, requests_mock: Mocker) -> None:
    username = "john"
    password = "top_secret"
    token = "secret_token"
    token_payload = {"token": token}
    auth_header = f"Bearer {token}"

    def match_token_request(request):
        return (
            f"username={username}" in request.text
            and f"password={password}" in request.text
            and request.headers["Content-Type"] == "application/x-www-form-urlencoded"
        )

    requests_mock.post(
        f"{base_url}/token",
        text=json.dumps(token_payload),
        additional_matcher=match_token_request,
    )

    requests_mock.get(
        f"{base_url}/proposals",
        additional_matcher=lambda req: req.headers.get("Authorization") == auth_header,
    )

    # You aren't logged in.
    session = Session.get_instance()
    assert not session.logged_in

    # Log in.
    session.login(username, password)

    # Make a request. The request is accepted by the request mocker only if logging has
    # worked, as the Authorixzation HTTP header is checked for.
    session.get("/proposals")

    # You are logged in.
    assert session.logged_in


@pytest.mark.parametrize("token_payload", ["invalid JSON", "{}"])
def test_login_raises_api_error_for_invalid_server_response(
    token_payload: str, base_url: str, requests_mock: Mocker
) -> None:
    username = "john"
    password = "top_secret"

    requests_mock.post(f"{base_url}/token", text=json.dumps(token_payload))

    with pytest.raises(APIError, match="parsed"):
        session = Session.get_instance()
        session.login(username, password)


def test_request_after_logging_out(base_url: str, requests_mock: Mocker) -> None:
    username = "john"
    password = "top_secret"
    credentials = {"username": username, "password": password}
    token = "secret_token"
    token_payload = {"token": token}

    requests_mock.post(
        f"{base_url}/token",
        text=json.dumps(token_payload),
    )

    requests_mock.get(
        f"{base_url}/proposals",
        additional_matcher=lambda req: "Authorization" not in req.headers,
    )

    # Log in, log out again and make a request.
    session = Session.get_instance()
    session.login(username, password)
    session.logout()
    session.get("/proposals")

    # You are logged out.
    assert not session.logged_in


def test_logout_may_be_called_if_not_logged_in():
    session = Session.get_instance()
    session.logout()
    assert True
