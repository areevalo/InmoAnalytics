from scrapers.idealista_scraper.idealista_scraper import IdealistaScraper


class MainLauncher:
    def __init__(self):
        self.scrapers = [IdealistaScraper()]#, FotocasaScraper()]

    def run_all_scrapers(self):
        # TODO: añadir concurrencia
        for scraper in self.scrapers:
            scraper.scrape()

# Ejecución del launcher
if __name__ == "__main__":
    launcher = MainLauncher()
    launcher.run_all_scrapers()