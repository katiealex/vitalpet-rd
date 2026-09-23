# app/tools/formula_tool.py
import sqlite3
import os
import math

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DB_PATH = os.path.join(BASE_DIR, "data", "evidence_vault.db")

# 物种默认参考体重 (当用户未指定时自动兜底)
DEFAULT_SPECIES_WEIGHTS = {
    "Dog": 10.0,
    "Cat": 4.0,
    "Rabbit": 2.0,
    "Guinea_Pig": 0.8,
    "Chinchilla": 0.6,
    "Ferret": 1.2,
    "Bird": 0.1
}

def normalize_species(species_str: str) -> str:
    """智能清洗物种输入，优先识别猫，兼容各类缩写与别名"""
    if not species_str:
        return "Dog"
    s = str(species_str).lower().strip()
    # 只要包含 cat、猫、feline，坚决判定为猫，防止受犬类文献干扰
    if any(k in s for k in ["cat", "猫", "feline"]):
        return "Cat"
    if any(k in s for k in ["dog", "犬", "狗", "canine"]):
        return "Dog"
    if any(k in s for k in ["rabbit", "兔"]):
        return "Rabbit"
    if any(k in s for k in ["guinea", "豚鼠", "荷兰猪", "天竺鼠"]):
        return "Guinea_Pig"
    if any(k in s for k in ["chinchilla", "龙猫"]):
        return "Chinchilla"
    if any(k in s for k in ["ferret", "雪貂"]):
        return "Ferret"
    if any(k in s for k in ["bird", "鸟", "鹦鹉"]):
        return "Bird"
    return "Dog"

def normalize_category(cat_str: str) -> str:
    """功效分类中英文双向归一化"""
    if not cat_str:
        return ""
    c = str(cat_str).lower().strip()
    mapping = {
        "joint": "Joint", "关节": "Joint", "软骨": "Joint",
        "skin": "Skin_Coat", "coat": "Skin_Coat", "皮毛": "Skin_Coat", "美毛": "Skin_Coat", "皮肤": "Skin_Coat",
        "gut": "Gut_Digestion", "digestion": "Gut_Digestion", "肠道": "Gut_Digestion", "消化": "Gut_Digestion", "益生菌": "Gut_Digestion",
        "kidney": "Kidney", "urinary": "Kidney", "肾": "Kidney", "肾脏": "Kidney", "泌尿": "Kidney", "结石": "Kidney",
        "immune": "Immune", "免疫": "Immune",
        "cardio": "Cardiopulmonary", "心": "Cardiopulmonary", "心脏": "Cardiopulmonary",
        "liver": "Liver", "肝": "Liver", "保肝": "Liver",
        "vitamin": "Vitamin", "维生素": "Vitamin"
    }
    for k, v in mapping.items():
        if k in c:
            return v
    return cat_str

DOSAGE_FORM_TEMPLATES = {
    "soft_chew": {
        "name": "冷挤压软咀嚼粒 (Soft Chew)",
        "unit_str": "粒",
        "default_weight_g": 3.0,
        "palatants": [
            {"name": "水解鸡肝粉 (强效诱食剂)", "pct": 12.0, "cost_kg": 65.0},
            {"name": "酿酒酵母提取物 (风味掩味剂)", "pct": 4.0, "cost_kg": 22.0}
        ],
        "excipients": [
            {"name": "植物甘油 99.5% (锁水防硬化)", "pct": 12.0, "cost_kg": 14.5},
            {"name": "预糊化木薯淀粉 (冷挤压塑形粘结)", "pct": 14.0, "cost_kg": 11.0},
            {"name": "大豆卵磷脂 (天然乳化防析出)", "pct": 4.0, "cost_kg": 28.0}
        ],
        "filler_name": "脱脂燕麦粉/豌豆纤维 (成型平衡基底)",
        "filler_cost_kg": 9.5
    },
    "chewable_tablet": {
        "name": "异形风味咀嚼片 (Chewable Tablet)",
        "unit_str": "片",
        "default_weight_g": 1.0,
        "palatants": [{"name": "喷雾干燥牛肉风味粉", "pct": 10.0, "cost_kg": 55.0}],
        "excipients": [
            {"name": "微晶纤维素 MCC PH102", "pct": 28.0, "cost_kg": 24.0},
            {"name": "硬脂酸镁 (脱模润滑剂)", "pct": 0.8, "cost_kg": 35.0},
            {"name": "气相二氧化硅 (抗结微粉)", "pct": 0.5, "cost_kg": 45.0}
        ],
        "filler_name": "药用麦芽糊精 (直接压片平衡填充剂)",
        "filler_cost_kg": 8.5
    },
    "powder_sachet": {
        "name": "独立防潮条包粉剂 (Powder Sachet)",
        "unit_str": "条",
        "default_weight_g": 2.0,
        "palatants": [{"name": "纯鸡肉冻干粉", "pct": 15.0, "cost_kg": 75.0}],
        "excipients": [{"name": "食品级二氧化硅", "pct": 1.0, "cost_kg": 45.0}],
        "filler_name": "低聚果糖菊粉/抗性糊精 (益生元载体补足至100%)",
        "filler_cost_kg": 20.0
    },
    "powder_tub": {
        "name": "大罐装散粉配量勺 (Scoop Powder)",
        "unit_str": "平勺",
        "default_weight_g": 1.0,
        "palatants": [{"name": "发酵乳酪风味粉", "pct": 10.0, "cost_kg": 50.0}],
        "excipients": [{"name": "食品级二氧化硅", "pct": 1.5, "cost_kg": 45.0}],
        "filler_name": "药用麦芽糊精 (流动载体补足至100%)",
        "filler_cost_kg": 8.5
    },
    "hard_capsule": {
        "name": "充填硬胶囊剂 (Hard Capsule)",
        "unit_str": "粒",
        "default_weight_g": 0.3,  # 默认采用适宜猫与小宠的 300mg (2#) 胶囊
        "palatants": [],           # 胶囊壳物理隔绝异味，不添加高磷肉粉
        "excipients": [
            {"name": "硬脂酸镁 (胶囊充填流动脱模剂)", "pct": 0.8, "cost_kg": 35.0},
            {"name": "气相二氧化硅 (防潮分散稳定剂)", "pct": 0.5, "cost_kg": 45.0}
        ],
        "filler_name": "微晶纤维素 MCC PH101 (低吸湿纯净填充剂)",
        "filler_cost_kg": 24.0
    },
    "liquid_drops": {
        "name": "高吸收滴管滴剂 (Liquid Drops)",
        "unit_str": "mL",
        "default_weight_g": 1.0,
        "palatants": [{"name": "精炼金枪鱼油", "pct": 20.0, "cost_kg": 120.0}],
        "excipients": [{"name": "天然维生素E (抗氧化)", "pct": 0.5, "cost_kg": 140.0}],
        "filler_name": "精炼中链甘油三酯 (MCT Oil 快速吸收油基底)",
        "filler_cost_kg": 45.0
    },
    "oral_suspension": {
        "name": "口服混悬乳液 (Oral Suspension)",
        "unit_str": "剂(5mL)",
        "default_weight_g": 5.0,
        "palatants": [{"name": "水解鱼蛋白浓缩液", "pct": 8.0, "cost_kg": 45.0}],
        "excipients": [
            {"name": "黄原胶 (增稠抗沉降)", "pct": 0.6, "cost_kg": 38.0},
            {"name": "羧甲基纤维素钠 CMC-Na", "pct": 0.8, "cost_kg": 26.0},
            {"name": "山梨酸钾 (抑菌保鲜)", "pct": 0.2, "cost_kg": 30.0}
        ],
        "filler_name": "去离子水 + 医用甘油体系",
        "filler_cost_kg": 4.5
    },
    "syringe_paste": {
        "name": "刻度推管软膏/营养膏 (Syringe Paste)",
        "unit_str": "刻度(3g)",
        "default_weight_g": 3.0,
        "palatants": [
            {"name": "精炼鲜鸡油", "pct": 15.0, "cost_kg": 35.0},
            {"name": "水解禽肝肉浆", "pct": 8.0, "cost_kg": 48.0}
        ],
        "excipients": [
            {"name": "大豆卵磷脂", "pct": 4.0, "cost_kg": 28.0},
            {"name": "黄原胶", "pct": 0.8, "cost_kg": 38.0},
            {"name": "天然迷迭香提取物", "pct": 0.2, "cost_kg": 160.0}
        ],
        "filler_name": "药用低DE值麦芽糖浆 (浓稠能量基质补足100%)",
        "filler_cost_kg": 7.5
    }
}

def query_ingredients_and_estimate_cost(species: str, target_category: str = "", ingredient_keyword: str = "") -> str:
    """查询公司内部原料主数据表"""
    if not os.path.exists(DB_PATH):
        return "原料数据库尚未初始化，请先执行导入脚本。"

    spec_clean = normalize_species(species)
    cat_clean = normalize_category(target_category)

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    sql = """
        SELECT c.Ingredient_ID, c.Ingredient_Name_CN, c.Ingredient_Name_EN,
               c.Category, c.Form, c.Purity_Percent, d.Species,
               d.Dose_Target, d.Dose_Unit, d.Evidence_Level, comm.Price_Per_KG_CNY,
               comm.Supplier_Name, s.Safety_Limit_BW, s.Banned_Species
        FROM ingredient_core c
        JOIN species_dose d ON c.Ingredient_ID = d.Ingredient_ID
        LEFT JOIN commercial comm ON c.Ingredient_ID = comm.Ingredient_ID
        LEFT JOIN safety_rules s ON c.Ingredient_ID = s.Ingredient_ID
        WHERE (LOWER(d.Species) = LOWER(?) OR d.Species = 'All')
    """
    params = [spec_clean]

    if cat_clean:
        sql += " AND (LOWER(c.Category) = LOWER(?) OR c.Ingredient_Name_CN LIKE ? OR c.Synonyms LIKE ?)"
        params.extend([cat_clean, f"%{cat_clean}%", f"%{cat_clean}%"])
    if ingredient_keyword:
        kw = ingredient_keyword.strip()
        sql += " AND (c.Ingredient_Name_CN LIKE ? OR c.Ingredient_Name_EN LIKE ? OR c.Synonyms LIKE ?)"
        params.extend([f"%{kw}%", f"%{kw}%", f"%{kw}%"])

    cursor.execute(sql, params)
    rows = cursor.fetchall()
    conn.close()

    if not rows:
        return f"在数据库中未找到适用于物种 [{spec_clean}] 且符合条件的候选原料。"

    output_lines = [f"【适用物种: {spec_clean} 的候选原料库匹配结果】:"]
    for r in rows:
        banned = r["Banned_Species"] if r["Banned_Species"] else "None"
        if spec_clean.lower() in str(banned).lower():
            continue

        price = f"{r['Price_Per_KG_CNY']} 元/kg" if r["Price_Per_KG_CNY"] else "暂无报价"
        output_lines.append(
            f"• 原料: {r['Ingredient_Name_CN']} ({r['Ingredient_Name_EN']}) [ID: {r['Ingredient_ID']}]\n"
            f"  品类: {r['Category']} | 形态: {r['Form']} | 纯度: {r['Purity_Percent']}%\n"
            f"  推荐剂量: {r['Dose_Target']} {r['Dose_Unit']} (循证等级: {r['Evidence_Level']})\n"
            f"  参考成本: {price} (供应商: {r['Supplier_Name']})\n"
            f"  安全耐受上限: {r['Safety_Limit_BW']} {r['Dose_Unit']}"
        )

    return "\n\n".join(output_lines)

def generate_complete_industrial_formula(
    species: str = "Cat",
    weight_kg: float = None,
    target_category: str = "",
    dosage_form: str = "hard_capsule",
    unit_weight_g: float = None,
    custom_active_ingredients: list = None,
    **kwargs
) -> str:
    """
    全剂型工业级宠物保健品配方质量配平与 BOM 成本自动核算引擎 (柔性配平，完全剔除固定死成分)
    """
    # 1. 核心修复：全面吸收物种别名并进行精准判定
    effective_species = species
    for s_alias in ["target_species", "spec", "animal", "pet_species"]:
        if s_alias in kwargs and kwargs[s_alias]:
            effective_species = kwargs[s_alias]
            break
    spec_clean = normalize_species(effective_species)

    # 2. 核心修复：全面吸收体重别名 (防止模型传 dose_kg, weight, kg 等)
    effective_weight = weight_kg
    if effective_weight is None:
        for w_alias in ["dose_kg", "weight", "w", "animal_weight", "kg", "pet_weight", "body_weight"]:
            if w_alias in kwargs and kwargs[w_alias] is not None:
                try:
                    effective_weight = float(kwargs[w_alias])
                    break
                except Exception:
                    pass

    if effective_weight is None or float(effective_weight) <= 0:
        effective_weight = DEFAULT_SPECIES_WEIGHTS.get(spec_clean, 4.0 if spec_clean == "Cat" else 10.0)
    else:
        effective_weight = float(effective_weight)

    # 3. 核心修复：全面吸收规格克重别名 (防止模型传 unit_weight, size_g 等)
    effective_unit_weight = unit_weight_g
    if effective_unit_weight is None:
        for u_alias in ["unit_weight", "size_g", "capsule_size", "single_weight", "weight_g", "unit_weight_mg", "size"]:
            if u_alias in kwargs and kwargs[u_alias] is not None:
                try:
                    val = float(kwargs[u_alias])
                    if val > 30.0:  # 传了毫克值自动折算为克
                        val = val / 1000.0
                    effective_unit_weight = val
                    break
                except Exception:
                    pass

    cat_clean = normalize_category(target_category)

    # 4. 剂型确定
    form_clean = "hard_capsule" if spec_clean == "Cat" and "kidney" in str(target_category).lower() else "soft_chew"
    if dosage_form:
        d_lower = str(dosage_form).lower().strip()
        for k in DOSAGE_FORM_TEMPLATES:
            if k in d_lower or d_lower in k:
                form_clean = k
                break

    tmpl = DOSAGE_FORM_TEMPLATES.get(form_clean, DOSAGE_FORM_TEMPLATES["hard_capsule"])

    if effective_unit_weight and float(effective_unit_weight) > 0:
        actual_unit_weight_g = float(effective_unit_weight)
    else:
        actual_unit_weight_g = tmpl["default_weight_g"]

    unit_weight_mg = actual_unit_weight_g * 1000.0

    # 5. 吸收 custom_active_ingredients 别名
    active_input = custom_active_ingredients
    if not active_input:
        for alias in ["active_ingredients", "ingredients", "custom_ingredients", "custom_active_ingredient"]:
            if alias in kwargs and isinstance(kwargs[alias], list):
                active_input = kwargs[alias]
                break

    # 6. 计算单日动物实际所需的所有活性成分总净重 (mg)
    daily_active_items = []
    total_daily_active_mg = 0.0

    # A. 从本地 SQLite 查
    if os.path.exists(DB_PATH) and cat_clean:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        sql = """
            SELECT c.Ingredient_ID, c.Ingredient_Name_CN, c.Ingredient_Name_EN, 
                   c.Purity_Percent, d.Dose_Target, comm.Price_Per_KG_CNY
            FROM ingredient_core c
            JOIN species_dose d ON c.Ingredient_ID = d.Ingredient_ID
            LEFT JOIN commercial comm ON c.Ingredient_ID = comm.Ingredient_ID
            WHERE (LOWER(d.Species) = LOWER(?) OR d.Species = 'All')
              AND (LOWER(c.Category) = LOWER(?) OR c.Ingredient_Name_CN LIKE ? OR c.Synonyms LIKE ?)
              AND c.Is_Active = 'TRUE'
        """
        cursor.execute(sql, (spec_clean, cat_clean, f"%{cat_clean}%", f"%{cat_clean}%"))
        for r in cursor.fetchall():
            purity = float(r["Purity_Percent"] or 100.0) / 100.0
            target_dose = float(r["Dose_Target"] or 0.0)
            needed_mg = target_dose * effective_weight
            actual_raw_mg = needed_mg / purity

            total_daily_active_mg += actual_raw_mg
            price_kg = float(r["Price_Per_KG_CNY"] or 80.0)

            daily_active_items.append({
                "name": f"{r['Ingredient_Name_CN']} ({r['Ingredient_Name_EN']})",
                "source": "【公司原料库已收录】",
                "daily_raw_mg": actual_raw_mg,
                "price_kg": price_kg
            })
        conn.close()

    # B. 从文献推导参数中提取
    if active_input:
        for cust in active_input:
            if not isinstance(cust, dict):
                continue
            c_name = cust.get("name", "创新活性原料")

            # 核心容错：兼容小模型传的各种剂量键
            c_dose = 0.0
            for d_alias in ["dose_mg_per_kg", "dose_per_kg", "dose", "mg_per_kg", "target_dose", "daily_dose"]:
                if d_alias in cust and cust[d_alias] is not None:
                    try:
                        c_dose = float(cust[d_alias])
                        break
                    except Exception:
                        pass

            # 若传的是单只总毫克数
            if c_dose <= 0:
                for t_alias in ["dose_per_unit", "total_mg", "dose_mg", "mg"]:
                    if t_alias in cust and cust[t_alias] is not None:
                        try:
                            c_dose = float(cust[t_alias]) / effective_weight
                            break
                        except Exception:
                            pass

            if c_dose <= 0:
                c_dose = 15.0  # 默认临床合理基准

            needed_mg = c_dose * effective_weight
            c_purity = float(cust.get("purity_percent", 95.0)) / 100.0
            c_price = float(cust.get("price_per_kg", 180.0))
            c_pmid = cust.get("pmid", "PubMed文献自研")

            actual_raw_mg = needed_mg / c_purity
            total_daily_active_mg += actual_raw_mg

            daily_active_items.append({
                "name": c_name,
                "source": f"【文献自研 PMID:{c_pmid}】",
                "daily_raw_mg": actual_raw_mg,
                "price_kg": c_price
            })

    # 【核心改动】：如果用户既没有在原料库匹配到成分，也没有传入 custom_active_ingredients，直接返回说明，绝不塞入死成分！
    if not daily_active_items:
        return f"未检测到适用于物种 [{spec_clean}] 的有效成分，请提供活性成分名称及文献剂量（mg/kg/天）以便进行质量平衡计算。"

    # 7. 智能分服与单体含量配比
    max_active_per_unit = unit_weight_mg * 0.70  # 单粒最多装 70% 活性物，留出辅料空间
    if total_daily_active_mg > max_active_per_unit:
        daily_units = math.ceil(total_daily_active_mg / max_active_per_unit)
    else:
        daily_units = 1

    # 单粒中各活性物的含量与成本
    active_bom = []
    unit_active_total_mg = 0.0

    for item in daily_active_items:
        unit_mg = item["daily_raw_mg"] / daily_units
        unit_active_total_mg += unit_mg
        pct = (unit_mg / unit_weight_mg) * 100.0
        cost = (unit_mg / 1_000_000.0) * item["price_kg"]

        active_bom.append({
            "name": item["name"],
            "source": item["source"],
            "mg": unit_mg,
            "pct": pct,
            "cost": cost
        })

    # 8. 组装适口性与辅料系统
    subtotal_pct = (unit_active_total_mg / unit_weight_mg) * 100.0
    palatant_bom = []
    excipient_bom = []

    for p in tmpl["palatants"]:
        pct = p["pct"]
        mg = unit_weight_mg * (pct / 100.0)
        cost = (mg / 1_000_000.0) * p["cost_kg"]
        subtotal_pct += pct
        palatant_bom.append({"name": p["name"], "mg": mg, "pct": pct, "cost": cost})

    for e in tmpl["excipients"]:
        pct = e["pct"]
        mg = unit_weight_mg * (pct / 100.0)
        cost = (mg / 1_000_000.0) * e["cost_kg"]
        subtotal_pct += pct
        excipient_bom.append({"name": e["name"], "mg": mg, "pct": pct, "cost": cost})

    # 9. 载体补足配平至 100.0% (Q.S. to 100%)
    filler_pct = max(0.0, 100.0 - subtotal_pct)
    filler_mg = unit_weight_mg * (filler_pct / 100.0)
    filler_cost = (filler_mg / 1_000_000.0) * tmpl["filler_cost_kg"]

    # 10. 批量与成本核算
    all_cost_per_unit = sum(x["cost"] for x in active_bom) + sum(x["cost"] for x in palatant_bom) + sum(x["cost"] for x in excipient_bom) + filler_cost
    batch_units = int(100_000.0 / actual_unit_weight_g)

    dosage_instruction = f"每日推荐: 每日 {daily_units} {tmpl['unit_str']}" if daily_units > 1 else f"每日推荐: 1 {tmpl['unit_str']}/天"

    lines = [
        f"📋 【{spec_clean}（体重设定: {effective_weight}kg）{cat_clean or '专属'}研发配方 - 工业级质量平衡 BOM 生产单】",
        f"• 选定剂型: {tmpl['name']} | 单粒规格: {actual_unit_weight_g}g/{tmpl['unit_str']} ({actual_unit_weight_g*1000:.0f}mg) | {dosage_instruction}",
        f"• 工业批次: 100kg 生产规模理论可产出 {batch_units:,} {tmpl['unit_str']} (按60{tmpl['unit_str']}/瓶包装折合约 {batch_units//60:,} 瓶)\n",
        "---------------------------------------------------------------------------------------------------------------------",
        f"{'原料角色 / 工业名称':<40} | {'数据溯源':<24} | {'单份投料(mg)':<12} | {'占比(%)':<8} | {'100kg投料量(kg)':<14} | {'单份成本'}",
        "---------------------------------------------------------------------------------------------------------------------",
        "【一、功效活性组分 (Active APIs)】"
    ]

    for a in active_bom:
        batch_kg = (a["pct"] / 100.0) * 100.0
        lines.append(f"  • {a['name']:<38} | {a['source']:<20} | {a['mg']:<14.1f} | {a['pct']:<8.2f}% | {batch_kg:<16.2f} | ￥{a['cost']:.4f}")

    if palatant_bom:
        lines.append("【二、宠物风味适口性系统 (Palatants)】")
        for p in palatant_bom:
            batch_kg = (p["pct"] / 100.0) * 100.0
            lines.append(f"  • {p['name']:<38} | {'【经典适口性工艺】':<20} | {p['mg']:<14.1f} | {p['pct']:<8.2f}% | {batch_kg:<16.2f} | ￥{p['cost']:.4f}")

    if excipient_bom:
        lines.append("【三、剂型成型与工艺辅料 (Excipients & Binders)】")
        for e in excipient_bom:
            batch_kg = (e["pct"] / 100.0) * 100.0
            lines.append(f"  • {e['name']:<38} | {'【剂型成型骨架】':<20} | {e['mg']:<14.1f} | {e['pct']:<8.2f}% | {batch_kg:<16.2f} | ￥{e['cost']:.4f}")

    lines.append("【四、赋形载体平衡组分 (Q.S. Filler)】")
    lines.append(f"  • {tmpl['filler_name']:<38} | {'【自动配平至100%】':<20} | {filler_mg:<14.1f} | {filler_pct:<8.2f}% | {(filler_pct/100.0)*100.0:<16.2f} | ￥{filler_cost:.4f}")

    lines.append("---------------------------------------------------------------------------------------------------------------------")
    lines.append(f"【合计】 工业质量总配平: 100.00% ({actual_unit_weight_g*1000:.0f}mg/{tmpl['unit_str']}) | 单份净原料成本: ￥{all_cost_per_unit:.3f} 元/{tmpl['unit_str']} (约合每大单位 ￥{all_cost_per_unit*60:.2f} 元/60{tmpl['unit_str']})")
    lines.append("---------------------------------------------------------------------------------------------------------------------")

    return "\n".join(lines)

