#!/usr/bin/env python3
# check_evidence.py - 查看本地 PubMed 证据库收录情况与统计

import os
import sqlite3

def check_evidence_vault():
    # 动态定位项目根目录下的 data/evidence_vault.db
    base_dir = os.path.dirname(os.path.abspath(__file__))
    db_path = os.path.join(base_dir, "data", "evidence_vault.db")

    if not os.path.exists(db_path):
        print(f"❌ 证据库文件尚未生成: {db_path}")
        print("💡 提示: 运行 agent.py 检索或运行 harvester.py 巡检后会自动创建并落库。")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # 1. 检查是否存在 pubmed_evidence 表
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='pubmed_evidence'")
    if not cursor.fetchone():
        print("⚠️ 数据库中尚未发现 pubmed_evidence 数据表。")
        conn.close()
        return

    # 2. 统计总文献数
    cursor.execute("SELECT COUNT(*) FROM pubmed_evidence")
    total_count = cursor.fetchone()[0]
    print(f"\n📚 本地证据库 (evidence_vault.db) 当前已收录文献: {total_count} 篇\n" + "="*70)

    if total_count == 0:
        print("目前库中暂无文献数据。可以通过运行 agent 提问或定时任务抓取文献。")
        conn.close()
        return

    # 3. 按原料/检索词分类统计收录数量
    cursor.execute("""
        SELECT ingredient_term, COUNT(*) as cnt 
        FROM pubmed_evidence 
        GROUP BY ingredient_term 
        ORDER BY cnt DESC
    """)
    category_stats = cursor.fetchall()
    print("📊 原料/主题收录分布统计:")
    for term, cnt in category_stats:
        print(f"  • {term:<25}: {cnt} 篇")
    print("-" * 70)

    # 4. 展示最新入库的 5 篇文献详情卡片
    cursor.execute("""
        SELECT pmid, ingredient_term, target_species, year, journal, title, url
        FROM pubmed_evidence
        ORDER BY rowid DESC
        LIMIT 5
    """)
    recent_rows = cursor.fetchall()
    print("🔍 最新入库的 5 篇文献摘要卡片:")
    for idx, (pmid, term, species, year, journal, title, url) in enumerate(recent_rows, 1):
        species_label = species if species else "通用"
        journal_label = journal if journal else "N/A"
        print(f"\n[{idx}] PMID: {pmid} | 原料: {term} | 物种: {species_label} | 年份: {year}")
        print(f"    期刊: {journal_label}")
        print(f"    标题: {title}")
        print(f"    链接: {url}")

    conn.close()
    print("\n" + "="*70 + "\n")

if __name__ == "__main__":
    check_evidence_vault()

