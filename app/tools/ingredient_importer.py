import os
import sqlite3
import pandas as pd

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
EXCEL_PATH = os.path.join(BASE_DIR, "data", "VitalPet_Ingredient_Master_Template.xlsx")
DB_PATH = os.path.join(BASE_DIR, "data", "evidence_vault.db")

def sync_excel_to_db():
    if not os.path.exists(EXCEL_PATH):
        print(f"❌ 找不到文件: {EXCEL_PATH}")
        return

    print("🔄 正在将 Excel 原料主数据同步至 SQLite 数据库...")
    xls = pd.ExcelFile(EXCEL_PATH)
    conn = sqlite3.connect(DB_PATH)

    sheets = ["Ingredient_Core", "Species_Dose", "Commercial", "Safety_Rules"]
    for sheet in sheets:
        if sheet in xls.sheet_names:
            df = pd.read_excel(xls, sheet)
            # 清理列名两端空格
            df.columns = [c.strip() for c in df.columns]
            # 存入 SQLite，覆盖旧表
            df.to_sql(sheet.lower(), conn, if_exists="replace", index=False)
            print(f"  + 表 [{sheet}] 已同步，共 {len(df)} 行数据")

    conn.close()
    print("✅ 同步完成！数据已就绪。")

if __name__ == "__main__":
    sync_excel_to_db()

