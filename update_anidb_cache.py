import gzip
import io
import os
import time
import sqlite3
import requests
import xml.etree.ElementTree as ET
from pathlib import Path
from datetime import datetime, timedelta

DB = Path(__file__).with_name("anidb_cache.db")
CACHE_DIR = Path(__file__).parent / "_cache"
CACHE_DIR.mkdir(exist_ok=True)
LOCAL_GZ = CACHE_DIR / "anime-titles.xml.gz"

TITLES_URL = os.environ.get("TITLES_URL", "http://anidb.net/api/anime-titles.xml.gz")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "*/*", "Referer": "https://anidb.net/", "Accept-Encoding": "identity", "Connection": "close"
}

MAX_AGE = timedelta(days=1)

def ensure_title_schema(con: sqlite3.Connection):
    cur = con.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS titles (
            aid INTEGER NOT NULL, lang TEXT NOT NULL, type TEXT NOT NULL, title TEXT NOT NULL
        )
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_titles_aid ON titles(aid)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_titles_title ON titles(title)")
    cur.execute("""
        CREATE VIRTUAL TABLE IF NOT EXISTS titles_fts
        USING fts5(title, lang, type, aid UNINDEXED, content='titles', content_rowid='rowid')
    """)
    con.commit()

def should_redownload(path: Path) -> bool:
    if not path.exists(): return True
    mtime = datetime.fromtimestamp(path.stat().st_mtime)
    return datetime.now() - mtime > MAX_AGE

def download_with_retries(url: str, dst: Path, headers: dict, retries=3, backoff=2.0):
    last_err = None
    for i in range(retries):
        try:
            print(f"Downloading anime-titles.xml.gz ... (attempt {i+1}/{retries})")
            r = requests.get(url, headers=headers, timeout=60, stream=True)
            if r.status_code == 403:
                raise requests.HTTPError("403 Forbidden from AniDB (blocked)")
            r.raise_for_status()
            tmp = dst.with_suffix(".part")
            with open(tmp, "wb") as f:
                for chunk in r.iter_content(chunk_size=1024 * 64):
                    if chunk: f.write(chunk)
            os.replace(tmp, dst)
            return
        except Exception as e:
            last_err = e
            if i < retries - 1:
                wait = backoff * (2 ** i)
                print(f"Download failed: {e}. Retrying in {wait:.1f}s ...")
                time.sleep(wait)
            else:
                print("Giving up after retries.")
                raise last_err

def refresh_titles_if_stale():
    if should_redownload(LOCAL_GZ):
        try:
            download_with_retries(TITLES_URL, LOCAL_GZ, HEADERS)
        except Exception as e:
            if not LOCAL_GZ.exists(): raise

    with open(LOCAL_GZ, "rb") as f:
        xml_bytes = gzip.decompress(f.read())

    root = ET.parse(io.BytesIO(xml_bytes)).getroot()
    rows = []
    for anime in root.findall("anime"):
        aid = int(anime.get("aid"))
        for t in anime.findall("title"):
            lang = t.get("{http://www.w3.org/XML/1998/namespace}lang") or t.get("lang") or "x-jat"
            rows.append((aid, lang, t.get("type") or "synonym", (t.text or "").strip()))

    con = sqlite3.connect(DB)
    try:
        ensure_title_schema(con)
        cur = con.cursor()
        cur.execute("DELETE FROM titles")
        cur.execute("DELETE FROM titles_fts")
        cur.executemany("INSERT INTO titles(aid, lang, type, title) VALUES (?, ?, ?, ?)", rows)
        cur.execute("INSERT INTO titles_fts(rowid, title, lang, type) SELECT rowid, title, lang, type FROM titles")
        con.commit()
        print(f"Loaded {len(rows):,} title rows into SQLite.")
    finally:
        con.close()

if __name__ == "__main__":
    refresh_titles_if_stale()