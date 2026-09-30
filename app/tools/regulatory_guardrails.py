# app/tools/regulatory_guardrails.py
import sqlite3
import os
from typing import List, Dict

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DB_PATH = os.path.join(BASE_DIR, "data", "evidence_vault.db")

# 绝对禁用毒理物质黑名单 (物种专一性毒理库)
BANNED_SUBSTANCES_MAP = {
    "Cat": [
        {"name": "对乙酰氨基酚 (扑热息痛 / Paracetamol / Acetaminophen)", "risk": "红细胞高铁血红蛋白血症与急性肝坏死致死"},
        {"name": "茶树精油 (Tea Tree Oil)", "risk": "缺乏葡萄糖醛酸转移酶导致中枢神经毒性与昏迷"},
        {"name": "百合提取物 (Lilium spp.)", "risk": "极微量即导致急性不可逆性肾小管坏死衰竭"},
        {"name": "有机硫化物/洋葱大蒜提取物 (Allium)", "risk": "海因茨小体溶血性贫血"}
    ],
    "Dog": [
        {"name": "木糖醇 (Xylitol)", "risk": "刺激胰岛素极速超量释放导致致死性低血糖与急性肝坏死"},
        {"name": "可可碱/巧克力提取物 (Theobromine)", "risk": "严重中枢神经兴奋与心律失常致死"},
        {"name": "茶树精油 (眼周/高浓度)", "risk": "严重神经共济失调与眼部角膜溃疡穿孔"}
    ]
}

def audit_formula_compliance(species: str, weight_kg: float, active_ingredients_audit: List[Dict]) -> Dict:
    """
    自动审查配方中的活性成分是否违反法规禁令、毒理红线或超过安全耐受上限
    :param active_ingredients_audit: 格式 [{'name': '原料名', 'dose_mg_per_kg': 15.0}]
    """
    spec_clean = "Cat" if any(k in species.lower() for k in ["cat", "猫"]) else "Dog"
    alerts = []
    compliance_items = []
    has_critical_violation = False

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # 1. 毒理黑名单筛查
    banned_list = BANNED_SUBSTANCES_MAP.get(spec_clean, [])
    for act in active_ingredients_audit:
        act_name = act.get("name", "").lower()
        for b in banned_list:
            if any(term.lower() in act_name for term in b["name"].split("/")):
                has_critical_violation = True
                alerts.append({
                    "level": "🚨 严重致死违规",
                    "ingredient": act["name"],
                    "reason": f"物种 [{spec_clean}] 严禁摄入！毒理机理: {b['risk']}"
                })

    # 2. 安全上限与法规准入核查
    for act in active_ingredients_audit:
        name = act.get("name", "")
        dose_mg_kg = float(act.get("dose_mg_per_kg", 0.0))

        # 查数据库安全规则表
        sql = """
            SELECT c.Ingredient_Name_CN, s.Safety_Limit_BW, s.Safety_Limit_Unit, 
                   s.CN_Feed_Status, s.US_Status, s.Interactions
            FROM ingredient_core c
            LEFT JOIN safety_rules s ON c.Ingredient_ID = s.Ingredient_ID
            WHERE c.Ingredient_Name_CN LIKE ? OR c.Ingredient_Name_EN LIKE ? OR c.Synonyms LIKE ?
        """
        cursor.execute(sql, (f"%{name}%", f"%{name}%", f"%{name}%"))
        row = cursor.fetchone()

        if row and row["Safety_Limit_BW"]:
            safety_limit = float(row["Safety_Limit_BW"])
            status_cn = row["CN_Feed_Status"] or "Listed"
            status_us = row["US_Status"] or "AAFCO_Defined"
            
            # 剂量超标判定
            if dose_mg_kg > safety_limit:
                has_critical_violation = True
                alerts.append({
                    "level": "⚠️ 剂量超标报警",
                    "ingredient": name,
                    "reason": f"当前设计量 {dose_mg_kg:.1f} mg/kg 已超过官方安全耐受上限 ({safety_limit:.1f} mg/kg)，超标 {(dose_mg_kg/safety_limit - 1)*100:.1f}%！存在代谢蓄积风险。"
                })
            else:
                compliance_items.append({
                    "ingredient": name,
                    "designed_dose": f"{dose_mg_kg:.1f} mg/kg",
                    "safety_limit": f"{safety_limit:.1f} mg/kg",
                    "cn_status": "✅ 农业农村部已列明" if status_cn == "Listed" else f"ℹ️ {status_cn}",
                    "us_status": status_us,
                    "result": "合规安全"
                })
        else:
            # 原料库未收录的新成分
            compliance_items.append({
                "ingredient": name,
                "designed_dose": f"{dose_mg_kg:.1f} mg/kg",
                "safety_limit": "文献自研阈值 (库内未登记)",
                "cn_status": "需企业原料合规备案",
                "us_status": "Self-Affirmed GRAS",
                "result": "需进一步法规评估"
            })

    conn.close()

    return {
        "is_safe": not has_critical_violation,
        "alerts": alerts,
        "compliance_items": compliance_items
    }

