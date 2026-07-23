from __future__ import annotations


OFFICIAL_REGIONS = [
    "Trung du và miền núi phía Bắc",
    "Đồng bằng sông Hồng",
    "Bắc Trung Bộ",
    "Nam Trung Bộ",
    "Đông Nam Bộ",
    "Đồng bằng sông Cửu Long",
]

LOCATION_VIETNAMESE = {
    "Buon Ma Thuot": "Buôn Ma Thuột",
    "Ca Mau": "Cà Mau",
    "Can Tho": "Cần Thơ",
    "Chau Doc": "Châu Đốc",
    "Da Lat": "Đà Lạt",
    "Da Nang": "Đà Nẵng",
    "Dien Bien Phu": "Điện Biên Phủ",
    "Dong Hoi": "Đồng Hới",
    "Ha Noi": "Hà Nội",
    "Hai Phong": "Hải Phòng",
    "Ho Chi Minh City": "TP. Hồ Chí Minh",
    "Hue": "Huế",
    "Lao Cai": "Lào Cai",
    "Nha Trang": "Nha Trang",
    "Phan Rang-Thap Cham": "Phan Rang - Tháp Chàm",
    "Phu Quoc": "Phú Quốc",
    "Pleiku": "Pleiku",
    "Quy Nhon": "Quy Nhơn",
    "Vinh": "Vinh",
    "Vung Tau": "Vũng Tàu",
}

LOCATIONS_BY_REGION = {
    "Trung du và miền núi phía Bắc": ["Dien Bien Phu", "Lao Cai"],
    "Đồng bằng sông Hồng": ["Ha Noi", "Hai Phong"],
    "Bắc Trung Bộ": ["Dong Hoi", "Hue", "Vinh"],
    "Nam Trung Bộ": [
        "Buon Ma Thuot",
        "Da Lat",
        "Da Nang",
        "Nha Trang",
        "Phan Rang-Thap Cham",
        "Pleiku",
        "Quy Nhon",
    ],
    "Đông Nam Bộ": ["Ho Chi Minh City", "Vung Tau"],
    "Đồng bằng sông Cửu Long": [
        "Ca Mau",
        "Can Tho",
        "Chau Doc",
        "Phu Quoc",
    ],
}

LOCATION_TO_REGION = {
    location: region
    for region, locations in LOCATIONS_BY_REGION.items()
    for location in locations
}

