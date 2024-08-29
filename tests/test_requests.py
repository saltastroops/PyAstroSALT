import pytest

from pyastrosalt.requests import Session


def test_session_is_a_singleton() -> None:
    instance_1 = Session.get_instance()
    instance_2 = Session.get_instance()

    assert instance_1 is not None
    assert instance_1 is instance_2


def test_request_makes_a_request_to_the_correct_url(requests_mock) -> None:
    requests_mock.get("https://example.org/status", text="status")
    response = Session.get_instance().request("GET", "/status")
    assert response.status_code == 200
    assert response.text == "status"


@pytest.mark.parametrize(
    "url", ("http://example.org/status", "https://example.org/status")
)
def test_request_rejects_full_urls(url: str) -> None:
    with pytest.raises(ValueError, match="base URL"):
        session = Session.get_instance()
        session.request("GET", url)
    assert True


@pytest.mark.parametrize("endpoint", ("status", "//status"))
def test_request_requires_single_leading_slash_for_endpoint(endpoint: str) -> None:
    with pytest.raises(ValueError, match="must start with a single slash"):
        session = Session.get_instance()
        session.request("GET", endpoint)
    assert True
