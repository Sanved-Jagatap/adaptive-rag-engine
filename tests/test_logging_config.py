import logging

from app.core.logging_config import configure_logging


def test_configure_logging_sets_root_level_from_settings(monkeypatch):
    from app.core.config import settings

    monkeypatch.setattr(settings, "log_level", "DEBUG")
    configure_logging()
    assert logging.getLogger().level == logging.DEBUG


def test_configure_logging_defaults_to_info_on_unknown_level(monkeypatch):
    from app.core.config import settings

    monkeypatch.setattr(settings, "log_level", "NOT_A_REAL_LEVEL")
    configure_logging()
    assert logging.getLogger().level == logging.INFO


def test_configure_logging_does_not_raise():
    # Smoke test — mainly guards against a typo breaking app startup,
    # since configure_logging() is called unconditionally when app.main
    # is imported.
    configure_logging()
