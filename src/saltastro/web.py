from typing import Optional, cast

# TODO: Replace with correct URL.
from urllib.parse import urljoin

import requests

SALT_API_URL = "http://localhost:8001"


DEFAULT_STATUS_CODE_ERRORS = {
    400: "It seems there was a problem with your input.",
    401: "You are not authenticated. Please use saltastro.web.login to authenticate.",
    403: "You are not allowed to perform this action.",
    404: "The required API endpoint could not be found. Please contact SALT.",
    500: "An internal server error has occurred. Please contact SALT.",
}


class SessionHandler:
    """Utility class for handling API requests."""

    _session: requests.Session = requests.Session()
    _access_token: Optional[str] = None

    @classmethod
    def get_session(cls) -> requests.Session:
        """
        Return the requests session for making HTTP API requests.

        Returns
        -------
        `~requests.Session`
            Requests session.
        """
        return cls._session

    @classmethod
    def set_access_token(cls, access_token: str) -> None:
        """
        Make sure the requests session sends an Authorization header.

        Parameters
        ----------
        access_token: str
            The access token to pass in the Authorization header.
        """
        cls._access_token = access_token
        cls._session.headers.update({"Authorization": f"Bearer {access_token}"})

    @classmethod
    def delete_access_token(cls) -> None:
        """Make sure the requests session does not send an Authorization header."""
        cls._access_token = None
        del cls._session.headers["Authorization"]


class HttpStatusError(BaseException):
    """
    An exception describing an error for an HTTP response with an error status code.

    Parameters
    ----------
    status_code: int
        HTTP status code.
    message: str
        Error message

    Attributes
    ----------
    status_code: int
        HTTP status code.
    message: str
        Error message
    """

    def __init__(self, status_code: int, message: str):
        self.status_code = status_code
        self.message = message


def login(username: str, password: str) -> None:
    """
    Login on the SALT server.

    This function requests an API token from the server. This token is automatically
    added to all requests made with the `~requests.Session` object returned by the
    `~saltastro.web.session` function.

    Parameters
    ----------
    username: str
        The username, as used in the SALT Web Manager or Principal Investigator Proposal
        Tool.
    password: str
        The password, as used in the SALT Web Manager or Principal Investigator Proposal
        Tool.
    """
    resp = requests.post(
        urljoin(SALT_API_URL, "/token/"),
        data={"username": username, "password": password},
    )
    check_for_http_errors(resp)
    access_token = resp.json()["access_token"]
    SessionHandler.set_access_token(access_token)


def logout() -> None:
    """
    Log out from the SALT server.

    This function removes the API token from the `requests.Session` object returned by
    the `~saltastro.web.session` function.
    """
    SessionHandler.delete_access_token()


def check_for_http_errors(response: requests.Response) -> None:
    """
    Raise an error if the given response has an HTTP error status code.

    If the given response has an HTTP code of 400 or above, an
    `~saltastro.web.HttpStatusError` is raised, which contains the status code and an
    error message. The message is determined as follows:

    * If the response body is a JSON object and has a message property, the value of
    that property is used.
    * Otherwise, if the the response body is a JSON object and has an error property,
    the value of that property is used.
    * Otherwise a generic message based on the status code is used.

    Parameters
    ----------
    response: `requests.Response`
        HTTP response.
    """
    status_code = response.status_code
    if status_code < 400:
        return

    message: Optional[str] = None
    try:
        json = response.json()
        if "message" in json:
            message = str(json["message"])
        elif "error" in json:
            message = str(json["error"])
    except requests.exceptions.JSONDecodeError:
        pass

    if message is None:
        message = DEFAULT_STATUS_CODE_ERRORS.get(
            status_code, f"The request failed with a status code {status_code}."
        )

    raise HttpStatusError(status_code=status_code, message=cast(str, message))
