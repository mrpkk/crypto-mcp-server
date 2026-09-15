"""Smart alert engine — evaluates rules against LIVE tools.

Not noise: every fired alert answers WHY IT MATTERS, with the live source
and the actual numbers. Rules that cannot be evaluated are reported in
meta.warnings (never silently skipped, never faked).
"""
from __future__ import annotations

from typing import Any

from providers.base import make_envelope


async def evaluate_rules(rules: list[dict[str, Any]]) -> dict[str, Any]:
    alerts: list[dict[str, Any]] = []
    warnings: list[str] = []

    for rule in rules:
        rule_id = rule.get("id")
        kind = rule.get("kind")
        params = rule.get("params") or {}
        try:
            if kind == "price_move":
                await _eval_price_move(rule_id, params, alerts, warnings)
            elif kind == "gas_below":
                await _eval_gas_below(rule_id, params, alerts, warnings)
            elif kind == "whale_above":
                await _eval_whale_above(rule_id, params, alerts, warnings)
            else:
                warnings.append(f"rule {rule_id}: unknown kind '{kind}'")
        except Exception as exc:
            warnings.append(f"rule {rule_id}: {exc}")

    data = {"alerts": alerts, "count": len(alerts), "rules_evaluated": len(rules)}
    return make_envelope(data, source="alert engine (live tools)", warnings=warnings)


async def _eval_price_move(rule_id: Any, params: dict, alerts: list, warnings: list) -> None:
    symbol = str(params.get("symbol", "BTC")).upper()
    threshold = float(params.get("threshold_pct", 5))
    from tools.price import get_price

    env = await get_price(f"{symbol}/USDT")
    if "error" in env:
        warnings.append(f"rule {rule_id}: price unavailable ({env['error']['code']})")
        return
    change = env["data"].get("change_24h")
    if change is None:
        warnings.append(f"rule {rule_id}: no 24h change for {symbol}")
        return
    if abs(float(change)) >= threshold:
        direction = "вырос" if change > 0 else "упал"
        alerts.append(
            {
                "rule_id": rule_id,
                "kind": "price_move",
                "symbol": symbol,
                "message": f"{symbol} {direction} на {change:+.2f}% за 24ч (порог {threshold}%)",
                "why_it_matters": "Движение превышает заданный порог — возможен вход/выход или пересмотр риска.",
                "values": {"change_24h": change, "price_usd": env["data"].get("price_usd")},
                "source": env["meta"]["source"],
                "timestamp": env["meta"]["timestamp"],
            }
        )


async def _eval_gas_below(rule_id: Any, params: dict, alerts: list, warnings: list) -> None:
    chain = str(params.get("chain", "ethereum")).lower()
    threshold = float(params.get("gwei_below", 10))
    from tools.gas import gas_tracker

    env = await gas_tracker(chain)
    if "error" in env:
        warnings.append(f"rule {rule_id}: gas unavailable ({env['error']['code']})")
        return
    gwei = env["data"].get("gas_price_gwei")
    if gwei is not None and float(gwei) <= threshold:
        alerts.append(
            {
                "rule_id": rule_id,
                "kind": "gas_below",
                "chain": chain,
                "message": f"{chain}: gas {gwei} gwei ≤ {threshold} — дешёвое окно",
                "why_it_matters": "Транзакции сейчас дешевле порога: хорошее время для переводов/свопов.",
                "values": {"gas_price_gwei": gwei},
                "source": env["meta"]["source"],
                "timestamp": env["meta"]["timestamp"],
            }
        )


async def _eval_whale_above(rule_id: Any, params: dict, alerts: list, warnings: list) -> None:
    min_usd = float(params.get("min_usd", 1_000_000))
    from tools.whales import whale_alerts

    env = await whale_alerts(min_value_usd=min_usd)
    if "error" in env:
        warnings.append(f"rule {rule_id}: whales unavailable ({env['error']['code']})")
        return
    for item in env["data"]["alerts"][:5]:
        amount_usd = item.get("amount_usd")
        alerts.append(
            {
                "rule_id": rule_id,
                "kind": "whale_above",
                "message": f"{item['token_symbol']}: перевод ≈ ${amount_usd:,.0f}",
                "why_it_matters": "Крупный on-chain перевод — возможное движение ликвидности.",
                "values": {"amount": item["amount"], "amount_usd": amount_usd, "chain": item.get("chain")},
                "source": env["meta"]["source"],
                "timestamp": item.get("timestamp"),
            }
        )
