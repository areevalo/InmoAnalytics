import concurrent.futures

from scrapers.idealista_scraper.idealista_scraper import IdealistaScraper
from scrapers.fotocasa_scraper.fotocasa_scraper import FotocasaScraper


class MainLauncher:
    def __init__(self):
        self.scrapers = [FotocasaScraper()] # IdealistaScraper(),

    def run_all_scrapers(self):
        with concurrent.futures.ThreadPoolExecutor(max_workers=len(self.scrapers)) as executor:
            executor.map(lambda scraper: scraper.scrape(), self.scrapers)

# Ejecución del launcher
if __name__ == "__main__":
    launcher = MainLauncher()
    launcher.run_all_scrapers()