import os
import runpy
import unittest
from pathlib import Path
from unittest.mock import patch


CONFIG_PATH = Path(__file__).resolve().parents[1] / "app" / "config.py"


class DatabaseConfigTests(unittest.TestCase):
    def load_config(self, **environment):
        # Load only configuration, never the application or a real database.
        with patch.dict(os.environ, environment, clear=True), \
                patch("dotenv.load_dotenv"), patch("os.makedirs"):
            return runpy.run_path(str(CONFIG_PATH))["Config"]

    def test_production_requires_database_url(self):
        for value in (None, "", "   "):
            with self.subTest(value=value):
                env = {"FLASK_ENV": "production"}
                if value is not None:
                    env["DATABASE_URL"] = value
                with self.assertRaisesRegex(ValueError, "DATABASE_URL is required"):
                    self.load_config(**env)

    def test_production_rejects_sqlite(self):
        for url in ("sqlite:///check8_fixed.db", "sqlite+pysqlite:///:memory:"):
            with self.subTest(url=url):
                with self.assertRaisesRegex(ValueError, "Production requires PostgreSQL"):
                    self.load_config(FLASK_ENV="production", DATABASE_URL=url)

    def test_render_cannot_fall_back_even_without_production_flag(self):
        for env in ({}, {"DATABASE_URL": "sqlite:///check8_fixed.db"}):
            with self.subTest(env=env):
                with self.assertRaises(ValueError):
                    self.load_config(RENDER="true", **env)

    def test_postgresql_urls_use_installed_driver_and_preserve_credentials(self):
        suffix = "postgres.example:encoded%40password@pooler.example:5432/postgres?sslmode=require"
        for scheme in ("postgres", "postgresql", "postgresql+psycopg2"):
            with self.subTest(scheme=scheme):
                config = self.load_config(
                    FLASK_ENV="production", DATABASE_URL=f"  {scheme}://{suffix}  "
                )
                self.assertEqual(config.SQLALCHEMY_DATABASE_URI, f"postgresql+psycopg2://{suffix}")
                self.assertTrue(config.SQLALCHEMY_ENGINE_OPTIONS["pool_pre_ping"])

    def test_invalid_url_error_does_not_expose_secret(self):
        for url in ("invalid-secret", "postgresql://user:secret@host:invalid/db"):
            with self.subTest(url=url):
                with self.assertRaises(ValueError) as caught:
                    self.load_config(FLASK_ENV="production", DATABASE_URL=url)
                self.assertNotIn("secret", str(caught.exception))

    def test_development_can_still_use_local_sqlite(self):
        config = self.load_config()
        self.assertTrue(config.SQLALCHEMY_DATABASE_URI.startswith("sqlite:///"))
        config = self.load_config(DATABASE_URL="sqlite:///local.db")
        self.assertEqual(config.SQLALCHEMY_DATABASE_URI, "sqlite:///local.db")


if __name__ == "__main__":
    unittest.main()
