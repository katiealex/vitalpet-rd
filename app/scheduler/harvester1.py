# app/scheduler/harvester.py
import time
from apscheduler.schedulers.blocking import BlockingScheduler
from app.pubmed.client import PubMedClient
from app.pubmed.vocabulary import DAILY_MONITORED_TERMS
from app.db import init_db, save_evidence

def harvest_latest_pubmed_research():
    print("⏰ [Daily Harvester] 开始执行 PubMed 宠物营养最新文献日常巡检...")
    client = PubMedClient()
    total_added = 0

    for term in DAILY_MONITORED_TERMS:
        try:
            # 增量抓取过去 3 天录入的文献
            pmids = client.search(term, retmax=5, days_back=3)
            if pmids:
                articles = client.fetch_details(pmids)
                for art in articles:
                    save_evidence(art, ingredient_term=term, target_species="veterinary", source="daily_harvest")
                total_added += len(articles)
                print(f"  + [{term}] 检索到 {len(articles)} 篇文献并同步入库。")
            time.sleep(0.4) # 限速保护
        except Exception as e:
            print(f"  x 抓取 [{term}] 失败: {e}")

    print(f"✅ [Daily Harvester] 巡检完成，本次新收录 {total_added} 篇文献。")

def start_scheduler():
    init_db()
    scheduler = BlockingScheduler()
    # 每天凌晨 02:30 自动执行
    scheduler.add_job(harvest_latest_pubmed_research, 'cron', hour=2, minute=30)
    print("🚀 PubMed 自动巡检调度器已启动 (每天 02:30 触发)...")
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        pass

if __name__ == "__main__":
    # 也可以直接手动跑一次测试
    init_db()
    harvest_latest_pubmed_research()

