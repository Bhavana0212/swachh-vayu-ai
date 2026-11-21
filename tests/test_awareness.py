"""India Environmental Awareness content."""
from planner.awareness import (
    CONSTRUCTION_INFO,
    DIWALI_NOTE,
    DIWALI_PHASES,
    FESTIVALS,
    GOVERNMENT_RESOURCES,
    SOURCES,
    SOURCES_NOTE,
    STUBBLE_INFO,
    TRAFFIC_INFO,
)


def test_diwali_has_three_phases():
    assert set(DIWALI_PHASES) == {"Before Diwali", "During Diwali",
                                  "After Diwali"}
    assert all(len(tips) >= 2 for tips in DIWALI_PHASES.values())
    assert "firecracker" in DIWALI_NOTE.lower()


def test_stubble_info_honest_about_limits():
    assert "satellite" in STUBBLE_INFO["note"].lower()
    assert "October" in STUBBLE_INFO["when"]


def test_construction_and_traffic_honest():
    assert "does not have live traffic data" in TRAFFIC_INFO["note"]
    assert "rush" in TRAFFIC_INFO["rush_hours"].lower()
    assert len(CONSTRUCTION_INFO["precautions"]) >= 3


def test_sources_cover_pollutants():
    assert "PM2.5 (fine particles)" in SOURCES
    assert "NO2" in str(SOURCES)
    assert "POSSIBLE sources" in SOURCES_NOTE


def test_festivals_cover_five():
    names = {f.name for f in FESTIVALS}
    assert names == {"Diwali", "Holi", "Ganesh Chaturthi", "Durga Puja",
                     "Weddings"}
    assert all(len(f.ideas) >= 3 for f in FESTIVALS)


def test_government_resources_are_links():
    assert len(GOVERNMENT_RESOURCES) >= 3
    for name, url, note in GOVERNMENT_RESOURCES:
        assert url.startswith("https://")
        assert name.strip() and note.strip()
