"""This module provides methods for logging in and out from the SALT server."""

from pyastrosalt.session import Session


def login(username: str, password: str) -> None:
    """
    Log in to the SALT server.

    Args:
        username: A username belonging to a SALT account.
        password: The password belonging to the username.

    Raises:
        NotAuthenticatedError: The username or password is wrong.
    """
    Session.get_instance().login(username, password)


def logout() -> None:
    """
    Log out from the SALT server.
    """
    Session.get_instance().logout()
