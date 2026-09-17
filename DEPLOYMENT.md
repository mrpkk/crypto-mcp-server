# DEPLOYMENT — Āgama v2

## Local (recommended)

```bash
git clone https://github.com/mrpkk/crypto-mcp-server.git
cd crypto-mcp-server
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # заполнить по необходимости

python main.py                    # MCP (stdio) — для агентов
python api_server.py 8006         # REST + dashboard на 127.0.0.1:8006
```

## Environment (~/.env и/или проектный .env)

| Переменная | Назначение | Обязательна |
|---|---|---|
| `ETHERSCAN_API_KEY` | whale tools (Etherscan V2) | для whales |
| `GIGACHAT_AUTH_KEY` | AI-слой (primary) | для AI-инструментов |
| `GITHUB_TOKEN` | GitHub Models (fallback LLM) | опционально |
| `MISTRAL_API_KEY` | резервный LLM | опционально |
| `WHALE_WATCHLIST` | адреса через запятую для `whale_alerts` | опционально |
| `CORS_ORIGINS` | allowlist origins (по умолчанию `*`) | не обязательно |
| `PRO_API_KEYS` | legacy pro-ключи (заменены store из SQLite) | нет |
| `BUILD_SHA` | отображается в `/version` | нет |

Секреты хранятся только в окружении/`~/.env` и никогда не коммитятся.

## Production checklist

- [ ] `CORS_ORIGINS` = конкретные домены (не `*`)
- [ ] API-ключи созданы и выданы (`APIKeyStore.create_key`)
- [ ] Обратный прокси с TLS перед `api_server` (uvicorn за nginx/caddy)
- [ ] `/health` и `/ready` подключены к мониторингу; `/metrics` — к скрейперу
- [ ] Логи пишутся в JSON (включается автоматически при запуске `api_server.py`)

## systemd (пример)

```ini
[Unit]
Description=Āgama API
After=network.target

[Service]
WorkingDirectory=/home/USER/crypto-mcp-server
ExecStart=/home/USER/crypto-mcp-server/venv/bin/python api_server.py 8006
Restart=on-failure
EnvironmentFile=/home/USER/.env

[Install]
WantedBy=multi-user.target
```

## Docker

```bash
docker build -t agama .
docker run --rm -p 8006:8006 --env-file .env agama
```
