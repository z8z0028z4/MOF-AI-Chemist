"""
提示詞構建模組
============

負責構建各種類型的提示詞，包括提案生成、實驗設計等
"""

from typing import List, Dict, Any, Optional, Tuple
from langchain_core.documents import Document

from backend.utils.logger import get_logger

logger = get_logger(__name__)


def build_prompt(chunks: List[Document], question: str) -> Tuple[str, List[Dict]]:
    """
    構建嚴謹回答模式的提示詞，不允許使用任何外部知識

    Args:
        chunks: 文檔塊列表
        question: 問題

    Returns:
        Tuple[str, List[Dict]]: (系統提示詞, 引用列表)
    """
    # 檢查：chunks 必須是 List[Document]，question 應為 str
    context_text = ""
    citations = []
    citation_map = {}

    for i, doc in enumerate(chunks):
        # 檢查：doc 應有 metadata 屬性，且為 dict
        metadata = doc.metadata
        title = metadata.get("title", "Untitled")
        # 檢查：filename 來源於 "filename" 或 "source"，若都無則為 "Unknown"
        filename = metadata.get("filename") or metadata.get("source", "Unknown")
        # 檢查：page 來源於 "page_number" 或 "page"，若都無則為 "?"
        page = metadata.get("page_number") or metadata.get("page", "?")
        # 預覽片段，取前 80 字元，並將換行替換為空格
        snippet = doc.page_content[:80].replace("\n", " ")

        # 檢查：避免重複的 (filename, page) 組合
        citation_key = f"{filename}_p{page}"
        if citation_key not in citation_map:
            label = f"[{len(citations) + 1}]"
            citations.append({
                "label": label,
                "title": title,
                "source": filename,
                "page": page,
                "snippet": snippet
            })
            citation_map[citation_key] = label
        else:
            label = citation_map[citation_key]

        # context_text 累加每個 chunk 的內容，格式為 [n] title | Page n
        context_text += f"{label} {title} | Page {page}\n{doc.page_content}\n\n"

    # system_prompt is the final prompt containing context_text and question
    system_prompt = f"""

    You are a research literature search assistant. Please answer questions based only on the provided literature excerpts.
    Please use [1], [2], etc. to cite paragraph sources in your answers, and do not repeat the sources at the end.
    If the paragraphs mention specific experimental conditions (temperature, time, etc.), please be sure to include them in your answer.
    Important: You can only cite the provided literature excerpts. The current literature excerpt numbers are [1] to [{len(chunks)}] (total {len(chunks)} excerpts)

    --- Literature Summary ---
    {context_text}


    --- Question ---
    {question}
    """
    # Check: return system_prompt with trimmed whitespace and citations list
    return system_prompt.strip(), citations


def build_proposal_prompt(question: str, chunks: List[Document]) -> Tuple[str, List[Dict]]:
    """
    構建研究提案生成提示詞

    Args:
        question: 研究問題
        chunks: 文檔塊列表

    Returns:
        Tuple[str, List[Dict]]: (系統提示詞, 引用列表)
    """
    paper_context_text = ""
    citations = []
    citation_map = {}

    for i, doc in enumerate(chunks):

        meta = doc.metadata
        title = meta.get("title", "Untitled")
        filename = meta.get("filename") or meta.get("source", "Unknown")
        page = meta.get("page_number") or meta.get("page", "?")
        snippet = doc.page_content[:80].replace("\n", " ")

        # 檢查：避免重複的 (filename, page) 組合
        citation_key = f"{filename}_p{page}"
        if citation_key not in citation_map:
            label = f"[{len(citations) + 1}]"
            citations.append({
                "label": label,
                "title": title,
                "source": filename,
                "page": page,
                "snippet": snippet
            })
            citation_map[citation_key] = label
        else:
            label = citation_map[citation_key]

        paper_context_text += f"{label} {title} | Page {page}\n{doc.page_content}\n\n"

    system_prompt = f"""
    You are a scientific research expert who excels at proposing innovative and feasible research proposals based on literature summaries and research objectives.
    Your expertise covers materials science, chemistry, physics, and engineering, and you are capable of deriving new ideas grounded in experimental evidence and theoretical principles.

    Your task is to generate a structured research proposal based on the provided literature excerpts and research objectives. The proposal should be innovative, scientifically rigorous, and feasible.

    IMPORTANT: You must respond in valid JSON format only. Do not include any text before or after the JSON object.

    The JSON must have the following structure:
    {{
        "proposal_title": "Title of the research proposal",
        "need": "Research need and current limitations",
        "solution": "Proposed design and development strategies",
        "differentiation": "Comparison with existing technologies",
        "benefit": "Expected improvements and benefits",
        "experimental_overview": "Experimental approach and methodology",
        "materials_list": ["material1", "material2", "material3"],
        "mof_metal_element": "The primary metal element symbol (e.g., Cu, Zn, Zr, Fe, Co, Ni) if the proposed material is a MOF, otherwise empty string.",
        "mof_linker_name": "The chemical name of the primary organic ligand (linker) (e.g. 1,4-benzenedicarboxylic acid) if the proposed material is a MOF, otherwise empty string.",
        "mof_linker_name_2": "Optional. The chemical name of the secondary or auxiliary ligand/linker (e.g. oxalic acid) if applicable, otherwise empty string."
    }}

    Key requirements:
    1. Propose new components, structures, or mechanisms (e.g., new ligands, frameworks, catalysts, processing techniques) based on the literature
    2. Clearly explain structural or functional advantages and potential reactivity/performance
    3. All proposed designs must have a logical basis — avoid inventing unreasonable structures without justification
    4. Maintain scientific rigor, clarity, and avoid vague descriptions
    5. Use only the provided literature labels ([1], [2], etc.) for citations, and do not fabricate sources
    6. Ensure every claim is supported by a cited source or reasonable extension from the literature
    7. For materials_list, include ONLY IUPAC chemical names without any descriptions, notes, or parenthetical explanations. Each item must be a single chemical name only.

    Literature excerpts are provided below with labels from [1] to [{len(chunks)}] (total {len(chunks)} excerpts).
    """

    return system_prompt.strip(), citations


def build_detail_experimental_plan_prompt(chunks: List[Document], proposal_text: str) -> Tuple[str, List[Dict]]:
    """
    構建詳細實驗計劃生成提示詞

    Args:
        chunks: 文檔塊列表
        proposal_text: 提案文本

    Returns:
        Tuple[str, List[Dict]]: (系統提示詞, 引用列表)
    """
    context_text = ""
    citations = []
    citation_map = {}

    for i, doc in enumerate(chunks):
        # 處理可能是字典格式的 chunks
        if hasattr(doc, 'metadata'):
            metadata = doc.metadata
            page_content = doc.page_content
        else:
            metadata = doc.get('metadata', {})
            page_content = doc.get('page_content', '')

        title = metadata.get("title", "Untitled")
        # 檢查：filename 來源於 "filename" 或 "source"，若都無則為 "Unknown"
        filename = metadata.get("filename") or metadata.get("source", "Unknown")
        # 檢查：page 來源於 "page_number" 或 "page"，若都無則為 "?"
        page = metadata.get("page_number") or metadata.get("page", "?")
        # 預覽片段，取前 80 字元，並將換行替換為空格
        snippet = page_content[:80].replace("\n", " ")

        # 檢查：避免重複的 (filename, page) 組合
        citation_key = f"{filename}_p{page}"
        if citation_key not in citation_map:
            label = f"[{len(citations) + 1}]"
            citations.append({
                "label": label,
                "title": title,
                "source": filename,
                "page": page,
                "snippet": snippet
            })
            citation_map[citation_key] = label
        else:
            label = citation_map[citation_key]

        # context_text 累加每個 chunk 的內容，格式為 [n] title | Page n
        context_text += f"{label} {title} | Page {page}\n{page_content}\n\n"

    system_prompt = f"""
    You are an experienced consultant in materials experiment design. Based on the following research proposal and related literature excerpts, please provide the researcher with a detailed set of recommended experimental procedures.

    IMPORTANT: Please provide your response in plain text format only. Do NOT use any markdown formatting, bold text, or special formatting. Use simple text with clear section headers and bullet points.

    Please include the following sections:

    SYNTHESIS PROCESS:
    Provide a step-by-step description of each experimental operation, including sequence, logic, and purpose.
    Guidelines for synthesis process:
    - Suggest specific ranges of experimental conditions (temperature, time, pressure, etc.)
    - For each reaction condition and step mentioned in the literature, cite the source ([1], [2], etc.)
    - For suggested conditions not based on literature, explain your logic clearly

    MATERIALS AND CONDITIONS:
    List the required raw materials for each step (including proportions) and the reaction conditions (temperature, time, containers).

    ANALYTICAL METHODS:
    Suggest characterization tools (such as XRD, BET, TGA) and explain the purpose of each.

    PRECAUTIONS:
    Highlight key points or parameter limitations mentioned in the literature.

    Format your response with clear section headers in CAPITAL LETTERS, followed by detailed explanations. Use simple bullet points (-) for lists.
    Use [1], [2], etc. to cite the literature sources in your response. Only cite the provided literature excerpts, numbered [1] to [{len(chunks)}] (total {len(chunks)} excerpts).

    --- literature chunks ---
    {context_text}

    --- User's Proposal ---
    {proposal_text}
    """
    return system_prompt.strip(), citations


def build_inference_prompt(chunks: List[Document], question: str) -> Tuple[str, List[Dict]]:
    """
    構建推理提示詞

    Args:
        chunks: 文檔塊列表
        question: 問題

    Returns:
        Tuple[str, List[Dict]]: (系統提示詞, 引用列表)
    """
    context_text = ""
    citations = []
    citation_map = {}

    for i, doc in enumerate(chunks):
        meta = doc.metadata
        title = meta.get("title", "Untitled")
        filename = meta.get("filename") or meta.get("source", "Unknown")
        page = meta.get("page_number") or meta.get("page", "?")
        snippet = doc.page_content[:80].replace("\n", " ")

        # 檢查：避免重複的 (filename, page) 組合
        citation_key = f"{filename}_p{page}"
        if citation_key not in citation_map:
            label = f"[{len(citations) + 1}]"
            citations.append({
                "label": label,
                "title": title,
                "source": filename,
                "page": page,
                "snippet": snippet
            })
            citation_map[citation_key] = label
        else:
            label = citation_map[citation_key]

        context_text += f"{label} {title} | Page {page}\n{doc.page_content}\n\n"

    system_prompt = f"""
    You are a materials synthesis consultant who understands and excels at comparing the chemical and physical properties of materials. You can propose innovative suggestions based on known experimental conditions for situations where there is no clear literature.

    Please conduct extended thinking based on the following literature and experimental data:
    - You can propose new combinations, temperatures, times, or pathways.
    - Even combinations not yet documented in the literature can be suggested, but you must provide reasonable reasoning.
    - When making inferences and extended thinking, please try to mention "what literature clues this idea originates from" to support your explanation. The current literature excerpt numbers are [1] to [{len(chunks)}] (total {len(chunks)} excerpts)

    --- Literature Summary ---
    {context_text}

    --- Question ---
    {question}
    """
    return system_prompt.strip(), citations


def build_dual_inference_prompt(
    chunks_paper: List[Document],
    question: str,
    experiment_chunks: List[Document]
) -> Tuple[str, List[Dict]]:
    """
    構建雙重推理提示詞（文獻+實驗數據）

    Args:
        chunks_paper: 文獻文檔塊列表
        question: 問題
        experiment_chunks: 實驗文檔塊列表

    Returns:
        Tuple[str, List[Dict]]: (系統提示詞, 引用列表)
    """
    paper_context_text = ""
    exp_context_text = ""
    citations = []
    label_index = 1

    # --- Literature Summary ---
    paper_context_text += "--- Literature Summary ---\n"
    for doc in chunks_paper:
        meta = doc.metadata
        title = meta.get("title", "Untitled")
        filename = meta.get("filename") or meta.get("source", "Unknown")
        page = meta.get("page_number") or meta.get("page", "?")
        snippet = doc.page_content[:80].replace("\n", " ")
        label = f"[{label_index}]"

        citations.append({
            "label": label,
            "title": title,
            "source": filename,
            "page": page,
            "snippet": snippet,
            "type": "paper"
        })

        paper_context_text += f"{label} {title} | Page {page}\n{doc.page_content}\n\n"
        label_index += 1

    # --- Experiment Summary ---
    exp_context_text += "--- Similar Experiment Summary ---\n"
    for doc in experiment_chunks:
        meta = doc.metadata
        filename = meta.get("filename") or meta.get("source", "Unknown")
        exp_id = meta.get("exp_id", "unknown_exp")
        snippet = doc.page_content[:80].replace("\n", " ")
        label = f"[{label_index}]"

        citations.append({
            "label": label,
            "title": exp_id,
            "source": filename,
            "page": "-",  # 沒有頁數
            "snippet": snippet,
            "type": "experiment"
        })

        exp_context_text += f"{label} Experiment {exp_id}\n{doc.page_content}\n\n"
        label_index += 1

    # --- Prompt Injection ---
    system_prompt = f"""
    You are a materials synthesis consultant who understands and excels at comparing the chemical and physical properties of materials.

    You will see three parts of information. Please conduct comprehensive analysis and provide specific inferences and innovative suggestions for experiments:
    1. Literature summary (with source annotations [1], [2])
    2. Similar experiment summary (from vector database)
    3. Experiment records (tables)

    Please propose new suggestions for the research question, including:
    - Adjusted synthesis pathways and conditions (such as temperature, time, ratios)
    - Factors that may affect synthesis success rate
    - Reasoning behind the causes, citing literature ([1], [2]...) or similar experiment results when necessary
    Important: You can only cite the provided literature excerpts. The current literature excerpt numbers are [1] to [{len(chunks_paper) + len(experiment_chunks)}] (total {len(chunks_paper) + len(experiment_chunks)} excerpts)

    --- Literature Knowledge Sources ---
    {paper_context_text}

    --- Experiment Records ---
    {exp_context_text}

    --- Research Question ---
    {question}
    """
    return system_prompt.strip(), citations


def build_iterative_proposal_prompt(
    question: str,
    new_chunks: List[Document],
    old_chunks: List[Document],
    past_proposal: str
) -> Tuple[str, str, List[Dict]]:
    """
    構建迭代式提案生成提示詞

    Args:
        question: 用戶反饋
        new_chunks: 新檢索到的文檔塊
        old_chunks: 原有的文檔塊
        past_proposal: 之前的提案內容

    Returns:
        Tuple[str, str, List[Dict]]: (系統提示詞, 用戶提示詞, 引用列表)
    """
    citations = []

    def format_chunks(chunks: List[Document], label_offset=0) -> Tuple[str, List[Dict]]:
        text = ""
        local_citations = []
        for i, doc in enumerate(chunks):
            meta = doc.metadata
            title = meta.get("title", "Untitled")
            filename = meta.get("filename") or meta.get("source", "Unknown")
            page = meta.get("page_number") or meta.get("page", "?")
            snippet = doc.page_content[:80].replace("\n", " ")
            label = f"[{label_offset + i + 1}]"

            local_citations.append({
                "label": label,
                "title": title,
                "source": filename,
                "page": page,
                "snippet": snippet
            })

            text += f"{label} {title} | Page {page}\n{doc.page_content}\n\n"

        return text, local_citations

    old_text, old_citations = format_chunks(old_chunks)
    new_text, new_citations = format_chunks(new_chunks, label_offset=len(old_citations))
    citations.extend(old_citations + new_citations)

    system_prompt = f"""
    You are an experienced materials experiment design consultant. Please help modify parts of the research proposal based on user feedback, original proposal, and literature content.

    Your task is to generate a modified research proposal based on user feedback, original proposal, and literature content. The proposal should be innovative, scientifically rigorous, and feasible.

    IMPORTANT: You must respond in valid JSON format only. Do not include any text before or after the JSON object.

    The JSON must have the following structure:
    {{
        "proposal_title": "Title of the research proposal",
        "need": "Research need and current limitations",
        "solution": "Proposed design and development strategies",
        "differentiation": "Comparison with existing technologies",
        "benefit": "Expected improvements and benefits",
        "experimental_overview": "Experimental approach and methodology",
        "materials_list": ["material1", "material2", "material3"],
        "mof_metal_element": "The primary metal element symbol (e.g., Cu, Zn, Zr, Fe, Co, Ni) if the proposed material is a MOF, otherwise empty string.",
        "mof_linker_name": "The chemical name of the primary organic ligand (linker) (e.g. 1,4-benzenedicarboxylic acid) if the proposed material is a MOF, otherwise empty string.",
        "mof_linker_name_2": "Optional. The chemical name of the secondary or auxiliary ligand/linker (e.g. oxalic acid) if applicable, otherwise empty string."
    }}

    Key requirements:
    1. Prioritize the areas that the user wants to modify and look for possible improvement directions from the literature
    2. Except for the areas that the user is dissatisfied with, other parts should maintain the original proposal content without changes
    3. Maintain scientific rigor, clarity, and avoid vague descriptions
    4. Use only the provided literature labels ([1], [2], etc.) for citations, and do not fabricate sources
    5. Ensure every claim is supported by a cited source or reasonable extension from the literature
    6. For materials_list, include ONLY IUPAC chemical names without any descriptions, notes, or parenthetical explanations. Each item must be a single chemical name only.

    Literature excerpts are provided below with labels from [1] to [{len(old_chunks) + len(new_chunks)}] (total {len(old_chunks) + len(new_chunks)} excerpts).
    """

    user_prompt = f"""
    --- User Feedback ---
    {question}

    --- Original Proposal Content ---
    {past_proposal}

    --- Literature Excerpts Based on Original Proposal ---
    {old_text}

    --- New Retrieved Excerpts Based on Feedback ---
    {new_text}
    """

    return system_prompt.strip(), user_prompt, citations
