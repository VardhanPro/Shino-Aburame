import os
import sqlite3
import requests
import xmltodict
import time
import json
import re
from flask import Flask, render_template, request, g, jsonify, Response
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
TRACKER_DB = 'tracker.db'
ANIDB_CACHE_DB = 'anidb_cache.db'
IMAGE_BASE_URL = "https://cdn-eu.anidb.net/images/main/"

# --- Database & Helper Functions (Unchanged) ---
def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(TRACKER_DB)
        db.row_factory = sqlite3.Row
    return db

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

def rl_wait(min_interval=2.1):
    db = get_db()
    cur = db.cursor()
    cur.execute("SELECT last_ts FROM rate_limit WHERE id=1")
    last_call_time = cur.fetchone()["last_ts"]
    now = time.time()
    wait_time = (last_call_time + min_interval) - now
    if wait_time > 0:
        print(f"Rate limiting: waiting for {wait_time:.2f} seconds...")
        time.sleep(wait_time)
    cur.execute("UPDATE rate_limit SET last_ts=?", (time.time(),))
    db.commit()

def cache_get(key, max_age_seconds=7*24*3600):
    db = get_db()
    cur = db.cursor()
    cur.execute("SELECT value, fetched_at FROM api_cache WHERE key=?", (key,))
    row = cur.fetchone()
    if not row: return None
    if time.time() - row["fetched_at"] > max_age_seconds: return None
    return json.loads(row["value"])

def cache_put(key, value):
    db = get_db()
    cur = db.cursor()
    cur.execute("REPLACE INTO api_cache(key, value, fetched_at) VALUES (?, ?, ?)",
                (key, json.dumps(value), time.time()))
    db.commit()
    
def cache_delete(key):
    db = get_db()
    cur = db.cursor()
    cur.execute("DELETE FROM api_cache WHERE key=?", (key,))
    db.commit()

# --- Main App Routes ---
@app.route('/')
def index():
    cursor = get_db().cursor()
    # --- NEW: SQL query to sort completed anime to the bottom ---
    cursor.execute("""
        SELECT * FROM anime 
        ORDER BY 
            CASE 
                WHEN watched_episodes >= total_episodes AND total_episodes > 0 THEN 1 
                ELSE 0 
            END, 
            title ASC
    """)
    animes = [dict(row) for row in cursor.fetchall()]
    return render_template('index.html', animes=animes)

@app.route('/api/image/<path:filename>')
def image_proxy(filename):
    image_url = f"{IMAGE_BASE_URL}{filename}"
    try:
        response = requests.get(image_url, stream=True, timeout=20)
        response.raise_for_status()
        return Response(response.iter_content(chunk_size=1024), content_type=response.headers['Content-Type'])
    except requests.RequestException as e:
        print(f"Failed to proxy image {filename}: {e}")
        return "", 404

# --- API ENDPOINTS (Unchanged from last version) ---
@app.route('/api/search')
def search_api():
    query = request.args.get('q', '').strip()
    page = int(request.args.get('page', 1))
    page_size = 10
    offset = (page - 1) * page_size
    if len(query) < 2: return jsonify({'results': [], 'total': 0})
    search_query = f"{query}*"
    conn_cache = sqlite3.connect(ANIDB_CACHE_DB)
    conn_cache.row_factory = sqlite3.Row
    cursor_cache = conn_cache.cursor()
    cursor_cache.execute(
        "SELECT count(DISTINCT aid) as total FROM titles_fts WHERE title MATCH ? AND lang = 'en'", (search_query,)
    )
    total = cursor_cache.fetchone()['total']
    cursor_cache.execute(
        "SELECT DISTINCT aid, title FROM titles_fts WHERE title MATCH ? AND lang = 'en' ORDER BY CASE WHEN type = 'main' THEN 0 WHEN type = 'official' THEN 1 ELSE 2 END, rank LIMIT ? OFFSET ?",
        (search_query, page_size, offset)
    )
    results = [dict(row) for row in cursor_cache.fetchall()]
    conn_cache.close()
    return jsonify({'results': results, 'total': total})

@app.route('/api/add', methods=['POST'])
def add_anime():
    aid = request.get_json().get('aid')
    if not aid: return jsonify({'success': False, 'message': 'Anime ID is required.'}), 400

    try:
        cache_key = f"anime:{aid}"
        api_data = cache_get(cache_key)
        if not api_data:
            rl_wait()
            api_url = f"http://api.anidb.net:9001/httpapi?request=anime&client={os.getenv('ANIDB_CLIENT')}&clientver={os.getenv('ANIDB_CLIENT_VERSION')}&protover=1&aid={aid}"
            headers = {'User-Agent': 'Mozilla/5.0'}
            response = requests.get(api_url, headers=headers, timeout=10)
            response.raise_for_status()
            api_data = xmltodict.parse(response.content)
            if "error" in api_data: raise Exception(api_data["error"])
            cache_put(cache_key, api_data)
        
        anime_node = api_data.get("anime", {})
        titles = anime_node.get("titles", {}).get("title", [])
        if not isinstance(titles, list): titles = [titles]
        main_title = next((t.get('#text') for t in titles if t.get('@type') == 'main'), "Unknown Title")
        
        raw_description = anime_node.get("description") or "No description available."
        cleaned_description = re.sub(r'https?://anidb.net/ch\d+\s*\[(.*?)\]', r'\1', raw_description)
        cleaned_description = cleaned_description.replace('Source: Wikipedia', 'Source: <a href="https://www.wikipedia.org" target="_blank" rel="noopener noreferrer">Wikipedia</a>')
        cleaned_description = cleaned_description.replace('Source: ANN', 'Source: <a href="https://www.animenewsnetwork.com/" target="_blank" rel="noopener noreferrer">ANN</a>')

        picture_filename = anime_node.get('picture')
        
        anime_data = {
            'aid': aid, 'title': main_title,
            'total_episodes': int(anime_node.get("episodecount", 0)),
            'description': cleaned_description,
            'start_date': anime_node.get("startdate"), 'end_date': anime_node.get("enddate"),
            'image_url': f"/api/image/{picture_filename}" if picture_filename else None,
            'anime_type': anime_node.get("type", "Unknown")
        }

        db = get_db()
        cursor = db.cursor()
        cursor.execute(
            "INSERT INTO anime (aid, title, total_episodes, description, start_date, end_date, image_url, anime_type) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                anime_data['aid'], anime_data['title'], anime_data['total_episodes'],
                anime_data['description'], anime_data['start_date'], anime_data['end_date'],
                anime_data['image_url'] if picture_filename else None, anime_data['anime_type']
            )
        )
        new_id = cursor.lastrowid
        db.commit()

        anime_data['id'] = new_id
        anime_data['watched_episodes'] = 0
        return jsonify({'success': True, 'anime': anime_data})

    except sqlite3.IntegrityError:
        return jsonify({'success': False, 'message': f"Anime is already in your list."})
    except Exception as e:
        print(f"An error occurred: {e}")
        return jsonify({'success': False, 'message': f'An error occurred: {str(e)}'}), 500

@app.route('/api/update/<int:anime_id>', methods=['POST'])
def update_progress(anime_id):
    action = request.json.get('action')
    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT watched_episodes, total_episodes FROM anime WHERE id = ?", (anime_id,))
    anime = cursor.fetchone()
    if not anime: return jsonify({'success': False, 'message': 'Anime not found.'}), 404
    new_count = anime['watched_episodes']
    if action == 'increment' and new_count < anime['total_episodes']: new_count += 1
    elif action == 'decrement' and new_count > 0: new_count -= 1
    cursor.execute("UPDATE anime SET watched_episodes = ? WHERE id = ?", (new_count, anime_id))
    db.commit()
    return jsonify({'success': True, 'watched_episodes': new_count})

@app.route('/api/remove/<int:anime_id>', methods=['DELETE'])
def remove_anime(anime_id):
    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT aid FROM anime WHERE id = ?", (anime_id,))
    row = cursor.fetchone()
    if row:
        cache_delete(f"anime:{row['aid']}")
        print(f"Cleared API cache for AID {row['aid']}")
    cursor.execute("DELETE FROM anime WHERE id = ?", (anime_id,))
    db.commit()
    return jsonify({'success': True, 'message': 'Anime removed.'})

if __name__ == '__main__':
    app.run(debug=True)