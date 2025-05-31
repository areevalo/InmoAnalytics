import random
import time
from django.core.management.base import BaseCommand
from django.db import IntegrityError

from database.models import Properties, PropertyFeatures
from scrapers.base_scraper import BaseScraper, extract_cookies_from_session
from scrapers.fotocasa_scraper.fotocasa_scraper import FotocasaScraper, parse_helpers as fotocasa_helpers
from scrapers.idealista_scraper.idealista_scraper import IdealistaScraper, parse_helpers as idealista_helpers
from utils.property_compare import compare_property_data
from django.utils import timezone
from datetime import timedelta

RENEW_SESSION_EVERY = 30  # Renueva la sesión cada X propiedades procesadas de un mismo origen para evitar bloqueos
DAYS_FOR_VERIFICATION = 3  # Días desde la última actualización para verificar si la propiedad sigue activa

class Command(BaseCommand):
    help = "Verifica si las viviendas siguen activas y actualiza cambios"

    def handle(self, *args, **kwargs):
        """Recorre todas las propiedades, verifica si siguen activas y actualiza los campos modificados"""
        idealista_scraper = IdealistaScraper()
        fotocasa_scraper = FotocasaScraper()
        # Diccionario para gestionar las sesiones y contadores de uso por portal
        sessions = {
            'Idealista': {'scraper': idealista_scraper, 'session': None, 'count': 0},
            'Fotocasa': {'scraper': fotocasa_scraper, 'session': None, 'count': 0},
        }

        verification_limit_date = timezone.now() - timedelta(days=DAYS_FOR_VERIFICATION)
        # Obtener las propiedades activas que necesitan ser verificadas (no actualizadas hace 3 días o más)
        # Se ordenan por fecha de actualización y luego por fecha de creación para procesar primero las más antiguas.
        for property_obj in Properties.objects.filter(active=True, update_time_stamp__lte=verification_limit_date).order_by('update_time_stamp', 'create_time_stamp'):
            resp_content = None
            old_checksum = None
            try:
                session_data = sessions[property_obj.origin]
                # Crea la sesión o la renueva si es necesario
                if session_data['session'] is None or session_data['count'] % RENEW_SESSION_EVERY == 0:
                    cookies = extract_cookies_from_session(session_data['session']) if session_data['session'] else None
                    # Intento inicial de abrir/renovar sesión
                    ok, session, _ = session_data['scraper'].open_browser_with_session(
                        session=session_data['session'],
                        cookies=cookies,
                        url=property_obj.url
                    )
                    if not ok:
                        # Si falla el primer intento por bloqueo del portal, se reintenta con una nueva sesión
                        self.stderr.write(f"No ha sido posible obtener la sesión en {property_obj.origin}. "
                                          f"Creando nueva sesión...")
                        ok, session, _ = session_data['scraper'].open_browser_with_session(
                            url=property_obj.url
                        )
                    session_data['session'] = session
                    time.sleep(6)
                session_data['count'] += 1

                response = session_data['session'].get(
                    url=property_obj.url,
                    headers=session_data['scraper'].req_headers
                )
                if response.status_code == 403:
                    self.stderr.write(f"Acceso denegado a {property_obj.url}. Reintentando con Playwright...")
                    cookies = extract_cookies_from_session(session) if session_data['session'] else None
                    ok, session, resp_content = session_data['scraper'].open_browser_with_session(
                        session=session_data['session'],
                        cookies=cookies,
                        url=property_obj.url
                    )
                    if not ok:
                        ok, session, _ = session_data['scraper'].open_browser_with_session(
                            url=property_obj.url
                        )

                # Comprobación de si la propiedad ya no existe (404)
                if response.status_code == 404 or "propertyNotFound" in response.url:
                    property_obj.active = False
                    property_obj.save()
                    self.stdout.write(f"Propiedad {property_obj.id} marcada como inactiva")
                else:
                    resp_content = response.content if response.status_code == 200 else resp_content
                    property_obj.active = True

                    # Parseo de los datos de la propiedad según su portal de origen
                    if property_obj.origin == 'Idealista':
                        features_parsed = idealista_helpers.get_property_data(
                            resp_content, session_data['scraper'].logger
                        )
                        if not features_parsed:
                            self.stderr.write(f"No ha sido posible obtener los datos de la propiedad en "
                                              f"{property_obj.url}. Pasando a la siguiente...")
                            continue
                        property_parsed = features_parsed.property
                    elif property_obj.origin == 'Fotocasa':
                        property_parsed, features_parsed = fotocasa_helpers.get_property_data(
                            resp_content, property_obj, session_data['scraper'].logger
                        )
                        if not property_parsed or not features_parsed:
                            self.stderr.write(f"No ha sido posible obtener los datos de la propiedad en"
                                              f" {property_obj.url}. Pasando a la siguiente...")
                            continue
                        property_parsed = session_data['scraper'].normalize_data(property_parsed)
                    else:
                        self.stderr.write(f"Origen desconocido '{property_obj.origin}' para parseo. "
                                          f"Pasando a la siguiente...")
                        continue

                    try:
                        features_stored = PropertyFeatures.objects.get(property=property_obj)
                    except PropertyFeatures.DoesNotExist:
                        features_stored = None # No debería entrar por aquí, pero por si acaso

                    # Inicializar valor a False para verificar si se modifica alguna característica para hacer 'save'
                    some_feature_changed = False
                    # Comparar y actualizar solo los campos modificados
                    changes = compare_property_data(property_obj, features_stored, property_parsed, features_parsed)
                    if changes:
                        for field, value in changes.items():
                            if hasattr(property_obj, field):
                                if field == 'checksum':
                                    # Guardar el checksum antiguo antes de sobreescribirlo
                                    old_checksum = getattr(property_obj, field)
                                setattr(property_obj, field, value)
                            elif features_stored and hasattr(features_stored, field):
                                setattr(features_stored, field, value)
                                some_feature_changed = True
                        property_obj.save()
                        if features_stored and some_feature_changed:
                            features_stored.save()
                            self.stdout.write(f"Propiedad {property_obj.id} y sus características actualizadas: "
                                              f"{list(changes.keys())}")
                        else:
                            self.stdout.write(f"Propiedad {property_obj.id} actualizada: {list(changes.keys())}")
                    else:
                        # Aunque no haya cambios en los datos parseados, se guarda para actualizar 'update_time_stamp'
                        property_obj.save()
                        self.stdout.write(f"Propiedad {property_obj.id} activa (sin cambios detectados)")
                time.sleep(2.5 + 1 * random.random())  # Pausa para evitar bloqueos por scraping excesivo
            except IntegrityError as e:
                # Este error ocurre si se intenta guardar un 'checksum' que ya existe para otra propiedad,
                # indicando una duplicación de la misma propiedad
                self.stderr.write(f"Error con {getattr(property_obj, 'url', 'desconocido')}: checksum ya almacenado: {e}")
                property_obj.active = False
                try:
                    if old_checksum: # Revertir al checksum original si se había modificado
                        setattr(property_obj, 'checksum', old_checksum)
                    property_obj.save()
                except Exception as e:
                    self.stderr.write(f"Error guardando propiedad inactiva con checksum antiguo: "
                                      f"{getattr(property_obj, 'url', 'desconocido')}: {e}")
                self.stdout.write(f"Propiedad {property_obj.id} marcada como inactiva por duplicidad de propiedad "
                                  f"(checksum ya existe en BD)")
            except Exception as e:
                self.stderr.write(f"Error con {getattr(property_obj, 'url', 'desconocido')}: {e}")
        else:
            self.stdout.write("Verificación de propiedades completada. Fin de proceso")
