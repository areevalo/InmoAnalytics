from dataclasses import dataclass

@dataclass
class Property:
    url: str
    price: int
    municipality: str
    neighborhood: str
    origin: str
    checksum: str
    street: str = None


@dataclass
class PropertyFeatures:
    property: Property = None
    rooms: int = 0
    baths: int = 0
    area: float = 0
    type_of_home: str = None
    pool: bool = False
    garage: bool = False
    energy_calification: str = None
    garden: bool = False
    fitted_wardrobes: bool = False
    air_conditioning: bool = False
    underfloor_heating: bool = False
    heating: bool = False
    terrace: bool = False
    storage_room: bool = False
    ownership_status: str = "Disponible"
    balcony: bool = False
    floor_level: str = None
    elevator: bool = False
    orientation: str = None
    construction_year: str = None