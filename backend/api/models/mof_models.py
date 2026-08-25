from pydantic import BaseModel, Field
from typing import Any, List, Optional


class MofConfiguredFields(BaseModel):
    checkpoint_path: bool
    h_mof_cif_root: bool
    downstream: bool
    normalization: bool


class MofDisplaySettings(BaseModel):
    target_property: str
    condition: str
    unit: str


class MofPrivateSettingsStatus(BaseModel):
    settings_file_exists: bool
    settings_location: str
    ready_for_real_run: bool
    missing_fields: list[str]
    invalid_fields: list[str]
    configured_fields: MofConfiguredFields
    display: MofDisplaySettings
    redacted: bool


# Tool status models
class ToolStatus(BaseModel):
    ready: bool
    installed: bool
    version: Optional[str] = None
    error: Optional[str] = None


class ToolsStatusResponse(BaseModel):
    pormake: ToolStatus
    pmtransformer: ToolStatus


class ToolInstallResponse(BaseModel):
    status: str
    message: str


class ToolInstallStatusResponse(BaseModel):
    status: str
    progress: float
    message: str
    log: Optional[str] = None


# Catalog models
class CatalogItem(BaseModel):
    id: str
    label: str
    role: str
    coordination_number: int


# Job creation models
class CifGeneratorJobRequest(BaseModel):
    node_id: str
    linker_id: str
    topology: Optional[str] = None
    max_results: int = Field(default=10, ge=1, le=20)


class PormakeCandidate(BaseModel):
    metal_id: str
    metal_element: str
    organic_id: str
    organic_role: str
    organic_coordination_number: int
    assembly_pattern: str
    match_kind: str
    confidence: float
    covered_atom_fraction: float
    uncovered_elements: dict[str, int] = Field(default_factory=dict)
    evidence: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    port_modes: list[str] = Field(default_factory=list)
    node_id: str
    linker_id: str
    auto_generatable: bool
    compatible_topologies: list[str] = Field(default_factory=list)


class PormakeResolveRequest(BaseModel):
    metal: str = Field(min_length=1)
    linker: str = Field(min_length=1)
    max_candidates: int = Field(default=5, ge=1, le=10)


class PormakeResolveResponse(BaseModel):
    status: str
    metal_element: Optional[str] = None
    linker_smiles: Optional[str] = None
    linker_identity: dict[str, Any] = Field(default_factory=dict)
    candidates: list[PormakeCandidate] = Field(default_factory=list)
    scaffold_suggestions: list[PormakeCandidate] = Field(default_factory=list)
    diagnostics: dict[str, Any] = Field(default_factory=dict)
    message: str


class ProposalTranslateRequest(BaseModel):
    metal_element: str
    linker_smiles: str
    linker_smiles_2: Optional[str] = None
    max_candidates: int = Field(default=5, ge=1, le=10)


class ProposalTranslateResponse(PormakeResolveResponse):
    # Temporary compatibility fields for the existing Proposal UI.
    node_id: Optional[str] = None
    linker_id: Optional[str] = None
    linker_id_2: Optional[str] = None
    compatible_topologies: list[str] = Field(default_factory=list)


class ProposalScreeningRequest(BaseModel):
    node_id: str
    linker_id: str
    topology: Optional[str] = None
    max_results: int = Field(default=5, ge=1, le=20)


class ProposalScreeningResponse(BaseModel):
    generator_job_id: str
    node_id: str
    linker_id: str
    topology: Optional[str]
    status: str


class CifTextUpload(BaseModel):
    filename: str
    content: str


class PropertyPredictorUploadJobRequest(BaseModel):
    profile_id: str
    files: List[CifTextUpload] = Field(min_length=1, max_length=10)
    custom_checkpoint_path: Optional[str] = None
    custom_target_property: Optional[str] = None
    custom_condition: Optional[str] = None
    custom_unit: Optional[str] = None
    custom_mean: Optional[float] = None
    custom_std: Optional[float] = None


# Job / Run status models
class JobStatusResponse(BaseModel):
    job_id: str
    tool: str
    status: str
    progress: float
    message: str
    created_at: str
    updated_at: str


class RunArtifact(BaseModel):
    artifact_id: str
    filename: str
    relative_path: str
    topology: Optional[str] = None
    local_prefilter_rmsd: Optional[float] = None
    max_rmsd: Optional[float] = None
    node_catalog_id: Optional[str] = None
    linker_catalog_id: Optional[str] = None
    predicted_value: Optional[float] = None
    unit: Optional[str] = None
    target_property: Optional[str] = None
    condition: Optional[str] = None


class RunStatusResponse(BaseModel):
    run_id: str
    tool: str
    status: str
    progress: float
    message: str
    created_at: str
    updated_at: str
    artifacts: List[RunArtifact] = []
    failures: List[dict] = []


class VerifyCkptRequest(BaseModel):
    checkpoint_path: str


# XRD pattern models
class XrdPeak(BaseModel):
    two_theta: float
    intensity: float
    hkl: str
    d_spacing: float


class XrdProfile(BaseModel):
    two_theta: List[float]
    intensity: List[float]


class XrdPatternResponse(BaseModel):
    space_group: str
    space_group_number: int
    crystal_system: str
    wavelength: float
    num_peaks: int
    peaks: List[XrdPeak]
    profile: XrdProfile
