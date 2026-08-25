import pandas as pd
import os

from backend.config import EXPERIMENT_DIR

def export_new_experiments_to_txt(
    excel_path: str,
    output_dir: str,
    id_column_count: int = 3
):
    """
    將尚未嵌入的實驗資料從 Excel 匯出為語意文本 (.txt)，每列對應一筆。
    若該筆資料已存在對應 txt 檔，則略過不重複建立。

    Parameters:
    - excel_path: Excel 檔案路徑
    - output_dir: 輸出 txt 的資料夾路徑
    - id_column_count: 用來產生唯一 ID 的前幾個欄位數（預設為前 3 欄）
    """
    if not os.path.isabs(output_dir):
        output_dir = os.path.abspath(output_dir)

    # 確保 Excel 文件路徑使用絕對路徑
    if not os.path.isabs(excel_path):
        excel_path = os.path.abspath(excel_path)

    os.makedirs(output_dir, exist_ok=True)
    df = pd.read_excel(excel_path)

    embedded = []
    skipped = []
    txt_paths = []

    def clean_value(val):
        if pd.isna(val):
            return "NA"
        elif isinstance(val, pd.Timestamp):
            return val.strftime("%Y-%m-%d")
        else:
            return str(val)

    for idx, row in df.iterrows():
        # 產生唯一識別 ID（依前幾欄組成）
        raw_id = "_".join(clean_value(row[i]) for i in df.columns[:id_column_count])
        exp_id = "".join(c if c.isalnum() or c in "-_." else "_" for c in raw_id)
        txt_path = os.path.join(output_dir, f"{exp_id}.txt")

        if os.path.exists(txt_path):
            skipped.append(exp_id)
            continue

        # 將此列內容轉為語意化段落
        content = "\n".join(
            [f"[{col}] {row[col]}" for col in df.columns if pd.notna(row[col])]
        )
        with open(txt_path, "w", encoding="utf-8") as f:
            f.write(content)
        embedded.append(exp_id)
        txt_paths.append(txt_path)

    return (
        pd.DataFrame({
            "exp_id": embedded + skipped,
            "status": ["✅ 嵌入成功"] * len(embedded) + ["⏭️ 已存在略過"] * len(skipped)
        }),
        txt_paths
    )

# 範例執行
if __name__ == "__main__":
    excel_path = os.path.join(EXPERIMENT_DIR, "experiment_log_for_agent.xlsx")
    result_df = export_new_experiments_to_txt(excel_path, EXPERIMENT_DIR)
    print(result_df)
