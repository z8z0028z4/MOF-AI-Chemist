from pathlib import Path
from unittest.mock import Mock

import pytest


@pytest.mark.unit
@pytest.mark.fast
def test_binary_architecture_normalizes_file_output():
    from backend.services.mof.griday_builder import binary_matches_host

    assert binary_matches_host("aarch64", "ELF 64-bit LSB pie executable, ARM aarch64")
    assert binary_matches_host("x86_64", "ELF 64-bit LSB pie executable, x86-64")
    assert not binary_matches_host("aarch64", "ELF 64-bit LSB executable, x86-64")


@pytest.mark.unit
@pytest.mark.fast
def test_matching_griday_is_reused_without_build(tmp_path):
    from backend.services.mof.griday_builder import ensure_griday_compatible

    grid_gen = tmp_path / "scripts" / "grid_gen"
    grid_gen.parent.mkdir()
    grid_gen.write_bytes(b"binary")
    run = Mock(return_value=Mock(returncode=0, stdout="ELF 64-bit LSB x86-64", stderr=""))

    result = ensure_griday_compatible(
        tmp_path, host_arch="x86_64", run=run, binary_info=lambda _: "ELF 64-bit LSB x86-64"
    )

    assert result.ready is True
    assert result.rebuilt is False
    run.assert_not_called()


@pytest.mark.unit
@pytest.mark.fast
def test_mismatch_rebuild_cleans_objects_and_verifies_binary(tmp_path):
    from backend.services.mof.griday_builder import ensure_griday_compatible

    root = tmp_path
    scripts = root / "scripts"
    scripts.mkdir()
    (root / "Makefile").write_text("all:")
    (scripts / "Makefile").write_text("all:")
    (scripts / "grid_gen").write_bytes(b"old")
    (root / "old.o").write_bytes(b"stale")
    calls = []

    def fake_run(cmd, **kwargs):
        calls.append(cmd)
        if cmd[:2] == ["make", "-C"]:
            (scripts / "grid_gen").write_bytes(b"arm")
        return Mock(returncode=0, stdout="", stderr="")

    result = ensure_griday_compatible(
        root,
        host_arch="aarch64",
        run=fake_run,
        binary_info=lambda _: "ELF 64-bit LSB aarch64" if (scripts / "grid_gen").read_bytes() == b"arm" else "ELF 64-bit LSB x86-64",
    )

    assert result.ready is True
    assert result.rebuilt is True
    assert not (root / "old.o").exists()
    assert ["make", "clean"] in calls
    assert ["make", "-C", "scripts"] in calls


@pytest.mark.unit
@pytest.mark.fast
def test_build_failure_is_not_ready(tmp_path):
    from backend.services.mof.griday_builder import ensure_griday_compatible

    scripts = tmp_path / "scripts"
    scripts.mkdir()
    (tmp_path / "Makefile").write_text("all:")
    (scripts / "Makefile").write_text("all:")
    (scripts / "grid_gen").write_bytes(b"x86")

    result = ensure_griday_compatible(
        tmp_path,
        host_arch="aarch64",
        run=lambda *args, **kwargs: Mock(returncode=2, stdout="", stderr="compiler missing"),
        binary_info=lambda _: "ELF 64-bit LSB x86-64",
    )

    assert result.ready is False
    assert "compiler missing" in result.error


@pytest.mark.unit
@pytest.mark.fast
def test_worker_preserves_upstream_false_diagnostic(tmp_path, monkeypatch):
    from backend.workers.mof import pmtransformer_worker as worker

    log = tmp_path / "prepare_data.log"
    log.write_text("2026 - /input/large.cif failed : supercell have more than max_length\n")
    monkeypatch.setattr(worker, "_preparation_diagnostic", lambda *_: "supercell have more than max_length")
    assert worker._preparation_diagnostic("large.cif", tmp_path) == "supercell have more than max_length"


@pytest.mark.unit
@pytest.mark.fast
def test_worker_exception_diagnostic_includes_exception_context():
    from backend.workers.mof.pmtransformer_worker import _format_preparation_exception

    message = _format_preparation_exception("demo.cif", OSError(8, "Exec format error"))
    assert "demo.cif" in message
    assert "OSError" in message
    assert "Exec format error" in message
