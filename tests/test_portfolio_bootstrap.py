from __future__ import annotations

import fcntl
from io import StringIO
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from scripts import bootstrap_portfolio
import traffic_sim.portfolio_release as release
from tests.test_portfolio_release import FIXED_CLOCK, _closed_support, _generator, _make_repository


class PortfolioBootstrapCliTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        _make_repository(self.root)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def invoke(self, *arguments: str, generator=None) -> tuple[int, dict[str, object], str]:
        output = StringIO()
        code = bootstrap_portfolio.main(
            ["--repository-root", str(self.root), *arguments],
            generator=generator,
            stdout=output,
        )
        text = output.getvalue()
        self.assertEqual(len(text.splitlines()), 1, text)
        return code, json.loads(text), text

    def test_success_emits_exactly_one_json_document(self) -> None:
        with _closed_support():
            code, payload, text = self.invoke("--run-id", "cli-success", generator=_generator())
        self.assertEqual(code, 0)
        self.assertEqual(payload["status"], "promoted")
        self.assertEqual(payload["runId"], "cli-success")
        self.assertEqual(payload["artifactCount"], 11)
        self.assertTrue(text.endswith("\n"))

    def test_generation_failure_uses_exit_one_and_machine_code(self) -> None:
        def fail(_context: release.GenerationContext) -> None:
            raise ValueError("injected generation failure")

        with _closed_support():
            code, payload, _ = self.invoke("--run-id", "cli-failure", generator=fail)
        self.assertEqual(code, bootstrap_portfolio.GENERATION_FAILURE_EXIT)
        self.assertEqual(payload["status"], "error")
        self.assertEqual(payload["code"], "generation_failed")
        self.assertIn("injected generation failure", payload["message"])

    def test_lock_timeout_uses_exit_75_and_machine_code(self) -> None:
        lock = self.root / "reports" / "portfolio" / ".portfolio-release.lock"
        lock.parent.mkdir(parents=True, exist_ok=True)
        with lock.open("a+", encoding="utf-8") as handle:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            try:
                with _closed_support():
                    code, payload, _ = self.invoke(
                        "--run-id",
                        "cli-contended",
                        "--lock-timeout",
                        "0",
                        generator=_generator(),
                    )
            finally:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        self.assertEqual(code, bootstrap_portfolio.LOCK_TIMEOUT_EXIT)
        self.assertEqual(payload["code"], "lock_timeout")

    def test_verify_sources_and_current_modes(self) -> None:
        code, payload, _ = self.invoke("--verify-sources")
        self.assertEqual(code, 0)
        self.assertEqual(payload["status"], "verified")
        self.assertEqual(payload["sourceVerification"]["requiredCount"], 2)
        with _closed_support():
            release.promote_portfolio_release(
                _generator(),
                repository_root=self.root,
                run_id="cli-verify",
                clock=FIXED_CLOCK,
                lock_timeout_seconds=0,
            )
            code, payload, _ = self.invoke("--verify-current")
        self.assertEqual(code, 0)
        self.assertEqual(payload["runId"], "cli-verify")
        self.assertEqual(payload["compatibilityAliases"]["aliasCount"], 11)

    def test_post_promotion_alias_warning_is_still_exit_zero(self) -> None:
        summary = {
            "status": "promoted_with_alias_error",
            "runId": "warning-run",
            "aliases": {"status": "failed", "errors": ["injected"]},
        }
        with mock.patch.object(bootstrap_portfolio, "promote_portfolio_release", return_value=summary):
            code, payload, _ = self.invoke("--run-id", "warning-run", generator=_generator())
        self.assertEqual(code, 0)
        self.assertEqual(payload["status"], "promoted_with_alias_error")

    def test_unknown_scenario_is_rejected_without_generation(self) -> None:
        code, payload, _ = self.invoke(
            "--scenario-id",
            "not-abay",
            "--run-id",
            "wrong-scenario",
            generator=_generator(),
        )
        self.assertEqual(code, 1)
        self.assertEqual(payload["code"], "generation_failed")


if __name__ == "__main__":
    unittest.main()
