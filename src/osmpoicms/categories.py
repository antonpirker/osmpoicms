CATEGORIES: list[tuple[str, str]] = [
    ("restaurants", "Restaurants"),
    ("huts", "Mountain Huts"),
    ("bars", "Bars & Nightlife"),
    ("hotels", "Hotels"),
    ("doctors", "Doctors"),
    ("pharmacies", "Pharmacies"),
    ("supermarkets", "Supermarkets"),
    ("shopping", "Shopping"),
    ("banks", "Banks & ATMs"),
    ("leisure", "Leisure"),
]

CATEGORY_TAGS: dict[str, list[tuple[str, str]]] = {
    "restaurants": [
        ("amenity", "restaurant"),
        ("amenity", "cafe"),
        ("amenity", "fast_food"),
    ],
    "huts": [
        ("tourism", "alpine_hut"),
        ("tourism", "wilderness_hut"),
        ("amenity", "shelter"),
    ],
    "bars": [
        ("amenity", "bar"),
        ("amenity", "pub"),
        ("amenity", "nightclub"),
        ("amenity", "biergarten"),
    ],
    "hotels": [
        ("tourism", "hotel"),
        ("tourism", "hostel"),
        ("tourism", "guest_house"),
        ("tourism", "motel"),
    ],
    "doctors": [
        ("amenity", "doctors"),
        ("amenity", "clinic"),
        ("healthcare", "doctor"),
    ],
    "pharmacies": [
        ("amenity", "pharmacy"),
    ],
    "supermarkets": [
        ("shop", "supermarket"),
        ("shop", "convenience"),
    ],
    "shopping": [
        ("shop", "clothes"),
        ("shop", "sports"),
        ("shop", "shoes"),
        ("shop", "electronics"),
        ("shop", "gift"),
        ("shop", "toys"),
        ("shop", "books"),
        ("shop", "department_store"),
    ],
    "banks": [
        ("amenity", "bank"),
        ("amenity", "atm"),
    ],
    "leisure": [
        ("leisure", "park"),
        ("leisure", "swimming_pool"),
        ("leisure", "water_park"),
        ("amenity", "public_bath"),
        ("leisure", "sports_centre"),
        ("leisure", "fitness_centre"),
        ("leisure", "tennis"),
        ("leisure", "playground"),
        ("amenity", "theatre"),
        ("amenity", "cinema"),
        ("tourism", "museum"),
    ],
}

_COMMON_COLUMNS: list[tuple[str, str]] = [
    ("name", "Name"),
    ("addr:street", "Street"),
    ("addr:housenumber", "No."),
    ("phone", "Phone"),
    ("website", "Website"),
    ("opening_hours", "Opening Hours"),
]

_EXTRA_COLUMNS: dict[str, list[tuple[str, str]]] = {
    "restaurants": [("cuisine", "Cuisine")],
    "huts": [("ele", "Elevation (m)")],
    "hotels": [("stars", "Stars"), ("rooms", "Rooms")],
    "doctors": [("healthcare:speciality", "Speciality")],
    "banks": [("operator", "Operator")],
    "leisure": [("access", "Access")],
}


def get_columns(category: str) -> list[tuple[str, str]]:
    return _COMMON_COLUMNS + _EXTRA_COLUMNS.get(category, [])
