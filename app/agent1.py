# app/agent.py
import os
import sys
import re

os.environ["NO_PROXY"] = "127.0.0.1,localhost,0.0.0.0,.bosch.com"
os.environ["no_proxy"] = "127.0.0.1,localhost,0.0.0.0,.bosch.com"

import json
import ollama
from dotenv import load_dotenv

from app.db import init_db
from app.tools.pubmed_tool import search_pubmed_evidence
from app.tools.formula_tool import (
    query_ingredients_and_estimate_cost,
    generate_complete_industrial_formula
)

load_dotenv()
MODEL_NAME = os.getenv("OLLAMA_MODEL", "vitalpet-rd:0.1")
client = ollama.Client(host="http://127.0.0.1:11434")

SYSTEM_PROMPT = """你是由 VitalPet-RD 驱动的宠物营养、保健品研发与工业制剂工程 AI 专家。
你的职责是根据科学证据、公司内部原料库与现代制剂工艺，为各类宠物（犬猫、兔子、龙猫、豚鼠、雪貂、鸟类等）设计可直接下车间生产试制（Pilot Production）的【工业级完整配方质量平衡 BOM 生产单】与研发评估报告。

【核心调用规则与决策铁律 - 必须严格执行】：
1. 真实系统调用：严禁在回答正文中手写伪造模拟的 JSON 或模拟结果！所有配方设计与文献必须通过系统级工具调用产生。

2. 严格尊重用户指定的物种与体重：
   - 用户指定的是猫（如 5kg 猫），调用 `generate_complete_industrial_formula` 时参数必须明确传递 `species='Cat', weight_kg=5.0`！
   - 即使引用的文献是在犬身上完成的（如针对犬肾病的临床试验），也绝不能把调用工具的物种私自改为 Dog！应在结案报告中说明该文献是犬类研究成果并推导至猫。

3. 复合方案与文献检索：
   - 遇到多成分联合方案（如 OFL 方案：Oligo-fucoidan + Fucoxanthin + L-carnitine），必须将组合词与病症作为整体检索（如 'Oligo-fucoidan Fucoxanthin L-carnitine CKD'），目标物种填 'veterinary'。

4. 工业配平单生成即结案（单次原则）：
   - 检索完文献拿到有效剂量后，调用一次 `generate_complete_industrial_formula` 即可获得完整的 BOM 表。
   - 工具返回 BOM 表后，配平计算已经完成，【严禁再次重复调用该工具】，应立刻输出最终研发评估报告！

5. 剂型与包装：
   - 猫科动物（尤其是肾病/挑食病宠）：优先采用 hard_capsule（硬胶囊，规格 unit_weight_g=0.3 即 300mg，无高磷肉粉）。
"""

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "generate_complete_industrial_formula",
            "description": "生成工业级完整的宠物保健品生产配方 BOM 表（包含功效活性组分、适口性风味剂、成型辅料并自动配平至100%）。输出 100kg 生产投料单与单体成本。",
            "parameters": {
                "type": "object",
                "properties": {
                    "species": {
                        "type": "string",
                        "description": "目标宠物物种（必须严格与用户需求一致，如 'Cat' 或 'Dog'）"
                    },
                    "weight_kg": {
                        "type": "number",
                        "description": "动物体重公斤数，例如 5.0 表示 5kg"
                    },
                    "target_category": {
                        "type": "string",
                        "description": "功效大类（如 'Joint', 'Skin_Coat', 'Kidney', 'Gut_Digestion'）"
                    },
                    "dosage_form": {
                        "type": "string",
                        "enum": [
                            "soft_chew", "chewable_tablet", "powder_sachet", 
                            "powder_tub", "hard_capsule", "liquid_drops", 
                            "oral_suspension", "syringe_paste"
                        ],
                        "description": "目标生产剂型：猫肾病优先 hard_capsule(胶囊)，默认 soft_chew"
                    },
                    "unit_weight_g": {
                        "type": "number",
                        "description": "单粒/单片/单袋规格（克）。猫用胶囊通常为 0.3g (300mg)。"
                    },
                    "custom_active_ingredients": {
                        "type": "array",
                        "description": "文献推导原料列表",
                        "items": {
                            "type": "object",
                            "properties": {
                                "name": {"type": "string", "description": "原料名称，如 'Oligo-fucoidan'"},
                                "dose_mg_per_kg": {"type": "number", "description": "文献临床推荐日有效量 (mg/kg 体重/天)"},
                                "purity_percent": {"type": "number", "description": "纯度百分比，默认 95.0"},
                                "price_per_kg": {"type": "number", "description": "参考采购价 (元/kg)"},
                                "pmid": {"type": "string", "description": "支持该剂量的 PubMed PMID"}
                            },
                            "required": ["name", "dose_mg_per_kg"]
                        }
                    }
                },
                "required": ["species", "weight_kg"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "query_ingredients_and_estimate_cost",
            "description": "从公司内部原料主数据表中，查询指定物种适用的原料配比、推荐有效剂量与成本估算。",
            "parameters": {
                "type": "object",
                "properties": {
                    "species": {"type": "string", "description": "目标宠物物种"},
                    "target_category": {"type": "string", "description": "可选功效分类"},
                    "ingredient_keyword": {"type": "string", "description": "可选原料名称"}
                },
                "required": ["species"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_pubmed_evidence",
            "description": "从 PubMed 搜索关于各类宠物营养素功效、安全性、复方组合研究的最新科研文献。",
            "parameters": {
                "type": "object",
                "properties": {
                    "ingredient_or_topic": {"type": "string", "description": "原料英文名、复合配方名（例如 'Oligo-fucoidan Fucoxanthin L-carnitine CKD'）或论文标题。"},
                    "target_species": {"type": "string", "description": "目标物种。复合方案请填 'veterinary'。"}
                },
                "required": ["ingredient_or_topic"]
            }
        }
    }
]

TOOL_MAP = {
    "generate_complete_industrial_formula": generate_complete_industrial_formula,
    "query_ingredients_and_estimate_cost": query_ingredients_and_estimate_cost,
    "search_pubmed_evidence": search_pubmed_evidence
}

def unwrap_tool_arguments(args):
    if not isinstance(args, dict):
        return {}
    cleaned = dict(args)
    while any(k in cleaned for k in ["arguments", "params", "parameters"]):
        for k in ["arguments", "params", "parameters"]:
            if k in cleaned:
                sub = cleaned.pop(k)
                if isinstance(sub, dict):
                    cleaned.update(sub)
                elif isinstance(sub, str):
                    try:
                        parsed = json.loads(sub)
                        if isinstance(parsed, dict):
                            cleaned.update(parsed)
                    except Exception:
                        pass
                break
    cleaned.pop("function", None)
    cleaned.pop("name", None)
    safe_args = {}
    for k, v in cleaned.items():
        if isinstance(v, dict):
            safe_args[k] = str(list(v.values())[0]) if v else ""
        else:
            safe_args[k] = v
    return safe_args

def extract_text_tool_calls(text: str):
    detected_calls = []
    tool_blocks = re.findall(r"<tool_call>(.*?)</tool_call>", text, re.DOTALL)
    for b in tool_blocks:
        try:
            d = json.loads(b.strip())
            if "name" in d:
                detected_calls.append((d["name"], d.get("arguments", {})))
        except Exception:
            pass

    json_blocks = re.findall(r"```json(.*?)```", text, re.DOTALL)
    for b in json_blocks:
        try:
            d = json.loads(b.strip())
            func_name = d.get("function") or d.get("name")
            if func_name and func_name in TOOL_MAP:
                detected_calls.append((func_name, d.get("params") or d.get("arguments") or {}))
        except Exception:
            pass
    return detected_calls

def chat_with_vitalpet(messages: list) -> str:
    max_steps = 6
    step = 0
    formula_generated = False  # 标记配方是否已经计算完成

    while step < max_steps:
        step += 1
        print(f"\n🧠 [步骤 {step}] AI 正在分析决策...")

        # 核心防循环：如果上一轮配方已经生成成功，则不再向模型提供 generate 工具，强制其结案作答！
        active_tools = TOOLS
        if formula_generated:
            active_tools = [t for t in TOOLS if t["function"]["name"] != "generate_complete_industrial_formula"]

        response = client.chat(
            model=MODEL_NAME,
            messages=messages,
            tools=active_tools if active_tools else None
        )

        tool_calls_to_run = []
        if response.message.tool_calls:
            for tc in response.message.tool_calls:
                tool_calls_to_run.append((tc.function.name, tc.function.arguments))
        else:
            content_text = response.message.content or ""
            text_calls = extract_text_tool_calls(content_text)
            if text_calls:
                print("⚡ [智能拦截] 检测到模型在正文中输出工具调用代码，自动转换为真实调用...")
                tool_calls_to_run = text_calls

        if tool_calls_to_run:
            messages.append(response.message)
            for func_name, raw_args in tool_calls_to_run:
                clean_args = unwrap_tool_arguments(raw_args)
                if func_name in TOOL_MAP:
                    print(f"⚙️ [执行工具] {func_name} -> 参数: {clean_args}")
                    func = TOOL_MAP[func_name]
                    try:
                        tool_result = func(**clean_args)
                    except Exception as err:
                        tool_result = f"工具执行异常: {err}"

                    if func_name == "generate_complete_industrial_formula":
                        print(f"📥 [完整工业 BOM 配平单已生成]:\n{tool_result}\n")
                        # 只要非异常，标记配方已就绪，准备结案！
                        if "工业质量总配平" in str(tool_result) or "100.00%" in str(tool_result):
                            formula_generated = True
                    else:
                        preview = str(tool_result)[:250] + "..." if len(str(tool_result)) > 250 else str(tool_result)
                        print(f"📥 [数据已返回]:\n{preview}\n")

                    messages.append({
                        "role": "tool",
                        "content": str(tool_result)
                    })
                else:
                    messages.append({
                        "role": "tool",
                        "content": f"系统错误: 找不到工具 {func_name}"
                    })
            continue
        else:
            print("\n💡 [证据与配方数据已全部齐备，生成最终研发评估报告]:\n" + "="*60)
            final_content = response.message.content or ""
            print(final_content)
            print("\n" + "="*60)
            return final_content

    fallback = "⚠️ 已达最大多步规划上限，已为您呈现已知信息。"
    print(fallback)
    return fallback

if __name__ == "__main__":
    init_db()
    print(f"🐾 VitalPet-RD 研发助手启动完成 (当前模型: {MODEL_NAME})")
    print("💡 提示：支持复合方案检索、全剂型工业BOM配平与PubMed文献自主研发，输入 'exit' 退出。\n" + "="*60)

    conversation_history = [
        {"role": "system", "content": SYSTEM_PROMPT}
    ]

    while True:
        try:
            user_input = input("\n🧑‍🔬 请输入您的问题: ").strip()
            if not user_input:
                continue

            if user_input.lower() in ["exit", "q", "quit"]:
                print("👋 感谢使用 VitalPet-RD，系统已安全退出。")
                break

            conversation_history.append({"role": "user", "content": user_input})
            answer = chat_with_vitalpet(conversation_history)
            conversation_history.append({"role": "assistant", "content": answer})

        except EOFError:
            print("\n⚠️ 交互终端输入流结束，进程退出。")
            break
        except KeyboardInterrupt:
            print("\n👋 收到键盘中断信号，程序退出。")
            break
        except Exception as e:
            print(f"\n❌ 会话出现异常: {e}")

