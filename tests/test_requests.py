import json
from itertools import product
from typing import Type

import pytest
from requests_mock import Mocker

from pyastrosalt.exceptions import APIError, BadRequestError
from pyastrosalt.requests import Session

HTTP_METHODS = ("get", "post", "put", "patch", "delete")


def test_session_is_a_singleton() -> None:
    instance_1 = Session.get_instance()
    instance_2 = Session.get_instance()

    assert instance_1 is not None
    assert instance_1 is instance_2


def test_request_makes_a_request_to_the_correct_url(
    base_url: str, requests_mock: Mocker
) -> None:
    requests_mock.get(f"{base_url}/status", text="status")
    session = Session.get_instance()
    response = session.request("GET", "/status")
    assert response.status_code == 200
    assert response.text == "status"


@pytest.mark.parametrize("http_method", HTTP_METHODS)
def test_http_method_makes_a_request_to_the_correct_url(
    http_method: str, base_url: str, requests_mock: Mocker
) -> None:
    getattr(requests_mock, http_method)(f"{base_url}/status", text="status")
    session = Session.get_instance()
    response = getattr(session, http_method)("/status")
    assert response.status_code == 200
    assert response.text == "status"


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
