from app import app


def test_hello_world():
    client = app.test_client()
    response = client.get("/")
    assert response.status_code == 200
    assert response.data.decode() == "Hello World"


def test_healthz():
    client = app.test_client()
    response = client.get("/healthz")
    assert response.status_code == 200
