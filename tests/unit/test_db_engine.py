"""Unit tests for database engine and session factory."""

from unittest.mock import MagicMock, patch

import src.db as db_module


class TestGetEngine:
    def setup_method(self):
        db_module._engine = None

    def teardown_method(self):
        db_module._engine = None

    @patch("src.db.create_async_engine")
    @patch("src.db.get_settings")
    def test_creates_engine(self, mock_settings, mock_create):
        mock_settings.return_value = MagicMock(
            async_database_url="postgresql+asyncpg://test:test@localhost/test",
            is_development=False,
        )
        mock_create.return_value = MagicMock()

        engine = db_module.get_engine()

        assert engine is not None
        mock_create.assert_called_once()

    @patch("src.db.create_async_engine")
    @patch("src.db.get_settings")
    def test_caches_engine(self, mock_settings, mock_create):
        mock_settings.return_value = MagicMock(
            async_database_url="postgresql+asyncpg://test:test@localhost/test",
            is_development=False,
        )
        mock_create.return_value = MagicMock()

        engine1 = db_module.get_engine()
        engine2 = db_module.get_engine()

        assert engine1 is engine2
        mock_create.assert_called_once()


class TestGetSessionFactory:
    def setup_method(self):
        db_module._engine = None
        db_module._session_factory = None

    def teardown_method(self):
        db_module._engine = None
        db_module._session_factory = None

    @patch("src.db.create_async_engine")
    @patch("src.db.get_settings")
    def test_creates_session_factory(self, mock_settings, mock_create):
        mock_settings.return_value = MagicMock(
            async_database_url="postgresql+asyncpg://test:test@localhost/test",
            is_development=False,
        )
        mock_create.return_value = MagicMock()

        factory = db_module.get_session_factory()

        assert factory is not None

    @patch("src.db.create_async_engine")
    @patch("src.db.get_settings")
    def test_caches_session_factory(self, mock_settings, mock_create):
        mock_settings.return_value = MagicMock(
            async_database_url="postgresql+asyncpg://test:test@localhost/test",
            is_development=False,
        )
        mock_create.return_value = MagicMock()

        factory1 = db_module.get_session_factory()
        factory2 = db_module.get_session_factory()

        assert factory1 is factory2
