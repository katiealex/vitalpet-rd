# app/pubmed/client.py
import os
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

class PubMedClient:
    def __init__(self):
        # 增加 limits 设置以提高并发稳定性
        limits = httpx.Limits(max_keepalive_connections=5, max_connections=10)
        self.client = httpx.Client(timeout=15.0, limits=limits)

    def search(self, query: str, retmax: int = 5, days_back: Optional[int] = None) -> List[str]:
        """
        检索 PubMed 返回符合条件的文献 PMID 列表
        :param query: 搜索词（原料名、病症等）
        :param retmax: 返回的最大文献数
        :param days_back: 检索过去 N 天内收录的文献
        """
        url = f"{BASE_URL}/esearch.fcgi"
        
        # 稳健拼接，防止 query 为空时出现开头孤立的 'AND'
        query_clean = query.strip()
        if query_clean:
            term = f"({query_clean}) AND {PET_FILTER}"
        else:
            term = PET_FILTER

        params = {
            "db": "pubmed",
            "term": term,
            "retmode": "json",
            "retmax": retmax,
            "email": EMAIL,
            "sort": "pub_date",  # 确保优先返回最新发表的文献
        }
        if NCBI_API_KEY:
            params["api_key"] = NCBI_API_KEY
        if days_back:
            params["reldate"] = days_back
            params["datetype"] = "edat"

        resp = self.client.get(url, params=params)
        resp.raise_for_status()
        return resp.json().get("esearchresult", {}).get("idlist", [])

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
                # 递归提取当前节点内的全部文本，避免标签截断
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

