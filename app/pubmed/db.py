# app/db.py
import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "evidence_vault.db")

def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS pubmed_evidence (
                pmid TEXT PRIMARY KEY,
                ingredient_term TEXT,
                target_species TEXT,
                title TEXT,
                abstract TEXT,
                year TEXT,
                journal TEXT,
                pmc_id TEXT,
                url TEXT,
                harvest_source TEXT, -- 'online_query' 或 'daily_harvest'
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_ingredient ON pubmed_evidence(ingredient_term);")
        conn.commit()

def save_evidence(art: dict, ingredient_term: str, target_species: str, source: str = "online_query"):
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR IGNORE INTO pubmed_evidence 
            (pmid, ingredient_term, target_species, title, abstract, year, journal, pmc_id, url, harvest_source)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            art["pmid"], ingredient_term, target_species, art["title"],
            art["abstract"], art["year"], art["journal"], art["pmc_id"],
            art["url"], source
        ))
        conn.commit()

def query_local_cache(ingredient_term: str, limit: int = 3):
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("""
            SELECT pmid, title, abstract, year, journal, url 
            FROM pubmed_evidence 
            WHERE ingredient_term LIKE ? OR title LIKE ?
            ORDER BY year DESC 
            LIMIT ?
        """, (f"%{ingredient_term}%", f"%{ingredient_term}%", limit))
        return [dict(row) for row in cursor.fetchall()]

