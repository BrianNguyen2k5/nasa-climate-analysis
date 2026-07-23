from __future__ import annotations

import os
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from ai_assistant.config import load_ai_config
from ai_assistant.models import (
    ModelAttemptsExhaustedError,
    ModelConfigurationError,
    build_model_attempts,
    execute_model_attempts,
)


class FakeProviderError(Exception):
    def __init__(self, message: str, status_code: int) -> None:
        super().__init__(message)
        self.status_code = status_code


class FakeClient:
    def __init__(self, behavior) -> None:
        self.behavior = behavior
        self.calls: list[tuple[str, str]] = []

    def call(self, attempt):
        signature = (attempt.key_source, attempt.model)
        self.calls.append(signature)
        return self.behavior(attempt)


def _config(
    *,
    primary_key: str | None = "primary-test-secret",
    backup_key: str | None = None,
    primary_model: str = "model-primary",
    backup_model: str = "model-backup",
):
    return SimpleNamespace(
        groq_api_key=primary_key,
        groq_api_key_backup=backup_key,
        groq_primary_model=primary_model,
        groq_backup_model=backup_model,
        groq_code_model="model-code",
        gemini_api_key=primary_key,
        gemini_api_key_backup=backup_key,
        gemini_primary_model=primary_model,
        gemini_backup_model=backup_model,
    )


def _signatures(attempts) -> list[tuple[str, str]]:
    return [(attempt.key_source, attempt.model) for attempt in attempts]


class ModelFallbackTests(unittest.TestCase):
    def test_01_primary_key_tries_primary_then_backup_model(self) -> None:
        attempts = build_model_attempts("groq", _config())

        self.assertEqual(
            _signatures(attempts),
            [
                ("primary", "model-primary"),
                ("primary", "model-backup"),
            ],
        )

    def test_02_primary_and_backup_keys_create_four_ordered_attempts(self) -> None:
        attempts = build_model_attempts(
            "groq",
            _config(backup_key="backup-test-secret"),
        )

        self.assertEqual(
            _signatures(attempts),
            [
                ("primary", "model-primary"),
                ("primary", "model-backup"),
                ("backup", "model-primary"),
                ("backup", "model-backup"),
            ],
        )
        for attempt in attempts:
            rendered = repr(attempt)
            self.assertNotIn("primary-test-secret", rendered)
            self.assertNotIn("backup-test-secret", rendered)

    def test_03_duplicate_backup_key_is_removed(self) -> None:
        attempts = build_model_attempts(
            "groq",
            _config(backup_key="primary-test-secret"),
        )

        self.assertEqual(
            _signatures(attempts),
            [
                ("primary", "model-primary"),
                ("primary", "model-backup"),
            ],
        )

    def test_04_duplicate_backup_model_is_removed(self) -> None:
        attempts = build_model_attempts(
            "groq",
            _config(backup_model="model-primary"),
        )

        self.assertEqual(
            _signatures(attempts),
            [("primary", "model-primary")],
        )

    def test_05_rate_limit_advances_to_next_attempt(self) -> None:
        attempts = build_model_attempts("groq", _config())

        def behavior(attempt):
            if attempt.model == "model-primary":
                raise FakeProviderError("rate limited", 429)
            return "ok"

        client = FakeClient(behavior)
        result = execute_model_attempts("Groq", attempts, client.call)

        self.assertEqual(result, "ok")
        self.assertEqual(
            client.calls,
            [
                ("primary", "model-primary"),
                ("primary", "model-backup"),
            ],
        )

    def test_06_unavailable_primary_model_uses_backup_model(self) -> None:
        attempts = build_model_attempts("gemini", _config())

        def behavior(attempt):
            if attempt.model == "model-primary":
                raise FakeProviderError("model unavailable", 404)
            return "backup-model-response"

        client = FakeClient(behavior)
        result = execute_model_attempts("Gemini", attempts, client.call)

        self.assertEqual(result, "backup-model-response")
        self.assertEqual(
            client.calls,
            [
                ("primary", "model-primary"),
                ("primary", "model-backup"),
            ],
        )

    def test_07_invalid_primary_key_can_reach_backup_key(self) -> None:
        attempts = build_model_attempts(
            "groq",
            _config(backup_key="backup-test-secret"),
        )

        def behavior(attempt):
            if attempt.key_source == "primary":
                raise FakeProviderError("invalid api key", 401)
            return "backup-key-response"

        client = FakeClient(behavior)
        result = execute_model_attempts("Groq", attempts, client.call)

        self.assertEqual(result, "backup-key-response")
        self.assertEqual(
            client.calls,
            [
                ("primary", "model-primary"),
                ("primary", "model-backup"),
                ("backup", "model-primary"),
            ],
        )

    def test_08_first_success_stops_remaining_attempts(self) -> None:
        attempts = build_model_attempts(
            "groq",
            _config(backup_key="backup-test-secret"),
        )
        client = FakeClient(lambda attempt: "first-response")

        result = execute_model_attempts("Groq", attempts, client.call)

        self.assertEqual(result, "first-response")
        self.assertEqual(client.calls, [("primary", "model-primary")])

    def test_09_non_retryable_error_stops_immediately(self) -> None:
        attempts = build_model_attempts(
            "groq",
            _config(backup_key="backup-test-secret"),
        )

        def behavior(attempt):
            raise ValueError("invalid application input")

        client = FakeClient(behavior)
        with self.assertRaisesRegex(ValueError, "invalid application input"):
            execute_model_attempts("Groq", attempts, client.call)

        self.assertEqual(client.calls, [("primary", "model-primary")])

    def test_10_all_retryable_failures_are_secret_safe(self) -> None:
        attempts = build_model_attempts(
            "groq",
            _config(backup_key="backup-test-secret"),
        )

        def behavior(attempt):
            raise FakeProviderError(
                f"provider unavailable for {attempt.key_source}",
                503,
            )

        client = FakeClient(behavior)
        with self.assertRaises(ModelAttemptsExhaustedError) as context:
            execute_model_attempts("Groq", attempts, client.call)

        message = str(context.exception)
        self.assertEqual(len(client.calls), 4)
        self.assertNotIn("primary-test-secret", message)
        self.assertNotIn("backup-test-secret", message)
        self.assertIn("Provider Groq không khả dụng", message)

    def test_11_missing_keys_does_not_call_provider(self) -> None:
        attempts = build_model_attempts(
            "groq",
            _config(primary_key=None, backup_key=None),
        )
        client = FakeClient(lambda attempt: "must-not-run")

        with self.assertRaisesRegex(
            ModelConfigurationError,
            "Chưa cấu hình API key",
        ):
            execute_model_attempts("Groq", attempts, client.call)

        self.assertEqual(attempts, [])
        self.assertEqual(client.calls, [])

    def test_12_each_request_restarts_from_standard_order(self) -> None:
        config = _config(backup_key="backup-test-secret")
        all_calls: list[list[tuple[str, str]]] = []

        for _ in range(2):
            attempts = build_model_attempts("groq", config)

            def behavior(attempt):
                if len(client.calls) == 1:
                    raise FakeProviderError("rate limited", 429)
                return "ok"

            client = FakeClient(behavior)
            result = execute_model_attempts("Groq", attempts, client.call)
            self.assertEqual(result, "ok")
            all_calls.append(client.calls)

        self.assertEqual(
            all_calls,
            [
                [
                    ("primary", "model-primary"),
                    ("primary", "model-backup"),
                ],
                [
                    ("primary", "model-primary"),
                    ("primary", "model-backup"),
                ],
            ],
        )

    def test_13_config_loads_primary_and_backup_environment_keys(self) -> None:
        environment = {
            "GROQ_API_KEY": "groq-primary-test",
            "GROQ_API_KEY_BACKUP": "groq-backup-test",
            "GEMINI_API_KEY": "gemini-primary-test",
            "GEMINI_API_KEY_BACKUP": "gemini-backup-test",
        }

        with (
            patch("ai_assistant.config.load_dotenv"),
            patch.dict(os.environ, environment, clear=True),
        ):
            config = load_ai_config()

        self.assertTrue(config.groq_api_key == environment["GROQ_API_KEY"])
        self.assertTrue(
            config.groq_api_key_backup
            == environment["GROQ_API_KEY_BACKUP"]
        )
        self.assertTrue(config.gemini_api_key == environment["GEMINI_API_KEY"])
        self.assertTrue(
            config.gemini_api_key_backup
            == environment["GEMINI_API_KEY_BACKUP"]
        )


if __name__ == "__main__":
    unittest.main()
