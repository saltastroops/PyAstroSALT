from unittest.mock import patch, MagicMock

from pyastrosalt.auth import login, logout


class FakeSession:
    login = MagicMock()
    logout = MagicMock()


def test_login():
    fake_session = FakeSession()
    with patch("pyastrosalt.auth.Session", autospec=True) as session_mock:
        session_mock.get_instance.return_value = fake_session
        login(username="john", password="john_password")
        fake_session.login.assert_called_with("john", "john_password")


def test_logout():
    fake_session = FakeSession()
    with patch("pyastrosalt.auth.Session", autospec=True) as session_mock:
        session_mock.get_instance.return_value = fake_session
        logout()
        fake_session.logout.assert_called_with()
