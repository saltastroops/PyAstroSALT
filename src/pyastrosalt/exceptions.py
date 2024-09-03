from requests import Response

__all__ = [
    "APIError",
    "BadRequestError",
    "NotAuthenticatedError",
    "ForbiddenError",
    "NotFoundError",
    "ServerError",
]


class APIError(Exception):
    """The server responded with a status code greater than or equal to 400.

    Attributes:
        message: The error message returned by the server. This should be an empty
          string if no message was returned.
    """

    message: str
    _response: Response

    def __init__(self, message: str, response: Response):
        """Initialize the exception.

        Args:
            message: The error message returned by the server. This should be an empty
              string if no message was returned.
            response: The server response.
        """
        self.message = message
        self._response = response

    @property
    def status_code(self) -> int:
        """The status code returned by the server."""
        return self._response.status_code

    def __str__(self) -> str:
        """Return the error message."""
        return self.message


class BadRequestError(APIError):
    """The server responded with the status code 400 (Bad Request).

    Attributes:
        message: The error message returned by the server. This should be an empty
          string if no message was returned.
    """

    def __init__(self, message: str, response: Response):
        """Initialize the exception.

        Args:
            message: The error message returned by the server. This should be an empty
              string if no message was returned.
            response: The server response. The status code of the response must be 400.
        """
        if response.status_code != 400:
            raise ValueError("The status code of the response must be 400.")
        super().__init__(message, response)


class NotAuthenticatedError(APIError):
    """The server responded with the status code 401 (Not Authorized).

    Attributes:
        message: The error message returned by the server. This should be an empty
          string if no message was returned.
    """

    def __init__(self, message: str, response: Response):
        """Initialize the exception.

        Args:
            message: The error message returned by the server. This should be an empty
              string if no message was returned.
            response: The server response. The status code of the response must be 401.
        """
        if response.status_code != 401:
            raise ValueError("The status code of the response must be 401.")
        super().__init__(message, response)


class ForbiddenError(APIError):
    """The server responded with the status code 403 (Forbidden).

    Attributes:
        message: The error message returned by the server. This should be an empty
          string if no message was returned.
    """

    def __init__(self, message: str, response: Response):
        """Initialize the exception.

        Args:
            message: The error message returned by the server. This should be an empty
              string if no message was returned.
            response: The server response. The status code of the response must be 403.
        """
        if response.status_code != 403:
            raise ValueError("The status code of the response must be 403.")
        super().__init__(message, response)


class NotFoundError(APIError):
    """The server responded with the status code 404 (Not Found).

    Attributes:
        message: The error message returned by the server. This should be an empty
          string if no message was returned.
    """

    def __init__(self, message: str, response: Response):
        """Initialize the exception.

        Args:
            message: The error message returned by the server. This should be an empty
              string if no message was returned.
            response: The server response. The status code of the response must be 404.
        """
        if response.status_code != 404:
            raise ValueError("The status code of the response must be 404.")
        super().__init__(message, response)


class ServerError(APIError):
    """The server responded with the status code 500 (Internal Server Error).

    Attributes:
        message: The error message returned by the server. This should be an empty
          string if no message was returned.
    """

    def __init__(self, message: str, response: Response):
        """Initialize the exception.

        Args:
            message: The error message returned by the server. This should be an empty
              string if no message was returned.
            response: The server response. The status code of the response must be 500.
        """
        if response.status_code != 500:
            raise ValueError("The status code of the response must be 500.")
        super().__init__(message, response)
