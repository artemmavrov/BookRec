from pathlib import Path

import pytest
from pydantic import ValidationError

from bookrec.config import Settings, get_settings


def test_settings_defaults() -> None:
    settings = Settings()

    assert settings.log_level == "INFO"
    assert settings.log_json is True
    assert settings.health_check_timeout == 2.0


def test_settings_read_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("BOOKREC_DATABASE_DSN", "postgresql://u:p@db:5432/books")
    monkeypatch.setenv("BOOKREC_LOG_LEVEL", "DEBUG")
    monkeypatch.setenv("BOOKREC_HEALTH_CHECK_TIMEOUT", "5.5")

    settings = Settings()

    assert settings.database_dsn == "postgresql://u:p@db:5432/books"
    assert settings.log_level == "DEBUG"
    assert settings.health_check_timeout == 5.5


def test_settings_require_database_dsn(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("BOOKREC_DATABASE_DSN")

    with pytest.raises(ValidationError):
        Settings(_env_file=None)


def test_settings_reject_invalid_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("BOOKREC_HEALTH_CHECK_TIMEOUT", "abc")

    with pytest.raises(ValidationError):
        Settings()


def test_settings_ignore_unrelated_keys_in_env_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("BOOKREC_DATABASE_DSN")
    env_file = tmp_path / ".env"
    env_file.write_text(
        "POSTGRES_USER=bookrec\nBOOKREC_DATABASE_DSN=postgresql://u:p@db:5432/books\n",
        encoding="utf-8",
    )

    settings = Settings(_env_file=env_file)

    assert settings.database_dsn == "postgresql://u:p@db:5432/books"


def test_get_settings_is_cached() -> None:
    assert get_settings() is get_settings()
