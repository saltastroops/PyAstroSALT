import pytest
import requests
import responses

from pyastrosalt.web import (
    DEFAULT_STATUS_CODE_ERRORS,
    HttpStatusError,
    check_for_http_errors, set_base_url, api_url,
)
from tests.conftest import does_not_raise


def test_set_base_url_changes_the_base_url():
    """Test that set_base_url changes the base URL."""
    set_base_url("http://www.example.com")

    assert api_url("ping") == "http://www.example.com/ping"


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
def test_check_for_errors_does_not_raise_for_non_error_codes(status_code: int) -> None:
    """Test that check_for_http_error uses a generic message if necessary."""
    responses.add(
        method="GET",
        url="http://example.com",
        body="Some response body.",
        status=status_code,
    )

    response = requests.get("http://example.com")
    with does_not_raise():
        check_for_http_errors(response)
