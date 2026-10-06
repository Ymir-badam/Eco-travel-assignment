"""
08 - Carbon footprint estimation.

Uses a local emission-factor table rather than a paid API, so it never
fails and needs no key. THESE FIGURES ARE ROUNDED, ILLUSTRATIVE
AVERAGES (loosely based on published grams-CO2e-per-passenger-km ranges,
e.g. UK DESNZ/DEFRA conversion factors) - before using them anywhere
that matters, swap in figures from a citable, dated source. Numbers are
always reported to sensible precision (nearest whole kg, "about") rather
than implying an accuracy the data doesn't have.
"""

# grams of CO2e per passenger-km
EMISSION_FACTORS = {
    "walk": 0,
    "cycle": 0,
    "train": 35,
    "coach": 27,
    "electric_car": 50,
    "car_petrol": 170,
    "ferry": 115,
    "flight_short": 250,
    "flight_long": 150,
}

VEHICLE_LABELS = {
    "walk": "Walking",
    "cycle": "Cycling",
    "train": "Train",
    "coach": "Coach / long-distance bus",
    "electric_car": "Electric car",
    "car_petrol": "Petrol car",
    "ferry": "Ferry",
    "flight_short": "Short-haul flight",
    "flight_long": "Long-haul flight",
}


def estimate_kg(vehicle_type, distance_km):
    """Rough kg CO2e for one leg. Raises KeyError for an unknown mode."""
    grams = EMISSION_FACTORS[vehicle_type] * float(distance_km)
    return grams / 1000.0


def compare_modes(distance_km, modes=None):
    """Rank a shortlist of modes best-first for a given distance."""
    modes = modes or ["train", "coach", "car_petrol", "flight_short"]
    results = [(m, estimate_kg(m, distance_km)) for m in modes]
    return sorted(results, key=lambda pair: pair[1])


def emission_band(kg_co2e):
    if kg_co2e <= 20:
        return "low"
    if kg_co2e <= 100:
        return "medium"
    return "high"
