from unittest.mock import MagicMock, patch

import pytest

from backend.api.routes.external_paper import PaperDownloadRequest, download_paper
from backend.services.europepmc_handler import (
    build_pdf_candidate_urls,
    download_and_store,
    is_pdf_response,
)


@pytest.mark.fast
@pytest.mark.unit
def test_build_pdf_candidate_urls_prefers_europepmc_render_only():
    urls = build_pdf_candidate_urls(
        "PMC12345",
        "https://pmc.ncbi.nlm.nih.gov/articles/PMC12345/pdf/",
    )

    assert urls == ["https://europepmc.org/articles/PMC12345?pdf=render"]


@pytest.mark.fast
@pytest.mark.unit
def test_is_pdf_response_accepts_pdf_bytes_with_generic_content_type():
    response = MagicMock()
    response.headers = {"Content-Type": "application/octet-stream"}
    response.content = b"%PDF-1.7 fake content"

    assert is_pdf_response(response) is True


@pytest.mark.fast
@pytest.mark.unit
def test_download_and_store_uses_europepmc_render_and_saves_pdf(tmp_path):
    pdf_response = MagicMock()
    pdf_response.ok = True
    pdf_response.status_code = 200
    pdf_response.headers = {"Content-Type": "application/octet-stream"}
    pdf_response.content = b"%PDF-1.7 downloaded"

    with patch(
        "backend.services.europepmc_handler.requests.get",
        return_value=pdf_response,
    ) as mock_get:
        file_path = download_and_store(
            {
                "pmcid": "PMC12345",
                "title": "Europe PMC Render Test",
                "pdf_url": "https://pmc.ncbi.nlm.nih.gov/articles/PMC12345/pdf/",
            },
            str(tmp_path),
        )

    assert mock_get.call_count == 1
    assert mock_get.call_args.args[0] == "https://europepmc.org/articles/PMC12345?pdf=render"
    assert file_path
    assert file_path.endswith("Europe_PMC_Render_Test_PMC12345.pdf")
    assert (tmp_path / "Europe_PMC_Render_Test_PMC12345.pdf").read_bytes().startswith(b"%PDF")


@pytest.mark.fast
@pytest.mark.unit
def test_download_and_store_rejects_html_without_fallback_probe(tmp_path):
    html_response = MagicMock()
    html_response.ok = True
    html_response.status_code = 200
    html_response.headers = {"Content-Type": "text/html"}
    html_response.content = b"<html>not a pdf</html>"

    with patch(
        "backend.services.europepmc_handler.requests.get",
        return_value=html_response,
    ) as mock_get:
        file_path = download_and_store(
            {
                "pmcid": "PMC12345",
                "title": "HTML Response Test",
                "pdf_url": "https://pmc.ncbi.nlm.nih.gov/articles/PMC12345/pdf/",
            },
            str(tmp_path),
        )

    assert mock_get.call_count == 1
    assert file_path == ""
    assert not list(tmp_path.iterdir())


@pytest.mark.fast
@pytest.mark.unit
@pytest.mark.asyncio
async def test_download_route_passes_request_to_download_service():
    with patch("backend.api.routes.external_paper.download_and_store") as mock_download:
        mock_download.return_value = "local_data/downloaded_papers/test_PMC12345.pdf"

        response = await download_paper(
            PaperDownloadRequest(
                pmcid="PMC12345",
                title="Route Download Test",
                pdf_url="https://europepmc.org/articles/PMC12345?pdf=render",
            )
        )

    assert response.success is True
    assert response.file_path == "local_data/downloaded_papers/test_PMC12345.pdf"
    assert response.storage_target == "downloaded_papers"
    assert response.storage_directory == "local_data/downloaded_papers"
    mock_download.assert_called_once()
    record, folder = mock_download.call_args.args
    assert record == {
        "pmcid": "PMC12345",
        "title": "Route Download Test",
        "pdf_url": "https://europepmc.org/articles/PMC12345?pdf=render",
    }
    assert str(folder).endswith("local_data/downloaded_papers")


@pytest.mark.fast
@pytest.mark.unit
@pytest.mark.asyncio
async def test_download_route_does_not_support_embedding_inbox_downloads():
    with patch("backend.api.routes.external_paper.download_and_store") as mock_download:
        mock_download.return_value = "local_data/downloaded_papers/test_PMC12345.pdf"

        response = await download_paper(
            PaperDownloadRequest(
                pmcid="PMC12345",
                title="Download Only Test",
                pdf_url="https://europepmc.org/articles/PMC12345?pdf=render",
            )
        )

    assert response.success is True
    assert response.storage_target == "downloaded_papers"
    assert response.storage_directory == "local_data/downloaded_papers"
    assert str(mock_download.call_args.args[1]).endswith("local_data/downloaded_papers")
