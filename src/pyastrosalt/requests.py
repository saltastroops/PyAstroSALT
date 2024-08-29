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

    @classmethod
    def get_instance(cls) -> "Session":
        if not cls._session:
            cls._session = cls()
        return cls._session
