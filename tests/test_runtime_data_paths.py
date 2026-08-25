from pathlib import Path

import pytest


@pytest.mark.fast
@pytest.mark.unit
def test_runtime_data_paths_are_centralized_under_data_dir():
    from backend import config

    assert config.DATA_DIR == config.PROJECT_ROOT / "tests" / "test_data"
    assert Path(config.PAPER_DIR) == config.DATA_DIR / "papers"
    assert Path(config.EXPERIMENT_DIR) == config.DATA_DIR / "experiment"
    assert Path(config.VECTOR_INDEX_DIR) == config.DATA_DIR / "vector_index"
    assert Path(config.PARSED_CHEMICALS_DIR) == config.DATA_DIR / "parsed_chemicals"
    assert Path(config.METADATA_REGISTRY_PATH) == config.DATA_DIR / "metadata_registry.xlsx"


@pytest.mark.fast
@pytest.mark.unit
def test_services_reuse_configured_runtime_data_paths():
    from backend import config
    from backend.api.routes import paper as paper_routes
    from backend.services import embedding_service, knowledge_service, metadata_registry, pubchem_service
    from backend.services.chemical_database_service import ChemicalDatabaseService

    assert paper_routes.PAPERS_DIR == config.PAPER_DIR
    assert embedding_service.VECTOR_INDEX_DIR == config.VECTOR_INDEX_DIR
    assert knowledge_service.EXPERIMENT_DIR == config.EXPERIMENT_DIR
    assert metadata_registry.REGISTRY_PATH == config.METADATA_REGISTRY_PATH
    assert pubchem_service.PARSED_CHEMICAL_DIR == config.PARSED_CHEMICALS_DIR
    assert ChemicalDatabaseService().parsed_dir == config.PARSED_CHEMICALS_DIR


@pytest.mark.fast
@pytest.mark.unit
def test_relative_path_resolution_is_independent_of_current_working_directory(monkeypatch, tmp_path):
    from backend import config

    monkeypatch.chdir(tmp_path)

    resolved = Path(config.resolve_project_path("local_data/papers/example.pdf"))

    assert resolved == config.PROJECT_ROOT / "local_data" / "papers" / "example.pdf"
