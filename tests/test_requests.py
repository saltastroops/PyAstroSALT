from pyastrosalt.requests import Session


def test_session_is_a_singleton() -> None:
    instance_1 = Session.get_instance()
    instance_2 = Session.get_instance()

    assert instance_1 is not None
    assert instance_1 is instance_2
