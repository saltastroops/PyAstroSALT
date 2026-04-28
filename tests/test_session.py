from pyastrosalt.session import Session


def test_production_server_is_the_default():
    """Test that by default the production server is used."""
    session = Session()
    assert session.base_url == Session.PRODUCTION_BASE_URL


def test_use_playground():
    """Test that use_playground switches to the playground server."""
    session = Session()
    assert session.base_url != Session.PLAYGROUND_BASE_URL
    session.use_playground()
    assert session.base_url == Session.PLAYGROUND_BASE_URL


def test_use_production_server():
    """Test that use_playground switches to the playground server."""
    session = Session()
    session.use_playground()
    assert session.base_url != Session.PRODUCTION_BASE_URL
    session.use_production_server()
    assert session.base_url == Session.PRODUCTION_BASE_URL
