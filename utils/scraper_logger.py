# import logging
# from datetime import datetime
# import os
#
# class ScraperLogger:
#     def __init__(self, name):
#         self.logger = logging.getLogger(name)
#         self.logger.setLevel(logging.INFO)
#
#         if not os.path.exists('logs'):
#             os.makedirs('logs')
#
#         timestamp = datetime.now().strftime("%d-%m-%Y__%H-%M-%S")
#         log_filename = f'logs/scraper__{timestamp}.log'
#
#         handler = logging.FileHandler(log_filename)
#         formatter = logging.Formatter('%(asctime)s-%(name)s-%(levelname)s-%(message)s')
#         handler.setFormatter(formatter)
#
#         self.logger.addHandler(handler)
import logging
from datetime import datetime
import os
import sys


class ScraperLogger:
    def __init__(self, name):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.INFO)

        # Evitar duplicación de logs si ya hay handlers
        if not self.logger.handlers:
            # Crear directorio de logs si no existe
            if not os.path.exists('logs'):
                os.makedirs('logs')

            # Formato de timestamp para el nombre del archivo
            timestamp = datetime.now().strftime("%d-%m-%Y__%H-%M-%S")
            log_filename = f'logs/scraper__{timestamp}.log'

            # Configurar formato personalizado (solo hora:minutos:segundos)
            formatter = logging.Formatter('%(asctime)s - %(name)s:%(levelname)s: %(message)s', datefmt='%H:%M:%S')

            # Handler para archivo
            file_handler = logging.FileHandler(log_filename)
            file_handler.setFormatter(formatter)
            self.logger.addHandler(file_handler)

            # Handler para consola
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setFormatter(formatter)
            self.logger.addHandler(console_handler)
