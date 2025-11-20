import asyncio
import random
from src.scraper import FunPayScraper
from src.utils.csvgen import CSVGenerator


async def main():
    scraper = FunPayScraper(currency='usd')
    try:
        categories = await scraper.get_categories()
        random_subcategory_url = str(random.choice(random.choice(categories).subcategories).url)
        
        offers = await scraper.get_offers(url=random_subcategory_url)
        CSVGenerator.save_to_file(offers, "offers.csv")
    finally:
        await scraper.session_close()
  

if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    loop.run_until_complete(main())
