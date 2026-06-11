"""配置管理 — 从环境变量读取所有配置项。"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


# --- Deepseek API ---
DEEPSEEK_API_KEY: str = os.environ.get("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE_URL: str = os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")
DEEPSEEK_MODEL: str = os.environ.get("DEEPSEEK_MODEL", "deepseek-chat")

# --- 服务 ---
HOST: str = os.environ.get("HOST", "0.0.0.0")
PORT: int = int(os.environ.get("PORT", "8000"))
DEBUG: bool = os.environ.get("DEBUG", "false").lower() in ("true", "1", "yes")

# --- 数据库 ---
_db_path_env = os.environ.get("DB_PATH")
if _db_path_env:
    DB_PATH: Path = Path(_db_path_env)
else:
    DB_PATH: Path = Path.home() / ".panel_studio" / "panel.db"
