"""
Data Analyzer API Routes

Provides REST endpoints for material analysis functionality including
analysis coordination and report export.
"""

from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from fastapi.responses import FileResponse
from typing import Dict, Any, Optional
import json
import io
from pathlib import Path
import logging

from backend.services.data_analyzer_service import create_data_analyzer_service
from backend.services.report_service import create_report_service
from backend.utils.logger import get_logger
from backend.core.config import settings

logger = get_logger(__name__)

# Create router
router = APIRouter(prefix="/data-analyzer", tags=["Data Analyzer"])

# Initialize services
data_analyzer_service = create_data_analyzer_service()
report_service = create_report_service()

# Configuration
ALLOWED_EXTENSIONS = settings.data_analyzer_allowed_extensions
MAX_FILE_SIZE = settings.data_analyzer_max_file_size


def allowed_file(filename: str, technique: str) -> bool:
    """Check if file extension is allowed for the technique."""
    if technique not in ALLOWED_EXTENSIONS:
        return False

    if '.' not in filename:
        return False

    extension = '.' + filename.rsplit('.', 1)[1].lower()
    return extension in ALLOWED_EXTENSIONS[technique]


@router.post("/analyze")
async def analyze_materials(
    # Original material files
    original_xrd: Optional[UploadFile] = File(None),
    original_ir: Optional[UploadFile] = File(None),
    original_tga: Optional[UploadFile] = File(None),
    original_bet: Optional[UploadFile] = File(None),
    # Modified material files
    modified_xrd: Optional[UploadFile] = File(None),
    modified_ir: Optional[UploadFile] = File(None),
    modified_tga: Optional[UploadFile] = File(None),
    modified_bet: Optional[UploadFile] = File(None),
    # Context information
    modificationDescription: Optional[str] = Form(None),
    userQuery: Optional[str] = Form(None)
):
    """
    Analyze materials using uploaded files across multiple techniques.
    Supports original vs modified material comparison.

    Args:
        original_xrd, original_ir, original_tga, original_bet: Original material files
        modified_xrd, modified_ir, modified_tga, modified_bet: Modified material files
        modificationDescription: Description of modifications made
        userQuery: Specific user query for analysis

    Returns:
        Analysis results with features, plots, and LLM summary
    """
    try:
        logger.info("Starting material analysis request with original vs modified comparison")

        # Validate and collect files
        files = {}

        # Define file mappings for original and modified materials
        original_files = {
            'original_xrd': original_xrd,
            'original_ir': original_ir,
            'original_tga': original_tga,
            'original_bet': original_bet
        }

        modified_files = {
            'modified_xrd': modified_xrd,
            'modified_ir': modified_ir,
            'modified_tga': modified_tga,
            'modified_bet': modified_bet
        }

        # Process original material files
        for file_key, file in original_files.items():
            if file and file.filename:
                technique = file_key.replace('original_', '')
                if not allowed_file(file.filename, technique):
                    raise HTTPException(
                        status_code=400,
                        detail=f'Invalid file type for original {technique}. Allowed: {ALLOWED_EXTENSIONS[technique]}'
                    )

                content = await file.read()
                if len(content) > MAX_FILE_SIZE:
                    raise HTTPException(
                        status_code=400,
                        detail=f'Original {technique} file too large. Max size: {MAX_FILE_SIZE} bytes'
                    )

                await file.seek(0)
                files[file_key] = file
                logger.info(f"Accepted original {technique} file: {file.filename}")

        # Process modified material files
        for file_key, file in modified_files.items():
            if file and file.filename:
                technique = file_key.replace('modified_', '')
                if not allowed_file(file.filename, technique):
                    raise HTTPException(
                        status_code=400,
                        detail=f'Invalid file type for modified {technique}. Allowed: {ALLOWED_EXTENSIONS[technique]}'
                    )

                content = await file.read()
                if len(content) > MAX_FILE_SIZE:
                    raise HTTPException(
                        status_code=400,
                        detail=f'Modified {technique} file too large. Max size: {MAX_FILE_SIZE} bytes'
                    )

                await file.seek(0)
                files[file_key] = file
                logger.info(f"Accepted modified {technique} file: {file.filename}")

        if not files:
            raise HTTPException(status_code=400, detail='No valid files provided')

        # Create analysis request with additional parameters
        analysis_request = {
            'files': files,
            'modification_description': modificationDescription,
            'user_query': userQuery
        }

        # Perform analysis
        result = data_analyzer_service.analyze_materials_with_context(analysis_request)

        logger.info(f"Analysis completed with {len(result['features'])} techniques")
        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Analysis failed: {str(e)}")
        raise HTTPException(status_code=422, detail=f'Analysis failed: {str(e)}')


@router.post("/export")
async def export_report(analysis_result: Dict[str, Any], format_type: str = "docx"):
    """
    Export analysis results as Word document.

    Args:
        analysis_result: Result from analyze endpoint
        format_type: Export format (default: docx)

    Returns:
        Word document file
    """
    try:
        if not analysis_result:
            raise HTTPException(status_code=400, detail='analysisResult is required')

        if format_type != 'docx':
            raise HTTPException(status_code=400, detail='Only docx format is supported')

        logger.info("Starting report export")

        # Generate Word document
        docx_buffer = report_service.generate_docx_report(analysis_result)

        # Return file as streaming response
        from fastapi.responses import StreamingResponse

        def iter_file():
            yield docx_buffer

        return StreamingResponse(
            iter_file(),
            media_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            headers={'Content-Disposition': 'attachment; filename="material_analysis_report.docx"'}
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Export failed: {str(e)}")
        raise HTTPException(status_code=422, detail=f'Export failed: {str(e)}')


@router.get("/datasets")
async def get_datasets():
    """
    Get available dataset types for analysis.

    Returns:
        List of available dataset types
    """
    datasets = [
        {'id': 'xrd', 'name': 'XRD Analysis', 'description': 'X-ray diffraction data analysis'},
        {'id': 'ir', 'name': 'IR Analysis', 'description': 'Infrared spectroscopy analysis'},
        {'id': 'tga', 'name': 'TGA Analysis', 'description': 'Thermogravimetric analysis'},
        {'id': 'bet', 'name': 'BET Analysis', 'description': 'Surface area and porosity analysis'}
    ]

    return {'datasets': datasets}


@router.get("/health")
async def health_check():
    """Health check endpoint for data analyzer service."""
    return {
        'status': 'healthy',
        'service': 'data_analyzer',
        'available_techniques': list(ALLOWED_EXTENSIONS.keys())
    }
