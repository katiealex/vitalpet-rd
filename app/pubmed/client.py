# app/pubmed/client.py
import os
import re
import xml.etree.ElementTree as ET
from typing import List, Dict, Optional
import httpx
from dotenv import load_dotenv

load_dotenv()

NCBI_API_KEY = os.getenv("NCBI_API_KEY", "")
EMAIL = os.getenv("NCBI_EMAIL", "rd@vitalpet.local")
BASE_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"

# 全面覆盖犬猫、小宠（兔、龙猫、豚鼠、雪貂、仓鼠等）、宠物鸟、爬宠及兽医学的专用过滤器
PET_FILTER = (
    '("Pets"[MeSH Terms] OR "veterinary"[MeSH Terms] OR "Veterinary Medicine"[MeSH Terms] '
    'OR "companion animal" OR "companion animals" OR "exotic pet" OR "exotic pets" OR "small mammal" '
    'OR "Dogs"[MeSH Terms] OR "Cats"[MeSH Terms] OR "canine" OR "feline" OR "dog" OR "cat" '
    'OR "Rabbits"[MeSH Terms] OR "rabbit" OR "rabbits" OR "chinchilla" OR "chinchillas" '
    'OR "guinea pig" OR "guinea pigs" OR "Cavia porcellus" OR "degus" '
    'OR "Ferrets"[MeSH Terms] OR "ferret" OR "ferrets" OR "Mustela putorius furo" '
    'OR "Cricetinae"[MeSH Terms] OR "hamster" OR "hamsters" OR "gerbil" OR "gerbils" '
    'OR "hedgehogs" OR "hedgehog" OR "sugar glider" '
    'OR "Psittaciformes"[MeSH Terms] OR "parrot" OR "parrots" OR "avian pet" OR "pet bird" '
    'OR "budgerigar" OR "cockatiel" OR "canary" OR "finch" '
    'OR "pet reptile" OR "captive reptile" OR "bearded dragon" OR "gecko" OR "tortoise" OR "chelonian")'
)

# 用于单一物种回退时剥离特定物种词的正则表达式
NARROW_SPECIES_PATTERN = re.compile(
    r'\b(cats?|feline|dogs?|canine|rabbits?|guinea pigs?|chinchillas?|ferrets?|犬|猫|狗|兔子|豚鼠)\b',
    re.IGNORECASE
)

class PubMedClient:
    def __init__(self):
        # limits 设置提高并发稳定性，trust_env 确保支持公司网络代理环境
        limits = httpx.Limits(max_keepalive_connections=5, max_connections=10)
        self.client = httpx.Client(timeout=15.0, limits=limits, trust_env=True)

    def _execute_esearch(self, term: str, retmax: int, days_back: Optional[int] = None, sort_by_date: bool = True) -> List[str]:
        """底层实际发起 esearch 请求"""
        url = f"{BASE_URL}/esearch.fcgi"
        params = {
            "db": "pubmed",
            "term": term,
            "retmode": "json",
            "retmax": retmax,
            "email": EMAIL,
        }
        if sort_by_date:
            params["sort"] = "pub_date"
        if NCBI_API_KEY:
            params["api_key"] = NCBI_API_KEY
        if days_back:
            params["reldate"] = days_back
            params["datetype"] = "edat"

        resp = self.client.get(url, params=params)
        resp.raise_for_status()
        return resp.json().get("esearchresult", {}).get("idlist", [])

    def search(self, query: str, retmax: int = 5, days_back: Optional[int] = None) -> List[str]:
        """
        具备三级智能回退能力的文献检索：
        1. 尝试原始检索；
        2. 若 0 篇且包含单一物种词，自动剥离物种词（物种回退到所有兽医伴侣动物）；
        3. 若仍为 0 篇且限制了时间，自动放开时间窗口；
        4. 若仍为 0 篇，切换为原生相关度检索（Relevance）。
        """
        query_clean = query.strip()
        term = f"({query_clean}) AND {PET_FILTER}" if query_clean else PET_FILTER

        # 尝试 1: 原始正常检索
        idlist = self._execute_esearch(term, retmax, days_back=days_back, sort_by_date=True)
        if idlist:
            return idlist

        # 尝试 2 (核心物种回退): 检查检索词中是否包含单一物种限制（如 'cat' 或 'dog'）
        broadened_query = NARROW_SPECIES_PATTERN.sub('', query_clean).strip()
        # 清理多余空格与标点
        broadened_query = re.sub(r'\s+', ' ', broadened_query).strip()

        if broadened_query and broadened_query != query_clean:
            print(f"🔄 [PubMed 物种回退] 单一物种未匹配到文献，自动回退至全伴侣动物/兽医范围: '{broadened_query}'...")
            term_broadened = f"({broadened_query}) AND {PET_FILTER}"
            idlist = self._execute_esearch(term_broadened, retmax, days_back=days_back, sort_by_date=True)
            if idlist:
                return idlist

        # 尝试 3 (时间回退): 如果指定了天数限制仍无结果，自动扩大到历史所有经典文献
        if days_back is not None:
            active_q = broadened_query if (broadened_query and broadened_query != query_clean) else query_clean
            term_no_date = f"({active_q}) AND {PET_FILTER}" if active_q else PET_FILTER
            idlist = self._execute_esearch(term_no_date, retmax, days_back=None, sort_by_date=True)
            if idlist:
                return idlist

        # 尝试 4 (相关度回退): 去掉 pub_date 强制最新排序，改走相关度算法
        active_q = broadened_query if (broadened_query and broadened_query != query_clean) else query_clean
        term_rel = f"({active_q}) AND {PET_FILTER}" if active_q else PET_FILTER
        idlist = self._execute_esearch(term_rel, retmax, days_back=None, sort_by_date=False)
        return idlist

    def fetch_details(self, pmids: List[str]) -> List[Dict]:
        """根据 PMID 批量拉取结构化文献详情"""
        if not pmids:
            return []

        url = f"{BASE_URL}/efetch.fcgi"
        params = {
            "db": "pubmed",
            "id": ",".join(pmids),
            "retmode": "xml",
            "email": EMAIL,
        }
        if NCBI_API_KEY:
            params["api_key"] = NCBI_API_KEY

        resp = self.client.get(url, params=params)
        resp.raise_for_status()
        return self._parse_xml(resp.text)

    def _parse_xml(self, xml_text: str) -> List[Dict]:
        """解析 XML 结果，提取完整标题、长摘要、年份、期刊与 PMC 全文 ID"""
        articles = []
        try:
            root = ET.fromstring(xml_text)
        except ET.ParseError:
            return []

        for article in root.findall(".//PubmedArticle"):
            pmid = article.findtext(".//MedlineCitation/PMID", "")

            # 提取标题并合并所有文本片段
            title_node = article.find(".//ArticleTitle")
            title = "".join(title_node.itertext()).strip() if title_node is not None else ""

            # 关键修复：使用 itertext() 提取含 <i>, <b>, <sup> 的完整结构化摘要
            abstract_nodes = article.findall(".//Abstract/AbstractText")
            abstract_parts = []
            for node in abstract_nodes:
                label = node.get("Label")
                text_content = "".join(node.itertext()).strip()
                if label:
                    abstract_parts.append(f"{label}: {text_content}")
                else:
                    abstract_parts.append(text_content)

            abstract = "\n".join(abstract_parts).strip()
            if not abstract:
                abstract = "无公开摘要文本。"

            # 提取年份
            pub_date = (
                article.findtext(".//Journal/JournalIssue/PubDate/Year") or
                article.findtext(".//Journal/JournalIssue/PubDate/MedlineDate", "N/A")
            )
            journal = article.findtext(".//Journal/Title", "")

            # 检测 PMC 免费全文 ID
            pmc_id = None
            for aid in article.findall(".//PubmedData/ArticleIdList/ArticleId"):
                if aid.get("IdType") == "pmc":
                    pmc_id = aid.text
                    break

            articles.append({
                "pmid": pmid,
                "title": title,
                "abstract": abstract,
                "year": pub_date,
                "journal": journal,
                "pmc_id": pmc_id,
                "url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"
            })
        return articles

    def close(self):
        """显式关闭网络客户端"""
        self.client.close()

