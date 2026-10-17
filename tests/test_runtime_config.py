import unittest
from pathlib import Path

from runtime_config import (
    RuntimeConfigurationError,
    validate_data_configuration,
    validate_database_write_path,
)

TEST_ROOT = Path(__file__).resolve().parents[1] / ".test-tmp" / "runtime-config"


class RuntimeConfigurationTests(unittest.TestCase):
    def test_mode_must_be_explicit(self):
        with self.assertRaises(RuntimeConfigurationError):
            validate_data_configuration("", TEST_ROOT / "data", TEST_ROOT / "production")

    def test_development_cannot_use_production_directory(self):
        production = TEST_ROOT / "production"
        with self.assertRaises(RuntimeConfigurationError):
            validate_data_configuration("development", production, production)
        with self.assertRaises(RuntimeConfigurationError):
            validate_data_configuration("test", production / "child", production)
        with self.assertRaises(RuntimeConfigurationError):
            validate_database_write_path(
                production / "monitor.db", "development", production
            )

    def test_production_cannot_be_redirected_to_another_directory(self):
        with self.assertRaises(RuntimeConfigurationError):
            validate_data_configuration("production", TEST_ROOT / "other", TEST_ROOT / "production")

    def test_isolated_development_and_test_directories_are_allowed(self):
        production = TEST_ROOT / "production"
        self.assertEqual(
            validate_data_configuration("development", TEST_ROOT / "development", production),
            (TEST_ROOT / "development").resolve(),
        )
        self.assertEqual(
            validate_data_configuration("test", TEST_ROOT / "test", production),
            (TEST_ROOT / "test").resolve(),
        )


if __name__ == "__main__":
    unittest.main()
