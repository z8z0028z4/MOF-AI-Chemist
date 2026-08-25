"""
化學品搜尋功能測試
================

測試化學品查詢、資料庫搜尋、結構繪製等功能
測試日期: 2025/9/19
"""

import pytest
import os
import json
from unittest.mock import patch, mock_open, MagicMock
from fastapi.testclient import TestClient
from backend.main import app
from backend.api.routes.chemical import router

client = TestClient(app)

class TestChemicalSearch:
    """化學品搜尋功能測試類"""

    def setup_method(self):
        """測試前設置"""
        self.test_chemical = {
            "cid": 702,
            "name": "ethanol",
            "formula": "C2H6O",
            "weight": "46.07",
            "smiles": "CCO",
            "cas": "64-17-5"
        }

        self.test_chemicals_list = [
            {
                "cid": 702,
                "name": "ethanol",
                "formula": "C2H6O",
                "cas": "64-17-5"
            },
            {
                "cid": 962,
                "name": "oxidane",
                "formula": "H2O",
                "cas": "7732-18-5"
            }
        ]

    def test_chemical_search_success(self):
        """測試化學品搜尋 API 成功情況"""
        with patch('backend.services.chemical_service.chemical_service.get_chemical_with_database_lookup') as mock_search:
            mock_search.return_value = self.test_chemical

            response = client.post("/api/v1/chemical/search", json={
                "chemical_name": "ethanol",
                "include_structure": True,
                "save_to_database": True
            })

            assert response.status_code == 200
            data = response.json()
            assert "name" in data
            assert data["name"] == "ethanol"

    def test_chemical_search_not_found(self):
        """測試化學品搜尋 API - 未找到化學品"""
        with patch('backend.services.chemical_service.chemical_service.get_chemical_with_database_lookup') as mock_search:
            mock_search.return_value = None

            response = client.post("/api/v1/chemical/search", json={
                "chemical_name": "nonexistent",
                "include_structure": True,
                "save_to_database": True
            })

            assert response.status_code == 404
            data = response.json()
            assert "化學品未找到" in data["detail"]

    def test_chemical_batch_search_success(self):
        """測試化學品批量搜尋 API 成功情況"""
        with patch('backend.services.chemical_service.chemical_service.batch_get_chemicals_with_database') as mock_batch:
            mock_batch.return_value = ([self.test_chemical], [])

            response = client.post("/api/v1/chemical/batch-search", json={
                "chemical_names": ["ethanol"],
                "include_structure": True,
                "save_to_database": True
            })

            assert response.status_code == 200
            data = response.json()
            assert "results" in data
            assert "not_found" in data
            assert len(data["results"]) == 1

    def test_chemical_database_search_success(self):
        """測試化學品資料庫搜尋 API 成功情況"""
        with patch('backend.services.chemical_service.chemical_service.search_chemicals_in_database') as mock_search:
            mock_search.return_value = self.test_chemicals_list

            response = client.get("/api/v1/chemical/database-search?query=ethanol&limit=10")

            assert response.status_code == 200
            data = response.json()
            assert "results" in data
            assert len(data["results"]) == 2

    def test_chemical_database_stats_success(self):
        """測試化學品資料庫統計 API 成功情況"""
        with patch('backend.services.chemical_service.chemical_service.get_database_stats') as mock_stats:
            mock_stats.return_value = {
                "total_chemicals": 333,
                "last_updated": "2025-09-19T17:30:00",
                "directory": "experiment_data/parsed_chemicals"
            }

            response = client.get("/api/v1/chemical/database-stats")

            assert response.status_code == 200
            data = response.json()
            assert "total_chemicals" in data
            assert data["total_chemicals"] == 333

    def test_chemical_database_list_success(self):
        """測試化學品資料庫列表 API 成功情況"""
        with patch('backend.services.chemical_database_service.chemical_db_service.get_all_chemicals') as mock_list:
            mock_list.return_value = self.test_chemicals_list

            response = client.get("/api/v1/chemical/database-list?limit=10")

            assert response.status_code == 200
            data = response.json()
            assert "chemicals" in data
            assert "total_count" in data
            assert len(data["chemicals"]) == 2

    def test_chemical_search_error_handling(self):
        """測試化學品搜尋 API 錯誤處理"""
        with patch('backend.services.chemical_service.chemical_service.get_chemical_with_database_lookup') as mock_search:
            mock_search.side_effect = Exception("搜尋服務錯誤")

            response = client.post("/api/v1/chemical/search", json={
                "chemical_name": "ethanol",
                "include_structure": True,
                "save_to_database": True
            })

            assert response.status_code == 500
            data = response.json()
            assert "化學品查詢失敗" in data["detail"]

    def test_chemical_batch_search_error_handling(self):
        """測試化學品批量搜尋 API 錯誤處理"""
        with patch('backend.services.chemical_service.chemical_service.batch_get_chemicals_with_database') as mock_batch:
            mock_batch.side_effect = Exception("批量搜尋服務錯誤")

            response = client.post("/api/v1/chemical/batch-search", json={
                "chemical_names": ["ethanol"],
                "include_structure": True,
                "save_to_database": True
            })

            assert response.status_code == 500
            data = response.json()
            assert "批量化學品查詢失敗" in data["detail"]

    def test_chemical_database_search_error_handling(self):
        """測試化學品資料庫搜尋 API 錯誤處理"""
        with patch('backend.services.chemical_service.chemical_service.search_chemicals_in_database') as mock_search:
            mock_search.side_effect = Exception("資料庫搜尋錯誤")

            response = client.get("/api/v1/chemical/database-search?query=ethanol")

            assert response.status_code == 500
            data = response.json()
            assert "數據庫搜索失敗" in data["detail"]

    def test_chemical_database_stats_error_handling(self):
        """測試化學品資料庫統計 API 錯誤處理"""
        with patch('backend.services.chemical_service.chemical_service.get_database_stats') as mock_stats:
            mock_stats.side_effect = Exception("統計服務錯誤")

            response = client.get("/api/v1/chemical/database-stats")

            assert response.status_code == 500
            data = response.json()
            assert "獲取統計信息失敗" in data["detail"]

    def test_chemical_database_list_error_handling(self):
        """測試化學品資料庫列表 API 錯誤處理"""
        with patch('backend.services.chemical_database_service.chemical_db_service.get_all_chemicals') as mock_list:
            mock_list.side_effect = Exception("列表服務錯誤")

            response = client.get("/api/v1/chemical/database-list")

            assert response.status_code == 500
            data = response.json()
            assert "獲取化學品列表失敗" in data["detail"]


class TestChemicalDatabaseService:
    """化學品資料庫服務測試"""

    def test_get_all_chemicals_success(self):
        """測試獲取所有化學品成功"""
        with patch('backend.services.chemical_database_service.ChemicalDatabaseService.get_all_chemicals') as mock_get_all:
            mock_get_all.return_value = [
                {"name": "ethanol", "formula": "C2H6O"},
                {"name": "water", "formula": "H2O"}
            ]

            response = client.get("/api/v1/chemical/database-list?limit=10")

            assert response.status_code == 200
            data = response.json()
            assert "chemicals" in data
            assert len(data["chemicals"]) == 2

    def test_search_chemicals_in_database_success(self):
        """測試資料庫中搜尋化學品成功"""
        with patch('backend.services.chemical_service.chemical_service.search_chemicals_in_database') as mock_search:
            mock_search.return_value = [
                {"name": "ethanol", "formula": "C2H6O", "match_score": 2}
            ]

            response = client.get("/api/v1/chemical/database-search?query=ethanol&limit=10")

            assert response.status_code == 200
            data = response.json()
            assert "results" in data
            assert len(data["results"]) == 1
            assert data["results"][0]["name"] == "ethanol"


class TestChemicalSearchIntegration:
    """化學品搜尋整合測試"""

    def setup_method(self):
        """測試前設置"""
        self.test_chemical = {
            "cid": 702,
            "name": "ethanol",
            "formula": "C2H6O",
            "weight": "46.07",
            "smiles": "CCO",
            "cas": "64-17-5"
        }

    def test_chemical_workflow(self):
        """測試完整的化學品工作流程"""
        # 1. 獲取資料庫統計
        with patch('backend.services.chemical_service.chemical_service.get_database_stats') as mock_stats:
            mock_stats.return_value = {"total_chemicals": 333}

            stats_response = client.get("/api/v1/chemical/database-stats")
            assert stats_response.status_code == 200

        # 2. 搜尋化學品
        with patch('backend.services.chemical_service.chemical_service.get_chemical_with_database_lookup') as mock_search:
            mock_search.return_value = self.test_chemical

            search_response = client.post("/api/v1/chemical/search", json={
                "chemical_name": "ethanol",
                "include_structure": True,
                "save_to_database": True
            })
            assert search_response.status_code == 200

        # 3. 獲取資料庫列表
        with patch('backend.services.chemical_database_service.chemical_db_service.get_all_chemicals') as mock_list:
            mock_list.return_value = [self.test_chemical]

            list_response = client.get("/api/v1/chemical/database-list?limit=10")
            assert list_response.status_code == 200

    def test_chemical_structure_generation(self):
        """測試化學品結構生成"""
        chemical_with_structure = {
            **self.test_chemical,
            "svg_structure": "<svg>...</svg>",
            "png_structure": "data:image/png;base64,..."
        }

        with patch('backend.services.chemical_service.chemical_service.get_chemical_with_database_lookup') as mock_search:
            mock_search.return_value = chemical_with_structure

            response = client.post("/api/v1/chemical/search", json={
                "chemical_name": "ethanol",
                "include_structure": True,
                "save_to_database": True
            })

            assert response.status_code == 200
            data = response.json()
            assert "svg_structure" in data
            assert "png_structure" in data

    def test_chemical_safety_data(self):
        """測試化學品安全數據"""
        chemical_with_safety = {
            **self.test_chemical,
            "safety_icons": {
                "ghs_icons": ["https://example.com/ghs.svg"],
                "nfpa_image": "https://example.com/nfpa.png"
            }
        }

        with patch('backend.services.chemical_service.chemical_service.get_chemical_with_database_lookup') as mock_search:
            mock_search.return_value = chemical_with_safety

            response = client.post("/api/v1/chemical/search", json={
                "chemical_name": "ethanol",
                "include_structure": True,
                "save_to_database": True
            })

            assert response.status_code == 200
            data = response.json()
            assert "safety_data" in data
            assert "ghs_icons" in data["safety_data"]


class TestChemicalAPIParameters:
    """化學品 API 參數測試"""

    def test_chemical_search_parameters(self):
        """測試化學品搜尋參數驗證"""
        # 測試缺少必要參數
        response = client.post("/api/v1/chemical/search", json={})
        assert response.status_code == 422  # 參數驗證錯誤

    def test_chemical_batch_search_parameters(self):
        """測試化學品批量搜尋參數驗證"""
        # 測試缺少必要參數
        response = client.post("/api/v1/chemical/batch-search", json={})
        assert response.status_code == 422  # 參數驗證錯誤

    def test_chemical_database_search_parameters(self):
        """測試化學品資料庫搜尋參數驗證"""
        # 測試缺少查詢參數
        response = client.get("/api/v1/chemical/database-search")
        assert response.status_code == 422  # 參數驗證錯誤

    def test_chemical_database_list_parameters(self):
        """測試化學品資料庫列表參數驗證"""
        with patch('backend.services.chemical_database_service.chemical_db_service.get_all_chemicals') as mock_list:
            mock_list.return_value = []

            # 測試不同的 limit 參數
            response = client.get("/api/v1/chemical/database-list?limit=5")
            assert response.status_code == 200

            response = client.get("/api/v1/chemical/database-list?limit=1000")
            assert response.status_code == 200


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
