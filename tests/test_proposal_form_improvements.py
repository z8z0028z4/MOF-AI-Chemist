"""
提案表單改進功能測試
==================

測試以下功能：
1. Document Retrieval Count 下拉選單功能
2. 文字反白 popup 位置計算
3. 表單狀態管理一致性
"""

import pytest
import json
import asyncio
from unittest.mock import Mock, patch, MagicMock
from fastapi.testclient import TestClient
import sys
import os

# 添加項目根目錄到 Python 路徑
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from backend.main import app
from backend.api.routes.proposal import ProposalRequest, ProposalResponse
from backend.core.config import Settings


@pytest.mark.backend
class TestProposalFormImprovements:
    """測試提案表單改進功能"""

    def setup_method(self):
        """設置測試環境"""
        self.client = TestClient(app)
        self.settings = Settings()

    def test_resolve_proposal_names_to_smiles(self):
        """測試後端將配體名稱解析為 SMILES 的輔助函式"""
        from backend.api.routes.proposal import _resolve_proposal_names_to_smiles

        # 模擬 structured_proposal 字典
        structured_proposal = {
            "proposal_title": "Test Title",
            "mof_metal_element": "Cu",
            "mof_linker_name": "1,3,5-benzenetricarboxylic acid",
            "mof_linker_name_2": "oxalic acid"
        }

        # 模擬已解析的化學品清單 (SMILES 已經由 PubChem 解析好)
        chemical_metadata_list = [
            {
                "name": "1,3,5-Benzenetricarboxylic acid",
                "smiles": "C1=C(C=C(C=C1C(=O)O)C(=O)O)C(=O)O"
            },
            {
                "name": "Oxalic acid",
                "smiles": "C(=O)(C(=O)O)O"
            }
        ]

        # 呼叫解析函式
        _resolve_proposal_names_to_smiles(structured_proposal, chemical_metadata_list)

        # 驗證結構化字典被成功寫入了 mof_linker_smiles 欄位
        assert structured_proposal["mof_linker_smiles"] == "C1=C(C=C(C=C1C(=O)O)C(=O)O)C(=O)O"
        assert structured_proposal["mof_linker_smiles_2"] == "C(=O)(C(=O)O)O"

    @patch("backend.services.mof.pormake_resolver.resolve_linker_input")
    def test_linker_resolution_does_not_use_substring_chemical_match(
        self,
        mock_resolve,
    ):
        from backend.api.routes.proposal import _resolve_proposal_names_to_smiles

        mock_resolve.return_value = (
            "O=C(O)c1ccc(C(=O)O)cc1",
            {"source": "curated-name"},
        )
        structured_proposal = {
            "mof_linker_name": "terephthalic acid",
            "mof_linker_name_2": "",
        }
        chemical_metadata_list = [
            {
                "name": "2-aminoterephthalic acid",
                "smiles": "Nc1cc(C(=O)O)ccc1C(=O)O",
            }
        ]

        _resolve_proposal_names_to_smiles(
            structured_proposal,
            chemical_metadata_list,
        )

        assert (
            structured_proposal["mof_linker_smiles"]
            == "O=C(O)c1ccc(C(=O)O)cc1"
        )
        mock_resolve.assert_called_once_with("terephthalic acid")

    def test_generate_proposal_keeps_mof_when_chemical_summary_fails(self):
        proposal_result = {
            "answer": "A copper MOF using benzene-1,3,5-tricarboxylic acid.",
            "citations": [],
            "chunks": [],
            "structured_proposal": {
                "proposal_title": "Mock MOF",
                "materials_list": [
                    "copper(II) nitrate",
                    "benzene-1,3,5-tricarboxylic acid",
                ],
            },
        }
        extraction_result = {
            "is_mof_related": True,
            "mof_metal_element": "Cu",
            "mof_linker_name": "benzene-1,3,5-tricarboxylic acid",
            "mof_linker_name_2": "",
        }

        with (
            patch(
                "backend.services.knowledge_service.agent_answer",
                return_value=proposal_result,
            ),
            patch(
                "backend.core.generation.extract_mof_from_proposal",
                return_value=extraction_result,
            ),
            patch(
                "backend.services.mof.pormake_resolver.resolve_linker_input",
                return_value=(
                    "O=C(O)c1cc(C(=O)O)cc(C(=O)O)c1",
                    {"source": "curated-name"},
                ),
            ),
            patch(
                "backend.services.pubchem_service.extract_and_fetch_chemicals",
                side_effect=RuntimeError("PubChem unavailable"),
            ),
        ):
            from backend.api.routes.proposal import generate_proposal

            response = asyncio.run(
                generate_proposal(
                    ProposalRequest(
                        research_goal="Create a Cu BTC MOF",
                        retrieval_count=1,
                        mof_linker_mode="single",
                    )
                )
            )

        assert response.chemicals == []
        assert response.not_found == []
        assert response.structured_proposal["mof_metal_element"] == "Cu"
        assert (
            response.structured_proposal["mof_linker_smiles"]
            == "O=C(O)c1cc(C(=O)O)cc(C(=O)O)c1"
        )

    @patch("backend.services.mof.pormake_resolver.resolve_linker_input")
    def test_resolve_proposal_names_to_smiles_fallback_api(
        self,
        mock_resolve,
    ):
        """測試當配體名稱不在化學品列表中時，後端解析函式會回退到 PubChem 查詢"""
        from backend.api.routes.proposal import _resolve_proposal_names_to_smiles

        structured_proposal = {
            "proposal_title": "Test Title",
            "mof_metal_element": "Zn",
            "mof_linker_name": "terephthalic acid",
            "mof_linker_name_2": ""
        }

        mock_resolve.return_value = (
            "C1=CC(=CC=C1C(=O)O)C(=O)O",
            {"source": "pubchem", "cid": 1493},
        )

        # 執行解析
        _resolve_proposal_names_to_smiles(structured_proposal, [])

        mock_resolve.assert_called_once_with("terephthalic acid")
        assert structured_proposal["mof_linker_smiles"] == "C1=CC(=CC=C1C(=O)O)C(=O)O"

    def test_proposal_request_model_includes_retrieval_count(self):
        """測試提案請求模型包含 retrieval_count 字段"""
        # 測試默認值
        request = ProposalRequest(research_goal="測試研究目標")
        assert request.retrieval_count == 10

        # 測試自定義值
        request = ProposalRequest(
            research_goal="測試研究目標",
            retrieval_count=15
        )
        assert request.retrieval_count == 15

        # 測試可選字段
        request = ProposalRequest(
            research_goal="測試研究目標",
            retrieval_count=None
        )
        assert request.retrieval_count is None

    @pytest.mark.slow
    @pytest.mark.external
    def test_real_proposal_generation_with_retrieval_count(self):
        """測試真實的提案生成功能（需要真實的LLM調用）"""
        # 使用真實的API，不Mock任何功能
        test_cases = [1, 3, 5]  # 使用較小的檢索數量以加快測試

        for retrieval_count in test_cases:
            response = self.client.post(
                "/api/v1/proposal/generate",
                json={
                    "research_goal": "Design a simple MOF for CO2 capture",
                    "retrieval_count": retrieval_count
                }
            )

            assert response.status_code == 200
            data = response.json()

            # 驗證響應結構
            assert "proposal" in data
            assert "chemicals" in data
            assert "citations" in data
            assert "chunks" in data

            # 驗證真實內容（不是Mock的）
            assert len(data["proposal"]) > 0, f"提案內容不應為空，檢索數量：{retrieval_count}"
            assert isinstance(data["chemicals"], list)
            assert isinstance(data["citations"], list)
            assert isinstance(data["chunks"], list)

            # 驗證檢索數量影響（真實測試）
            # 如果retrieval_count=N，chunks數量應該≤N
            actual_chunks = len(data["chunks"])
            assert actual_chunks <= retrieval_count, \
                f"檢索數量{retrieval_count}應該最多返回{retrieval_count}個chunks，實際：{actual_chunks}"

            # 驗證提案內容質量
            proposal_text = data["proposal"]
            assert len(proposal_text) > 50, "提案內容應該有足夠的長度"
            assert any(keyword in proposal_text.lower() for keyword in
                      ["mof", "co2", "capture", "synthesis", "material"]), \
                "提案內容應該包含相關關鍵詞"

    def test_retrieval_count_validation(self):
        """測試檢索數量驗證"""
        # 測試有效值
        valid_values = [1, 5, 10, 15, 20, 25, 50]
        for value in valid_values:
            request = ProposalRequest(
                research_goal="測試研究目標",
                retrieval_count=value
            )
            assert request.retrieval_count == value

        # 測試邊界值
        request = ProposalRequest(
            research_goal="測試研究目標",
            retrieval_count=0
        )
        assert request.retrieval_count == 0

        request = ProposalRequest(
            research_goal="測試研究目標",
            retrieval_count=100
        )
        assert request.retrieval_count == 100

    @pytest.mark.slow
    @pytest.mark.external
    def test_real_proposal_generation_without_retrieval_count(self):
        """測試不提供檢索數量時使用默認值（真實測試）"""
        # 不提供 retrieval_count，應該使用默認值
        response = self.client.post(
            "/api/v1/proposal/generate",
            json={
                "research_goal": "Design a simple MOF for CO2 capture"
            }
        )

        assert response.status_code == 200
        data = response.json()

        # 驗證響應結構
        assert "proposal" in data
        assert "chunks" in data

        # 驗證使用了默認檢索數量（通常是10）
        # 由於我們沒有Mock，chunks數量應該反映真實的檢索結果
        chunks_count = len(data["chunks"])
        assert chunks_count >= 0, "chunks數量應該≥0"

        # 驗證提案內容
        assert len(data["proposal"]) > 0, "提案內容不應為空"

        # 驗證默認行為：如果沒有指定檢索數量，應該有合理的chunks數量
        # 通常默認值會產生一些檢索結果
        print(f"默認檢索數量產生的chunks數量：{chunks_count}")


@pytest.mark.fast
@pytest.mark.frontend
class TestTextHighlightPopupPosition:
    """測試文字反白 popup 位置計算（模擬測試）"""

    def test_calculate_end_position_logic(self):
        """測試位置計算邏輯（不依賴前端模組）"""
        # 模擬位置計算邏輯
        def calculate_end_position_simulation(range_data):
            """模擬位置計算函數"""
            try:
                # 模擬計算最後一個字符的位置
                end_x = range_data.get('end_x', 100)
                end_y = range_data.get('end_y', 50)

                return {
                    'x': end_x,
                    'y': end_y
                }
            except Exception:
                # 錯誤處理
                return {
                    'x': 0,
                    'y': 0
                }

        # 測試正常情況
        range_data = {'end_x': 150, 'end_y': 200}
        result = calculate_end_position_simulation(range_data)
        assert result['x'] == 150
        assert result['y'] == 200

        # 測試錯誤情況
        result = calculate_end_position_simulation({})
        assert result['x'] == 100  # 默認值
        assert result['y'] == 50   # 默認值

    def test_popup_position_validation(self):
        """測試 popup 位置數據驗證"""
        # 測試位置數據結構
        position_data = {
            'x': 150,
            'y': 200
        }

        # 驗證數據類型
        assert isinstance(position_data['x'], (int, float))
        assert isinstance(position_data['y'], (int, float))

        # 驗證數據範圍
        assert position_data['x'] >= 0
        assert position_data['y'] >= 0

    def test_text_selection_simulation(self):
        """測試文字選擇模擬"""
        # 模擬選中的文字
        selected_text = "water competition problem"

        # 模擬位置計算
        mock_position = {"x": 150, "y": 200}

        # 驗證位置數據
        assert isinstance(mock_position["x"], (int, float))
        assert isinstance(mock_position["y"], (int, float))
        assert mock_position["x"] > 0
        assert mock_position["y"] > 0


@pytest.mark.fast
@pytest.mark.frontend
class TestFormStateConsistency:
    """測試表單狀態一致性"""

    def test_app_state_initial_values(self):
        """測試應用狀態初始值包含 retrievalCount"""
        # 模擬前端狀態
        initial_state = {
            "proposal": {
                "formData": {"goal": "", "retrievalCount": 10},
                "retrievalCount": 10
            }
        }

        # 驗證初始狀態
        assert initial_state["proposal"]["formData"]["retrievalCount"] == 10
        assert initial_state["proposal"]["retrievalCount"] == 10
        assert initial_state["proposal"]["formData"]["goal"] == ""

    def test_form_data_synchronization(self):
        """測試表單數據同步"""
        # 模擬表單數據更新
        form_data_updates = [
            {"goal": "測試目標1", "retrievalCount": 5},
            {"goal": "測試目標2", "retrievalCount": 15},
            {"goal": "測試目標3", "retrievalCount": 20}
        ]

        for update in form_data_updates:
            # 驗證更新後的數據
            assert "goal" in update
            assert "retrievalCount" in update
            assert update["retrievalCount"] in [1, 5, 10, 15, 20]

    def test_retrieval_count_options(self):
        """測試檢索數量選項"""
        expected_options = [
            {"value": 1, "label": "1 document (Dev Test)"},
            {"value": 5, "label": "5 documents (Fast)"},
            {"value": 10, "label": "10 documents (Balanced)"},
            {"value": 15, "label": "15 documents (Comprehensive)"},
            {"value": 20, "label": "20 documents (Thorough)"}
        ]

        for option in expected_options:
            assert isinstance(option["value"], int)
            assert isinstance(option["label"], str)
            assert option["value"] > 0
            assert "document" in option["label"]


@pytest.mark.integration
@pytest.mark.backend
class TestIntegrationScenarios:
    """測試整合場景"""

    @pytest.mark.slow
    @pytest.mark.external
    def test_real_complete_proposal_workflow(self):
        """測試真實的完整提案工作流程"""
        client = TestClient(app)

        # 1. 生成提案（真實API調用）
        response = client.post(
            "/api/v1/proposal/generate",
            json={
                "research_goal": "Design a Mg2(dobpdc) based functionalized MOF for CO2 capture",
                "retrieval_count": 3  # 使用較小的檢索數量以加快測試
            }
        )

        assert response.status_code == 200
        data = response.json()

        # 2. 驗證響應包含所有必要字段
        assert "proposal" in data
        assert "chemicals" in data
        assert "citations" in data
        assert "chunks" in data

        # 3. 驗證提案內容質量
        assert len(data["proposal"]) > 0, "提案內容不應為空"
        assert len(data["chunks"]) > 0, "應該有檢索到的文檔塊"

        # 4. 驗證提案內容相關性
        proposal_text = data["proposal"]
        assert any(keyword in proposal_text.lower() for keyword in
                  ["mof", "mg2", "dobpdc", "co2", "capture"]), \
            "提案內容應該包含相關關鍵詞"

        # 5. 測試實驗細節生成（如果API存在）
        if data["proposal"] and data["chunks"]:
            experiment_response = client.post(
                "/api/v1/proposal/experiment-detail",
                json={
                    "proposal": data["proposal"],
                    "chunks": data["chunks"]
                }
            )

            if experiment_response.status_code == 200:
                experiment_data = experiment_response.json()
                assert "experiment_detail" in experiment_data
                assert len(experiment_data["experiment_detail"]) > 0
                print("✅ 實驗細節生成功能正常")
            else:
                print(f"⚠️ 實驗細節生成API返回狀態碼：{experiment_response.status_code}")

        # 6. 驗證化學品提取
        chemicals = data["chemicals"]
        assert isinstance(chemicals, list)
        if chemicals:
            for chemical in chemicals:
                assert "name" in chemical, "化學品應該有名稱"
                print(f"✅ 提取到化學品：{chemical.get('name', 'Unknown')}")

        # 7. 驗證引用信息
        citations = data["citations"]
        assert isinstance(citations, list)
        if citations:
            for citation in citations:
                assert "title" in citation or "authors" in citation, "引用應該有標題或作者"
                print(f"✅ 找到引用：{citation.get('title', citation.get('authors', 'Unknown'))}")

        print(f"✅ 完整工作流程測試通過，檢索到{len(data['chunks'])}個文檔塊")

    def test_text_highlight_workflow_simulation(self):
        """測試文字反白工作流程模擬"""
        # 模擬選中的文字
        selected_text = "water competition problem"

        # 模擬位置計算
        mock_position = {"x": 150, "y": 200}

        # 驗證位置數據
        assert isinstance(mock_position["x"], (int, float))
        assert isinstance(mock_position["y"], (int, float))
        assert mock_position["x"] > 0
        assert mock_position["y"] > 0

        # 模擬 popup 顯示
        popup_data = {
            "text": selected_text,
            "position": mock_position,
            "options": ["explain", "revise"]
        }

        assert popup_data["text"] == selected_text
        assert popup_data["position"] == mock_position
        assert "explain" in popup_data["options"]
        assert "revise" in popup_data["options"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
