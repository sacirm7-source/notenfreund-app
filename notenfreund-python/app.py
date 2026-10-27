from datetime import date, datetime
from pathlib import Path
import random
import sqlite3
import uuid
from urllib.parse import urlsplit

from flask import Flask, abort, flash, redirect, render_template, request, send_from_directory, url_for
from werkzeug.utils import secure_filename

BASE_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = BASE_DIR / "uploads"
DB_PATH = BASE_DIR / "notenfreund.db"
UPLOAD_DIR.mkdir(exist_ok=True)
ALLOWED_EXTENSIONS = {"pdf", "mscz", "mscx", "musicxml", "xml", "mxl", "mid", "midi"}
MAX_UPLOAD_BYTES = 40 * 1024 * 1024

app = Flask(__name__)
app.secret_key = "change-this-local-key"
app.config["MAX_CONTENT_LENGTH"] = MAX_UPLOAD_BYTES

STAGES = ["Neu", "In Übung", "Gut geübt", "Beherrscht"]


def connect_db():
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def init_db():
    with connect_db() as db:
        db.execute("""
            CREATE TABLE IF NOT EXISTS pieces (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                composer TEXT NOT NULL DEFAULT '',
                stage TEXT NOT NULL DEFAULT 'Neu',
                stored_name TEXT NOT NULL,
                original_name TEXT NOT NULL,
                extension TEXT NOT NULL,
                created_at TEXT NOT NULL,
                practiced_on TEXT
            )
        """)
        columns = {row["name"] for row in db.execute("PRAGMA table_info(pieces)")}
        if "source_url" not in columns:
            db.execute("ALTER TABLE pieces ADD COLUMN source_url TEXT")


def get_piece(piece_id):
    with connect_db() as db:
        row = db.execute("SELECT * FROM pieces WHERE id = ?", (piece_id,)).fetchone()
    if row is None:
        abort(404)
    return row


@app.get("/")
def index():
    query = request.args.get("q", "").strip()
    stage = request.args.get("stage", "Alle")
    sql = "SELECT * FROM pieces WHERE 1=1"
    args = []
    if stage in STAGES:
        sql += " AND stage = ?"
        args.append(stage)
    if query:
        sql += " AND (title LIKE ? OR composer LIKE ? OR original_name LIKE ?)"
        args.extend([f"%{query}%"] * 3)
    sql += " ORDER BY created_at DESC"
    with connect_db() as db:
        pieces = db.execute(sql, args).fetchall()
        counts = {row["stage"]: row["count"] for row in db.execute("SELECT stage, COUNT(*) AS count FROM pieces GROUP BY stage")}
        total = sum(counts.values())
    return render_template("index.html", pieces=pieces, stages=STAGES, selected_stage=stage, query=query, counts=counts, total=total)


@app.post("/upload")
def upload():
    uploaded = request.files.get("score")
    if uploaded is None or not uploaded.filename:
        flash("Bitte wähle zuerst eine Notendatei aus.", "error")
        return redirect(url_for("index"))
    original = secure_filename(uploaded.filename)
    if not original or "." not in original:
        flash("Der Dateiname ist nicht gültig.", "error")
        return redirect(url_for("index"))
    extension = original.rsplit(".", 1)[1].lower()
    if extension not in ALLOWED_EXTENSIONS:
        flash("Erlaubte Formate: PDF, MuseScore, MusicXML und MIDI.", "error")
        return redirect(url_for("index"))
    piece_id = uuid.uuid4().hex
    stored = f"{piece_id}.{extension}"
    uploaded.save(UPLOAD_DIR / stored)
    title = original.rsplit(".", 1)[0]
    with connect_db() as db:
        db.execute("INSERT INTO pieces (id, title, stored_name, original_name, extension, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                   (piece_id, title, stored, original, extension, datetime.now().isoformat(timespec="seconds")))
    flash(f"{original} wurde hinzugefügt.", "success")
    return redirect(url_for("index"))


@app.post("/add-link")
def add_link():
    title = request.form.get("title", "").strip()
    source_url = request.form.get("source_url", "").strip()
    parsed = urlsplit(source_url)
    if not title:
        flash("Bitte gib einen Titel für das Stück ein.", "error")
    elif parsed.scheme not in {"http", "https"} or not parsed.netloc:
        flash("Bitte gib einen gültigen Weblink ein, der mit http:// oder https:// beginnt.", "error")
    else:
        piece_id = uuid.uuid4().hex
        with connect_db() as db:
            db.execute(
                "INSERT INTO pieces (id, title, stage, stored_name, original_name, extension, created_at, source_url) VALUES (?, ?, 'Neu', '', ?, 'link', ?, ?)",
                (piece_id, title, source_url, datetime.now().isoformat(timespec="seconds"), source_url),
            )
        flash(f"Link für „{title}“ gespeichert.", "success")
    return redirect(url_for("index"))


@app.post("/piece/<piece_id>/update")
def update_piece(piece_id):
    get_piece(piece_id)
    title = request.form.get("title", "").strip()
    composer = request.form.get("composer", "").strip()
    stage = request.form.get("stage", "Neu")
    if not title:
        flash("Der Titel darf nicht leer sein.", "error")
    elif stage not in STAGES:
        flash("Der Status ist ungültig.", "error")
    else:
        with connect_db() as db:
            db.execute("UPDATE pieces SET title = ?, composer = ?, stage = ? WHERE id = ?", (title, composer, stage, piece_id))
        flash("Änderungen gespeichert.", "success")
    return redirect(url_for("index"))


@app.post("/piece/<piece_id>/practice")
def practice(piece_id):
    get_piece(piece_id)
    with connect_db() as db:
        db.execute("UPDATE pieces SET practiced_on = ? WHERE id = ?", (date.today().isoformat(), piece_id))
    flash("Für heute als geübt markiert.", "success")
    return redirect(url_for("index"))


@app.post("/piece/<piece_id>/delete")
def delete_piece(piece_id):
    piece = get_piece(piece_id)
    with connect_db() as db:
        db.execute("DELETE FROM pieces WHERE id = ?", (piece_id,))
    try:
        if piece["stored_name"]:
            (UPLOAD_DIR / piece["stored_name"]).unlink(missing_ok=True)
    except OSError:
        pass
    flash("Stück und gespeicherte Datei gelöscht.", "success")
    return redirect(url_for("index"))


@app.get("/piece/<piece_id>/open")
def open_piece(piece_id):
    piece = get_piece(piece_id)
    if piece["source_url"]:
        return redirect(piece["source_url"])
    if piece["extension"] != "pdf":
        flash("Diese Datei ist gespeichert. Die Vorschau unterstützt derzeit PDF; MuseScore, MusicXML und MIDI haben noch keinen eingebauten Noten-Viewer.", "error")
        return redirect(url_for("index"))
    return send_from_directory(UPLOAD_DIR, piece["stored_name"], as_attachment=False, download_name=piece["original_name"])


@app.post("/random")
def random_piece():
    with connect_db() as db:
        candidates = db.execute("SELECT id FROM pieces WHERE stage IN ('Neu', 'In Übung')").fetchall()
    if not candidates:
        flash("Noch kein Stück mit Status „Neu“ oder „In Übung“ vorhanden.", "error")
    else:
        chosen = random.choice(candidates)["id"]
        flash(f"Dein zufälliges Übungsstück: {get_piece(chosen)['title']}", "success")
    return redirect(url_for("index"))


@app.errorhandler(413)
def too_large(_error):
    flash("Die Datei ist größer als 40 MB.", "error")
    return redirect(url_for("index"))


init_db()

if __name__ == "__main__":
    # Im selben privaten WLAN kann das Android-Handy den PC über dessen lokale IP erreichen.
    app.run(host="0.0.0.0", port=5000, debug=False)
