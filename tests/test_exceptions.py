from unittest.mock import Mock

import pytest
from pyastrosalt.exceptions import (
    APIError,
    BadRequestError,
    ForbiddenError,
    NotAuthenticatedError,
    NotFoundError,
    ServerError,
)


def test_http_exception_has_message_as_string_representation() -> None:
    mock_response = Mock()
    mock_response.status_code = 418
    error = APIError("I'm a teapot.", mock_response)

    assert str(error) == "I'm a teapot."


def test_api_error_has_correct_status_code() -> None:
    mock_response = Mock()
    mock_response.status_code = 418
    error = APIError("I'm a teapot.", mock_response)

    assert error.status_code == 418


def test_bad_request_error_requires_status_code_400() -> None:
    # Try to create an error with an incorrect status code.
    mock_response = Mock()
    mock_response.status_code = 418
    with pytest.raises(ValueError, match="400"):
        BadRequestError("The proposal does not exist.", mock_response)

    # Create an error with the correct status code.
    mock_response.status_code = 400
    BadRequestError("The proposal does not exist.", mock_response)
    assert True


def test_not_authenticated_error_requires_status_code_401() -> None:
    # Try to create an error with an incorrect status code.
    mock_response = Mock()
    mock_response.status_code = 418
    with pytest.raises(ValueError, match="401"):
        NotAuthenticatedError("The proposal does not exist.", mock_response)

    # Create an error with the correct status code.
    mock_response.status_code = 401
    NotAuthenticatedError("The proposal does not exist.", mock_response)
    assert True


def test_forbidden_error_requires_status_code_403() -> None:
    # Try to create an error with an incorrect status code.
    mock_response = Mock()
    mock_response.status_code = 418
    with pytest.raises(ValueError, match="403"):
        ForbiddenError("You are not allowed to do this.", mock_response)

    # Create an error with the correct status code.
    mock_response.status_code = 403
    ForbiddenError("You are not allowed to do this.", mock_response)
    assert True


def test_not_found_error_requires_status_code_404() -> None:
    # Try to create an error with an incorrect status code.
    mock_response = Mock()
    mock_response.status_code = 418
    with pytest.raises(ValueError, match="404"):
        NotFoundError("The proposal does not exist.", mock_response)

    # Create an error with the correct status code.
    mock_response.status_code = 404
    NotFoundError("The proposal does not exist.", mock_response)
    assert True


def test_server_error_requires_status_code_500() -> None:
    # Try to create an error with an incorrect status code.
    mock_response = Mock()
    mock_response.status_code = 418
    with pytest.raises(ValueError, match="500"):
        ServerError("The proposal does not exist.", mock_response)

    # Create an error with the correct status code.
    mock_response.status_code = 500
    ServerError("The proposal does not exist.", mock_response)
    assert True
