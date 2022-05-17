from urllib.parse import urljoin

import requests

from pyastrosalt.web import SALT_API_URL, SessionHandler, check_for_http_errors


def login(username: str, password: str) -> None:
    """
    Login on the SALT server.

    This function requests an API token from the server. This token is automatically
    added to all requests made with the `~requests.Session` object returned by the
    `~pyastrosalt.web.SessionHandler.get_session` function.

    Parameters
    ----------
    username : str
        The username, as used in the SALT Web Manager or Principal Investigator Proposal
        Tool.
    password : str
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

    This function removes the API token from the `~requests.Session` object returned by
    the `~pyastrosalt.web.SessionHandler.get_session` function.
    """
    SessionHandler.delete_access_token()
