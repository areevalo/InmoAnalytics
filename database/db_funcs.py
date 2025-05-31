import os
import django

from django.db import transaction, close_old_connections, connection, IntegrityError
from scrapers.constants import PROP_FIELDS, FEATURES_FIELDS

# Configurar DJANGO_SETTINGS_MODULE
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'inmoanalytics.settings')

# Inicializar Django
django.setup()

from database.models import Properties, PropertyFeatures

batch = []
BATCH_SIZE = 30
MAX_RETRIES = 10
MAX_CONNECTION_RETRIES = 3

def update_fields(obj, data, fields):
    """Actualiza los campos de un objeto (Property o PropertyFeatures) en caso de diferencia con otro objeto comparado
    y cuyo valor no es None"""
    updated = False
    for field in fields:
        new_value = getattr(data, field, None)
        if getattr(obj, field, None) != new_value and new_value is not None:
            setattr(obj, field, new_value)
            updated = True
    return updated

def add_to_batch(properties_data, logger):
    """Agrega datos al lote y realiza inserciones cuando se alcanza el tamaño establecido en BATCH_SIZE"""
    global batch
    connection_retries = 0
    while connection_retries < MAX_CONNECTION_RETRIES:
        try:
            close_old_connections()  # Cierra conexiones antiguas antes de interactuar con la base de datos
            # Eliminar duplicados en el propio listado (por checksum)
            unique_properties_data = {p.property.checksum: p for p in properties_data}.values()
            properties_to_insert = []
            for p_data in unique_properties_data:
                try:
                    prop = Properties.objects.get(checksum=p_data.property.checksum)
                    if not prop.active:
                        # Si la propiedad existe pero está desactivada, eliminar la antigua inactiva y añadir la nueva
                        prop.delete()
                        properties_to_insert.append(p_data)
                        logger.info(f"Propiedad inactiva con checksum duplicado eliminada y nueva añadida: {p_data.property.checksum}")
                    else:
                        if prop.origin == p_data.property.origin:
                            # Si la propiedad ya existe con el mismo origen, se actualizan los campos necesarios
                            # en caso de que haya cambios
                            try:
                                features = PropertyFeatures.objects.get(property=prop)
                            except PropertyFeatures.DoesNotExist:
                                features = None

                            updated = update_fields(prop, p_data.property, PROP_FIELDS)
                            if features:
                                updated |= update_fields(features, p_data, FEATURES_FIELDS)
                            else:
                                # Si la propiedad no tiene vinculadas características, se crean los registros desde cero
                                PropertyFeatures.objects.create(
                                    property=prop,
                                    **{field: getattr(p_data, field, None) for field in FEATURES_FIELDS}
                                )
                                updated = True

                            if updated:
                                prop.save()
                                if features:
                                    features.save()
                                logger.info(f"Propiedad y/o características con checksum {p_data.property.checksum} actualizadas en BD.")
                            else:
                                logger.info(f"Propiedad con checksum {p_data.property.checksum} ya está actualizada. No se realizaron cambios.")
                        else:
                            # Si la propiedad ya existe pero con origen diferente, se omite la revisión y actualización de características
                            logger.info(f"Propiedad con checksum {p_data.property.checksum} ya existe con origen diferente.")

                except Properties.DoesNotExist:
                    # No existe la propiedad en BD, se añade para insertar
                    properties_to_insert.append(p_data)
                except Exception as e:
                    logger.error(f"Error procesando datos para la propiedad con checksum '{p_data.property.checksum}': "
                                 f"{e}")

            break
        except Exception as e:
            logger.error(f"Error al conectar con la base de datos: {e}. Reintentando...")
            connection_retries+=1
            connection.close()

    batch.extend(properties_to_insert)
    logger.info(f"Se han agregado {len(properties_to_insert)} nuevas propiedades al lote para la inserción.")
    # Si el lote alcanza el tamaño establecido, se intenta insertar en la BD
    if len(batch) >= BATCH_SIZE:
        retries = 0
        while retries < MAX_RETRIES:
            # Se realizan un número de reintentos para insertar el lote en la BD (MAX_RETRIES)
            try:
                ok, batch = insert_properties_and_features(batch, logger)
                if ok:
                    batch.clear()
                    break
            except Exception as e:
                logger.error(f"Error al insertar el lote en la base de datos: {e}. Reintentando...")
                connection.close()
                retries += 1
                if retries >= MAX_RETRIES:
                    logger.error("Se alcanzó el número máximo de reintentos. Abortando operación de inserción...")
                    break



def insert_properties_and_features(properties_data, logger):
    """Inserta un lote de propiedades y sus características en la BD
    de manera transaccional para evitar inconsistencias"""
    try:
        with transaction.atomic():
            for ix, p in enumerate(properties_data):
                # Insertar datos en la tabla properties
                property_obj = Properties.objects.create(
                    url=p.property.url,
                    price=p.property.price,
                    municipality=p.property.municipality,
                    neighborhood=p.property.neighborhood,
                    street=p.property.street,
                    origin=p.property.origin,
                    checksum=p.property.checksum
                )

                # Insertar datos en la tabla property_features
                PropertyFeatures.objects.create(
                    property_id=property_obj.id,
                    rooms=p.rooms,
                    baths=p.baths,
                    area=p.area,
                    type_of_home=p.type_of_home,
                    pool=p.pool,
                    garage=p.garage,
                    energy_calification=p.energy_calification,
                    garden=p.garden,
                    fitted_wardrobes=p.fitted_wardrobes,
                    air_conditioning=p.air_conditioning,
                    underfloor_heating=p.underfloor_heating,
                    heating=p.heating,
                    terrace=p.terrace,
                    storage_room=p.storage_room,
                    ownership_status=p.ownership_status,
                    balcony=p.balcony,
                    floor_level=p.floor_level,
                    elevator=p.elevator,
                    orientation=p.orientation,
                    construction_year=p.construction_year
                )

        logger.info(f"{len(properties_data)} propiedades y características insertadas correctamente.")
        return True, properties_data

    except IntegrityError as e:
        if "Duplicate entry" in str(e):
            # En caso de detectar intento de inserción de un checksum duplicado, quitar propiedad del listado y
            # devolver de nuevo el listado entero para insertar el resto de propiedades
            properties_data.pop(ix)
            logger.error(f"Error al insertar propiedades por duplicidad de una de ellas. "
                         f"Eliminada del lote y devuelto para posterior reintento: {properties_data[ix]}")
            return False, properties_data
        else:
            logger.error(f"Error al insertar el lote de propiedades y sus características. Excepción: {e}")
            return False, properties_data
    except Exception as e:
        logger.error(f"Error al insertar el lote de propiedades y sus características. Excepción: {e}")
        connection.close()
        return False, properties_data