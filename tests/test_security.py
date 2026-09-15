"""S4 tests: secrets never reach logs; disclaimers always present."""
import json
import logging

import pytest
from fastapi.testclient import TestClient

import api_server
from auth.keys import APIKeyStore
from observability import JsonLogFormatter
from providers.base import make_envelope


def test_api_key_not_logged(tmp_path, monkeypatch, caplog):
    store = APIKeyStore(str(tmp_path / "keys.db"))
    monkeypatch.setattr(api_server, "api_key_store", store)
    api_server.rate_limiter.reset()
    secret_key = store.create_key("pro", "log-check")

    with caplog.at_level(logging.DEBUG):
        client = TestClient(api_server.app)
        response = client.get("/version", headers={"x-api-key": secret_key})

    assert response.status_code == 200
    for record in caplog.records:
        assert secret_key not in record.getMessage()
        assert secret_key not in json.dumps(getattr(record, "__dict__", {}), default=str)
    api_server.rate_limiter.reset()


def test_json_formatter_whitelists_fields():
    formatter = JsonLogFormatter()
    record = logging.LogRecord(
        name="x", level=logging.INFO, pathname=__file__, lineno=1,
        msg="request done", args=(), exc_info=None,
    )
    record.api_key = "cms_SUPER_SECRET"  # extra field outside whitelist

    payload = json.loads(formatter.format(record))

    assert "api_key" not in payload
    assert "cms_SUPER_SECRET" not in json.dumps(payload)


def test_envelope_contains_disclaimer():
    envelope = make_envelope({"x": 1}, source="test")
    assert envelope["meta"]["disclaimer"] == "Not financial advice."


@pytest.mark.asyncio
async def test_gas_response_has_disclaimer(monkeypatch):
    import tools.gas as gas_module
    from tests.test_gas_tracker import FakeProvider

    monkeypatch.setattr(gas_module, "_get_onchain_provider", lambda: FakeProvider())

    async def _price(chain):
        return 3000.0, []

    monkeypatch.setattr(gas_module, "_native_price_usd", _price)
    out = await gas_module.gas_tracker("ethereum")
    assert out["meta"]["disclaimer"] == "Not financial advice."
