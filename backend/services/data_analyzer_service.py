"""
Data Analyzer Service

Orchestrates material analysis across multiple techniques (XRD, IR, TGA, BET)
and coordinates with LLM for expert analysis and recommendations.
"""

from pathlib import Path
from typing import Dict, Any, Optional, List
import json
import logging

from backend.services.analysis.xrd_analysis import create_xrd_analyzer
from backend.services.analysis.ir_analysis import create_ir_analyzer
from backend.services.analysis.tga_analysis import create_tga_analyzer
from backend.services.analysis.bet_analysis import create_bet_analyzer
from backend.core.llm_client import LLMClient
from backend.core.prompt_builder import create_material_analysis_request
from backend.core.schema_manager import get_schema_by_type, create_conditional_material_analysis_schema
from backend.core.settings_manager import settings_manager
from backend.utils.logger import get_logger

logger = get_logger(__name__)


class DataAnalyzerService:
    """Main service for coordinating material analysis across techniques."""

    def __init__(self):
        self.logger = logger
        self.xrd_analyzer = create_xrd_analyzer()
        self.ir_analyzer = create_ir_analyzer()
        self.tga_analyzer = create_tga_analyzer()
        self.bet_analyzer = create_bet_analyzer()
        self.llm_client = LLMClient()

        # JSON schema for LLM output
        self.analysis_schema = get_schema_by_type('material_analysis')

    def analyze_materials(self, files: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze materials using provided files across multiple techniques.

        Args:
            files: Dict with technique names as keys and file data as values
                  Format: {'xrd': file_data, 'ir': file_data, 'tga': file_data, 'bet': file_data}

        Returns:
            Dict containing analysis results with features, plots, and LLM summary
        """
        self.logger.info("Starting material analysis with provided files")

        # Initialize result structure
        result = {
            'features': {},
            'plots': {},
            'summary': ''
        }

        # Process each technique if file is provided
        for technique, file_data in files.items():
            if file_data is None:
                continue

            try:
                technique_result = self._analyze_technique(technique, file_data)
                if technique_result:
                    result['features'][technique] = technique_result['features']
                    if technique_result.get('plot'):
                        result['plots'][technique] = technique_result['plot']

            except Exception as e:
                self.logger.error(f"Error analyzing {technique}: {str(e)}")
                # Continue with other techniques even if one fails
                result['features'][technique] = {'error': str(e)}

        # Generate LLM summary if we have any features
        if result['features']:
            try:
                llm_summary = self._generate_llm_analysis(result['features'])
                result['summary'] = llm_summary
            except Exception as e:
                self.logger.error(f"Error generating LLM analysis: {str(e)}")
                result['summary'] = f"Analysis completed but LLM summary failed: {str(e)}"

        self.logger.info(f"Material analysis completed with {len(result['features'])} techniques")
        return result

    def analyze_materials_with_context(self, analysis_request: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze materials with additional context (modification description and user query).
        Supports original vs modified material comparison.

        Args:
            analysis_request: Dictionary containing files, modification_description, and user_query

        Returns:
            Dictionary containing analysis results with context-aware LLM analysis
        """
        files = analysis_request.get('files', {})
        modification_description = analysis_request.get('modification_description', '')
        user_query = analysis_request.get('user_query', '')

        self.logger.info(f"Starting contextual material analysis with {len(files)} files")
        self.logger.info(f"Modification description: {modification_description[:100] if modification_description else 'None'}")
        self.logger.info(f"User query: {user_query[:100] if user_query else 'None'}")

        # Initialize result structure
        result = {
            'features': {},
            'plots': {},
            'summary': '',
            'modification_description': modification_description,
            'user_query': user_query
        }

        # Separate original and modified files by technique
        techniques_data = {}

        # Process files and group by technique
        for file_key, file_data in files.items():
            if file_data is None:
                continue

            # Extract technique from file key (e.g., 'original_xrd' -> 'xrd')
            if file_key.startswith('original_'):
                technique = file_key.replace('original_', '')
                material_type = 'original'
            elif file_key.startswith('modified_'):
                technique = file_key.replace('modified_', '')
                material_type = 'modified'
            else:
                self.logger.warning(f"Unknown file key format: {file_key}")
                continue

            if technique not in techniques_data:
                techniques_data[technique] = {}

            try:
                technique_result = self._analyze_technique(technique, file_data)
                if technique_result:
                    techniques_data[technique][material_type] = {
                        'features': technique_result['features'],
                        'plot': technique_result.get('plot')
                    }
                    self.logger.info(f"Successfully analyzed {material_type} {technique}")

            except Exception as e:
                self.logger.error(f"Error analyzing {material_type} {technique}: {str(e)}")
                techniques_data[technique][material_type] = {'error': str(e)}

        # Process results by technique
        for technique, data in techniques_data.items():
            if not data:
                continue

            # Combine original and modified features for comparison
            technique_features = {}
            technique_plots = {}

            for material_type, result_data in data.items():
                if 'error' in result_data:
                    technique_features[f'{material_type}_error'] = result_data['error']
                else:
                    technique_features[material_type] = result_data['features']
                    if result_data.get('plot'):
                        technique_plots[material_type] = result_data['plot']

            if technique_features:
                result['features'][technique] = technique_features
                if technique_plots:
                    result['plots'][technique] = technique_plots

        # Generate context-aware LLM summary if we have any features
        if result['features']:
            try:
                llm_summary = self._generate_contextual_llm_analysis(
                    result['features'],
                    modification_description,
                    user_query
                )
                result['summary'] = llm_summary
            except Exception as e:
                self.logger.error(f"Error generating contextual LLM analysis: {str(e)}")
                result['summary'] = f"Analysis completed but LLM summary failed: {str(e)}"

        self.logger.info(f"Contextual material analysis completed with {len(result['features'])} techniques")
        return result

    def _analyze_technique(self, technique: str, file_data: Any) -> Optional[Dict[str, Any]]:
        """Analyze a single technique based on file type."""
        if technique == 'xrd':
            return self._analyze_xrd(file_data)
        elif technique == 'ir':
            return self._analyze_ir(file_data)
        elif technique == 'tga':
            return self._analyze_tga(file_data)
        elif technique == 'bet':
            return self._analyze_bet(file_data)
        else:
            self.logger.warning(f"Unknown technique: {technique}")
            return None

    def _analyze_xrd(self, file_data: Any) -> Dict[str, Any]:
        """Analyze XRD data."""
        # Handle uploaded file object
        if hasattr(file_data, 'filename'):
            # Save uploaded file to temporary location
            import tempfile
            import shutil

            with tempfile.NamedTemporaryFile(delete=False, suffix='.csv') as tmp_file:
                shutil.copyfileobj(file_data.file, tmp_file)
                file_path = Path(tmp_file.name)

            try:
                features = self.xrd_analyzer.parse_data_file(file_path)
                plot_data = self.xrd_analyzer.generate_plot_data(file_path)

                return {
                    'features': features,
                    'plot': plot_data
                }
            finally:
                # Clean up temporary file
                if file_path.exists():
                    file_path.unlink()
        else:
            file_path = Path(file_data)
            features = self.xrd_analyzer.parse_data_file(file_path)
            plot_data = self.xrd_analyzer.generate_plot_data(file_path)

            return {
                'features': features,
                'plot': plot_data
            }

    def _analyze_ir(self, file_data: Any) -> Dict[str, Any]:
        """Analyze IR data."""
        # Handle uploaded file object
        if hasattr(file_data, 'filename'):
            # Save uploaded file to temporary location
            import tempfile
            import shutil

            with tempfile.NamedTemporaryFile(delete=False, suffix='.csv') as tmp_file:
                shutil.copyfileobj(file_data.file, tmp_file)
                file_path = Path(tmp_file.name)

            try:
                features = self.ir_analyzer.parse_data_file(file_path)
                plot_data = self.ir_analyzer.generate_plot_data(file_path)

                return {
                    'features': features,
                    'plot': plot_data
                }
            finally:
                # Clean up temporary file
                if file_path.exists():
                    file_path.unlink()
        else:
            file_path = Path(file_data)
            features = self.ir_analyzer.parse_data_file(file_path)
            plot_data = self.ir_analyzer.generate_plot_data(file_path)

            return {
                'features': features,
                'plot': plot_data
            }

    def _analyze_tga(self, file_data: Any) -> Dict[str, Any]:
        """Analyze TGA data."""
        # Handle uploaded file object
        if hasattr(file_data, 'filename'):
            # Save uploaded file to temporary location
            import tempfile
            import shutil

            with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as tmp_file:
                shutil.copyfileobj(file_data.file, tmp_file)
                file_path = Path(tmp_file.name)

            try:
                features = self.tga_analyzer.parse_excel(file_path)
                # TGA doesn't generate plots
                return {
                    'features': features,
                    'plot': None
                }
            finally:
                # Clean up temporary file
                if file_path.exists():
                    file_path.unlink()
        else:
            file_path = Path(file_data)
            features = self.tga_analyzer.parse_excel(file_path)
            # TGA doesn't generate plots
            return {
                'features': features,
                'plot': None
            }

    def _analyze_bet(self, file_data: Any) -> Dict[str, Any]:
        """Analyze BET data."""
        # Handle uploaded file object
        if hasattr(file_data, 'filename'):
            # Save uploaded file to temporary location
            import tempfile
            import shutil

            with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
                shutil.copyfileobj(file_data.file, tmp_file)
                file_path = Path(tmp_file.name)

            try:
                features = self.bet_analyzer.parse_first_page(file_path)
                # BET doesn't generate plots
                return {
                    'features': features,
                    'plot': None
                }
            finally:
                # Clean up temporary file
                if file_path.exists():
                    file_path.unlink()
        else:
            file_path = Path(file_data)
            features = self.bet_analyzer.parse_first_page(file_path)
            # BET doesn't generate plots
            return {
                'features': features,
                'plot': None
            }

    def _generate_llm_analysis(self, features: Dict[str, Any], user_query: Optional[str] = None) -> str:
        """Generate LLM analysis using GPT-5 responses API with JSON schema."""
        try:
            # Create analysis request using unified prompt builder
            analysis_request = create_material_analysis_request(features, user_query)

            # Call LLM with JSON schema constraint
            full_prompt = f"{analysis_request['system_prompt']}\n\n{analysis_request['user_prompt']}"

            # 獲取當前模型和參數設定
            current_model = settings_manager.get_current_model()
            llm_params = settings_manager.get_llm_parameters()

            # 根據可用的技術創建條件性schema
            available_techniques = [tech for tech in features.keys() if features[tech]]
            conditional_schema = create_conditional_material_analysis_schema(available_techniques)

            # 🔍 DEBUG: 記錄關鍵信息
            self.logger.info(f"🔍 [DATA_ANALYZER] 可用技術: {available_techniques}")
            self.logger.info(f"🔍 [DATA_ANALYZER] 當前模型: {current_model}")
            self.logger.info(f"🔍 [DATA_ANALYZER] LLM參數: {llm_params}")
            self.logger.info(f"🔍 [DATA_ANALYZER] 條件性Schema: {json.dumps(conditional_schema, indent=2, ensure_ascii=False)}")
            self.logger.info(f"🔍 [DATA_ANALYZER] 提示詞長度: {len(full_prompt)} 字符")

            # 記錄參數映射過程
            self.logger.info(f"🔍 [DATA_ANALYZER] 參數映射檢查:")
            self.logger.info(f"   - max_tokens: {llm_params.get('max_tokens')}")
            self.logger.info(f"   - max_output_tokens: {llm_params.get('max_output_tokens')}")
            self.logger.info(f"   - timeout: {llm_params.get('timeout')}")
            self.logger.info(f"   - reasoning_effort: {llm_params.get('reasoning_effort')}")
            self.logger.info(f"   - verbosity: {llm_params.get('verbosity')}")

            # 使用LLMClient的結構化方法，與研究提案相同的Responses API流程
            self.logger.info("🔍 [DATA_ANALYZER] 開始調用 LLMClient.call_structured_llm")
            self.logger.info(f"🔍 [DATA_ANALYZER] 調用參數:")
            self.logger.info(f"   - prompt長度: {len(full_prompt)}")
            self.logger.info(f"   - schema類型: {type(conditional_schema)}")
            self.logger.info(f"   - model: {current_model}")
            self.logger.info(f"   - llm_params: {llm_params}")

            # 使用LLMClient的結構化方法，與研究提案保持一致
            from backend.core.llm_client import get_llm_client

            llm_client = get_llm_client()
            response = llm_client.call_structured_llm(
                prompt=full_prompt,
                schema=conditional_schema,
                model=current_model,
                llm_params=llm_params
            )

            self.logger.info(f"🔍 [DATA_ANALYZER] LLMClient.call_structured_llm 返回類型: {type(response)}")
            self.logger.info(f"🔍 [DATA_ANALYZER] LLMClient.call_structured_llm 返回內容: {str(response)[:200]}...")

            # 檢查response格式
            if isinstance(response, dict):
                self.logger.info(f"✅ [DATA_ANALYZER] 成功獲得結構化回應 (dict)")
                self.logger.info(f"🔍 [DATA_ANALYZER] 回應鍵值: {list(response.keys())}")
            elif isinstance(response, str):
                self.logger.warning(f"⚠️ [DATA_ANALYZER] 獲得文本回應而非結構化回應")
                self.logger.warning(f"⚠️ [DATA_ANALYZER] 這可能表示JSON schema未正確應用")
            else:
                self.logger.warning(f"⚠️ [DATA_ANALYZER] 未知的回應類型: {type(response)}")

            # Parse structured response (LLMClient.call_structured_llm returns dict)
            if isinstance(response, dict):
                # 兼容多種字段名稱
                summary = response.get('overall_summary') or response.get('summary', 'Analysis completed successfully.')
                recommendations = response.get('recommendations', [])

                # 記錄實際返回的字段以便調試
                self.logger.info(f"📊 [DATA_ANALYZER] LLM返回的字段: {list(response.keys())}")
                self.logger.info(f"📊 [DATA_ANALYZER] 提取的summary: {summary[:100]}...")

                if recommendations:
                    summary += f"\n\nRecommendations:\n" + "\n".join(f"- {rec}" for rec in recommendations)

                return summary
            else:
                # Fallback if response is not dict
                return str(response)

        except Exception as e:
            self.logger.error(f"LLM analysis failed: {str(e)}")
            return self._create_fallback_summary(features)

    def _generate_contextual_llm_analysis(self, features: Dict[str, Any], modification_description: str, user_query: str) -> str:
        """Generate context-aware LLM analysis using modification description and user query."""
        try:
            # Create analysis request using unified prompt builder
            analysis_request = create_material_analysis_request(features, user_query)

            # Enhance system prompt with modification context
            enhanced_system_prompt = f"""{analysis_request['system_prompt']}

IMPORTANT CONTEXT:
- Modification Description: {modification_description if modification_description else 'No modification description provided'}
- User Query: {user_query if user_query else 'No specific query provided'}

Please focus your analysis on comparing the differences between original and modified materials based on the provided data.
Pay special attention to how the modifications might have affected the material properties."""

            # Call LLM with enhanced context
            full_prompt = f"{enhanced_system_prompt}\n\n{analysis_request['user_prompt']}"

            # 獲取當前模型和參數設定
            current_model = settings_manager.get_current_model()
            llm_params = settings_manager.get_llm_parameters()

            # 根據可用的技術創建條件性schema
            available_techniques = [tech for tech in features.keys() if features[tech]]
            conditional_schema = create_conditional_material_analysis_schema(available_techniques)

            # 🔍 DEBUG: 記錄關鍵信息
            self.logger.info(f"🔍 [DATA_ANALYZER_CONTEXTUAL] 可用技術: {available_techniques}")
            self.logger.info(f"🔍 [DATA_ANALYZER_CONTEXTUAL] 當前模型: {current_model}")
            self.logger.info(f"🔍 [DATA_ANALYZER_CONTEXTUAL] 條件性Schema: {json.dumps(conditional_schema, indent=2, ensure_ascii=False)}")

            # 使用LLMClient的結構化方法，與研究提案保持一致
            from backend.core.llm_client import get_llm_client

            llm_client = get_llm_client()
            response = llm_client.call_structured_llm(
                prompt=full_prompt,
                schema=conditional_schema,
                model=current_model,
                llm_params=llm_params
            )

            self.logger.info(f"🔍 [DATA_ANALYZER_CONTEXTUAL] LLMClient.call_structured_llm 返回類型: {type(response)}")
            self.logger.info(f"🔍 [DATA_ANALYZER_CONTEXTUAL] LLMClient.call_structured_llm 返回內容: {str(response)[:200]}...")

            # Parse structured response (LLMClient.call_structured_llm returns dict)
            if isinstance(response, dict):
                self.logger.info(f"✅ [DATA_ANALYZER_CONTEXTUAL] 成功獲得結構化回應 (dict)")
                self.logger.info(f"🔍 [DATA_ANALYZER_CONTEXTUAL] 回應鍵值: {list(response.keys())}")

                # 兼容多種字段名稱
                summary = response.get('overall_summary') or response.get('summary', 'Contextual analysis completed successfully.')
                recommendations = response.get('recommendations', [])

                # 記錄實際返回的字段以便調試
                self.logger.info(f"📊 [DATA_ANALYZER_CONTEXTUAL] LLM返回的字段: {list(response.keys())}")
                self.logger.info(f"📊 [DATA_ANALYZER_CONTEXTUAL] 提取的summary: {summary[:100]}...")

                # 構建完整的結構化回應
                structured_response = {
                    'summary': summary,
                    'recommendations': recommendations,
                    'structured_analysis': {}
                }

                # 添加技術特定的結構化分析
                for technique in available_techniques:
                    if technique in response:
                        structured_response['structured_analysis'][technique] = response[technique]
                        self.logger.info(f"📊 [DATA_ANALYZER_CONTEXTUAL] 添加 {technique} 結構化分析")

                return structured_response
            elif isinstance(response, str):
                self.logger.warning(f"⚠️ [DATA_ANALYZER_CONTEXTUAL] 獲得文本回應而非結構化回應")
                self.logger.warning(f"⚠️ [DATA_ANALYZER_CONTEXTUAL] 這可能表示JSON schema未正確應用")
                return response
            else:
                self.logger.warning(f"⚠️ [DATA_ANALYZER_CONTEXTUAL] 未知的回應類型: {type(response)}")
                return str(response)

        except Exception as e:
            self.logger.error(f"Contextual LLM analysis failed: {str(e)}")
            return self._create_contextual_fallback_summary(features, modification_description, user_query)

    def _create_fallback_summary(self, features: Dict[str, Any]) -> str:
        """Create fallback summary when LLM analysis fails."""
        summary_parts = ["Material Analysis Summary:"]

        for technique, data in features.items():
            if 'error' in data:
                summary_parts.append(f"\n{technique.upper()}: Analysis failed - {data['error']}")
                continue

            summary_parts.append(f"\n{technique.upper()} Results:")

            if technique == 'xrd':
                summary_parts.append(f"- Detected {data.get('peak_count', 0)} peaks")
                summary_parts.append(f"- Max intensity: {data.get('max_intensity', 'N/A')}")

            elif technique == 'ir':
                summary_parts.append(f"- Detected {data.get('peak_count', 0)} peaks")
                functional_groups = data.get('functional_groups', {})
                if functional_groups:
                    summary_parts.append(f"- Functional groups: {', '.join(functional_groups.keys())}")

            elif technique == 'tga':
                summary_parts.append(f"- Sample: {data.get('sample_name', 'Unknown')}")
                summary_parts.append(f"- Unit adsorption: {data.get('unit_adsorption', 'N/A')}")
                summary_parts.append(f"- Desorption energy: {data.get('desorption_energy', 'N/A')}")

            elif technique == 'bet':
                summary_parts.append(f"- Surface area: {data.get('surface_area', 'N/A')} m²/g")
                summary_parts.append(f"- Pore size: {data.get('pore_size', 'N/A')} nm")

        summary_parts.append("\nNote: Detailed AI analysis was unavailable. Please review the extracted features above.")

        return "\n".join(summary_parts)

    def _create_contextual_fallback_summary(self, features: Dict[str, Any], modification_description: str, user_query: str) -> str:
        """Create fallback summary with context when LLM analysis fails."""
        summary_parts = ["Material Analysis Summary with Context:"]

        if modification_description:
            summary_parts.append(f"\nModification Description: {modification_description}")

        if user_query:
            summary_parts.append(f"\nUser Query: {user_query}")

        summary_parts.append("\nAnalysis Results:")

        for technique, data in features.items():
            if 'error' in data:
                summary_parts.append(f"\n{technique.upper()}: Analysis failed - {data['error']}")
                continue

            summary_parts.append(f"\n{technique.upper()} Results:")

            if technique == 'xrd':
                summary_parts.append(f"- Detected {data.get('peak_count', 0)} peaks")
                summary_parts.append(f"- Max intensity: {data.get('max_intensity', 'N/A')}")

            elif technique == 'ir':
                summary_parts.append(f"- Detected {data.get('peak_count', 0)} peaks")
                functional_groups = data.get('functional_groups', {})
                if functional_groups:
                    summary_parts.append(f"- Functional groups: {', '.join(functional_groups.keys())}")

            elif technique == 'tga':
                summary_parts.append(f"- Sample: {data.get('sample_name', 'Unknown')}")
                summary_parts.append(f"- Unit adsorption: {data.get('unit_adsorption', 'N/A')}")
                summary_parts.append(f"- Desorption energy: {data.get('desorption_energy', 'N/A')}")

            elif technique == 'bet':
                summary_parts.append(f"- Surface area: {data.get('surface_area', 'N/A')} m²/g")
                summary_parts.append(f"- Pore size: {data.get('pore_size', 'N/A')} nm")

        summary_parts.append("\nNote: Detailed AI analysis was unavailable. Please review the extracted features above.")

        return "\n".join(summary_parts)


def create_data_analyzer_service() -> DataAnalyzerService:
    """Factory function to create data analyzer service instance."""
    return DataAnalyzerService()
