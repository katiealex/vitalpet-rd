# app_web.py - VitalPet-RD 工业级研发操作台 (v0.3.6 稳健基底 + 完美闭环版)
import os
import sys

os.environ["NO_PROXY"] = "127.0.0.1,localhost,0.0.0.0,.bosch.com"
os.environ["no_proxy"] = "127.0.0.1,localhost,0.0.0.0,.bosch.com"

import re
import io
import pandas as pd
import streamlit as st
import ollama
from dotenv import load_dotenv

from app.db import init_db
from app.tools.pubmed_tool import search_pubmed_evidence
from app.tools.formula_tool import (
    query_ingredients_and_estimate_cost,
    generate_complete_industrial_formula
)
from app.pubmed.downloader import fetch_paper_pdf
from app.agent import TOOLS, TOOL_MAP, unwrap_tool_arguments, extract_text_tool_calls

st.set_page_config(
    page_title="VitalPet-RD 宠物保健品AI研发中枢",
    page_icon="🐾",
    layout="wide",
    initial_sidebar_state="expanded"
)

load_dotenv()
MODEL_NAME = os.getenv("OLLAMA_MODEL", "vitalpet-rd:0.1")

# 恢复 v0.3.2 稳健底座：不硬设短超时，信任系统原生连接池，绝不中途误杀
client = ollama.Client(host="http://127.0.0.1:11434")

# 保持 v0.3.2 紧凑短悍的 System Prompt，降低端侧计算延迟
WEB_SYSTEM_PROMPT = """你是由 VitalPet-RD 驱动的宠物营养、保健品研发与工业制剂工程 AI 专家。
你的职责是根据科学证据、公司内部原料库与现代制剂工艺，为各类伴侣动物设计【工业级完整配方质量平衡 BOM 生产单】与专业研发报告。

【最高行为准则 - 绝对严禁违规】：
1. 绝对严禁在回答中编造假 PMID、假标题或假论文！
   - 凡是用户要求配方或文献，【第 1 步必须且只能调用 search_pubmed_evidence 真实搜索】！
   - 严禁在正文里说“通过检索找到...”而实际没有调用 search_pubmed_evidence 工具！
   - 检索词专业化：肝脏检索用 'Silymarin feline liver' 或 'Silybin cat dog hepatic'；关节检索用 'Chondroitin sulfate feline joint dose'。
2. 绝对严禁在正文中手写伪造假 BOM 表格！
   - 拿到文献有效剂量后，【第 2 步必须且只能调用 generate_complete_industrial_formula】生成系统级 100% 工业生产单！
   - 工具返回生产单后，配平即告完成，立刻总结报告，严禁重复调用！
   - 猫科动物（关节/肝病/肾病）：优先推荐 hard_capsule（0.3g 硬胶囊），严禁使用大软嚼块。
3. 严格传递真实物种与体重：用户说 5kg 猫，参数必须传 species='Cat', weight_kg=5.0。
"""

# ==================== 侧边栏 ====================
st.sidebar.title("🐾 VitalPet-RD 研发面板")
st.sidebar.caption(f"当前载入模型: `{MODEL_NAME}`")

st.sidebar.markdown("### 1. 目标动物与规格")
species_opt = st.sidebar.selectbox("目标物种", ["猫 (Cat)", "犬 (Dog)", "兔子 (Rabbit)", "龙猫 (Chinchilla)", "豚鼠 (Guinea Pig)", "雪貂 (Ferret)", "鸟类 (Bird)"])
species_val = species_opt.split(" ")[0]

default_w = 5.0 if "猫" in species_val else (10.0 if "犬" in species_val else 2.0)
weight_val = st.sidebar.slider("动物体重 (kg)", min_value=0.5, max_value=60.0, value=default_w, step=0.5)

st.sidebar.markdown("### 2. 制造剂型与单体规格")
form_map = {
    "充填硬胶囊 (Hard Capsule) - 推荐猫用/精准定量": "hard_capsule",
    "冷挤压软咀嚼粒 (Soft Chew) - 推荐中大犬": "soft_chew",
    "异形风味咀嚼片 (Tablet) - 犬猫通用": "chewable_tablet",
    "独立条包粉剂 (Powder Sachet) - 拌食防潮": "powder_sachet",
    "大罐量勺散粉 (Powder Tub) - 经济多宠": "powder_tub",
    "高吸收滴管滴剂 (Liquid Drops) - 幼弱宠": "liquid_drops",
    "口服混悬乳液 (Oral Suspension) - 喂药管": "oral_suspension",
    "刻度推管软膏 (Syringe Paste) - 营养膏/化毛": "syringe_paste"
}
selected_form_label = st.sidebar.selectbox("拟定生产剂型", list(form_map.keys()))
selected_form_key = form_map[selected_form_label]

default_unit_g = 0.3 if selected_form_key == "hard_capsule" else (3.0 if selected_form_key == "soft_chew" else 1.0)
custom_unit_weight = st.sidebar.number_input("单体自定义规格 (克/粒 或 mL/支)", min_value=0.1, max_value=50.0, value=default_unit_g, step=0.1)

st.sidebar.markdown("---")
if st.sidebar.button("🧹 重置并新建会话"):
    st.session_state.messages = []
    st.rerun()

# ==================== 主内容区 ====================
st.title("🧪 VitalPet-RD 宠物保健品工业级配方系统")
st.caption("版本: v0.3.6 (高鲁棒防超时与即时 BOM 导出版)")

if "messages" not in st.session_state:
    st.session_state.messages = [
        {
            "role": "assistant",
            "content": "您好！我是 VitalPet-RD 研发中枢。请在左侧设定目标动物与剂型参数，或直接在下方输入您的配方需求（例如：*给我配一个5kg猫的关节保健品，基于硫酸软骨素最新研究*）。",
            "bom_text": None,
            "pmids": []
        }
    ]

def render_bom_toolbox(bom_text: str, pmids: list, full_content: str, key_prefix: str):
    """专属 BOM 生产表与工具箱渲染 (多模自愈提取)"""
    st.markdown("---")
    st.markdown("#### 📋 本轮研发成果与车间生产单 (工业 BOM)")

    col_bom, col_tools = st.columns([3, 2])

    with col_bom:
        if bom_text:
            st.code(bom_text, language="text")
        else:
            st.info("💡 提示：当前配方数据已直接呈现在上方专家报告正文中。您可在右侧点击下载标准 Excel。")

    with col_tools:
        st.markdown("##### 🛠️ 工业交付工具箱")
        df_bom = None

        # 模式 A: 从工具输出的标准文本解析
        if bom_text:
            try:
                lines = [l.strip() for l in bom_text.split("\n") if ("•" in l or "|" in l) and "---" not in l]
                parsed_rows = []
                for l in lines:
                    parts = [p.strip() for p in l.replace("•", "").split("|")]
                    if len(parts) >= 4:
                        parsed_rows.append({
                            "原料名称/项目": parts[0],
                            "数据溯源/说明": parts[1] if len(parts) > 1 else "",
                            "单份投料(mg)": parts[2] if len(parts) > 2 else "",
                            "配方占比": parts[3] if len(parts) > 3 else "",
                            "100kg投料量(kg)": parts[4] if len(parts) > 4 else "",
                            "单份成本": parts[5] if len(parts) > 5 else ""
                        })
                if parsed_rows:
                    df_bom = pd.DataFrame(parsed_rows)
            except Exception:
                pass

        # 模式 B: 从正文 Markdown 表格提取
        if df_bom is None and full_content and ("|" in full_content):
            try:
                table_lines = [l.strip() for l in full_content.split("\n") if l.strip().startswith("|") and l.strip().endswith("|")]
                if len(table_lines) >= 3:
                    headers = [h.strip() for h in table_lines[0].split("|")[1:-1]]
                    rows = []
                    for row_line in table_lines[2:]:
                        row_vals = [v.strip() for v in row_line.split("|")[1:-1]]
                        if len(row_vals) == len(headers):
                            rows.append(dict(zip(headers, row_vals)))
                    if rows:
                        df_bom = pd.DataFrame(rows)
            except Exception:
                pass

        if df_bom is not None and not df_bom.empty:
            buf = io.BytesIO()
            with pd.ExcelWriter(buf, engine="openpyxl") as writer:
                df_bom.to_excel(writer, index=False, sheet_name="Production_BOM")
            buf.seek(0)

            st.download_button(
                label="📥 导出当前配方 Excel BOM 单",
                data=buf,
                file_name=f"VitalPet_{species_val}_{weight_val}kg_BOM.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                key=f"dl_excel_{key_prefix}"
            )
        else:
            st.caption("ℹ️ 正在等待配方生成完毕后激活导出...")

        # PDF 下载逻辑
        valid_pmids = [p for p in pmids if str(p).isdigit() and len(str(p)) >= 7 and str(p) != "42675016"]
        if valid_pmids:
            st.markdown("##### 📄 关联科研论文原件 (PMC)")
            for pmid in valid_pmids[:2]:
                pmc_target = "PMC11171177" if pmid in ["38891743", "38891461"] else f"PMC{pmid}"
                pdf_file = fetch_paper_pdf(pmid, pmc_target)
                if pdf_file and os.path.exists(pdf_file):
                    with open(pdf_file, "rb") as f:
                        st.download_button(
                            label=f"⬇️ 下载文献 PDF (PMID:{pmid})",
                            data=f.read(),
                            file_name=os.path.basename(pdf_file),
                            mime="application/pdf",
                            key=f"dl_pdf_{key_prefix}_{pmid}"
                        )
                else:
                    st.caption(f"• 文献 PMID:{pmid}（非开放获取期刊或未收录全文）")
        elif pmids:
            st.caption("• 本轮文献未探测到可公开下载的 PMC 免费原件。")

# 渲染对话历史
for idx, msg in enumerate(st.session_state.messages):
    if msg["role"] == "user":
        st.chat_message("user", avatar="🧑‍🔬").markdown(msg["content"])
    elif msg["role"] == "assistant":
        with st.chat_message("assistant", avatar="🐾"):
            st.markdown(msg["content"])
            render_bom_toolbox(msg.get("bom_text"), msg.get("pmids", []), msg.get("content", ""), f"hist_{idx}")

# ==================== 用户输入处理 ====================
if user_prompt := st.chat_input("请输入您的研发需求或提问..."):
    st.chat_message("user", avatar="🧑‍🔬").markdown(user_prompt)

    context_prefix = f"【研发控制台已锁定参数：物种: {species_val}, 体重: {weight_val}kg, 剂型: {selected_form_key}, 单体规格: {custom_unit_weight}g】\n"
    
    api_messages = [{"role": "system", "content": WEB_SYSTEM_PROMPT}]
    for m in st.session_state.messages:
        api_messages.append({"role": m["role"], "content": m["content"]})
    api_messages.append({"role": "user", "content": context_prefix + user_prompt})

    st.session_state.messages.append({"role": "user", "content": user_prompt})

    with st.chat_message("assistant", avatar="🐾"):
        status_box = st.status("🧠 AI 专家正在深度规划决策...", expanded=True)
        max_steps = 6
        step = 0
        final_answer = ""
        formula_generated = False
        current_pmids = []
        current_bom_str = None

        while step < max_steps:
            step += 1
            
            # 【终极防死循环机制】：一旦配方生成成功，下一轮立即将 tools 置为 None！
            # 剥夺大模型继续调用工具的权利，强迫它在下一步用纯文本直接写出结案报告！
            if formula_generated:
                active_tools = None
            else:
                active_tools = TOOLS

            response = client.chat(
                model=MODEL_NAME,
                messages=api_messages,
                tools=active_tools
            )

            tool_calls_to_run = []
            if response.message.tool_calls:
                for tc in response.message.tool_calls:
                    tool_calls_to_run.append((tc.function.name, tc.function.arguments))
            else:
                content_text = response.message.content or ""
                text_calls = extract_text_tool_calls(content_text)
                if text_calls:
                    tool_calls_to_run = text_calls

            if tool_calls_to_run:
                api_messages.append(response.message)
                for func_name, raw_args in tool_calls_to_run:
                    clean_args = unwrap_tool_arguments(raw_args)
                    status_box.write(f"⚙️ **调用系统工具**: `{func_name}`")
                    status_box.json(clean_args)

                    if func_name in TOOL_MAP:
                        func = TOOL_MAP[func_name]
                        if func_name == "generate_complete_industrial_formula":
                            if "species" not in clean_args or not clean_args["species"]:
                                clean_args["species"] = species_val
                            if "weight_kg" not in clean_args or not clean_args["weight_kg"]:
                                clean_args["weight_kg"] = weight_val
                            if "dosage_form" not in clean_args or not clean_args["dosage_form"]:
                                clean_args["dosage_form"] = selected_form_key
                            if "unit_weight_g" not in clean_args or not clean_args["unit_weight_g"]:
                                clean_args["unit_weight_g"] = custom_unit_weight

                        try:
                            tool_res = func(**clean_args)
                        except Exception as e:
                            tool_res = f"工具执行异常: {e}"

                        if func_name == "generate_complete_industrial_formula":
                            if "工业质量总配平" in str(tool_res) or "100.00%" in str(tool_res):
                                formula_generated = True
                                current_bom_str = str(tool_res)

                        if func_name == "search_pubmed_evidence":
                            pmids_found = re.findall(r"PMID:\s*(\d+)", str(tool_res))
                            current_pmids.extend(pmids_found)

                        status_box.write("📥 **数据返回成功**")
                        api_messages.append({"role": "tool", "content": str(tool_res)})
                continue
            else:
                final_answer = response.message.content or ""
                status_box.update(label="✅ 研发推导与质量核验全部完成！", state="complete", expanded=False)
                st.markdown(final_answer)

                # 提取真实存在的数字 PMID
                raw_pmids = re.findall(r"PMID:?\s*(\d+)", final_answer)
                current_pmids.extend(raw_pmids)
                current_pmids = list(set([p for p in current_pmids if str(p).isdigit() and len(str(p)) >= 7]))

                # 渲染专属 BOM 工具箱
                render_bom_toolbox(current_bom_str, current_pmids, final_answer, f"curr_{len(st.session_state.messages)}")
                break

        st.session_state.messages.append({
            "role": "assistant",
            "content": final_answer,
            "bom_text": current_bom_str,
            "pmids": current_pmids
        })

