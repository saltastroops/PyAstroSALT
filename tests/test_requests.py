from itertools import product

import pytest

from pyastrosalt.requests import Session


HTTP_METHODS = ("get",)


def test_session_is_a_singleton() -> None:
    instance_1 = Session.get_instance()
    instance_2 = Session.get_instance()

    assert instance_1 is not None
    assert instance_1 is instance_2


def test_request_makes_a_request_to_the_correct_url(requests_mock) -> None:
    requests_mock.get("https://example.org/status", text="status")
    session = Session.get_instance()
    response = session.request("GET", "/status")
    assert response.status_code == 200
    assert response.text == "status"


@pytest.mark.parametrize("http_method", HTTP_METHODS)
def test_http_method_makes_a_request_to_the_correct_url(
    http_method: str, requests_mock
) -> None:
    requests_mock.get("https://example.org/status", text="status")
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
