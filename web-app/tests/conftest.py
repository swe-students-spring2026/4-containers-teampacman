"""Pytest fixtures for Flask tests."""

from __future__ import annotations

import pytest

import app as app_module


@pytest.fixture
def app():
    """Provide the Flask app with testing config (pytest-flask)."""
    app_module.app.config["TESTING"] = True
    app_module.reset_gaze_cache_for_tests()
    yield app_module.app
    app_module.reset_gaze_cache_for_tests()
