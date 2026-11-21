"""India Environmental Awareness: Diwali mode, stubble burning,
construction dust, traffic intelligence, seasonal comparison, pollutant
source education and the festival guide.

All content is educational and clearly separated from measured data. No
traffic or route data is invented — traffic guidance is time-based
(rush-hour awareness) only. Sources are described as POSSIBLE sources,
never as an attribution for today's readings.
"""
from __future__ import annotations

from dataclasses import dataclass

# --- Diwali mode -----------------------------------------------------------

DIWALI_PHASES: dict[str, list[str]] = {
    "Before Diwali": [
        "Stock N95/FFP2 masks for the family and check the purifier filter.",
        "Seal obvious gaps around windows in the rooms you use most.",
        "Plan celebrations that do not depend on firecrackers — diyas, "
        "lights, rangoli, and sweets carry the festival.",
    ],
    "During Diwali": [
        "Keep windows closed during peak bursting hours (evening to late "
        "night) and run the purifier.",
        "Keep children and elderly family members indoors during the "
        "heaviest bursting.",
        "If you step out, wear a fitted N95/FFP2 mask.",
    ],
    "After Diwali": [
        "Air out the home at the cleanest hour the next morning.",
        "Wet-mop floors — firecracker residue settles as dust.",
        "Check the forecast for the next few days; PM2.5 stays high after "
        "Diwali night.",
    ],
}

DIWALI_NOTE = ("Diwali night routinely produces the year's worst PM2.5 "
               "readings in North Indian cities. Firecrackers release "
               "fine particles, metals and gases that stay in the air for "
               "days in still winter weather.")

# --- Stubble burning -------------------------------------------------------

STUBBLE_INFO = {
    "what": ("After the paddy harvest (October–November), farmers in Punjab "
             "and Haryana burn crop residue in the fields. The smoke drifts "
             "across North India and is a major contributor to the "
             "post-monsoon smog season."),
    "when": "Peak burning weeks are usually late October to mid-November, "
            "varying by harvest timing.",
    "what_to_do": [
        "Expect worse mornings in late October and November across Delhi, "
        "Punjab, Haryana and western UP.",
        "Keep the purifier and masks ready before the season starts.",
        "Check the 5-day forecast daily — wind direction decides which "
        "cities the smoke reaches.",
    ],
    "note": ("This section is educational background. SwachhVayu AI does "
             "not track live fire counts or attribute today's AQI to "
             "stubble burning — that needs satellite data this app does "
             "not use."),
}

# --- Construction dust -----------------------------------------------------

CONSTRUCTION_INFO = {
    "what": ("Construction and road work release coarse dust (PM10) — "
             "one of the biggest PM10 sources in fast-growing Indian "
             "cities."),
    "precautions": [
        "Avoid walking past active construction sites where possible; "
        "take the other side of the road.",
        "Keep windows facing a construction site closed and wet-mop "
        "dust that settles indoors.",
        "Wear a mask on dusty stretches — even a basic mask helps "
        "against coarse dust.",
        "Report uncovered construction debris through the Community "
        "page's Report Local Pollution tool.",
    ],
}

# --- Traffic intelligence (time-based only, no invented data) --------------

TRAFFIC_INFO = {
    "note": ("SwachhVayu AI does not have live traffic data, so it does "
             "not compare routes or claim a road is congested. The "
             "guidance below is time-based: rush hours are the most "
             "polluted part of the day in almost every Indian city."),
    "rush_hours": "Morning rush: roughly 8–10 AM. Evening rush: roughly "
                  "6–9 PM. Both overlap with the day's pollution peaks.",
    "tips": [
        "Travel before 8 AM or between 11 AM and 4 PM when you can — the "
        "cleanest window on the dashboard shows today's best hour.",
        "Metro and bus travel keeps you out of roadside exhaust and cuts "
        "per-person emissions.",
        "If you must travel at rush hour, wear a mask and prefer routes "
        "away from the busiest roads.",
    ],
}

# --- Pollutant source education --------------------------------------------

SOURCES: dict[str, list[str]] = {
    "PM2.5 (fine particles)": [
        "Vehicle exhaust (especially diesel)",
        "Cooking smoke and biomass burning",
        "Firecrackers and open waste burning",
        "Industrial emissions and power generation",
    ],
    "PM10 (coarse dust)": [
        "Construction and road dust",
        "Dry soil and dust storms",
        "Vehicle tyre and brake wear",
    ],
    "Nitrogen dioxide (NO2)": [
        "Vehicle exhaust — the main urban source",
        "Power plants and industry",
        "Gas cooking (indoors)",
    ],
    "Ozone (O3)": [
        "Forms in sunlight from NO2 and VOCs — a summer, daytime pollutant",
        "Higher on hot, sunny, still days",
    ],
    "Carbon monoxide (CO)": [
        "Incomplete combustion: vehicles, cooking fires, biomass burning",
    ],
    "Sulphur dioxide (SO2)": [
        "Coal burning, industry and power generation",
        "Some diesel vehicles",
    ],
}

SOURCES_NOTE = ("These are POSSIBLE sources for each pollutant, for "
                "education. SwachhVayu AI does not attribute today's "
                "readings to a specific source — that needs measurements "
                "this app does not have.")

# --- Festival guide --------------------------------------------------------

@dataclass
class Festival:
    """Lower-emission, lower-waste ways to celebrate one festival."""

    name: str
    when: str
    ideas: list[str]


FESTIVALS: list[Festival] = [
    Festival(
        name="Diwali",
        when="October / November",
        ideas=[
            "Celebrate with diyas, fairy lights and rangoli instead of "
            "firecrackers.",
            "Gift plants, handmade items or experiences instead of plastic-"
            "wrapped goods.",
            "Share sweets in reusable boxes; avoid single-use packaging.",
            "Keep celebrations outdoors in the daytime, when the air is "
            "usually better than the firecracker-heavy evening.",
        ],
    ),
    Festival(
        name="Holi",
        when="March",
        ideas=[
            "Use natural, dry colours (turmeric, beetroot, flower-based) "
            "instead of chemical powders.",
            "Celebrate with water conservation in mind — dry Holi or a "
            "single bucket per person.",
            "Avoid plastic balloons and water pouches; use reusable "
            "containers.",
        ],
    ),
    Festival(
        name="Ganesh Chaturthi",
        when="August / September",
        ideas=[
            "Choose a clay (shadu mati) idol that dissolves in water "
            "instead of plaster of Paris.",
            "Do a home visarjan in a bucket and reuse the water for plants.",
            "Decorate with flowers and leaves instead of thermocol and "
            "plastic.",
        ],
    ),
    Festival(
        name="Durga Puja",
        when="September / October",
        ideas=[
            "Use clay idols and natural decorations; avoid thermocol.",
            "Walk or take the metro to pandals — it is the cleanest way to "
            "pandal-hop.",
            "Carry a reusable water bottle and avoid single-use cups at "
            "food stalls.",
        ],
    ),
    Festival(
        name="Weddings",
        when="Year-round (peak November–February)",
        ideas=[
            "Choose a venue close to most guests to cut travel emissions.",
            "Plan food quantities carefully and donate leftovers through a "
            "local food-rescue group.",
            "Use real plates and steel glasses instead of disposables; "
            "rent, don't buy, decor.",
            "Skip firecrackers at the baraat — lights and music carry the "
            "celebration.",
        ],
    ),
]

GOVERNMENT_RESOURCES = [
    ("CPCB — National Air Quality Index",
     "https://cpcb.nic.in/national-air-quality-index/",
     "The official Indian AQI bands and health messages."),
    ("SAFAR — System of Air Quality and Weather Forecasting",
     "https://safar.tropmet.res.in/",
     "Official air-quality forecasts for major Indian cities."),
    ("Sameer app (CPCB)",
     "https://play.google.com/store/apps/details?id=com.cpcb.sameer",
     "CPCB's official app for station readings and complaints."),
    ("National Clean Air Programme (NCAP)",
     "https://prana.cpcb.gov.in/",
     "India's national programme to cut particulate pollution."),
]
