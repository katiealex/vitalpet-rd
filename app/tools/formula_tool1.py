# app/tools/formula_tool.py
import sqlite3
import os

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
    """智能清洗物种输入，兼容 'dog cat', '犬猫', '猫咪' 等"""
    if not species_str:
        return "Dog"
    s = species_str.lower().strip()
    if any(k in s for k in ["cat", "猫", "feline"]):
        if any(k in s for k in ["dog", "犬", "狗", "canine"]):
            return "Dog" # 组合物种默认以犬规格做基准，标明犬猫通用
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
    c = cat_str.lower().strip()
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
        "active_max_pct": 45.0,
        "active_min_pct": 3.0,
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
        "active_max_pct": 50.0,
        "active_min_pct": 3.0,
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
        "active_max_pct": 60.0,
        "active_min_pct": 2.0,
        "palatants": [{"name": "纯鸡肉冻干粉", "pct": 15.0, "cost_kg": 75.0}],
        "excipients": [{"name": "食品级二氧化硅", "pct": 1.0, "cost_kg": 45.0}],
        "filler_name": "低聚果糖菊粉/抗性糊精 (益生元载体补足至100%)",
        "filler_cost_kg": 20.0
    },
    "powder_tub": {
        "name": "大罐装散粉配量勺 (Scoop Powder)",
        "unit_str": "平勺",
        "default_weight_g": 1.0,
        "active_max_pct": 60.0,
        "active_min_pct": 2.0,
        "palatants": [{"name": "发酵乳酪风味粉", "pct": 10.0, "cost_kg": 50.0}],
        "excipients": [{"name": "食品级二氧化硅", "pct": 1.5, "cost_kg": 45.0}],
        "filler_name": "药用麦芽糊精 (流动载体补足至100%)",
        "filler_cost_kg": 8.5
    },
    "hard_capsule": {
        "name": "充填硬胶囊剂 (Hard Capsule)",
        "unit_str": "粒",
        "default_weight_g": 0.5,  # 默认0号胶囊 500mg
        "active_max_pct": 80.0,
        "active_min_pct": 20.0,   # 【核心防线】胶囊中活性物载药量不得低于20%，杜绝纯灌辅料的无效胶囊
        "palatants": [],           # 胶囊壳物理隔绝异味，严禁加高磷肉粉
        "excipients": [
            {"name": "硬脂酸镁 (胶囊充填流动脱模剂)", "pct": 0.6, "cost_kg": 35.0},
            {"name": "气相二氧化硅 (防潮分散稳定剂)", "pct": 0.5, "cost_kg": 45.0}
        ],
        "filler_name": "微晶纤维素 MCC PH101 (低吸湿纯净填充剂)",
        "filler_cost_kg": 24.0
    },
    "liquid_drops": {
        "name": "高吸收滴管滴剂 (Liquid Drops)",
        "unit_str": "mL",
        "default_weight_g": 1.0,
        "active_max_pct": 40.0,
        "active_min_pct": 2.0,
        "palatants": [{"name": "精炼金枪鱼油", "pct": 20.0, "cost_kg": 120.0}],
        "excipients": [{"name": "天然维生素E (抗氧化)", "pct": 0.5, "cost_kg": 140.0}],
        "filler_name": "精炼中链甘油三酯 (MCT Oil 快速吸收油基底)",
        "filler_cost_kg": 45.0
    },
    "oral_suspension": {
        "name": "口服混悬乳液 (Oral Suspension)",
        "unit_str": "剂(5mL)",
        "default_weight_g": 5.0,
        "active_max_pct": 30.0,
        "active_min_pct": 1.0,
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
        "active_max_pct": 35.0,
        "active_min_pct": 2.0,
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
    species: str = "Dog", 
    weight_kg: float = None, 
    target_category: str = "", 
    dosage_form: str = "soft_chew",
    unit_weight_g: float = None,
    custom_active_ingredients: list = None,
    **kwargs
) -> str:
    """
    全剂型工业级宠物保健品配方质量配平与 BOM 成本自动核算引擎 (内置防幻觉载药量监控与合理性拦截)
    """
    # 1. 容错提取 custom_active_ingredients 别名
    if not custom_active_ingredients:
        for alias in ["active_ingredients", "ingredients", "custom_ingredients"]:
            if alias in kwargs and isinstance(kwargs[alias], list):
                custom_active_ingredients = kwargs[alias]
                break

    # 2. 物种与体重容错兜底
    spec_clean = normalize_species(species)
    cat_clean = normalize_category(target_category)
    
    if weight_kg is None or float(weight_kg) <= 0:
        weight_kg = DEFAULT_SPECIES_WEIGHTS.get(spec_clean, 10.0)
    else:
        weight_kg = float(weight_kg)

    # 3. 剂型与规格处理
    form_clean = "soft_chew"
    if dosage_form:
        d_lower = dosage_form.lower().strip()
        for k in DOSAGE_FORM_TEMPLATES:
            if k in d_lower or d_lower in k:
                form_clean = k
                break

    tmpl = DOSAGE_FORM_TEMPLATES.get(form_clean, DOSAGE_FORM_TEMPLATES["soft_chew"])

    if unit_weight_g and float(unit_weight_g) > 0:
        actual_unit_weight_g = float(unit_weight_g)
    else:
        actual_unit_weight_g = tmpl["default_weight_g"]

    unit_weight_mg = actual_unit_weight_g * 1000.0

    active_bom = []
    total_active_mg = 0.0

    # 4. 从本地库查原料
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
            needed_mg = target_dose * weight_kg
            actual_mg = needed_mg / purity

            total_active_mg += actual_mg
            price_kg = float(r["Price_Per_KG_CNY"] or 80.0)
            cost_unit = (actual_mg / 1_000_000.0) * price_kg

            active_bom.append({
                "name": f"{r['Ingredient_Name_CN']} ({r['Ingredient_Name_EN']})",
                "source": "【公司原料库已收录】",
                "mg": actual_mg,
                "pct": (actual_mg / unit_weight_mg) * 100.0,
                "cost": cost_unit
            })
        conn.close()

    # 5. 处理文献推导原料 (【抗幻觉核心】：严格强制使用绝对质量 mg/kg，废除百分比)
    if custom_active_ingredients:
        for cust in custom_active_ingredients:
            if not isinstance(cust, dict):
                continue
            c_name = cust.get("name", "创新活性原料")
            
            # 严格以文献真实的每公斤体重绝对剂量为计算源泉
            c_dose = float(cust.get("dose_mg_per_kg") or 0.0)
            
            # 若模型传了非法负值或未填，给予合理的兽医临床基础起效量兜底（10~20 mg/kg）
            if c_dose <= 0:
                c_dose = 20.0

            needed_mg = c_dose * weight_kg
            c_purity = float(cust.get("purity_percent", 90.0)) / 100.0
            c_price = float(cust.get("price_per_kg", 180.0))
            c_pmid = cust.get("pmid", "PubMed文献自研")

            actual_mg = needed_mg / c_purity
            total_active_mg += actual_mg
            cost_unit = (actual_mg / 1_000_000.0) * c_price

            active_bom.append({
                "name": c_name,
                "source": f"【文献自研 PMID:{c_pmid}】",
                "mg": actual_mg,
                "pct": (actual_mg / unit_weight_mg) * 100.0,
                "cost": cost_unit
            })

    if not active_bom:
        # 若仍无，给予默认机体支持活性物
        default_mg = 120.0
        total_active_mg = default_mg
        active_bom.append({
            "name": "柠檬酸钾 (Potassium Citrate 碱化抗草酸钙结石)",
            "source": "【兽医临床推荐 OFL 配方】",
            "mg": default_mg,
            "pct": (default_mg / unit_weight_mg) * 100.0,
            "cost": 0.008
        })

    # 6. 【核心工业质量监控】：校验载药量是否过高或过低
    total_active_pct = (total_active_mg / unit_weight_mg) * 100.0
    active_limit = tmpl["active_max_pct"]
    active_floor = tmpl.get("active_min_pct", 2.0)

    # 拦截 A: 载药量超过物理成型极限 (无法结块或开裂)
    if total_active_pct > active_limit:
        return (
            f"⚠️ 配方工艺超限警告：当前活性组分总重达 {total_active_mg:.1f}mg ({total_active_pct:.1f}%)，"
            f"超过 [{tmpl['name']}] 工艺极限 ({active_limit}%)！\n"
            f"建议：① 调大单体规格参数 unit_weight_g；② 或将每日推荐量调整为 2{tmpl['unit_str']} 分次喂食。"
        )

    # 拦截 B: 载药量过低 (防止全是辅料的荒谬空心胶囊/药丸)
    if form_clean == "hard_capsule" and total_active_pct < active_floor:
        # 自动计算出更适合的微型胶囊规格（通常推荐活性物占 60%~75%）
        recommended_weight_mg = int(total_active_mg / 0.65)
        return (
            f"❌ 工业合理性拦截报警：当前有效成分在胶囊中占比仅为 {total_active_pct:.2f}%，填充辅料高达 {100-total_active_pct:.2f}%！\n"
            f"这违反了制剂学常识（胶囊成了纯吃微晶纤维素）。\n"
            f"• 当前 5kg 动物所需单日活性物实际仅为: {total_active_mg:.1f} mg\n"
            f"• 工业改进决策：请勿使用 500mg (0号) 大胶囊！建议将单体规格参数 unit_weight_g 改为 {recommended_weight_mg/1000.0:.2f}g（约 {recommended_weight_mg}mg 微型胶囊），或将辅料占比降至 30% 以内！"
        )

    # 7. 组装适口性与辅料系统
    subtotal_pct = total_active_pct
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

    # 8. 载体配平至 100.0% (Q.S. to 100%)
    filler_pct = max(0.0, 100.0 - subtotal_pct)
    filler_mg = unit_weight_mg * (filler_pct / 100.0)
    filler_cost = (filler_mg / 1_000_000.0) * tmpl["filler_cost_kg"]

    # 9. 批量生产投料核算
    all_cost_per_unit = sum(x["cost"] for x in active_bom) + sum(x["cost"] for x in palatant_bom) + sum(x["cost"] for x in excipient_bom) + filler_cost
    batch_units = int(100_000.0 / actual_unit_weight_g)

    lines = [
        f"📋 【{spec_clean}（体重设定: {weight_kg}kg）{cat_clean or '专属'}研发配方 - 工业级质量平衡 BOM 生产单】",
        f"• 选定剂型: {tmpl['name']} | 单只每日推荐: 1{tmpl['unit_str']}/天 (定制规格: {actual_unit_weight_g}g/{tmpl['unit_str']})",
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
    lines.append(f"【合计】 工业质量配平: 100.00% ({actual_unit_weight_g}g/{tmpl['unit_str']}) | 单份净原料成本: ￥{all_cost_per_unit:.3f} 元/{tmpl['unit_str']} (约合每大单位 ￥{all_cost_per_unit*60:.2f} 元/60{tmpl['unit_str']})")
    lines.append("---------------------------------------------------------------------------------------------------------------------")

    return "\n".join(lines)

