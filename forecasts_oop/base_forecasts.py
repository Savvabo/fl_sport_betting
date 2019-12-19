from abc import ABC, abstractmethod
from storage.mongodb_storage import MongoDBStorage
from helpers.helpers import parse_config
from multiprocessing.pool import ThreadPool
import logging
from functools import reduce
from helpers.downloader_helper import Downloader
import ast
from helpers.helpers import chunkify
logging.basicConfig(format=u'%(filename)s[LINE:%(lineno)d]# %(levelname)-8s [%(asctime)s]  %(message)s',
                    level=logging.DEBUG)
logging.getLogger("requests").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)
logging.getLogger("connectionpool").setLevel(logging.WARNING)


class BaseExchanger(ABC):
    def __init__(self):
        self.mdb = MongoDBStorage()
        self.parsed_forecasts = self.get_parsed_forecasts()
        self.config = parse_config('forecasts')
        self.downloader = Downloader()

    def get_parsed_forecasts(self):
        try:
            parsed_forecasts = self.mdb.get_forecasts(self.__resource_name__)
            return parsed_forecasts
        except AttributeError:
            raise Exception('resource_name was not provided')

    def is_forecast_in_db(self, forecast_id):
        if forecast_id in self.parsed_forecasts:
            return True

    def get_prettify_pages(self, page_numbers, request_data={}):
        pool = ThreadPool(int(self.config['scraping_pool_size']))
        # creating links to selected page
        urls_to_scrape = list(map(self.create_scrape_url, page_numbers))
        # request to pages
        response_pages = list(pool.map(lambda url: self.downloader.get(url, top_proxies=10, **request_data), urls_to_scrape))
        # making prettify_data from response
        pretty_pages = list(map(self.get_prettify_page, response_pages))
        pool.close()
        return pretty_pages

    def scrape_forecasts(self, request_data={}):
        start_page = 1
        all_forecasts = []
        scraping_limit = ast.literal_eval(self.config['scraping_limit'])
        while True:
            # creating list of pages we should to scrape
            end_page = start_page + int(self.config['scraping_pool_size'])
            page_numbers = list(range(start_page, end_page))
            prettify_pages = self.get_prettify_pages(page_numbers, request_data)
            is_last_page = list(filter(self.is_last_page, prettify_pages))
            # get all forecasts on each page
            batch_forecasts = list(map(self.get_forecasts_on_page, prettify_pages))
            # flatting them
            flat_forecasts = reduce(lambda x, y: x + y, batch_forecasts)
            # get uniq forecast id
            forecasts_id = list(map(self.get_forecast_id, flat_forecasts))
            # check them in db already, means we should stop parse because we already parse that page
            in_db_check = list(filter(self.is_forecast_in_db, forecasts_id))
            all_forecasts.extend(flat_forecasts)
            logging.info('scraped {} pages'.format(page_numbers[-1]))
            start_page += len(page_numbers)
            if is_last_page:
                logging.info(f'reached last page, is {page_numbers[-1]}')
                break
            if in_db_check:
                logging.info('Next pages already parsed')
                break
            elif scraping_limit and end_page >= int(self.config['scraping_limit']):
                logging.info('scraping limit is reached')
                break
        logging.info('all pages scraped, scraping finished, found {} forecasts'.format(len(all_forecasts)))
        return all_forecasts

    def parse_forecasts(self, forecasts):
        pool = ThreadPool(int(self.config['parsing_pool_size']))
        chunks = list(chunkify(forecasts, len(forecasts) // 10))
        parsed_forecasts = []
        for n, chunk in enumerate(chunks):
            logging.info('parsed {}/{} forecasts chunks'.format(n+1, len(chunks)))
            parsed_chunk = list(pool.map(self.parse_single_forecast, chunk))
            parsed_forecasts.extend(parsed_chunk)
        pool.close()
        return parsed_forecasts

    @abstractmethod
    def get_prettify_page(self, response):
        pass

    @abstractmethod
    def get_forecast_date(self, forecast):
        pass

    @abstractmethod
    def get_forecast_coefficient(self, forecast, *args, **kwargs):
        pass

    @abstractmethod
    def get_events_outcomes(self, *args, **kwargs):
        pass

    @abstractmethod
    def get_forecast_title(self, forecast):
        pass

    @abstractmethod
    def parse_single_forecast(self, forecast):
        pass


    @abstractmethod
    def get_forecasts_on_page(self, page):
        pass

    @abstractmethod
    def create_scrape_url(self, page_num):
        pass

    @abstractmethod
    def get_forecast_id(self, forecast):
        pass

    @abstractmethod
    def is_last_page(self, page):
        pass

    @abstractmethod
    def get_category(self, *args, **kwargs):
        pass




