"""
Unit tests for pormake_runner / pmtransformer_runner demo-mode guards (TODO 13.0
card a): both runners must refuse to launch their subprocess (pormake_worker.py /
pmtransformer_worker.py) when demo mode is active for at least one stage, guarding
immediately before subprocess.Popen(...) in their _run_worker_thread job-start path.

Written FIRST per TDD: this guard doesn't exist yet, so these should fail (RED)
before implementation. We drive _run_worker_thread directly (not via start_job's
background thread) so failures/assertions surface synchronously in the test.

Each runner's real pipeline does other work (catalog resolution, private-settings
lookup) before reaching subprocess.Popen; those steps are mocked/faked here so the
test reaches the Popen call site and can distinguish "guard fired" (status message
mentions demo mode) from failing for an unrelated reason.
"""

import json
from unittest.mock import MagicMock, patch

import pytest


def _set_demo_mode_on(monkeypatch):
    _set_demo_mode_off(monkeypatch)
    monkeypatch.setenv("DEMO_MOCK_PROPERTY_PREDICTION", "true")


def _set_demo_mode_off(monkeypatch):
    from backend.core import demo_config

    for var in (
        "DEMO_MOCK_PROPOSAL",
        "DEMO_MOCK_GENERATE_NEW_IDEA",
        "DEMO_MOCK_PROPERTY_PREDICTION",
        "DEMO_MOCK_EXPERIMENT_DETAIL",
    ):
        monkeypatch.setenv(var, "false")
    demo_config.reset_cache_for_tests()


class _FakeRun:
    def __init__(self, run_dir):
        self.run_dir = run_dir
        self.status = "preparing"
        self.last_message = None


class _FakeRunStore:
    def __init__(self, run_dir):
        self._run = _FakeRun(run_dir)

    def update_status(self, run_id, status, progress=None, message=None):
        self._run.status = status
        self._run.last_message = message
        return self._run

    def get_run(self, run_id):
        return self._run


class TestPormakeRunnerDemoGuard:
    def test_does_not_launch_subprocess_when_demo_mode_active(self, monkeypatch, tmp_path):
        from backend.services.mof.pormake_runner import PormakeRunner

        _set_demo_mode_on(monkeypatch)

        run_dir = tmp_path
        (run_dir / "request.json").write_text(
            json.dumps({"node_id": "N1", "linker_id": "L1"}), encoding="utf-8"
        )

        run_store = _FakeRunStore(run_dir)
        artifact_service = MagicMock()
        tool_env_service = MagicMock()
        tool_env_service.is_installed.return_value = True

        runner = PormakeRunner(run_store, artifact_service, tool_env_service)

        fake_bb = {"pormake_code": "X", "coordination_number": 1}
        with patch(
            "backend.services.mof.pormake_runner.resolve_catalog_id",
            return_value=fake_bb,
        ), patch("backend.services.mof.pormake_runner.subprocess.Popen") as popen_mock:
            runner._run_worker_thread("demo-run")
            popen_mock.assert_not_called()

        assert run_store._run.status == "failed"
        assert "demo mode" in (run_store._run.last_message or "").lower()

    def test_does_launch_subprocess_when_demo_mode_off(self, monkeypatch, tmp_path):
        from backend.services.mof.pormake_runner import PormakeRunner

        _set_demo_mode_off(monkeypatch)

        run_dir = tmp_path
        (run_dir / "request.json").write_text(
            json.dumps({"node_id": "N1", "linker_id": "L1"}), encoding="utf-8"
        )

        run_store = _FakeRunStore(run_dir)
        artifact_service = MagicMock()
        tool_env_service = MagicMock()
        tool_env_service.is_installed.return_value = True
        tool_env_service.get_python_executable.return_value = "/usr/bin/python3"

        runner = PormakeRunner(run_store, artifact_service, tool_env_service)

        fake_bb = {"pormake_code": "X", "coordination_number": 1}
        fake_proc = MagicMock()
        fake_proc.wait.return_value = 0
        with patch(
            "backend.services.mof.pormake_runner.resolve_catalog_id",
            return_value=fake_bb,
        ), patch(
            "backend.services.mof.pormake_runner.subprocess.Popen", return_value=fake_proc
        ) as popen_mock:
            runner._run_worker_thread("real-run")
            popen_mock.assert_called_once()


    def test_launches_subprocess_when_property_demo_is_off_but_proposal_demo_is_on(
        self, monkeypatch, tmp_path
    ):
        from backend.services.mof.pormake_runner import PormakeRunner

        _set_demo_mode_off(monkeypatch)
        monkeypatch.setenv("DEMO_MOCK_PROPOSAL", "true")
        (tmp_path / "request.json").write_text(
            json.dumps({"node_id": "N1", "linker_id": "L1"}), encoding="utf-8"
        )
        run_store = _FakeRunStore(tmp_path)
        tool_env_service = MagicMock()
        tool_env_service.is_installed.return_value = True
        tool_env_service.get_python_executable.return_value = "/usr/bin/python3"
        runner = PormakeRunner(run_store, MagicMock(), tool_env_service)
        fake_proc = MagicMock()
        fake_proc.wait.return_value = 0

        with patch(
            "backend.services.mof.pormake_runner.resolve_catalog_id",
            return_value={"pormake_code": "X", "coordination_number": 1},
        ), patch(
            "backend.services.mof.pormake_runner.subprocess.Popen", return_value=fake_proc
        ) as popen_mock:
            runner._run_worker_thread("mixed-mode-run")

        popen_mock.assert_called_once()


class TestPmTransformerRunnerDemoGuard:
    def test_does_not_launch_subprocess_when_demo_mode_active(self, monkeypatch, tmp_path):
        from backend.services.mof.pmtransformer_runner import PmTransformerRunner

        _set_demo_mode_on(monkeypatch)

        run_dir = tmp_path
        input_dir = run_dir / "input_cifs"
        input_dir.mkdir()
        (input_dir / "sample.cif").write_text("fake cif", encoding="utf-8")
        (run_dir / "request.json").write_text(
            json.dumps({"profile_id": "p1"}), encoding="utf-8"
        )

        settings_path = tmp_path / "private_settings.json"
        settings_path.write_text(
            json.dumps(
                {
                    "profiles": [
                        {
                            "id": "p1",
                            "checkpoint_path": "ckpt.pt",
                            "downstream": "regression",
                            "normalization": {"mean": 0.0, "std": 1.0},
                        }
                    ]
                }
            ),
            encoding="utf-8",
        )

        run_store = _FakeRunStore(run_dir)
        artifact_service = MagicMock()
        tool_env_service = MagicMock()
        tool_env_service.is_installed.return_value = True

        runner = PmTransformerRunner(run_store, artifact_service, tool_env_service)

        with patch(
            "backend.services.mof.pmtransformer_runner.get_mof_private_settings_path",
            return_value=settings_path,
        ), patch("backend.services.mof.pmtransformer_runner.subprocess.Popen") as popen_mock:
            runner._run_worker_thread("demo-run")
            popen_mock.assert_not_called()

        assert run_store._run.status == "failed"
        assert "demo mode" in (run_store._run.last_message or "").lower()

    def test_launches_subprocess_when_property_demo_is_off_but_proposal_demo_is_on(
        self, monkeypatch, tmp_path
    ):
        from backend.services.mof.pmtransformer_runner import PmTransformerRunner

        _set_demo_mode_off(monkeypatch)
        monkeypatch.setenv("DEMO_MOCK_PROPOSAL", "true")
        input_dir = tmp_path / "input_cifs"
        input_dir.mkdir()
        (input_dir / "sample.cif").write_text("fake cif", encoding="utf-8")
        (tmp_path / "request.json").write_text(json.dumps({"profile_id": "p1"}), encoding="utf-8")
        settings_path = tmp_path / "private_settings.json"
        settings_path.write_text(
            json.dumps({"profiles": [{"id": "p1", "checkpoint_path": "ckpt.pt", "downstream": "regression", "normalization": {"mean": 0.0, "std": 1.0}}]}),
            encoding="utf-8",
        )
        run_store = _FakeRunStore(tmp_path)
        tool_env_service = MagicMock()
        tool_env_service.is_installed.return_value = True
        tool_env_service.get_python_executable.return_value = "/usr/bin/python3"
        runner = PmTransformerRunner(run_store, MagicMock(), tool_env_service)
        fake_proc = MagicMock()
        fake_proc.wait.return_value = 0

        with patch(
            "backend.services.mof.pmtransformer_runner.get_mof_private_settings_path",
            return_value=settings_path,
        ), patch(
            "backend.services.mof.pmtransformer_runner.subprocess.Popen", return_value=fake_proc
        ) as popen_mock:
            runner._run_worker_thread("mixed-mode-run")

        popen_mock.assert_called_once()
