from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.unit
@pytest.mark.fast
def test_backend_launchers_default_to_loopback():
    launcher_paths = (
        "start_react.sh",
        "run_backend.sh",
        "run_backend.bat",
        "restart_backend.bat",
        "scripts/run_backend.bat",
        "scripts/restart_backend.bat",
    )

    for relative_path in launcher_paths:
        content = (ROOT / relative_path).read_text(encoding="utf-8")
        assert "0.0.0.0" not in content, relative_path
        assert "--host 127.0.0.1" in content, relative_path


@pytest.mark.unit
@pytest.mark.fast
def test_direct_backend_execution_defaults_to_loopback():
    content = (ROOT / "backend/main.py").read_text(encoding="utf-8")

    assert 'host="127.0.0.1"' in content
    assert 'host="0.0.0.0"' not in content


@pytest.mark.unit
@pytest.mark.fast
def test_vite_server_defaults_to_loopback():
    content = (ROOT / "frontend/vite.config.js").read_text(encoding="utf-8")

    assert "host: '127.0.0.1'" in content
    assert "host: true" not in content


@pytest.mark.unit
def test_vite_supports_explicit_managed_ports_without_changing_defaults():
    content = (ROOT / "frontend/vite.config.js").read_text(encoding="utf-8")

    assert "process.env.MOF_FRONTEND_PORT || 3000" in content
    assert "process.env.MOF_BACKEND_PORT || 8000" in content
    assert "target: `http://localhost:${backendPort}`" in content


@pytest.mark.unit
def test_start_react_propagates_explicit_ports_and_keeps_defaults():
    content = (ROOT / "start_react.sh").read_text(encoding="utf-8")

    assert 'BACKEND_PORT="${MOF_BACKEND_PORT:-8000}"' in content
    assert 'FRONTEND_PORT="${MOF_FRONTEND_PORT:-3000}"' in content
    assert '--port "$BACKEND_PORT"' in content
    assert 'MOF_FRONTEND_PORT="$FRONTEND_PORT" MOF_BACKEND_PORT="$BACKEND_PORT" npm run dev' in content

