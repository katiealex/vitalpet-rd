# app/tools/pubmed_tool.py
from app.pubmed.client import PubMedClient
from app.db import save_evidence, query_local_cache

def search_pubmed_evidence(ingredient_or_topic: str, target_species: str = "both") -> str:
    """
    在线工具主函数：优先命中本地库，未命中再调 PubMed API 并持久化
    """
    # 1. 查本地缓存
    cached = query_local_cache(ingredient_or_topic, limit=2)
    if cached:
        res = ["【本地证据库已命中】:"]
        for c in cached:
            res.append(f"• [{c['year']}] {c['title']} (PMID: {c['pmid']})\n  摘要摘要: {c['abstract'][:250]}...\n  链接: {c['url']}")
        return "\n\n".join(res)

    # 2. 调远程 API
    species_term = "dog" if target_species == "dog" else ("cat" if target_species == "cat" else "")
    query = f"{ingredient_or_topic} {species_term}".strip()
    
    client = PubMedClient()
    pmids = client.search(query, retmax=2) # 4B 模型建议单次喂 2 篇精选摘要
    if not pmids:
        return f"未检索到与 '{ingredient_or_topic}' 在犬猫医学/营养相关的文献证据。"

    articles = client.fetch_details(pmids)
    formatted = []
    for art in articles:
        # 存库
        save_evidence(art, ingredient_term=ingredient_or_topic, target_species=target_species, source="online_query")
        # 浓缩文本供 4B 模型推理
        short_abs = art['abstract'][:300] + "..." if len(art['abstract']) > 300 else art['abstract']
        formatted.append(
            f"• 标题: {art['title']} ({art['year']}, {art['journal']})\n"
            f"  PMID: {art['pmid']}\n"
            f"  摘要: {short_abs}\n"
            f"  参考链接: {art['url']}"
        )
    return "\n\n".join(formatted)

