# app/agent.py
import os
import sys
import re

# 关键：确保本地回环地址绕过公司网络代理，而远程请求（PubMed）正常走代理
os.environ["NO_PROXY"] = "127.0.0.1,localhost,0.0.0.0"
os.environ["no_proxy"] = "127.0.0.1,localhost,0.0.0.0"

import json
import ollama
from dotenv import load_dotenv

from app.db import init_db
from app.tools.pubmed_tool import search_pubmed_evidence
from app.tools.formula_tool import (
    query_ingredients_and_estimate_cost,
    generate_complete_industrial_formula
)

# 加载配置
load_dotenv()
MODEL_NAME = os.getenv("OLLAMA_MODEL", "vitalpet-rd:0.1")
client = ollama.Client(host="http://127.0.0.1:11434")

SYSTEM_PROMPT = """你是由 VitalPet-RD 驱动的宠物营养、保健品研发与工业制剂工程 AI 专家。
你的职责是根据科学证据、公司内部原料库与现代制剂工艺，为各类伴侣动物设计【工业级完整配方质量平衡 BOM 生产单】与专业研发报告。

【重大现实与时间基准（牢固认知）】：
- 现实世界已经远远超过 2024 年（当前为 2026 年），全球已经发表了海量 2024、2025、2026 年度的最新伴侣动物兽医科研文献！
- 严禁声称“当前是2024年7月”或“2024年之后的论文尚未发表”！检索最新科研文献时，必须以当前真实世界时间为基准，积极检索 2024 年及以后的文献。

【核心调用规则与决策铁律 - 必须严格执行】：
1. 真实系统级调用，严禁在正文伪造 JSON：
   - 严禁在回答正文中手写伪造模拟的 JSON、伪造工具调用代码块或假装调用（如“系统正在执行调用，请稍候”），凡是需要查询文献、配方或成本，必须真正发起系统级 function call！

2. 开放性咨询与文献探查规则（先搜后答）：
   - 当用户询问开放性/宽泛问题（例如：“有没有什么新论文”、“看有没有犬猫泪痕/胰腺炎/过敏的研究”、“查一下2024年以后的文献”等）：
     【必须立刻发起 `search_pubmed_evidence` 工具调用】！绝对严禁未查先回、严禁直接凭空假设或拒绝！
   - 专业兽医检索词转译能力（关键）：
     遇到通俗或中文词汇，应自动转化为英文专业兽医术语进行组合检索：
     * “犬猫泪痕/眼部发红” -> 转化为 `Epiphora dogs cats OR tear staining canine feline`；
     * “黑下巴/毛囊炎” -> 转化为 `Feline acne OR chin folliculitis`；
     * “软便/拉稀/肠炎” -> 转化为 `Feline canine diarrhea probiotics`；
     * “掉毛/皮屑/瘙痒” -> 转化为 `Alopecia pruritus dogs cats omega-3`；
     * 涉及多成分（如 OFL 方案） -> 将组合词作为整体传入（如 'Oligo-fucoidan Fucoxanthin L-carnitine CKD'）。
   - 若特定物种（如猫）检索无果，应主动将 target_species 设为 'veterinary' 或留空，以检索伴侣动物通用的前沿临床试验。

3. 严格尊重用户指定的物种与体重：
   - 用户指定的是猫（如 5kg 猫），调用 `generate_complete_industrial_formula` 时参数必须明确传递 `species='Cat', weight_kg=5.0`！
   - 即使引用的文献是在犬身上完成的（如针对犬肾病的临床试验），也绝不能把调用工具的物种私自改为 Dog！应在结案报告中说明该文献是犬类研究成果并推导至猫。

4. 工业配平单生成即结案（单次原则）：
   - 检索完文献拿到有效剂量后，调用一次 `generate_complete_industrial_formula` 即可获得完整的 BOM 表。
   - 工具返回 BOM 表后，配平计算已经完成，【严禁再次重复调用该工具】，应立刻输出最终研发评估报告！
   - 在最终输出结案报告时，【必须完整引用并展示工具生成的 100% 工业质量平衡 BOM 表】（包括活性物、辅料 MCC、脱模剂各自的 mg 含量、质量百分比与成本），严禁只写几句总结而将详细配平数据表吞掉！

5. 剂型与包装推荐：
   - 猫科动物（尤其是肾病/挑食病宠）：优先采用 hard_capsule（硬胶囊，规格 unit_weight_g=0.3 即 300mg，无高磷肉粉）或 liquid_drops。
   - 中大型犬日常补充：优先采用 soft_chew（软嚼粒 3.0g）或 chewable_tablet（咀嚼片 1.0g）。
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
                        "description": "功效大类（如 'Joint', 'Skin_Coat', 'Kidney', 'Eye', 'Gut_Digestion'）"
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
                                "name": {"type": "string", "description": "原料名称，如 'Bilberry Extract' 或 'Lutein'"},
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
                    "ingredient_or_topic": {"type": "string", "description": "原料英文名、复合配方名（例如 'Epiphora dogs cats' 或 'Oligo-fucoidan Fucoxanthin L-carnitine CKD'）或论文标题。"},
                    "target_species": {"type": "string", "description": "目标物种。宽泛或复合方案请填 'veterinary'。"}
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
    """
    鲁棒性清洗：彻底解决小模型将 {'function': ..., 'arguments': {...}} 
    或 {'tool': ..., 'parameters': {...}} 嵌套传递的问题
    """
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
    cleaned.pop("tool", None)
    cleaned.pop("name", None)

    safe_args = {}
    for k, v in cleaned.items():
        if isinstance(v, dict):
            safe_args[k] = str(list(v.values())[0]) if v else ""
        else:
            safe_args[k] = v
    return safe_args

def extract_text_tool_calls(text: str):
    """
    拦截兜底：若 4B 模型未调原生 API，而在正文输出了 ```json { "tool": ... } ``` 
    或 ```json { "function": ... } ``` 或 <tool_call>，自动提取并强行转为真实系统执行！
    """
    detected_calls = []

    # 1. 匹配 <tool_call> ... </tool_call>
    tool_blocks = re.findall(r"<tool_call>(.*?)</tool_call>", text, re.DOTALL)
    for b in tool_blocks:
        try:
            d = json.loads(b.strip())
            name = d.get("name") or d.get("tool") or d.get("function")
            args = d.get("arguments") or d.get("parameters") or d.get("params") or {}
            if name and name in TOOL_MAP:
                detected_calls.append((name, args))
        except Exception:
            pass

    # 2. 匹配 ```json ... ``` 块（兼容带不带语言标签及带注释的多行 JSON）
    json_blocks = re.findall(r"```(?:json)?\s*({.*?})\s*```", text, re.DOTALL)
    for b in json_blocks:
        try:
            cleaned_json_str = re.sub(r'//.*?\n', '\n', b.strip())
            d = json.loads(cleaned_json_str)
            func_name = d.get("function") or d.get("tool") or d.get("name")
            if func_name and func_name in TOOL_MAP:
                args = d.get("parameters") or d.get("params") or d.get("arguments") or {}
                detected_calls.append((func_name, args))
        except Exception:
            pass

    return detected_calls

def chat_with_vitalpet(messages: list) -> str:
    max_steps = 6
    step = 0
    formula_generated = False

    while step < max_steps:
        step += 1
        print(f"\n🧠 [步骤 {step}] AI 正在分析决策...")

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

