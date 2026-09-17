"""S6 tests: static web dashboard served by the API."""
import pytest
from fastapi.testclient import TestClient

import api_server


@pytest.fixture()
def client():
    api_server.rate_limiter.reset()
    yield TestClient(api_server.app)
    api_server.rate_limiter.reset()


def test_dashboard_root_served(client):
    response = client.get("/")
    assert response.status_code == 200
    body = response.text
    assert "Āgama" in body
    assert "Market Pulse" in body
    assert "/static/styles.css" in body
    assert "/static/app.js" in body


def test_dashboard_has_onboarding_and_demo(client):
    body = client.get("/").text
    assert "Explore live data" in body
    assert "demo-badge" in body
    assert "Watchlist" in body
    assert "Smart alerts" in body


def test_tokens_css_served(client):
    response = client.get("/static/tokens.css")
    assert response.status_code == 200
    assert "--bg: #0a0e17" in response.text
    assert "--primary: #5b8def" in response.text


def test_styles_css_served(client):
    response = client.get("/static/styles.css")
    assert response.status_code == 200
    assert ".badge-live" in response.text
    assert ".skeleton" in response.text


def test_app_js_served(client):
    response = client.get("/static/app.js")
    assert response.status_code == 200
    assert "qualityBadge" in response.text
    assert "renderPulse" in response.text
    assert "connectStream" in response.text
    assert "renderWatchlist" in response.text
