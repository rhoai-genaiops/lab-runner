"""Unit tests for the module 3 summarization trace seed."""

import unittest
from types import SimpleNamespace
from unittest.mock import patch

from lab_runner.config import Config
from lab_runner.steps.base import StepStatus
from lab_runner.steps.trace_step import SeedSummarizationTraceStep


def _config() -> Config:
    return Config(username="user1", password="unused", cluster_domain="apps.example.com")


class SeedSummarizationTraceStepTest(unittest.TestCase):
    def test_skips_when_a_trace_already_exists(self):
        step = SeedSummarizationTraceStep(namespace="user1-canopy")
        found = SimpleNamespace(returncode=0, stdout="ok\n", stderr="")
        with patch("lab_runner.steps.trace_step.oc.exec_in_pod", return_value=found) as exec_pod:
            self.assertTrue(step.verify(_config()))
        self.assertIn("summarization", exec_pod.call_args.args[2][2])
        self.assertEqual(exec_pod.call_args.args[1], "user1-canopy")

    def test_posts_summarization_and_waits_for_the_trace(self):
        step = SeedSummarizationTraceStep(namespace="user1-canopy")
        posted = SimpleNamespace(returncode=0, stdout="ok\n", stderr="")
        found = SimpleNamespace(returncode=0, stdout="ok\n", stderr="")
        with (
            patch("lab_runner.steps.trace_step.oc.exec_in_pod", side_effect=[posted, found]) as exec_pod,
            patch("lab_runner.steps.trace_step.time.sleep"),
        ):
            result = step.run(_config())

        self.assertEqual(result.status, StepStatus.SUCCESS)
        request, check = exec_pod.call_args_list
        self.assertEqual(request.args[0], "app.kubernetes.io/name=canopy-be")
        self.assertEqual(request.args[1], "user1-canopy")
        self.assertIn("127.0.0.1:8000/summarization", request.args[2][2])
        self.assertIn("Redwood Digital University", request.args[2][2])
        self.assertIn("get_experiment_by_name", check.args[2][2])

    def test_module_3_ends_with_the_seed_step(self):
        from pathlib import Path

        source = Path("lab_runner/modules/m03_scale_101.py").read_text()
        last_append = source.rfind("steps.append(")
        self.assertIn("SeedSummarizationTraceStep", source[last_append:])
        self.assertIn("namespace=ns", source[last_append:])


if __name__ == "__main__":
    unittest.main()
