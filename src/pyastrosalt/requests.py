"""This module facilitates HTTP requests to the SALT API.

Usage example:

  session = Session.get_instance()
  response = session.get("/status")

The session object has get, post, put, patch and delete methods, which as a rule accept
the same arguments as their counterparts in the `requests` library. The only exception
is the first argument, which in the `requests` library must be the full URL, but for the
methods of the session instance must be just the endpoint, such as `/status`.
"""

from typing import IO, Any, Dict, Literal, Optional, Sequence, Tuple, Union

from requests import Response
from requests import Session as RequestsSession
from requests.exceptions import JSONDecodeError as _JSONDecodeError

__all__ = ["Session"]

from pyastrosalt.exceptions import (
    APIError,
    BadRequestError,
    ForbiddenError,
    NotAuthenticatedError,
    NotFoundError,
    ServerError,
)

DEFAULT_BASE_URL = "https://example.org"


class Session:
    """The session for handling HTTP requests to the SALT API server.

    This is a wrapper around the session provided by the `requests` library. You can
    get the session by calling the `get_instance` method, which always returns the same
    session.

    Before making a request to the server requiring authentication you have to log in
    by using the `login` method. The `logout` method allows you to log out again.

    When making a request with the `request`, `get`, `post`, `put`, `patch` or `delete`
    method you have to supply the API endpoint without the base URL.

    You can change the base URL by setting the `base_url` property. This URL must not
    have a trailing slash.
    """

    _base_url: str  # type: ignore
    _requests_session: RequestsSession
    _session: "Session" = None  # type: ignore

    @classmethod
    def get_instance(cls) -> "Session":
        """Return the session for making HTTP requests to the SALT API."""
        if not cls._session:
            cls._session = cls()
            cls._session._base_url = DEFAULT_BASE_URL
            cls._session._requests_session = RequestsSession()
        return cls._session

    @property
    def base_url(self) -> str:
        """The base URL relative to which the request endpoints must be given."""
        return self._base_url

    @base_url.setter
    def base_url(self, value: str) -> None:
        if value.endswith("/"):
            raise ValueError("The base URL must not have a trailing slash.")
        self._base_url = value

    @property
    def logged_in(self) -> bool:
        """Indicates whether you are currently logged in."""
        return "Authorization" in self._requests_session.headers

    def login(self, username: str, password: str) -> None:
        """Log in to the SALT API server.

        The method requests an API token from the API server, which will be sent in an
        HTTP header in all further HTTP requests.

        Use the `logout` method to log out again.

        Args:
            username: A valid SALT account username.
            password: The password for the username.

        Raises:
            NotAuthenticatedError: The username or password is wrong.
            APIError: The server response cannot be parsed.
        """
        # Request an API token.
        data = {"username": username, "password": password}
        response = self.post("/token", data=data)
        try:
            token = response.json()["token"]
        except (_JSONDecodeError, KeyError, TypeError):
            raise APIError("The server response cannot be parsed.", response)

        # Send the token in an Authorization header.
        self._requests_session.headers.update({"Authorization": f"Bearer {token}"})

    def logout(self):
        """Log out from the API server.

        This method ensures that no authorization header will be sent any longer when
        requests are made.

        The method does nothing if you are not logged in when calling it.
        """
        if self.logged_in:
            self._requests_session.headers.pop("Authorization")

    def request(
        self,
        method: Literal["GET", "POST", "PUT", "PATCH", "DELETE"],
        endpoint: str,
        **kwargs,
    ) -> Response:
        """Make an HTTP request to the API server.

        Args:
            method: The HTTP method for the request.
            endpoint: The API endpoint, without the base URL, such as `"/status"`. The
              endpoint must start with a single slash.
            **kwargs: Keyword arguments, as accepted by the `request` method of the
              `requests` library.

        Returns:
            The server response, as returned by the `request` method of the `requests`
            library.

        Raises:
            BadRequestError: The server responded with a 400 (Bad Request) error.
            NotAuthenticatedError: The server responded with a 401 (Not Authorized)
              error.
            ForbiddenError: The server responded with a 403 (Forbidden) error.
            NotFoundError: The server responded with a 404 (Not Found) error.
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

        # Make the API request
        url = self.base_url + endpoint
        response = self._requests_session.request(method, url, **kwargs)

        # Handle errors
        self._handle_errors(response)

        return response

    def get(
        self,
        endpoint: str,
        params: Optional[Union[Dict, Sequence[Tuple], bytes]] = None,
        **kwargs,
    ) -> Response:
        """Make a GET request to the API server.

        Args:
            endpoint: The API endpoint, without the base URL, such as `"/status"`. The
              endpoint must start with a single slash.
            params: A dictionary, list of tuples or string to send in the query string.
            **kwargs: Keyword arguments, as accepted by the `request` method of the
              `requests` library.

        Returns:
            The server response, as returned by the `request` method of the `requests`
            library.

        Raises:
            BadRequestError: The server responded with a 400 (Bad Request) error.
            NotAuthenticatedError: The server responded with a 401 (Not Authorized)
              error.
            ForbiddenError: The server responded with a 403 (Forbidden) error.
            NotFoundError: The server responded with a 404 (Not Found) error.
            ServerError: The server responded with a 500 (Internal Server Error) error.
            ValueError: The endpoint is invalid.
        """
        return self.request("GET", endpoint, params=params, **kwargs)

    def post(
        self,
        endpoint: str,
        data: Optional[Union[Dict, Sequence[Tuple], bytes, IO]] = None,
        json: Optional[Any] = None,
        **kwargs,
    ) -> Response:
        """Make a POST request to the API server.

        Args:
            endpoint: The API endpoint, without the base URL, such as `"/status"`. The
              endpoint must start with a single slash.
            data: A dictionary, list of tuples, bytes, or file-like object to send in
              the body.
            json: A JSON-serializable Python object to send in the body.
            **kwargs: Keyword arguments, as accepted by the `request` method of the
              `requests` library.

        Returns:
            The server response, as returned by the `request` method of the `requests`
            library.

        Raises:
            BadRequestError: The server responded with a 400 (Bad Request) error.
            NotAuthenticatedError: The server responded with a 401 (Not Authorized)
              error.
            ForbiddenError: The server responded with a 403 (Forbidden) error.
            NotFoundError: The server responded with a 404 (Not Found) error.
            ServerError: The server responded with a 500 (Internal Server Error) error.
            ValueError: The endpoint is invalid.
        """
        return self.request("POST", endpoint, data=data, json=json, **kwargs)

    def put(
        self,
        endpoint: str,
        data: Optional[Union[Dict, Sequence[Tuple], bytes, IO]] = None,
        json: Optional[Any] = None,
        **kwargs,
    ) -> Response:
        """Make a PUT request to the API server.

        Args:
            endpoint: The API endpoint, without the base URL, such as `"/status"`. The
              endpoint must start with a single slash.
            data: A dictionary, list of tuples, bytes, or file-like object to send in
              the body.
            json: A JSON-serializable Python object to send in the body.
            **kwargs: Keyword arguments, as accepted by the `request` method of the
              `requests` library.

        Returns:
            The server response, as returned by the `request` method of the `requests`
            library.

        Raises:
            BadRequestError: The server responded with a 400 (Bad Request) error.
            NotAuthenticatedError: The server responded with a 401 (Not Authorized)
              error.
            ForbiddenError: The server responded with a 403 (Forbidden) error.
            NotFoundError: The server responded with a 404 (Not Found) error.
            ServerError: The server responded with a 500 (Internal Server Error) error.
            ValueError: The endpoint is invalid.
        """
        return self.request("PUT", endpoint, data=data, json=json, **kwargs)

    def patch(
        self,
        endpoint: str,
        data: Optional[Union[Dict, Sequence[Tuple], bytes, IO]] = None,
        json: Optional[Any] = None,
        **kwargs,
    ) -> Response:
        """Make a PATCH request to the API server.

        Args:
            endpoint: The API endpoint, without the base URL, such as `"/status"`. The
              endpoint must start with a single slash.
            data: A dictionary, list of tuples, bytes, or file-like object to send in
              the body.
            json: A JSON-serializable Python object to send in the body.
            **kwargs: Keyword arguments, as accepted by the `request` method of the
              `requests` library.

        Returns:
            The server response, as returned by the `request` method of the `requests`
            library.

        Raises:
            BadRequestError: The server responded with a 400 (Bad Request) error.
            NotAuthenticatedError: The server responded with a 401 (Not Authorized)
              error.
            ForbiddenError: The server responded with a 403 (Forbidden) error.
            NotFoundError: The server responded with a 404 (Not Found) error.
            ServerError: The server responded with a 500 (Internal Server Error) error.
            ValueError: The endpoint is invalid.
        """
        return self.request("PATCH", endpoint, data=data, json=json, **kwargs)

    def delete(self, endpoint: str, **kwargs) -> Response:
        """Make a DELETE request to the API server.

        Args:
            endpoint: The API endpoint, without the base URL, such as `"/status"`. The
              endpoint must start with a single slash.
            **kwargs: Keyword arguments, as accepted by the `request` method of the
              `requests` library.

        Returns:
            The server response, as returned by the `request` method of the `requests`
            library.

        Raises:
            BadRequestError: The server responded with a 400 (Bad Request) error.
            NotAuthenticatedError: The server responded with a 401 (Not Authorized)
              error.
            ForbiddenError: The server responded with a 403 (Forbidden) error.
            NotFoundError: The server responded with a 404 (Not Found) error.
            ServerError: The server responded with a 500 (Internal Server Error) error.
            ValueError: The endpoint is invalid.
        """
        return self.request("DELETE", endpoint, **kwargs)

    @classmethod
    def _handle_errors(cls, response: Response) -> None:
        status_code = response.status_code
        if status_code < 400:
            # No error.
            return

        # Get the error message. We assume that the server has returned a JSON object
        # with a message member. Ifd that's wrong we use a default message.
        default_message = "API request error."
        try:
            message = response.json()["message"]
        except (_JSONDecodeError, KeyError, TypeError):
            message = default_message
        if status_code == 400:
            raise BadRequestError(message, response)
        elif status_code == 401:
            raise NotAuthenticatedError(message, response)
        elif status_code == 403:
            raise ForbiddenError(message, response)
        elif status_code == 404:
            raise NotFoundError(message, response)
        elif status_code == 500:
            raise ServerError(message, response)
        else:
            raise APIError(message, response)
