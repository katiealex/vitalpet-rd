# app/scheduler/harvester.py
import time
import sqlite3
import os
from apscheduler.schedulers.blocking import BlockingScheduler
from app.pubmed.client import PubMedClient
from app.db import init_db, save_evidence, DB_PATH

# 核心监控原料列表（使用精简、无多余物种词的英文标准通用名，防止与底层 PET_FILTER 冲突）
DAILY_MONITORED_TERMS = [
    "Glucosamine",
    "Chondroitin Sulfate",
    "Omega-3 Fatty Acids",
    "Enterococcus faecium",
    "Timothy Hay",
    "Ascorbic Acid",
    "Milk Thistle Silymarin"
]

def harvest_latest_pubmed_research():
    print("⏰ [Daily Harvester] 开始执行 PubMed 宠物营养文献巡检与下载...")
    init_db()
    client = PubMedClient()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    total_added = 0

    try:
        for term in DAILY_MONITORED_TERMS:
            try:
                # 1. 检查库中当前原料已收录的文献数量
                cursor.execute("SELECT COUNT(*) FROM pubmed_evidence WHERE ingredient_term LIKE ?", (f"%{term}%",))
                existing_count = cursor.fetchone()[0]

                # 2. 自适应策略：如果库里是 0 篇，不设 days_back，直接下载最新 5 篇做冷启动；如果已有，则拉取最近 30 天增量
                days = None if existing_count == 0 else 30
                limit = 5 if existing_count == 0 else 10

                pmids = client.search(term, retmax=limit, days_back=days)
                if not pmids:
                    print(f"  ℹ️ [{term}] 未检索到新文献。")
                    continue

                # 3. 过滤出本地库中不存在的新 PMID
                new_pmids = []
                for pmid in pmids:
                    cursor.execute("SELECT 1 FROM pubmed_evidence WHERE pmid = ?", (pmid,))
                    if not cursor.fetchone():
                        new_pmids.append(pmid)

                if new_pmids:
                    articles = client.fetch_details(new_pmids)
                    for art in articles:
                        save_evidence(art, ingredient_term=term, target_species="veterinary", source="daily_harvest")
                    total_added += len(articles)
                    print(f"  + [{term}] 成功下载并入库 {len(articles)} 篇文献。")
                else:
                    print(f"  ✓ [{term}] 检索到的 {len(pmids)} 篇文献本地已全部存在。")

                time.sleep(0.35)  # 限速保护
            except Exception as e:
                print(f"  x 抓取 [{term}] 出错: {e}")

    finally:
        conn.close()
        client.close()

    print(f"✅ [Daily Harvester] 巡检完成，本次新收录 {total_added} 篇文献。")

def start_scheduler():
    init_db()
    scheduler = BlockingScheduler()
    # 每天凌晨 02:30 定时触发
    scheduler.add_job(harvest_latest_pubmed_research, 'cron', hour=2, minute=30)
    print("🚀 PubMed 定时巡检后台调度器已就绪 (每天凌晨 02:30 自动执行)...")
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        print("👋 调度器已停止。")

if __name__ == "__main__":
    # 直接运行该脚本时立即执行一次巡检入库
    harvest_latest_pubmed_research()

