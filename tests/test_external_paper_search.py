"""
外部論文搜尋功能測試
====================

測試 Europe PMC API 的搜尋、下載和驗證功能
使用 Mock 模擬外部 API 呼叫，避免真實網路請求
"""

import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)


class TestExternalPaperSearch:
    """外部論文搜尋功能測試類"""

    def setup_method(self):
        """測試前設置"""
        self.mock_papers = [
            {
                "title": "Metal-Organic Frameworks for CO2 Capture",
                "pdf_url": "https://europepmc.org/articles/PMC12345?pdf=render",
                "doi": "10.1000/example.12345",
                "pmcid": "PMC12345",
                "source": "PubMed Central",
                "abstract": "This study investigates MOF materials for CO2 adsorption..."
            },
            {
                "title": "Advances in MOF Synthesis",
                "pdf_url": "https://europepmc.org/articles/PMC67890?pdf=render",
                "doi": "10.1000/example.67890",
                "pmcid": "PMC67890",
                "source": "PubMed Central",
                "abstract": "Novel synthesis methods for metal-organic frameworks..."
            }
        ]

    def test_search_papers_success(self):
        """測試論文搜尋成功情況"""
        with patch('backend.api.routes.external_paper.search_source') as mock_search:
            mock_search.return_value = self.mock_papers

            response = client.post(
                "/api/v1/external-paper/search",
                json={"keywords": ["MOF", "CO2"], "limit": 10}
            )

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["total_count"] == 2
            assert len(data["papers"]) == 2
            assert data["keywords"] == ["MOF", "CO2"]

    def test_search_papers_no_results(self):
        """測試論文搜尋無結果情況"""
        with patch('backend.api.routes.external_paper.search_source') as mock_search:
            mock_search.return_value = []

            response = client.post(
                "/api/v1/external-paper/search",
                json={"keywords": ["nonexistent_keyword_xyz"], "limit": 10}
            )

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["total_count"] == 0
            assert len(data["papers"]) == 0

    def test_search_papers_validation_error(self):
        """測試論文搜尋驗證錯誤"""
        # 空關鍵字列表
        response = client.post(
            "/api/v1/external-paper/search",
            json={"keywords": [], "limit": 10}
        )

        assert response.status_code == 422  # Validation error

    def test_download_paper_success(self):
        """測試論文下載成功情況"""
        with patch('backend.api.routes.external_paper.download_and_store') as mock_download:
            mock_download.return_value = "experiment_data/papers/test_paper_PMC12345.pdf"

            response = client.post(
                "/api/v1/external-paper/download",
                json={
                    "pmcid": "PMC12345",
                    "title": "Test Paper",
                    "pdf_url": "https://europepmc.org/articles/PMC12345?pdf=render"
                }
            )

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert "experiment_data/papers" in data["file_path"]

    def test_download_paper_failure(self):
        """測試論文下載失敗情況"""
        with patch('backend.api.routes.external_paper.download_and_store') as mock_download:
            mock_download.return_value = ""  # 空字串表示下載失敗

            response = client.post(
                "/api/v1/external-paper/download",
                json={
                    "pmcid": "PMC_INVALID",
                    "title": "Invalid Paper",
                    "pdf_url": "https://invalid.url/paper.pdf"
                }
            )

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is False
            assert data["file_path"] is None

    def test_validate_api_success(self):
        """測試 API 驗證成功情況"""
        with patch('backend.api.routes.external_paper.validate_europepmc_api') as mock_validate:
            mock_validate.return_value = True

            response = client.get("/api/v1/external-paper/validate")

            assert response.status_code == 200
            data = response.json()
            assert data["available"] is True
            assert "連線正常" in data["message"]

    def test_validate_api_failure(self):
        """測試 API 驗證失敗情況"""
        with patch('backend.api.routes.external_paper.validate_europepmc_api') as mock_validate:
            mock_validate.return_value = False

            response = client.get("/api/v1/external-paper/validate")

            assert response.status_code == 200
            data = response.json()
            assert data["available"] is False
            assert "無法連線" in data["message"]

    def test_search_by_doi_success(self):
        """測試 DOI 搜尋成功情況"""
        with patch('backend.api.routes.external_paper.search_by_doi') as mock_search:
            mock_search.return_value = self.mock_papers[0]

            response = client.post(
                "/api/v1/external-paper/search-by-doi",
                json={"doi": "10.1000/example.12345"}
            )

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["paper"] is not None

    def test_search_by_doi_not_found(self):
        """測試 DOI 搜尋未找到情況"""
        with patch('backend.api.routes.external_paper.search_by_doi') as mock_search:
            mock_search.return_value = {}

            response = client.post(
                "/api/v1/external-paper/search-by-doi",
                json={"doi": "10.1000/nonexistent"}
            )

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is False

    def test_get_publication_info_success(self):
        """測試獲取出版資訊成功情況"""
        with patch('backend.api.routes.external_paper.get_publication_info') as mock_info:
            mock_info.return_value = {
                "pmcid": "PMC12345",
                "title": "Test Paper",
                "authors": "Author A, Author B",
                "journal": "Nature",
                "publication_date": "2025-01-01"
            }

            response = client.get("/api/v1/external-paper/publication-info/PMC12345")

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["publication_info"]["pmcid"] == "PMC12345"

    def test_api_error_handling(self):
        """測試 API 錯誤處理"""
        with patch('backend.api.routes.external_paper.search_source') as mock_search:
            mock_search.side_effect = Exception("網路連線錯誤")

            response = client.post(
                "/api/v1/external-paper/search",
                json={"keywords": ["test"], "limit": 10}
            )

            assert response.status_code == 500
            data = response.json()
            assert "搜尋論文失敗" in data["detail"]


class TestExternalPaperIntegration:
    """外部論文搜尋整合測試"""

    def test_search_and_download_workflow(self):
        """測試完整的搜尋和下載流程"""
        mock_papers = [
            {
                "title": "Test Integration Paper",
                "pdf_url": "https://europepmc.org/articles/PMC99999?pdf=render",
                "doi": "10.1000/test.99999",
                "pmcid": "PMC99999",
                "source": "Test",
                "abstract": "Integration test paper"
            }
        ]

        with patch('backend.api.routes.external_paper.search_source') as mock_search, \
             patch('backend.api.routes.external_paper.download_and_store') as mock_download:

            mock_search.return_value = mock_papers
            mock_download.return_value = "experiment_data/papers/test_PMC99999.pdf"

            # 1. 搜尋論文
            search_response = client.post(
                "/api/v1/external-paper/search",
                json={"keywords": ["test"], "limit": 5}
            )
            assert search_response.status_code == 200
            search_data = search_response.json()
            assert len(search_data["papers"]) == 1

            # 2. 下載論文
            paper = search_data["papers"][0]
            download_response = client.post(
                "/api/v1/external-paper/download",
                json={
                    "pmcid": paper["pmcid"],
                    "title": paper["title"],
                    "pdf_url": paper["pdf_url"]
                }
            )
            assert download_response.status_code == 200
            download_data = download_response.json()
            assert download_data["success"] is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
