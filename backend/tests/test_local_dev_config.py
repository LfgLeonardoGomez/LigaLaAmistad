"""A developer runner must not inherit production upload credentials from .env."""

import os
from pathlib import Path
import subprocess
import sys


def test_explicit_local_settings_file_does_not_inherit_default_dotenv(tmp_path):
    env = os.environ.copy()
    for key in list(env):
        if key.upper().startswith("CLOUDINARY_"):
            del env[key]
    env.update({
        "LIGA_ENV_FILE": str(tmp_path / "absent-local-settings.env"),
        "DATABASE_URL": "sqlite:///:memory:",
        "SECRET_KEY": "private-local-config-test-key-2026",
        "COOKIE_SECURE": "false", "COOKIE_SAMESITE": "lax",
    })
    result = subprocess.run([
        sys.executable, "-c",
        "from app.core.config import settings; "
        "assert settings.database_url == 'sqlite:///:memory:'; "
        "assert not settings.cloudinary_is_configured",
    ], cwd=Path(__file__).resolve().parents[1], env=env, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
