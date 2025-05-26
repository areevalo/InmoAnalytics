from django.core.management.base import BaseCommand

from database.models import Properties, PropertyFeatures
from scrapers.fotocasa_scraper.fotocasa_scraper import FotocasaScraper, parse_helpers as fotocasa_helpers
from scrapers.idealista_scraper.idealista_scraper import IdealistaScraper, parse_helpers as idealista_helpers
from utils.property_compare import compare_property_data
from django.utils import timezone
from datetime import timedelta

RENEW_SESSION_EVERY = 30  # Renew session every 30 properties

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

        yesterday = timezone.now() - timedelta(days=0)
        for property_obj in Properties.objects.filter(active=True, update_time_stamp__lte=yesterday).order_by('create_time_stamp', 'update_time_stamp'):
            try:
                if property_obj.origin not in sessions:
                    continue
                session_data = sessions[property_obj.origin]
                # Renew session every N properties
                if session_data['session'] is None or session_data['count'] % RENEW_SESSION_EVERY == 0:
                    ok, session, _ = session_data['scraper'].open_browser_with_session(url=property_obj.url)
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

                if response.status_code in [404, 301]:
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

                    # Comparar y actualizar solo los campos modificados
                    changes = compare_property_data(property_obj, features_stored, property_parsed, features_parsed)
                    if changes:
                        for field, value in changes.items():
                            if hasattr(property_obj, field):
                                setattr(property_obj, field, value)
                            elif features_stored and hasattr(features_stored, field):
                                setattr(features_stored, field, value)
                        property_obj.save()
                        if features_stored:
                            features_stored.save()
                        self.stdout.write(f"Property {property_obj.id} updated: {list(changes.keys())}")
                    else:
                        property_obj.save()
                        self.stdout.write(f"Property {property_obj.id} active (no changes)")
            except Exception as e:
                self.stderr.write(f"Error with {getattr(property_obj, 'url', 'unknown')}: {e}")