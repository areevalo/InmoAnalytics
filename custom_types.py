from dataclasses import dataclass

@dataclass
class Property:
    url: str
    price: int
    municipality: str
    neighborhood: str
    origin: str
    checksum: str
    street: str = "NS/NC"


@dataclass
class PropertyFeatures:
    property: Property = None
    rooms: int = 0
    baths: int = 0
    area: float = 0
    type_of_home: str = "NS/NC"
    pool: bool = False
    garage: bool = False
    energy_calification: str = "NS/NC"
    garden: bool = False
    fitted_wardrobes: bool = False
    air_conditioning: bool = False
    underfloor_heating: bool = False
    heating: bool = False
    terrace: bool = False
    storage_room: bool = False
    ownership_status: str = "Disponible"
    balcony: bool = False
    floor_level: str = "NS/NC"
    elevator: bool = False
    orientation: str = "NS/NC"
    construction_year: str = "NS/NC"