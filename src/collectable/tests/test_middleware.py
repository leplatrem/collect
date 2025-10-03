# Additions to your existing test_views.py file


def test_health(db, client):
    response = client.get("/health/")
    assert response.status_code == 200


def test_readiness(db, client):
    response = client.get("/readiness/")
    assert response.status_code == 200
