"""
MOF feature API routes.
"""

import json
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, PlainTextResponse

import subprocess
from backend.api.models.mof_models import (
    CatalogItem,
    CifGeneratorJobRequest,
    JobStatusResponse,
    MofPrivateSettingsStatus,
    PormakeResolveRequest,
    PormakeResolveResponse,
    ProposalScreeningRequest,
    ProposalScreeningResponse,
    ProposalTranslateRequest,
    ProposalTranslateResponse,
    RunArtifact,
    RunStatusResponse,
    ToolInstallResponse,
    ToolInstallStatusResponse,
    ToolsStatusResponse,
    PropertyPredictorUploadJobRequest,
    VerifyCkptRequest,
    XrdPatternResponse,
)
from backend.config import MOF_DATA_DIR, PROJECT_ROOT
from backend.services.mof import (
    ArtifactNotFound,
    InvalidArtifactManifest,
    InvalidRunTransition,
    MofArtifactService,
    MofRunStore,
    RunNotFound,
    ToolEnvService,
    ToolReadinessError,
    get_public_catalog,
    load_safe_model_profiles,
    resolve_catalog_id,
    PormakeRunner,
    PmTransformerRunner,
)
from backend.services.mof.pormake_resolver import (
    LinkerResolutionError,
    resolve_pormake_candidates,
)
from backend.services.mof_settings_service import (
    get_mof_private_settings_path,
    get_mof_private_settings_status,
)
from backend.core import demo_config
from backend.services import demo_service

router = APIRouter(prefix="/mof", tags=["mof"])

# Initialize services
run_store = MofRunStore(MOF_DATA_DIR)
artifact_service = MofArtifactService(run_store)
tool_env_service = ToolEnvService(MOF_DATA_DIR)
pormake_runner = PormakeRunner(run_store, artifact_service, tool_env_service)
pmtransformer_runner = PmTransformerRunner(run_store, artifact_service, tool_env_service)



@router.get("/private-settings/status", response_model=MofPrivateSettingsStatus)
def get_private_settings_status():
    """Return redacted PMTransformer/MOF local settings readiness."""
    return get_mof_private_settings_status()


# --- Tool readiness ---


@router.get("/tools/status", response_model=ToolsStatusResponse)
def get_tools_status():
    """Return installation and readiness status of heavy tools."""
    pormake_status = (
        {
            "ready": True,
            "installed": True,
            "version": "demo-canned",
            "error": None,
        }
        if demo_config.is_stage_demo("property_prediction")
        else tool_env_service.get_status("pormake")
    )
    if demo_config.is_stage_demo("property_prediction"):
        pmtransformer_status = {
            "ready": True,
            "installed": True,
            "version": "demo-canned",
            "error": None,
        }
    else:
        pmtransformer_status = tool_env_service.get_status("pmtransformer")
        pmtransformer_status.update(tool_env_service.get_xrd_preflight())
    return {
        "pormake": pormake_status,
        "pmtransformer": pmtransformer_status,
    }


@router.post("/tools/{tool}/install", response_model=ToolInstallResponse)
def install_tool(tool: str):
    """Trigger background installation of a tool environment."""
    if tool not in ("pormake", "pmtransformer"):
        raise HTTPException(status_code=400, detail=f"Unknown tool: {tool}")
    try:
        return tool_env_service.start_install(tool)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tools/{tool}/install-status", response_model=ToolInstallStatusResponse)
def get_tool_install_status(tool: str):
    """Check background installation status and logs."""
    if tool not in ("pormake", "pmtransformer"):
        raise HTTPException(status_code=400, detail=f"Unknown tool: {tool}")
    return tool_env_service.get_install_status(tool)


# --- CIF Generator ---


@router.get("/cif-generator/catalog", response_model=list[CatalogItem])
def get_cif_generator_catalog():
    """Return building-block catalog of curated friendly names."""
    return get_public_catalog()


@router.get("/cif-generator/topologies", response_model=list[str])
def get_cif_generator_topologies(
    node_id: Optional[str] = None, linker_id: Optional[str] = None
):
    """Return compatible topologies filtered by selected building blocks."""
    return tool_env_service.get_compatible_topologies(node_id, linker_id)


@router.post("/cif-generator/resolve", response_model=PormakeResolveResponse)
def resolve_cif_generator_inputs(req: PormakeResolveRequest):
    """Resolve a metal and linker name/SMILES to exact PORMAKE candidates."""
    try:
        return resolve_pormake_candidates(
            metal=req.metal,
            linker=req.linker,
            tool_env_service=tool_env_service,
            max_candidates=req.max_candidates,
        )
    except (ValueError, LinkerResolutionError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.post("/cif-generator/jobs", response_model=JobStatusResponse)
def create_cif_generator_job(req: CifGeneratorJobRequest):
    """Create a new CIF generation run."""
    try:
        resolve_catalog_id(req.node_id)
        resolve_catalog_id(req.linker_id)
    except KeyError as e:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid building block ID in catalog: {e.args[0]}",
        )

    if req.topology:
        compatible = tool_env_service.get_compatible_topologies(
            req.node_id, req.linker_id
        )
        # If topologies can be loaded, enforce compatibility
        if compatible and req.topology not in compatible:
            raise HTTPException(
                status_code=400,
                detail=f"Topology '{req.topology}' is not compatible with selected building blocks.",
            )

    run = run_store.create_run(
        tool="pormake",
        request={
            "node_id": req.node_id,
            "linker_id": req.linker_id,
            "topology": req.topology,
            "max_results": req.max_results,
        },
    )

    if demo_config.is_stage_demo("property_prediction"):
        demo_artifacts, demo_results = demo_service.materialize_synthetic_cif_demo_artifacts(
            run.run_dir
        )
        artifact_service.write_manifest(run.run_id, demo_artifacts)
        fixture = {
            "results": demo_results,
            "failures": [],
            "demo_manifest": {
                "fixture_kind": "pormake-precomputed-demo",
                "fixture_count": len(demo_artifacts),
                "label": "PORMAKE-generated N409 + N10 precomputed Demo CIF fixtures",
            },
        }
        (run.run_dir / "result.json").write_text(json.dumps(fixture, indent=2), encoding="utf-8")
        run = run_store.update_status(
            run.run_id,
            "succeeded",
            progress=1.0,
            message="Demo mode: returning 10 PORMAKE-generated N409 + N10 CIF fixtures",
        )
        return JobStatusResponse(
            job_id=run.run_id,
            tool=run.tool,
            status=run.status,
            progress=run.progress,
            message=run.message,
            created_at=run.created_at,
            updated_at=run.updated_at,
        )

    pormake_runner.start_job(run.run_id)
    return JobStatusResponse(
        job_id=run.run_id,
        tool=run.tool,
        status=run.status,
        progress=run.progress,
        message=run.message,
        created_at=run.created_at,
        updated_at=run.updated_at,
    )


# --- Property Predictor ---


@router.get("/property-predictor/profiles")
def get_property_predictor_profiles():
    """Return safe model profiles."""
    if demo_config.is_stage_demo("property_prediction"):
        return {
            "default_profile_id": "demo-canned-property-profile",
            "profiles": [
                {
                    "id": "demo-canned-property-profile",
                    "label": "Demo static/canned synthetic property prediction",
                    "target_property": "CO2 uptake",
                    "condition": "298 K, 0.15 bar",
                    "unit": "mmol/g",
                    "ready": True,
                }
            ],
        }
    settings_path = get_mof_private_settings_path()
    return load_safe_model_profiles(settings_path)


@router.post("/property-predictor/jobs", response_model=JobStatusResponse)
def create_property_predictor_job(
    profile_id: str = Form(...),
    generator_run_id: Optional[str] = Form(None),
    artifact_ids: Optional[str] = Form(None),
    files: Optional[list[UploadFile]] = File(None),
    custom_checkpoint_path: Optional[str] = Form(None),
    custom_target_property: Optional[str] = Form(None),
    custom_condition: Optional[str] = Form(None),
    custom_unit: Optional[str] = Form(None),
    custom_mean: Optional[float] = Form(None),
    custom_std: Optional[float] = Form(None),
):
    """Create a new property prediction run."""
    # Check profile validity
    if not demo_config.is_stage_demo("property_prediction"):
        settings_path = get_mof_private_settings_path()
        profiles_data = load_safe_model_profiles(settings_path)
        profile = next(
            (p for p in profiles_data.get("profiles", []) if p["id"] == profile_id),
            None,
        )
        if not profile:
            raise HTTPException(
                status_code=400, detail=f"Invalid profile ID: {profile_id}"
            )
        if not profile.get("ready"):
            raise HTTPException(
                status_code=400, detail=f"Model profile '{profile_id}' is not ready."
            )

    # Validate custom checkpoint if provided
    if custom_checkpoint_path:
        custom_path = Path(custom_checkpoint_path).expanduser().resolve()
        if not custom_path.is_file():
            raise HTTPException(
                status_code=400,
                detail=f"Custom checkpoint file not found: {custom_checkpoint_path}",
            )

    # Validate inputs: must have files OR generator run artifacts, but not both or neither
    has_files = files is not None and len(files) > 0
    has_gen = bool(generator_run_id)

    if not has_files and not has_gen:
        raise HTTPException(
            status_code=400,
            detail="Must upload CIF files or provide a generator run_id.",
        )
    if has_files and has_gen:
        raise HTTPException(
            status_code=400,
            detail="Cannot provide both uploaded CIF files and a generator run_id.",
        )

    artifact_ids_list = []
    if has_gen:
        try:
            # Verify generator run exists
            run_store.get_run(generator_run_id)
        except RunNotFound:
            raise HTTPException(
                status_code=400,
                detail=f"Generator run not found: {generator_run_id}",
            )
        if artifact_ids:
            try:
                # Could be a JSON array or comma-separated list
                if artifact_ids.strip().startswith("["):
                    artifact_ids_list = json.loads(artifact_ids)
                else:
                    artifact_ids_list = [
                        x.strip()
                        for x in artifact_ids.split(",")
                        if x.strip()
                    ]
            except Exception:
                raise HTTPException(
                    status_code=400, detail="Invalid artifact_ids format."
                )

    cif_filenames = []
    if has_files:
        if len(files) > 10:
            raise HTTPException(
                status_code=400, detail="At most 10 CIF files can be uploaded."
            )
        for f in files:
            if not f.filename.endswith(".cif"):
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid file type for {f.filename}. Only .cif files are accepted.",
                )

    req_payload = {"profile_id": profile_id}
    if custom_checkpoint_path:
        req_payload["custom_checkpoint_path"] = custom_checkpoint_path
        if custom_target_property:
            req_payload["custom_target_property"] = custom_target_property
        if custom_condition:
            req_payload["custom_condition"] = custom_condition
        if custom_unit:
            req_payload["custom_unit"] = custom_unit
        if custom_mean is not None:
            req_payload["custom_mean"] = custom_mean
        if custom_std is not None:
            req_payload["custom_std"] = custom_std

    if has_gen:
        req_payload["generator_run_id"] = generator_run_id
        req_payload["artifact_ids"] = artifact_ids_list
    else:
        req_payload["uploaded_files"] = [f.filename for f in files]

    run = run_store.create_run(tool="pmtransformer", request=req_payload)

    # Write uploaded files to input_cifs folder inside the run directory
    if has_files:
        input_dir = run.run_dir / "input_cifs"
        input_dir.mkdir(parents=True, exist_ok=True)
        for f in files:
            try:
                dest = input_dir / f.filename
                # Use a loop to read in chunks to handle size constraints
                content = f.file.read()
                dest.write_bytes(content)
            except Exception as e:
                raise HTTPException(
                    status_code=500,
                    detail=f"Failed to save uploaded file {f.filename}: {e}",
                )

    if demo_config.is_stage_demo("property_prediction"):
        fixture = demo_service.get_property_prediction_response()
        (run.run_dir / "result.json").write_text(
            json.dumps(fixture, indent=2), encoding="utf-8"
        )
        run = run_store.update_status(
            run.run_id,
            "succeeded",
            progress=1.0,
            message="Demo mode: returning canned property-prediction fixture",
        )
        return JobStatusResponse(
            job_id=run.run_id,
            tool=run.tool,
            status=run.status,
            progress=run.progress,
            message=run.message,
            created_at=run.created_at,
            updated_at=run.updated_at,
        )

    pmtransformer_runner.start_job(run.run_id)
    return JobStatusResponse(
        job_id=run.run_id,
        tool=run.tool,
        status=run.status,
        progress=run.progress,
        message=run.message,
        created_at=run.created_at,
        updated_at=run.updated_at,
    )


@router.post("/property-predictor/upload-jobs", response_model=JobStatusResponse)
def create_property_predictor_upload_job(req: PropertyPredictorUploadJobRequest):
    """Create a prediction run from CIF text uploaded as JSON.

    This avoids multipart transport failures observed between Windows Chrome
    and the local WSL development server while preserving the same run format.
    """
    if not demo_config.is_stage_demo("property_prediction"):
        settings_path = get_mof_private_settings_path()
        profiles_data = load_safe_model_profiles(settings_path)
        profile = next(
            (p for p in profiles_data.get("profiles", []) if p["id"] == req.profile_id),
            None,
        )
        if not profile:
            raise HTTPException(
                status_code=400, detail=f"Invalid profile ID: {req.profile_id}"
            )
        if not profile.get("ready"):
            raise HTTPException(
                status_code=400,
                detail=f"Model profile '{req.profile_id}' is not ready.",
            )

    request_payload = {"profile_id": req.profile_id}
    if req.custom_checkpoint_path:
        checkpoint = Path(req.custom_checkpoint_path).expanduser().resolve()
        if not checkpoint.is_file():
            raise HTTPException(
                status_code=400,
                detail=f"Custom checkpoint file not found: {req.custom_checkpoint_path}",
            )
        request_payload.update(
            {
                "custom_checkpoint_path": req.custom_checkpoint_path,
                "custom_target_property": req.custom_target_property,
                "custom_condition": req.custom_condition,
                "custom_unit": req.custom_unit,
                "custom_mean": req.custom_mean,
                "custom_std": req.custom_std,
            }
        )

    total_bytes = 0
    filenames = []
    for uploaded in req.files:
        filename = uploaded.filename.strip()
        if (
            not filename
            or Path(filename).name != filename
            or not filename.lower().endswith(".cif")
        ):
            raise HTTPException(
                status_code=400,
                detail=f"Invalid CIF filename: {uploaded.filename}",
            )
        total_bytes += len(uploaded.content.encode("utf-8"))
        filenames.append(filename)
    if total_bytes > 20 * 1024 * 1024:
        raise HTTPException(
            status_code=400,
            detail="Combined CIF upload size must not exceed 20 MB.",
        )

    request_payload["uploaded_files"] = filenames
    run = run_store.create_run(tool="pmtransformer", request=request_payload)
    input_dir = run.run_dir / "input_cifs"
    input_dir.mkdir(parents=True, exist_ok=True)
    for uploaded, filename in zip(req.files, filenames):
        (input_dir / filename).write_text(uploaded.content, encoding="utf-8")

    if demo_config.is_stage_demo("property_prediction"):
        fixture = demo_service.get_property_prediction_response()
        (run.run_dir / "result.json").write_text(
            json.dumps(fixture, indent=2), encoding="utf-8"
        )
        run = run_store.update_status(
            run.run_id,
            "succeeded",
            progress=1.0,
            message="Demo mode: returning canned property-prediction fixture",
        )
        return JobStatusResponse(
            job_id=run.run_id,
            tool=run.tool,
            status=run.status,
            progress=run.progress,
            message=run.message,
            created_at=run.created_at,
            updated_at=run.updated_at,
        )

    pmtransformer_runner.start_job(run.run_id)
    return JobStatusResponse(
        job_id=run.run_id,
        tool=run.tool,
        status=run.status,
        progress=run.progress,
        message=run.message,
        created_at=run.created_at,
        updated_at=run.updated_at,
    )


ALLOWED_ROOTS = [
    Path.home().resolve(),
    PROJECT_ROOT.resolve(),
]


@router.get("/property-predictor/browse-ckpts")
def browse_checkpoints(path: Optional[str] = None):
    """Browse server filesystem for checkpoint (.ckpt) files."""
    if not path:
        path = str(Path.home().resolve())

    target_path = Path(path).resolve()

    # Simple safety check: make sure the path is inside the home directory or workspace
    is_allowed = any(
        target_path == root or root in target_path.parents for root in ALLOWED_ROOTS
    )
    if not is_allowed:
        target_path = Path.home().resolve()

    if not target_path.exists() or not target_path.is_dir():
        raise HTTPException(status_code=400, detail="Invalid directory path")

    dirs = []
    files = []

    try:
        for p in target_path.iterdir():
            if p.name.startswith(".") and p.name != ".gemini":
                continue

            try:
                if p.is_dir():
                    dirs.append({
                        "name": p.name,
                        "path": str(p),
                    })
                elif p.is_file() and p.suffix == ".ckpt":
                    stat = p.stat()
                    files.append({
                        "name": p.name,
                        "path": str(p),
                        "size_bytes": stat.st_size,
                        "modified_at": stat.st_mtime,
                    })
            except Exception:
                pass
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    dirs.sort(key=lambda x: x["name"].lower())
    files.sort(key=lambda x: x["name"].lower())

    parent_path = str(target_path.parent) if target_path != target_path.parent else None

    return {
        "current_path": str(target_path),
        "parent_path": parent_path,
        "dirs": dirs,
        "files": files,
    }


@router.post("/property-predictor/verify-ckpt")
def verify_checkpoint(req: VerifyCkptRequest):
    """Verify if a checkpoint path is valid and can be loaded.

    Uses shallow verification only: checks file existence, extension, and
    minimum size.  The heavy ``torch.load`` deep-verification has been
    removed to avoid long timeouts and subprocess syntax issues.  The
    actual model loading is validated at inference time instead.
    """
    path = Path(req.checkpoint_path).expanduser().resolve()

    if not path.exists():
        return {"valid": False, "error": "檔案不存在"}
    if not path.is_file():
        return {"valid": False, "error": "指定路徑不是檔案"}
    if path.suffix != ".ckpt":
        return {"valid": False, "error": "必須是 .ckpt 格式檔案"}

    stat = path.stat()
    if stat.st_size < 1024 * 1024:
        return {"valid": False, "error": "檔案大小過小，非有效的權重檔"}

    # Format file size for the user message
    size_mb = stat.st_size / (1024 * 1024)
    size_label = f"{size_mb:.1f} MB" if size_mb < 1024 else f"{size_mb / 1024:.2f} GB"

    return {
        "valid": True,
        "info": f"權重檔案驗證通過（{path.name}, {size_label}）",
    }


# --- Shared jobs and runs ---


@router.get("/jobs/{job_id}", response_model=JobStatusResponse)
def get_job_status(job_id: str):
    """Retrieve job/run status metadata."""
    try:
        run = run_store.get_run(job_id)
        return JobStatusResponse(
            job_id=run.run_id,
            tool=run.tool,
            status=run.status,
            progress=run.progress,
            message=run.message,
            created_at=run.created_at,
            updated_at=run.updated_at,
        )
    except RunNotFound:
        raise HTTPException(status_code=404, detail="Job not found")


@router.post("/jobs/{job_id}/cancel", response_model=JobStatusResponse)
def cancel_job(job_id: str):
    """Cancel an active job."""
    try:
        # Request runners to terminate active processes
        pormake_runner.cancel_job(job_id)
        pmtransformer_runner.cancel_job(job_id)
        run = run_store.update_status(job_id, "cancelled")
        return JobStatusResponse(
            job_id=run.run_id,
            tool=run.tool,
            status=run.status,
            progress=run.progress,
            message=run.message,
            created_at=run.created_at,
            updated_at=run.updated_at,
        )
    except RunNotFound:
        raise HTTPException(status_code=404, detail="Job not found")
    except InvalidRunTransition as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/runs", response_model=list[JobStatusResponse])
def list_runs():
    """Retrieve recent runs/jobs."""
    runs = run_store.list_runs()
    return [
        JobStatusResponse(
            job_id=run.run_id,
            tool=run.tool,
            status=run.status,
            progress=run.progress,
            message=run.message,
            created_at=run.created_at,
            updated_at=run.updated_at,
        )
        for run in runs
    ]


@router.get("/runs/{run_id}", response_model=RunStatusResponse)
def get_run_status(run_id: str):
    """Get full status and result artifacts of a run."""
    try:
        run = run_store.get_run(run_id)
    except RunNotFound:
        raise HTTPException(status_code=404, detail="Run not found")

    artifacts = []
    failures = []

    # Try loading artifact manifest
    manifest_path = run.run_dir / "artifacts.json"
    artifact_paths = {}
    if manifest_path.is_file():
        try:
            m_data = json.loads(manifest_path.read_text(encoding="utf-8"))
            for art in m_data.get("artifacts", []):
                artifact_paths[art["artifact_id"]] = art["relative_path"]
        except Exception:
            pass

    # Try loading worker results
    result_path = run.run_dir / "result.json"
    if result_path.is_file():
        try:
            r_data = json.loads(result_path.read_text(encoding="utf-8"))
            failures = r_data.get("failures", [])
            for res_item in r_data.get("results", []):
                art_id = res_item.get("artifact_id")
                filename = res_item.get("filename")
                if not filename and "cif_name" in res_item:
                    filename = f"{res_item['cif_name']}.cif"

                artifacts.append(
                    RunArtifact(
                        artifact_id=art_id,
                        filename=filename or "",
                        relative_path=artifact_paths.get(art_id, ""),
                        topology=res_item.get("topology"),
                        local_prefilter_rmsd=res_item.get("local_prefilter_rmsd"),
                        max_rmsd=res_item.get("max_rmsd"),
                        node_catalog_id=res_item.get("node_catalog_id"),
                        linker_catalog_id=res_item.get("linker_catalog_id"),
                        predicted_value=res_item.get("predicted_value"),
                        unit=res_item.get("unit"),
                        target_property=res_item.get("target_property"),
                        condition=res_item.get("condition"),
                    )
                )
        except Exception:
            pass

    return RunStatusResponse(
        run_id=run.run_id,
        tool=run.tool,
        status=run.status,
        progress=run.progress,
        message=run.message,
        created_at=run.created_at,
        updated_at=run.updated_at,
        artifacts=artifacts,
        failures=failures,
    )


@router.get("/runs/{run_id}/artifacts/{artifact_id}")
def get_run_artifact(run_id: str, artifact_id: str):
    """Download a run artifact file."""
    try:
        file_path = artifact_service.resolve(run_id, artifact_id)
        return FileResponse(file_path, filename=file_path.name)
    except RunNotFound:
        raise HTTPException(status_code=404, detail="Run not found")
    except ArtifactNotFound:
        raise HTTPException(status_code=404, detail="Artifact not found")
    except InvalidArtifactManifest as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/runs/{run_id}/artifacts/{artifact_id}/text")
def get_run_artifact_text(run_id: str, artifact_id: str):
    """Get content of a run artifact as plain text."""
    try:
        file_path = artifact_service.resolve(run_id, artifact_id)
        return PlainTextResponse(file_path.read_text(encoding="utf-8"))
    except RunNotFound:
        raise HTTPException(status_code=404, detail="Run not found")
    except ArtifactNotFound:
        raise HTTPException(status_code=404, detail="Artifact not found")
    except InvalidArtifactManifest as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# --- Theoretical XRD calculation ---

import tempfile
import os


def run_xrd_calculation(
    cif_path: Path,
    wavelength: float = 1.54184,
    max_two_theta: float = 80.0,
    fwhm: float = 0.1,
) -> dict:
    """Invoke the xrd_calculator.py worker using the pmtransformer Python environment.

    The worker runs as a subprocess so that pymatgen (which is installed only in
    the pmtransformer venv) is available without polluting the main backend venv.
    """
    python_exe = tool_env_service.get_python_executable("pmtransformer")
    worker_script = (
        Path(__file__).parent.parent.parent / "workers" / "mof" / "xrd_calculator.py"
    )

    tool_env_service.require_xrd_ready()

    cmd = [
        str(python_exe),
        str(worker_script),
        "--cif", str(cif_path),
        "--wavelength", str(wavelength),
        "--max_two_theta", str(max_two_theta),
        "--fwhm", str(fwhm),
    ]

    result = subprocess.run(
        cmd, capture_output=True, text=True, timeout=120
    )

    if result.returncode != 0:
        # Try to extract a meaningful error from stdout (worker always outputs JSON)
        try:
            err_data = json.loads(result.stdout)
            raise RuntimeError(err_data.get("error", result.stderr or "XRD calculation failed"))
        except (json.JSONDecodeError, KeyError):
            raise RuntimeError(result.stderr or "XRD calculation failed")

    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Failed to parse XRD worker output: {exc}") from exc

    if "error" in data:
        raise RuntimeError(data["error"])

    return data


@router.post("/xrd/calculate", response_model=XrdPatternResponse)
async def calculate_xrd(
    file: Optional[UploadFile] = File(default=None),
    cif_path: Optional[str] = Form(default=None),
    generator_run_id: Optional[str] = Form(default=None),
    artifact_id: Optional[str] = Form(default=None),
    wavelength: float = Form(default=1.54184),
    max_two_theta: float = Form(default=80.0),
    fwhm: float = Form(default=0.1),
):
    """Calculate theoretical powder XRD pattern from a CIF file.

    Accepts either:
    - A CIF file uploaded via multipart form (``file`` field),
    - A server-side path to a CIF file (``cif_path`` form field), or
    - A generator run ID (``generator_run_id``) and artifact ID (``artifact_id``).

    Non-standard CIF headers (e.g. from CoRE MOF DB or GCMC simulation outputs)
    are automatically cleaned before calculation.

    All calculation executions are saved in the run store for history tracking.
    """
    has_file = file is not None
    has_path = bool(cif_path)
    has_gen = bool(generator_run_id) and bool(artifact_id)

    # Validate inputs: must have exactly one of the three options
    inputs_count = sum([has_file, has_path, has_gen])
    if inputs_count != 1:
        raise HTTPException(
            status_code=400,
            detail="Must provide exactly one input source: file upload, server-side path, or generator run and artifact IDs.",
        )

    # Prepare run store record payload
    req_payload = {
        "wavelength": wavelength,
        "max_two_theta": max_two_theta,
        "fwhm": fwhm,
    }
    if has_file:
        req_payload["uploaded_file"] = file.filename
    elif has_path:
        req_payload["cif_path"] = cif_path
    elif has_gen:
        req_payload["generator_run_id"] = generator_run_id
        req_payload["artifact_id"] = artifact_id

    run = run_store.create_run(tool="xrd", request=req_payload)
    input_dir = run.run_dir / "input_cifs"
    input_dir.mkdir(parents=True, exist_ok=True)

    target_path = None
    try:
        # --- Handle uploaded file ---
        if has_file:
            filename = file.filename or "structure.cif"
            if not filename.lower().endswith(".cif"):
                raise HTTPException(
                    status_code=400,
                    detail="Uploaded file must be in .cif format.",
                )
            contents = await file.read()
            dest = input_dir / filename
            dest.write_bytes(contents)
            target_path = dest

        # --- Handle server-side CIF path ---
        elif has_path:
            server_path = Path(cif_path).expanduser().resolve()
            if not server_path.exists():
                raise HTTPException(
                    status_code=404,
                    detail=f"CIF file not found: {cif_path}",
                )
            if not server_path.is_file():
                raise HTTPException(
                    status_code=400,
                    detail="cif_path must point to a file, not a directory.",
                )
            if server_path.suffix.lower() != ".cif":
                raise HTTPException(
                    status_code=400,
                    detail="cif_path must point to a .cif format file.",
                )
            dest = input_dir / server_path.name
            import shutil
            shutil.copy2(server_path, dest)
            target_path = dest

        # --- Handle generator run artifact ---
        elif has_gen:
            try:
                run_store.get_run(generator_run_id)
            except RunNotFound:
                raise HTTPException(
                    status_code=400,
                    detail=f"Generator run not found: {generator_run_id}",
                )
            try:
                resolved_path = artifact_service.resolve(generator_run_id, artifact_id)
            except Exception as e:
                raise HTTPException(
                    status_code=400,
                    detail=f"Failed to resolve artifact {artifact_id} for run {generator_run_id}: {e}",
                )

            dest = input_dir / resolved_path.name
            import shutil
            shutil.copy2(resolved_path, dest)
            target_path = dest

        if target_path is None:
            raise RuntimeError("XRD input source did not resolve to a CIF path")

        if demo_config.is_stage_demo("property_prediction"):
            matching_fixture = next(
                (
                    source
                    for source in demo_service.synthetic_cif_fixture_paths()
                    if source.name == target_path.name
                ),
                None,
            )
            if matching_fixture is None:
                raise HTTPException(
                    status_code=400,
                    detail="Demo XRD accepts only an exact packaged synthetic CIF fixture.",
                )
            if target_path.read_bytes() != matching_fixture.read_bytes():
                raise HTTPException(
                    status_code=400,
                    detail="Demo XRD accepts only an exact packaged synthetic CIF fixture.",
                )
            result = demo_service.get_synthetic_demo_xrd_pattern(target_path.name)
            run_message = "Demo mode: returning stored precomputed synthetic XRD fixture"
        else:
            run_store.update_status(
                run.run_id,
                "running",
                progress=0.2,
                message="Calculating XRD pattern",
            )
            result = run_xrd_calculation(
                cif_path=target_path,
                wavelength=wavelength,
                max_two_theta=max_two_theta,
                fwhm=fwhm,
            )
            run_message = "Calculation complete"

        # Save successful result & register artifact
        result_json_path = run.run_dir / "result.json"
        xrd_pattern_path = run.run_dir / "xrd_pattern.json"

        # Write result.json for standard run history artifact loader
        runner_output = {
            "status": "succeeded",
            "results": [
                {
                    "artifact_id": "xrd_pattern",
                    "filename": "xrd_pattern.json",
                }
            ]
        }
        result_json_path.write_text(json.dumps(runner_output, indent=2), encoding="utf-8")

        # Write full XRD pattern data
        xrd_pattern_path.write_text(json.dumps(result, indent=2), encoding="utf-8")

        # Register artifact
        artifact_service.write_manifest(
            run.run_id,
            [
                {
                    "artifact_id": "xrd_pattern",
                    "relative_path": "xrd_pattern.json",
                }
            ]
        )

        # Update run status to succeeded
        run_store.update_status(
            run.run_id,
            "succeeded",
            progress=1.0,
            message=run_message,
        )

        return result

    except HTTPException:
        # Re-raise standard HTTP exceptions
        try:
            run_store.update_status(
                run.run_id,
                "failed",
                progress=1.0,
                message="Input validation or resolution failed",
            )
        except Exception:
            pass
        raise
    except ToolReadinessError as exc:
        try:
            run_store.update_status(
                run.run_id,
                "failed",
                progress=1.0,
                message=str(exc),
            )
        except Exception:
            pass
        raise HTTPException(status_code=503, detail=str(exc))
    except Exception as exc:
        try:
            run_store.update_status(
                run.run_id,
                "failed",
                progress=1.0,
                message=str(exc),
            )
        except Exception:
            pass
        raise HTTPException(status_code=500, detail=str(exc))


# --- Proposal Integration Endpoints ---

@router.post("/proposal/translate", response_model=ProposalTranslateResponse)
def translate_proposal_mof_endpoint(req: ProposalTranslateRequest):
    """
    Resolve Proposal-mode metal/linker data to atom-complete PORMAKE candidates.
    """
    try:
        result = resolve_pormake_candidates(
            metal=req.metal_element,
            linker=req.linker_smiles,
            tool_env_service=tool_env_service,
            max_candidates=req.max_candidates,
        )
    except (ValueError, LinkerResolutionError, FileNotFoundError) as exc:
        return ProposalTranslateResponse(
            status="failed",
            message=str(exc),
        )

    first = result["candidates"][0] if result["candidates"] else None
    return ProposalTranslateResponse(
        **result,
        node_id=first["node_id"] if first else None,
        linker_id=first["linker_id"] if first else None,
        linker_id_2=None,
        compatible_topologies=first["compatible_topologies"] if first else [],
    )

@router.post("/proposal/run-screening", response_model=ProposalScreeningResponse)
def run_proposal_screening_endpoint(req: ProposalScreeningRequest):
    """
    啟動幾何拼裝（CIF 生成）的篩選背景任務。
    """
    try:
        resolve_catalog_id(req.node_id)
        resolve_catalog_id(req.linker_id)
    except KeyError as e:
        raise HTTPException(
            status_code=400,
            detail=f"無效的 PORMAKE 節點/配體代號: {e.args[0]}",
        )

    if req.topology:
        compatible = tool_env_service.get_compatible_topologies(
            req.node_id, req.linker_id
        )
        if compatible and req.topology not in compatible:
            raise HTTPException(
                status_code=400,
                detail=f"拓撲 '{req.topology}' 與所選的單元幾何不相容。",
            )

    run = run_store.create_run(
        tool="pormake",
        request={
            "node_id": req.node_id,
            "linker_id": req.linker_id,
            "topology": req.topology,
            "max_results": req.max_results,
        },
    )
    pormake_runner.start_job(run.run_id)

    return ProposalScreeningResponse(
        generator_job_id=run.run_id,
        node_id=req.node_id,
        linker_id=req.linker_id,
        topology=req.topology,
        status=run.status,
    )
