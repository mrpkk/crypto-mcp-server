from pydantic_settings import BaseSettings
from pathlib import Path


class Settings(BaseSettings):
    github_token: str = ""
    mistral_api_key: str = ""
    etherscan_api_key: str = ""
    alchemy_api_key: str = ""
    infura_project_id: str = ""

    db_path: str = str(Path(__file__).parent / "data" / "crypto_mcp.db")

    default_chain: str = "ethereum"
    supported_chains: list[str] = ["ethereum", "bsc", "polygon", "arbitrum", "optimism", "base"]

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
