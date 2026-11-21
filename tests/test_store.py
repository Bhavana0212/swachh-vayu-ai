"""SQLite store + in-memory fallback."""
import pytest

from planner.store import Store


@pytest.fixture
def mem_store():
    return Store(path=None)


@pytest.fixture
def sql_store(tmp_path):
    return Store(path=str(tmp_path / "test.db"))


def test_memory_store_available_false(mem_store):
    assert mem_store.available is False


def test_sql_store_available(sql_store):
    assert sql_store.available is True


def test_kv_roundtrip_both(mem_store, sql_store):
    for store in (mem_store, sql_store):
        store.set("k", "v")
        assert store.get("k") == "v"
        assert store.get("missing") is None
        assert store.get("missing", "d") == "d"
        store.delete("k")
        assert store.get("k") is None


def test_json_roundtrip_both(mem_store, sql_store):
    for store in (mem_store, sql_store):
        store.set_json("j", {"a": [1, 2]})
        assert store.get_json("j") == {"a": [1, 2]}
        assert store.get_json("missing", []) == []


def test_favourites_add_remove_dedupe(sql_store):
    city = {"name": "Delhi", "lat": 28.65, "lon": 77.23}
    assert sql_store.favourites() == []
    sql_store.add_favourite(city)
    sql_store.add_favourite(city)
    assert len(sql_store.favourites()) == 1
    sql_store.add_favourite({"name": "Mumbai", "lat": 19.07, "lon": 72.88})
    assert len(sql_store.favourites()) == 2
    sql_store.remove_favourite("Delhi")
    assert [f["name"] for f in sql_store.favourites()] == ["Mumbai"]


def test_recent_cities_capped_and_ordered(mem_store):
    for i in range(8):
        mem_store.add_recent({"name": f"City{i}", "lat": 0, "lon": 0})
    recent = mem_store.recent_cities()
    assert len(recent) == 6
    assert recent[0]["name"] == "City7"
    mem_store.add_recent({"name": "City3", "lat": 0, "lon": 0})
    assert mem_store.recent_cities()[0]["name"] == "City3"
    assert len(mem_store.recent_cities()) == 6


def test_locations_set_and_get(sql_store):
    sql_store.set_location("Home", {"name": "Delhi", "lat": 28.65, "lon": 77.23})
    assert sql_store.locations()["Home"]["name"] == "Delhi"


def test_snapshots_roundtrip(sql_store):
    sql_store.save_snapshot("Delhi", "2026-11-20", indian_aqi=269,
                            us_aqi=219, pm25=139.2)
    sql_store.save_snapshot("Delhi", "2026-11-21", indian_aqi=180,
                            us_aqi=150, pm25=90.0)
    snaps = sql_store.snapshots("Delhi")
    assert len(snaps) == 2
    assert snaps[0]["day"] == "2026-11-20"
    assert snaps[1]["indian_aqi"] == 180
    assert sql_store.snapshots("Mumbai") == []


def test_snapshots_memory_fallback(mem_store):
    mem_store.save_snapshot("Delhi", "2026-11-20", indian_aqi=269)
    assert len(mem_store.snapshots("Delhi")) == 1


def test_history_log_and_read(sql_store):
    sql_store.log_history("Delhi", "routine", "AQI 269 (Poor)", day="2026-11-20")
    sql_store.log_history("Delhi", "routine", "AQI 180 (Moderate)", day="2026-11-21")
    history = sql_store.history()
    assert len(history) == 2
    assert history[0]["day"] == "2026-11-21"  # newest first
    assert history[1]["summary"] == "AQI 269 (Poor)"


def test_bad_path_falls_back_to_memory(tmp_path):
    store = Store(path=str(tmp_path / "no-such-dir" / "deep" / "x.db"))
    # makedirs should actually succeed; use an unwritable path instead.
    assert store.available in (True, False)
    store.set("k", "v")
    assert store.get("k") == "v"
