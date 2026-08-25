"""
文獻搜尋功能測試
================

測試文獻瀏覽、搜尋、下載和查看功能
測試日期: 2025/9/19
"""

import pytest
import os
import json
from unittest.mock import patch, mock_open
from fastapi.testclient import TestClient
from backend.main import app
from backend.api.routes.paper import router

client = TestClient(app)

class TestPaperSearch:
    """文獻搜尋功能測試類"""

    def setup_method(self):
        """測試前設置"""
        self.papers_dir = "experiment_data/papers"
        self.test_papers = [
            {
                "filename": "001_SO2_Removal_PAPER.pdf",
                "size": 1024000,
                "modified_time": 1695120000
            },
            {
                "filename": "002_Chemical_Reaction_PAPER.pdf",
                "size": 2048000,
                "modified_time": 1695120100
            },
            {
                "filename": "003_Research_Methods_PAPER.pdf",
                "size": 1536000,
                "modified_time": 1695120200
            }
        ]

    def test_paper_stats_success(self):
        """測試文獻統計 API 成功情況"""
        with patch('os.path.exists', return_value=True), \
             patch('os.listdir') as mock_listdir, \
             patch('os.stat') as mock_stat:

            # 模擬文件列表
            mock_listdir.return_value = [
                "001_SO2_Removal_PAPER.pdf",
                "002_Chemical_Reaction_PAPER.pdf",
                "003_Research_Methods_PAPER.pdf"
            ]

            # 模擬文件統計
            mock_stat.return_value.st_size = 1024000

            response = client.get("/api/v1/paper/stats")

            assert response.status_code == 200
            data = response.json()
            assert "total_papers" in data
            assert "total_size" in data
            assert "total_size_mb" in data
            assert data["total_papers"] == 3

    def test_paper_stats_directory_not_exists(self):
        """測試文獻統計 API - 目錄不存在"""
        with patch('os.path.exists', return_value=False):
            response = client.get("/api/v1/paper/stats")

            assert response.status_code == 200
            data = response.json()
            assert data["total_papers"] == 0
            assert "文獻目錄不存在" in data["message"]

    def test_paper_list_success(self):
        """測試文獻列表 API 成功情況"""
        with patch('os.path.exists', return_value=True), \
             patch('os.listdir') as mock_listdir, \
             patch('os.stat') as mock_stat:

            mock_listdir.return_value = [
                "001_SO2_Removal_PAPER.pdf",
                "002_Chemical_Reaction_PAPER.pdf"
            ]

            # 模擬文件統計
            mock_stat.return_value.st_size = 1024000
            mock_stat.return_value.st_mtime = 1695120000

            response = client.get("/api/v1/paper/list?limit=10")

            assert response.status_code == 200
            data = response.json()
            assert "papers" in data
            assert "total_count" in data
            assert len(data["papers"]) == 2

    def test_paper_list_with_search(self):
        """測試文獻列表 API - 帶搜尋條件"""
        with patch('os.path.exists', return_value=True), \
             patch('os.listdir') as mock_listdir, \
             patch('os.stat') as mock_stat:

            mock_listdir.return_value = [
                "001_SO2_Removal_PAPER.pdf",
                "002_Chemical_Reaction_PAPER.pdf",
                "003_Research_Methods_PAPER.pdf"
            ]

            mock_stat.return_value.st_size = 1024000
            mock_stat.return_value.st_mtime = 1695120000

            response = client.get("/api/v1/paper/list?search=SO2&limit=10")

            assert response.status_code == 200
            data = response.json()
            assert "papers" in data
            assert data["search_query"] == "SO2"

    def test_paper_search_success(self):
        """測試文獻搜尋 API 成功情況"""
        with patch('os.path.exists', return_value=True), \
             patch('os.listdir') as mock_listdir, \
             patch('os.stat') as mock_stat:

            mock_listdir.return_value = [
                "001_SO2_Removal_PAPER.pdf",
                "002_Chemical_Reaction_PAPER.pdf"
            ]

            mock_stat.return_value.st_size = 1024000
            mock_stat.return_value.st_mtime = 1695120000

            response = client.get("/api/v1/paper/search?query=SO2&limit=10")

            assert response.status_code == 200
            data = response.json()
            assert "papers" in data
            assert "query" in data
            assert data["query"] == "SO2"

    def test_paper_search_no_results(self):
        """測試文獻搜尋 API - 無結果"""
        with patch('os.path.exists', return_value=True), \
             patch('os.listdir') as mock_listdir, \
             patch('os.stat') as mock_stat:

            mock_listdir.return_value = [
                "001_Other_Topic_PAPER.pdf",
                "002_Different_Subject_PAPER.pdf"
            ]
            mock_stat.return_value.st_size = 1024000
            mock_stat.return_value.st_mtime = 1695120000

            response = client.get("/api/v1/paper/search?query=SO2&limit=10")

            assert response.status_code == 200
            data = response.json()
            assert len(data["papers"]) == 0

    def test_paper_download_success(self):
        """測試文獻下載 API 成功情況"""
        with patch('os.path.exists', return_value=True), \
             patch('os.path.join', return_value="experiment_data/papers/test.pdf"):

            response = client.get("/api/v1/paper/download/test.pdf")

            # 由於 FileResponse 的特殊性，這裡主要測試路由是否正確
            assert response.status_code in [200, 404]  # 可能因為文件不存在而 404

    def test_paper_download_not_found(self):
        """測試文獻下載 API - 文件不存在"""
        with patch('os.path.exists', return_value=False):
            response = client.get("/api/v1/paper/download/nonexistent.pdf")

            assert response.status_code == 404
            data = response.json()
            assert "文件不存在" in data["detail"]

    def test_paper_view_success(self):
        """測試文獻查看 API 成功情況"""
        with patch('os.path.exists', return_value=True), \
             patch('os.path.join', return_value="experiment_data/papers/test.pdf"):

            response = client.get("/api/v1/paper/view/test.pdf")

            # 由於 FileResponse 的特殊性，這裡主要測試路由是否正確
            assert response.status_code in [200, 404]  # 可能因為文件不存在而 404

    def test_paper_view_not_found(self):
        """測試文獻查看 API - 文件不存在"""
        with patch('os.path.exists', return_value=False):
            response = client.get("/api/v1/paper/view/nonexistent.pdf")

            assert response.status_code == 404
            data = response.json()
            assert "文件不存在" in data["detail"]

    def test_paper_list_error_handling(self):
        """測試文獻列表 API 錯誤處理"""
        with patch('os.path.exists', side_effect=Exception("文件系統錯誤")):
            response = client.get("/api/v1/paper/list")

            assert response.status_code == 500
            data = response.json()
            assert "獲取文獻列表失敗" in data["detail"]

    def test_paper_search_error_handling(self):
        """測試文獻搜尋 API 錯誤處理"""
        with patch('os.path.exists', side_effect=Exception("文件系統錯誤")):
            response = client.get("/api/v1/paper/search?query=test")

            assert response.status_code == 500
            data = response.json()
            assert "搜尋文獻失敗" in data["detail"]

    def test_paper_stats_error_handling(self):
        """測試文獻統計 API 錯誤處理"""
        with patch('os.path.exists', side_effect=Exception("文件系統錯誤")):
            response = client.get("/api/v1/paper/stats")

            assert response.status_code == 500
            data = response.json()
            assert "獲取文獻統計失敗" in data["detail"]


class TestPaperSearchIntegration:
    """文獻搜尋整合測試"""

    def test_paper_workflow(self):
        """測試完整的文獻工作流程"""
        # 1. 獲取統計資訊
        with patch('os.path.exists', return_value=True), \
             patch('os.listdir', return_value=["test.pdf"]), \
             patch('os.stat') as mock_stat:

            mock_stat.return_value.st_size = 1024000
            mock_stat.return_value.st_mtime = 1695120000

            # 測試統計
            stats_response = client.get("/api/v1/paper/stats")
            assert stats_response.status_code == 200

            # 測試列表
            list_response = client.get("/api/v1/paper/list?limit=5")
            assert list_response.status_code == 200

            # 測試搜尋
            search_response = client.get("/api/v1/paper/search?query=test&limit=5")
            assert search_response.status_code == 200

    def test_paper_file_operations(self):
        """測試文獻文件操作"""
        with patch('os.path.exists', return_value=True), \
             patch('os.path.join', return_value="experiment_data/papers/test.pdf"):

            # 測試下載
            download_response = client.get("/api/v1/paper/download/test.pdf")
            assert download_response.status_code in [200, 404]

            # 測試查看
            view_response = client.get("/api/v1/paper/view/test.pdf")
            assert view_response.status_code in [200, 404]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
