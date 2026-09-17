/* Āgama dashboard — vanilla JS, XSS-safe (no innerHTML for data), honest error states. */
(() => {
  "use strict";

  const $ = (id) => document.getElementById(id);
  const api = (path) => fetch(path, { headers: { accept: "application/json" } }).then(async (r) => {
    const body = await r.json().catch(() => null);
    if (!r.ok || (body && body.error)) {
      const err = body && body.error ? body.error : { code: `HTTP_${r.status}`, message: "Request failed", suggested_action: null };
      const e = new Error(err.message || err.code);
      e.contract = err;
      throw e;
    }
    return body;
  });

  const QUALITY = [
    ["live", "LIVE"],
    ["cached", "CACHED"],
    ["stale", "STALE"],
    ["degraded", "DEGRADED"],
    ["unavailable", "UNAVAILABLE"],
  ];

  function qualityBadge(envelope) {
    let cls = "badge-live";
    let label = "LIVE";
    if (!envelope || envelope.error) {
      cls = "badge-unavailable";
      label = "UNAVAILABLE";
    } else {
      const meta = envelope.meta || {};
      const fresh = Number(meta.freshness_seconds || 0);
      if (meta.cached) { cls = "badge-cached"; label = "CACHED"; }
      if (fresh > 300) { cls = "badge-stale"; label = "STALE"; }
      if (meta.degraded) { cls = "badge-degraded"; label = "DEGRADED"; }
    }
    const span = document.createElement("span");
    span.className = `badge ${cls}`;
    span.appendChild(Object.assign(document.createElement("span"), { className: "dot" }));
    span.appendChild(document.createTextNode(label));
    return span;
  }

  function sourceLine(envelope) {
    const meta = envelope && envelope.meta ? envelope.meta : {};
    const el = document.createElement("div");
    el.className = "small muted";
    const when = meta.timestamp ? new Date(meta.timestamp).toLocaleTimeString() : "—";
    el.textContent = `source: ${meta.source || "n/a"} · ${when}`;
    return el;
  }

  function toast(message, kind = "info") {
    const host = $("toast-host");
    const el = document.createElement("div");
    el.className = `toast ${kind}`;
    el.textContent = message;
    host.appendChild(el);
    setTimeout(() => el.remove(), 6000);
  }

  function fmtUsd(value) {
    if (value === null || value === undefined) return "—";
    if (Math.abs(value) >= 1e9) return `$${(value / 1e9).toFixed(2)}B`;
    if (Math.abs(value) >= 1e6) return `$${(value / 1e6).toFixed(2)}M`;
    if (Math.abs(value) >= 1e3) return `$${value.toLocaleString("en-US", { maximumFractionDigits: 2 })}`;
    return `$${Number(value).toFixed(4)}`;
  }

  function metricCard(title, valueText, delta, envelope, symbol) {
    const card = document.createElement("div");
    card.className = "card";
    if (symbol) card.dataset.symbol = symbol;
    const header = document.createElement("div");
    header.className = "card-header";
    const h = document.createElement("h3");
    h.className = "card-title";
    h.textContent = title;
    header.appendChild(h);
    header.appendChild(qualityBadge(envelope));
    card.appendChild(header);

    const metric = document.createElement("div");
    metric.className = "metric";
    metric.textContent = valueText;
    card.appendChild(metric);

    if (delta !== null && delta !== undefined) {
      const d = document.createElement("div");
      d.className = `metric-delta ${Number(delta) >= 0 ? "up" : "down"}`;
      d.textContent = `${Number(delta) >= 0 ? "+" : ""}${Number(delta).toFixed(2)}% (24h)`;
      card.appendChild(d);
    }
    card.appendChild(sourceLine(envelope));
    return card;
  }

  async function renderPulse() {
    const host = $("pulse-cards");
    host.replaceChildren();
    for (const symbol of ["BTC", "ETH", "SOL"]) {
      const holder = document.createElement("div");
      holder.className = "card";
      holder.innerHTML = '<div class="skeleton" style="height:64px"></div>';
      host.appendChild(holder);
    }
    const gasHolder = document.createElement("div");
    gasHolder.className = "card";
    gasHolder.innerHTML = '<div class="skeleton" style="height:64px"></div>';
    host.appendChild(gasHolder);

    const results = await Promise.allSettled([
      api(`/price/${encodeURIComponent(symbol)}/USDT`),
      api(`/price/${encodeURIComponent(symbol)}/USDT`),
      api(`/price/${encodeURIComponent(symbol)}/USDT`),
    ]);
    host.replaceChildren();
    const symbols = ["BTC", "ETH", "SOL"];
    results.forEach((r, i) => {
      if (r.status === "fulfilled") {
        const env = r.value;
        host.appendChild(metricCard(symbols[i], fmtUsd(env.data.price_usd), env.data.change_24h, env, symbols[i]));
      } else {
        host.appendChild(metricCard(symbols[i], "—", null, { error: r.reason.contract || { code: "ERR" } }, symbols[i]));
      }
    });

    try {
      const gas = await api("/gas/ethereum");
      const gwei = gas.data.gas_price_gwei;
      const card = metricCard("ETH gas", `${gwei} gwei`, null, gas, "GAS");
      if (gas.data.native_price_usd) {
        const cost = document.createElement("div");
        cost.className = "small muted";
        cost.textContent = `transfer ≈ ${fmtUsd(gas.data.estimated_tx_cost_usd?.transfer)} · ETH ${fmtUsd(gas.data.native_price_usd)}`;
        card.appendChild(cost);
      }
      host.appendChild(card);
    } catch (e) {
      host.appendChild(metricCard("ETH gas", "—", null, { error: e.contract || { code: "ERR" } }, "GAS"));
    }
    $("pulse-updated").textContent = `обновлено ${new Date().toLocaleTimeString()}`;
  }

  async function renderTop() {
    const host = $("top-table");
    const badge = $("top-badge");
    try {
      const env = await api("/top?limit=8");
      badge.replaceWith(qualityBadge(env));
      const table = document.createElement("table");
      table.className = "table";
      table.innerHTML = "<thead><tr><th>Актив</th><th>Цена</th><th>24ч</th><th>Объём</th></tr></thead>";
      const tbody = document.createElement("tbody");
      env.data.items.forEach((item) => {
        const tr = document.createElement("tr");
        const cells = [
          item.symbol.replace("/USD", ""),
          fmtUsd(item.price_usd),
          item.change_24h === null ? "—" : `${Number(item.change_24h).toFixed(2)}%`,
          fmtUsd(item.volume_24h_usd),
        ];
        cells.forEach((text) => {
          const td = document.createElement("td");
          td.textContent = text;
          tr.appendChild(td);
        });
        tbody.appendChild(tr);
      });
      table.appendChild(tbody);
      host.replaceChildren(table);
    } catch (e) {
      host.replaceChildren(errorBox(e));
    }
  }

  async function renderYields() {
    const host = $("yields-table");
    const badge = $("yields-badge");
    try {
      const env = await api("/yields?min_apy=5&max_results=6");
      badge.replaceWith(qualityBadge(env));
      const table = document.createElement("table");
      table.className = "table";
      table.innerHTML = "<thead><tr><th>Протокол</th><th>Пул</th><th>Сеть</th><th>APY</th></tr></thead>";
      const tbody = document.createElement("tbody");
      env.data.items.forEach((pool) => {
        const tr = document.createElement("tr");
        [pool.protocol, pool.pool, pool.chain, `${pool.apy}%`].forEach((text) => {
          const td = document.createElement("td");
          td.textContent = text;
          tr.appendChild(td);
        });
        tbody.appendChild(tr);
      });
      table.appendChild(tbody);
      host.replaceChildren(table);
    } catch (e) {
      host.replaceChildren(errorBox(e));
    }
  }

  async function renderWhales() {
    const host = $("whales-table");
    const badge = $("whales-badge");
    try {
      const env = await api("/whales?min_value_usd=1000000&timeframe_hours=24");
      badge.replaceWith(qualityBadge(env));
      if (!env.data.alerts.length) {
        const empty = document.createElement("p");
        empty.className = "muted small";
        empty.textContent = "Крупных транзакций за окно не найдено (или watchlist пуст).";
        host.replaceChildren(empty);
        return;
      }
      const table = document.createElement("table");
      table.className = "table";
      table.innerHTML = "<thead><tr><th>Токен</th><th>Сумма</th><th>USD</th><th>Время</th></tr></thead>";
      const tbody = document.createElement("tbody");
      env.data.alerts.forEach((alert) => {
        const tr = document.createElement("tr");
        [alert.token_symbol, alert.amount.toFixed(4), fmtUsd(alert.amount_usd), new Date(alert.timestamp).toLocaleTimeString()]
          .forEach((text) => {
            const td = document.createElement("td");
            td.textContent = text;
            tr.appendChild(td);
          });
        tbody.appendChild(tr);
      });
      table.appendChild(tbody);
      host.replaceChildren(table);
    } catch (e) {
      host.replaceChildren(errorBox(e));
    }
  }

  function errorBox(e) {
    const box = document.createElement("div");
    box.className = "error-box";
    const contract = e.contract || {};
    box.textContent = `${contract.code || "ERROR"}: ${contract.message || e.message}`;
    if (contract.suggested_action) {
      const hint = document.createElement("div");
      hint.className = "small muted";
      hint.textContent = contract.suggested_action;
      box.appendChild(hint);
    }
    return box;
  }

  async function loadVersion() {
    try {
      const v = await api("/version");
      $("version-label").textContent = `v${v.version}`;
    } catch { /* non-critical */ }
  }


  async function renderWatchlist() {
    const host = $("watchlist-items");
    try {
      const list = await api("/watchlist");
      $("watchlist-count").textContent = String(list.items.length);
      if (!list.items.length) {
        host.textContent = "Пока пусто — добавьте актив, кошелёк или протокол.";
        return;
      }
      host.replaceChildren();
      list.items.forEach((item) => {
        const row = document.createElement("div");
        row.className = "row spread";
        const label = document.createElement("span");
        label.textContent = `[${item.kind}] ${item.value}${item.label ? " — " + item.label : ""}`;
        const del = document.createElement("button");
        del.className = "btn btn-ghost small";
        del.textContent = "✕";
        del.addEventListener("click", async () => {
          await fetch(`/watchlist/${item.id}`, { method: "DELETE" });
          renderWatchlist();
        });
        row.append(label, del);
        host.appendChild(row);
      });
    } catch (e) {
      host.replaceChildren(errorBox(e));
    }
  }

  async function addWatchlistItem() {
    const kind = $("wl-kind").value;
    const value = $("wl-value").value.trim();
    if (!value) return;
    try {
      await fetch("/watchlist", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ kind, value }),
      }).then(async (r) => { if (!r.ok) throw new Error((await r.json()).error?.message || "add failed"); });
      $("wl-value").value = "";
      renderWatchlist();
    } catch (e) {
      toast(e.message, "error");
    }
  }

  async function renderRules() {
    const host = $("alert-rules");
    try {
      const data = await api("/alerts");
      if (!data.rules.length) {
        host.textContent = "Правил нет.";
        return;
      }
      host.replaceChildren();
      data.rules.forEach((rule) => {
        const row = document.createElement("div");
        row.className = "row spread";
        const label = document.createElement("span");
        label.textContent = `#${rule.id} ${rule.kind} ${JSON.stringify(rule.params)}`;
        const del = document.createElement("button");
        del.className = "btn btn-ghost small";
        del.textContent = "✕";
        del.addEventListener("click", async () => {
          await fetch(`/alerts/${rule.id}`, { method: "DELETE" });
          renderRules();
        });
        row.append(label, del);
        host.appendChild(row);
      });
    } catch (e) {
      host.replaceChildren(errorBox(e));
    }
  }

  async function addRule() {
    const kind = $("rule-kind").value;
    const symbol = $("rule-symbol").value.trim() || "BTC";
    const threshold = Number($("rule-threshold").value || 5);
    let params = {};
    if (kind === "price_move") params = { symbol, threshold_pct: threshold };
    if (kind === "gas_below") params = { chain: "ethereum", gwei_below: threshold };
    if (kind === "whale_above") params = { min_usd: threshold * 1_000_000 };
    try {
      const response = await fetch("/alerts", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ kind, params }),
      });
      if (!response.ok) throw new Error((await response.json()).error?.message || "add failed");
      renderRules();
      toast("Правило добавлено", "success");
    } catch (e) {
      toast(e.message, "error");
    }
  }

  async function checkAlerts() {
    const host = $("alert-fires");
    host.replaceChildren(Object.assign(document.createElement("div"), { className: "skeleton", textContent: "" }));
    try {
      const env = await api("/alerts/check");
      host.replaceChildren();
      if (!env.data.alerts.length) {
        const none = document.createElement("p");
        none.className = "small muted";
        none.textContent = "Сработок нет (или правила не заданы).";
        host.appendChild(none);
        return;
      }
      env.data.alerts.forEach((fired) => {
        const box = document.createElement("div");
        box.className = "card";
        const title = document.createElement("div");
        title.textContent = fired.message;
        const why = document.createElement("div");
        why.className = "small muted";
        why.textContent = `Почему важно: ${fired.why_it_matters} · источник: ${fired.source}`;
        box.append(title, why);
        host.appendChild(box);
      });
    } catch (e) {
      host.replaceChildren(errorBox(e));
    }
  }

  function connectStream() {
    if (!window.EventSource) return;
    const stream = new EventSource("/stream/prices");
    stream.addEventListener("price", (event) => {
      try {
        const env = JSON.parse(event.data);
        if (!env.data || !env.data.symbol) return;
        const base = env.data.symbol.split("/")[0];
        const card = document.querySelector(`[data-symbol="${base}"]`);
        if (!card) return;
        const metric = card.querySelector(".metric");
        if (metric) metric.textContent = fmtUsd(env.data.price_usd);
        const delta = card.querySelector(".metric-delta");
        if (delta && env.data.change_24h !== null && env.data.change_24h !== undefined) {
          delta.textContent = `${Number(env.data.change_24h) >= 0 ? "+" : ""}${Number(env.data.change_24h).toFixed(2)}% (24h)`;
          delta.className = `metric-delta ${Number(env.data.change_24h) >= 0 ? "up" : "down"}`;
        }
      } catch { /* ignore malformed chunk */ }
    });
    stream.onerror = () => { /* EventSource переподключается сам */ };
  }

  function wireUi() {
    $("refresh-btn").addEventListener("click", () => refreshAll());
    $("wl-add").addEventListener("click", addWatchlistItem);
    $("rule-add").addEventListener("click", addRule);
    $("alerts-check").addEventListener("click", checkAlerts);
    $("theme-toggle").addEventListener("click", () => {
      const root = document.documentElement;
      const next = root.dataset.theme === "light" ? "dark" : "light";
      root.dataset.theme = next;
      localStorage.setItem("agama-theme", next);
    });
    $("demo-toggle").addEventListener("click", () => {
      $("demo-badge").classList.remove("hidden");
      toast("DEMO-режим: используются публичные free-источники (лимит 100 запросов/час).", "success");
    });
    $("onboarding-close").addEventListener("click", () => $("onboarding").remove());
    document.querySelectorAll(".nav-item").forEach((btn) => {
      btn.addEventListener("click", () => {
        document.querySelectorAll(".nav-item").forEach((b) => b.classList.remove("active"));
        btn.classList.add("active");
        if (btn.dataset.section !== "command") {
          toast("Раздел в разработке — сейчас доступен Command Center (Market Pulse).", "info");
        }
      });
    });
    const saved = localStorage.getItem("agama-theme");
    if (saved) document.documentElement.dataset.theme = saved;
  }

  async function refreshAll() {
    const tasks = [renderPulse(), renderTop(), renderYields(), renderWhales()];
    await Promise.allSettled(tasks);
  }

  wireUi();
  loadVersion();
  refreshAll();
  renderWatchlist();
  renderRules();
  connectStream();
  setInterval(renderPulse, 60000);
})();
