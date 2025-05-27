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

RENEW_SESSION_EVERY = 50  # Renew session every 50 properties

class Command(BaseCommand):
    help = "Verifica si las viviendas siguen activas y actualiza cambios"

    def handle(self, *args, **kwargs):
        """
        Recorre todas las propiedades, verifica si siguen activas y actualiza los campos modificados.
        """
        idealista_scraper = IdealistaScraper()
        fotocasa_scraper = FotocasaScraper()
        sessions = {
            'Idealista': {'scraper': idealista_scraper, 'session': None, 'count': 0},
            'Fotocasa': {'scraper': fotocasa_scraper, 'session': None, 'count': 0},
        }

        # Obtener las propiedades activas que necesitan ser verificadas (no actualizadas hace 3 días o más)
        yesterday = timezone.now() - timedelta(days=1)
        # TODO: cambiar a 3 días cuando se llegue a producción
        # yesterday = timezone.now() - timedelta(days=3)
        for property_obj in Properties.objects.filter(active=True, update_time_stamp__lte=yesterday).order_by('update_time_stamp', 'create_time_stamp'):
            try:
                if property_obj.origin not in sessions:
                    continue
                session_data = sessions[property_obj.origin]
                # Renew session every N properties
                if session_data['session'] is None or session_data['count'] % RENEW_SESSION_EVERY == 0:
                    cookies = extract_cookies_from_session(session) if session_data['session'] else None
                    ok, session, _ = session_data['scraper'].open_browser_with_session(
                        session=session_data['session'],
                        cookies=cookies,
                        url=property_obj.url
                    )
                    if not ok:
                        self.stderr.write(f"Could not open session for {property_obj.origin}")
                        continue
                    session_data['session'] = session
                session_data['count'] += 1

                response = session_data['session'].get(
                    url=property_obj.url,
                    headers=session_data['scraper'].req_headers
                )
                # TODO: controlar error en la petición HTTP (403)

                if response.status_code in [404, 301] or "propertyNotFound" in response.url:
                    property_obj.active = False
                    property_obj.save()
                    self.stdout.write(f"Property {property_obj.id} set as inactive")
                else:
                    property_obj.active = True
                    if property_obj.origin == 'Idealista':
                        features_parsed = idealista_helpers.get_property_data(
                            response.content, session_data['scraper'].logger
                        )
                        property_parsed = features_parsed.property
                    elif property_obj.origin == 'Fotocasa':
                        property_parsed, features_parsed = fotocasa_helpers.get_property_data(
                            response.content, property_obj, session_data['scraper'].logger
                        )
                        property_parsed = session_data['scraper'].normalize_data(property_parsed)

                    try:
                        features_stored = PropertyFeatures.objects.get(property=property_obj)
                    except PropertyFeatures.DoesNotExist:
                        features_stored = None

                    # Inicializar valor a False para verificar si se modifica alguna característica para hacer 'save'
                    some_feature_changed = False
                    # Comparar y actualizar solo los campos modificados
                    changes = compare_property_data(property_obj, features_stored, property_parsed, features_parsed)
                    if changes:
                        for field, value in changes.items():
                            if hasattr(property_obj, field):
                                if field == 'checksum':
                                    old_checksum = getattr(property_obj, field)
                                setattr(property_obj, field, value)
                            elif features_stored and hasattr(features_stored, field):
                                setattr(features_stored, field, value)
                                some_feature_changed = True
                        property_obj.save()
                        if features_stored and some_feature_changed:
                            features_stored.save()
                            self.stdout.write(f"Property {property_obj.id} and features updated: {list(changes.keys())}")
                        else:
                            self.stdout.write(f"Property {property_obj.id} updated: {list(changes.keys())}")
                    else:
                        property_obj.save()
                        self.stdout.write(f"Property {property_obj.id} active (no changes)")
                time.sleep(0.5 + 1 * random.random())  # To avoid hitting the server too hard
            except IntegrityError as e:
                self.stderr.write(f"Error with {getattr(property_obj, 'url', 'unknown')}: checksum already saved: {e}")
                property_obj.active = False
                try:
                    setattr(property_obj, 'checksum', old_checksum)
                    property_obj.save()
                except Exception as e:
                    self.stderr.write(f"Error saving inactive property with old checksum: {getattr(property_obj, 'url', 'unknown')}: {e}")
                self.stdout.write(f"Property {property_obj.id} set as inactive due to duplicated checksum (property already exists)")
            except Exception as e:
                self.stderr.write(f"Error with {getattr(property_obj, 'url', 'unknown')}: {e}")