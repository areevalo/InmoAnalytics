import os
import MySQLdb
import django

# Configurar el entorno Django
# os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'settings')
# django.setup()

from django.conf import settings


class DBConnector:
    def __init__(self, logger):
        self.logger = logger

    def get_connection(self):
        """
        Establece y retorna una conexión a la base de datos.
        """
        try:
            connection = MySQLdb.connect(
                host=settings.DATABASES['default']['HOST'],
                port=int(settings.DATABASES['default']['PORT']),
                user=settings.DATABASES['default']['USER'],
                passwd=settings.DATABASES['default']['PASSWORD'],
                db=settings.DATABASES['default']['NAME']
            )
            # Verificar conexión ejecutando una consulta
            cursor = connection.cursor()
            cursor.execute("SELECT 1")
            cursor.fetchone()
            self.logger.info("Conexión exitosa a la base de datos")
            return connection
        except MySQLdb.Error as e:
            self.logger.error(f"Error al conectar con la base de datos: {e}")
            return None
        except Exception as e:
            self.logger.error(f"Error desconocido al intentar conectar con la base de datos: {e}")
            return None

    def close_connection(self, connection):
        """
        Cierra una conexión activa a la base de datos.
        """
        if connection and connection.is_connected():
            connection.close()
            self.logger.info("Conexión cerrada")