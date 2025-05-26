def compare_property_data(prop_stored, features_stored, prop_parsed, features_parsed):
    """
    Compara los datos almacenados y parseados de una propiedad y sus características.
    Devuelve un diccionario con los campos que han cambiado y sus nuevos valores.
    Si cambia algún campo usado para el checksum, lo recalcula.
    """
    changes = {}

    # Campos comparados que afectan al checksum
    checksum_fields = ['floor_level', 'rooms', 'baths', 'area']
    checksum_changed = False

    # Comparar precio
    price_field = 'price'
    stored_value = getattr(prop_stored, price_field, None)
    parsed_value = getattr(prop_parsed, price_field, None)
    if stored_value != parsed_value:
        changes[price_field] = parsed_value
        if field in checksum_fields:
            checksum_changed = True

    # Comparar PropertyFeatures
    if features_stored and features_parsed:
        features_fields = [
            'rooms', 'baths', 'area', 'type_of_home', 'pool', 'garage', 'energy_calification',
            'garden', 'fitted_wardrobes', 'air_conditioning', 'underfloor_heating', 'heating',
            'terrace', 'storage_room', 'ownership_status', 'balcony', 'floor_level', 'elevator',
            'orientation', 'construction_year'
        ]
        for field in features_fields:
            stored_value = getattr(features_stored, field, None)
            parsed_value = getattr(features_parsed, field, None)
            if stored_value != parsed_value:
                changes[field] = parsed_value
                if field in checksum_fields:
                    checksum_changed = True

    # Recalcular checksum si corresponde
    if checksum_changed:
        from scrapers.base_scraper import BaseScraper
        property_data_to_hash = {
            'neighborhood': getattr(prop_parsed, 'neighborhood', None),
            'municipality': getattr(prop_parsed, 'municipality', None),
            'floor_level': getattr(features_parsed, 'floor_level', None),
            'rooms': getattr(features_parsed, 'rooms', None),
            'baths': getattr(features_parsed, 'baths', None),
            'area': getattr(features_parsed, 'area', None),
        }
        checksum = BaseScraper('').generate_property_checksum(property_data_to_hash)
        changes['checksum'] = checksum

    return changes