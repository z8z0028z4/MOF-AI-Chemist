import os
import pandas as pd
# 兼容性導入：支持相對導入和絕對導入
try:
    from .config import REGISTRY_EXPERIMENT_PATH
except ImportError:
    # 當作為模組導入時使用絕對導入
    from config import REGISTRY_EXPERIMENT_PATH

# 欄位順序定義
METADATA_EXPERIMENT_COLUMNS = [
    "expriment_tracing_number", "experiment_name", "date", "objective",
    "method", "result", "analysis_comment","type"
]

def append_experiment_metadata_to_registry(metadata: dict):
    os.makedirs(os.path.dirname(REGISTRY_EXPERIMENT_PATH), exist_ok=True)

    if not os.path.exists(REGISTRY_EXPERIMENT_PATH):
        df = pd.DataFrame(columns=REGISTRY_EXPERIMENT_PATH)
    else:
        df = pd.read_excel(REGISTRY_EXPERIMENT_PATH)

    # 新增這筆 metadata
    new_row = {col: metadata.get(col, "") for col in METADATA_EXPERIMENT_COLUMNS}
    df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)

    try:
        df.to_excel(REGISTRY_EXPERIMENT_PATH, index=False)
        print(f"✅ 已寫入 metadata：{metadata['experiment_name']}")
    except Exception as e:
        print(f"❌ 寫入 Excel 時失敗：{e}")


if __name__ == "__main__":
    # 範例測試
    sample_metadata = {
        "expriment_tracing_number": "1",
        "experiment_name" : "test1",
        "date": "20250706",
        "objective": "Test goal",
        "method": "Material A + B Mix and heat",
        "result": "Crystal formed",
        "analysis_comment": "high BET surface area, high co2 adosorption in TGA analysis",
        "type": "experiment"
    }
    append_experiment_metadata_to_registry(sample_metadata)
