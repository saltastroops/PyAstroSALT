from typing import Literal

from requests import Response, Session as RequestsSession


_DEFAULT_BASE_URL = "https://example.org"


class Session:
    """
    The session for handling HTTP requests to the SALT API server.

    This is a wrapper around the session provided by the `requests` library. You can
    get the session by calling the `get_instance` method, which always returns the same
    session.

    Before making a request to the server requiring authentication you have to log in
    by using the `login` method. The `logout` method allows you to log out again.

    When making a request with the `request`, `get`, `post`, `put`, `patch` or `delete`
    method you have to supply the API endpoint without the base URL.
    """

    _session: "Session" = None  # type: ignore
    _requests_session: RequestsSession

    @classmethod
    def get_instance(cls) -> "Session":
        if not cls._session:
            cls._session = cls()
            cls._session._requests_session = RequestsSession()
        return cls._session

    def request(
        self,
        method: Literal["GET", "POST", "PUT", "PATCH", "DELETE"],
        endpoint: str,
        **kwargs,
    ) -> Response:
        """
        Make an HTTP request to the API server.

        Args:
            method: HTTP method for the request.
            endpoint: API endpoint, without the base URL, such as `"/status"`. The
              endpoint must start with a single slash.
            **kwargs: Keyword arguments, as accepted by the `request` method of the
              `requests` library.

        Returns:
            The server response, as returned by the `request` method of the `requests`
            library.

        Raises:
            BadRequest: The server responded with a 400 (Bad Request) error.
            NotAuthenticated: The server responded with a 401 (Not Authorized) error.
            Forbidden: The server responded with a 403 (Forbidden) error.
            ServerError: The server responded with a 500 (Internal Server Error) error.
            ValueError: The endpoint is invalid.
        """
        # Full URLs are not allowed.
        if endpoint.startswith("http://") or endpoint.startswith("https://"):
            raise ValueError(
                "The endpoint must be the path relative to the base URL, not the URL "
                'itself. An example would be "/status".'
            )

        # The endpoint must start with a single slash.
        if not endpoint.startswith("/") or endpoint.startswith("//"):
            raise ValueError(
                "The endpoint must start with a single slash. An example would be "
                '"/status".'
            )

        url = "https://example.org" + endpoint
        return self._requests_session.request(method, url, **kwargs)
