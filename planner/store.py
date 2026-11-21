"""Local storage: SQLite with a graceful in-memory fallback.

Stores favourites, recent cities, saved locations, plan history,
preferences, habit logs and daily AQI snapshots. If the SQLite file
cannot be created or written (read-only filesystem, cloud sandbox), the
store falls back to an in-memory dict for the session — the app keeps
working, nothing crashes.

NOTE (documented in the README): Streamlit Community Cloud's filesystem
is ephemeral, so saved data may reset when the app sleeps or reboots.
"""
from __future__ import annotations

import json
import os
import sqlite3
from datetime import date

DEFAULT_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            "..", "swachhvayu.db")

_SCHEMA = """
CREATE TABLE IF NOT EXISTS kv (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS snapshots (
    city TEXT NOT NULL,
    day TEXT NOT NULL,
    indian_aqi INTEGER,
    us_aqi REAL,
    pm25 REAL,
    PRIMARY KEY (city, day)
);
CREATE TABLE IF NOT EXISTS history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    day TEXT NOT NULL,
    city TEXT NOT NULL,
    kind TEXT NOT NULL,
    summary TEXT NOT NULL
);
"""


class Store:
    """Key/value + snapshot + history store backed by SQLite or memory."""

    def __init__(self, path: str | None = DEFAULT_PATH):
        self.path = path
        self._memory: dict[str, str] = {}
        self._memory_snapshots: dict[tuple[str, str], dict] = {}
        self._memory_history: list[dict] = []
        self.available = False
        if path is None:
            return
        try:
            os.makedirs(os.path.dirname(os.path.abspath(path)),
                        exist_ok=True)
            conn = sqlite3.connect(path, timeout=5)
            conn.executescript(_SCHEMA)
            conn.commit()
            conn.close()
            self.available = True
        except (sqlite3.Error, OSError):
            self.available = False

    # -- low-level ---------------------------------------------------------
    def _connect(self):
        return sqlite3.connect(self.path, timeout=5)

    # -- key/value ---------------------------------------------------------
    def get(self, key: str, default: str | None = None) -> str | None:
        if self.available:
            try:
                with self._connect() as conn:
                    row = conn.execute(
                        "SELECT value FROM kv WHERE key = ?", (key,)
                    ).fetchone()
                return row[0] if row else default
            except sqlite3.Error:
                return self._memory.get(key, default)
        return self._memory.get(key, default)

    def set(self, key: str, value: str) -> None:
        if self.available:
            try:
                with self._connect() as conn:
                    conn.execute(
                        "INSERT OR REPLACE INTO kv (key, value) VALUES (?, ?)",
                        (key, value))
                    conn.commit()
                return
            except sqlite3.Error:
                pass
        self._memory[key] = value

    def delete(self, key: str) -> None:
        if self.available:
            try:
                with self._connect() as conn:
                    conn.execute("DELETE FROM kv WHERE key = ?", (key,))
                    conn.commit()
                return
            except sqlite3.Error:
                pass
        self._memory.pop(key, None)

    # -- JSON helpers ------------------------------------------------------
    def get_json(self, key: str, default=None):
        raw = self.get(key)
        if raw is None:
            return default
        try:
            return json.loads(raw)
        except ValueError:
            return default

    def set_json(self, key: str, value) -> None:
        self.set(key, json.dumps(value, ensure_ascii=False))

    # -- favourites --------------------------------------------------------
    def favourites(self) -> list[dict]:
        return self.get_json("favourites", []) or []

    def add_favourite(self, city: dict) -> list[dict]:
        favs = self.favourites()
        if all(f.get("name") != city.get("name") for f in favs):
            favs.append(city)
            self.set_json("favourites", favs)
        return favs

    def remove_favourite(self, name: str) -> list[dict]:
        favs = [f for f in self.favourites() if f.get("name") != name]
        self.set_json("favourites", favs)
        return favs

    # -- recent cities -----------------------------------------------------
    def recent_cities(self) -> list[dict]:
        return self.get_json("recent_cities", []) or []

    def add_recent(self, city: dict, limit: int = 6) -> list[dict]:
        recent = [c for c in self.recent_cities()
                  if c.get("name") != city.get("name")]
        recent.insert(0, city)
        recent = recent[:limit]
        self.set_json("recent_cities", recent)
        return recent

    # -- saved locations (Home / Office / School) --------------------------
    def locations(self) -> dict[str, dict]:
        return self.get_json("locations", {}) or {}

    def set_location(self, label: str, city: dict) -> dict[str, dict]:
        locs = self.locations()
        locs[label] = city
        self.set_json("locations", locs)
        return locs

    # -- snapshots (daily AQI history for analytics) -----------------------
    def save_snapshot(self, city: str, day: str | None = None,
                      indian_aqi: int | None = None,
                      us_aqi: float | None = None,
                      pm25: float | None = None) -> None:
        day = day or date.today().isoformat()
        if self.available:
            try:
                with self._connect() as conn:
                    conn.execute(
                        "INSERT OR REPLACE INTO snapshots "
                        "(city, day, indian_aqi, us_aqi, pm25) "
                        "VALUES (?, ?, ?, ?, ?)",
                        (city, day, indian_aqi, us_aqi, pm25))
                    conn.commit()
                return
            except sqlite3.Error:
                pass
        self._memory_snapshots[(city, day)] = {
            "city": city, "day": day, "indian_aqi": indian_aqi,
            "us_aqi": us_aqi, "pm25": pm25,
        }

    def snapshots(self, city: str) -> list[dict]:
        if self.available:
            try:
                with self._connect() as conn:
                    rows = conn.execute(
                        "SELECT city, day, indian_aqi, us_aqi, pm25 "
                        "FROM snapshots WHERE city = ? ORDER BY day",
                        (city,)).fetchall()
                return [{"city": r[0], "day": r[1], "indian_aqi": r[2],
                         "us_aqi": r[3], "pm25": r[4]} for r in rows]
            except sqlite3.Error:
                pass
        return sorted(
            (s for (c, _), s in self._memory_snapshots.items() if c == city),
            key=lambda s: s["day"])

    # -- history (saved plans / recommendations) ---------------------------
    def log_history(self, city: str, kind: str, summary: str,
                    day: str | None = None) -> None:
        day = day or date.today().isoformat()
        if self.available:
            try:
                with self._connect() as conn:
                    conn.execute(
                        "INSERT INTO history (day, city, kind, summary) "
                        "VALUES (?, ?, ?, ?)", (day, city, kind, summary))
                    conn.commit()
                return
            except sqlite3.Error:
                pass
        self._memory_history.append(
            {"day": day, "city": city, "kind": kind, "summary": summary})

    def history(self, limit: int = 20) -> list[dict]:
        if self.available:
            try:
                with self._connect() as conn:
                    rows = conn.execute(
                        "SELECT day, city, kind, summary FROM history "
                        "ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
                return [{"day": r[0], "city": r[1], "kind": r[2],
                         "summary": r[3]} for r in rows]
            except sqlite3.Error:
                pass
        return list(reversed(self._memory_history))[:limit]


# Module-level default store (lazy: created on first use).
_DEFAULT: Store | None = None


def default_store() -> Store:
    global _DEFAULT
    if _DEFAULT is None:
        _DEFAULT = Store()
    return _DEFAULT
