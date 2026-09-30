# app/pubmed/downloader.py
import os
import sqlite3
import httpx
from typing import Optional

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DB_PATH = os.path.join(BASE_DIR, "data", "evidence_vault.db")
PAPERS_DIR = os.path.join(BASE_DIR, "data", "papers")

os.makedirs(PAPERS_DIR, exist_ok=True)

class PaperDownloader:
    def __init__(self):
        # 信任环境代理 (确保公司内网环境正常访问外网 NCBI)
        limits = httpx.Limits(max_keepalive_connections=5, max_connections=10)
        self.client = httpx.Client(timeout=30.0, limits=limits, trust_env=True, follow_redirects=True)

    def download_pmc_pdf(self, pmid: str, pmc_id: str) -> Optional[str]:
        """根据 PMC ID 尝试下载官方免费全文 PDF 并持久化到本地"""
        if not pmc_id:
            return None
        
        pmc_clean = pmc_id if str(pmc_id).startswith("PMC") else f"PMC{pmc_id}"
        pdf_filename = f"{pmid}_{pmc_clean}.pdf"
        target_path = os.path.join(PAPERS_DIR, pdf_filename)

        # 1. 本地已存在则直接返回路径
        if os.path.exists(target_path) and os.path.getsize(target_path) > 1024:
            return target_path

        # 2. 发起 NCBI PMC PDF 官方下载请求
        url = f"https://www.ncbi.nlm.nih.gov/pmc/articles/{pmc_clean}/pdf/"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "application/pdf"
        }

        try:
            resp = self.client.get(url, headers=headers)
            if resp.status_code == 200 and "application/pdf" in resp.headers.get("content-type", ""):
                with open(target_path, "wb") as f:
                    f.write(resp.content)
                
                # 3. 将本地路径回写到 SQLite 证据库
                self._update_db_pdf_path(pmid, target_path)
                return target_path
            else:
                return None
        except Exception:
            return None

    def _update_db_pdf_path(self, pmid: str, local_path: str):
        try:
            with sqlite3.connect(DB_PATH) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "UPDATE pubmed_evidence SET pdf_path = ? WHERE pmid = ?",
                    (local_path, pmid)
                )
                conn.commit()
        except Exception:
            pass

    def close(self):
        self.client.close()

# 单例快速对外接口函数 (供 pubmed_tool.py 和 app_web.py 导入使用)
def fetch_paper_pdf(pmid: str, pmc_id: str) -> Optional[str]:
    downloader = PaperDownloader()
    try:
        return downloader.download_pmc_pdf(pmid, pmc_id)
    finally:
        downloader.close()

if __name__ == "__main__":
    test_pmid = "38891743"
    test_pmc = "PMC11171177"
    print(f"正在尝试下载测试文献: PMID {test_pmid} ({test_pmc})...")
    res = fetch_paper_pdf(test_pmid, test_pmc)
    if res:
        print(f"✅ 下载成功！文件保存在: {res}")
    else:
        print("❌ 未能下载到 PDF 原件。")

