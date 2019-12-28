from abc import ABC, abstractmethod
from storage.mongodb_storage import MongoDBStorage
from helpers.helpers import parse_config
from multiprocessing.pool import ThreadPool
import logging
from functools import reduce
from helpers.downloader_helper import Downloader
import ast
from helpers.helpers import chunkify
import hashlib
import time
import datetime


class BaseExchanger(ABC):
    def __init__(self):
        self.mdb = MongoDBStorage()
        self.parsed_forecasts = self.get_parsed_forecasts()
        self.config = parse_config('forecasts')
        try:
            check_url = 'https://' + self.__resource_name__
        except:
            check_url = 'https://www.google.com'
        self.downloader = Downloader(check_url, attempts=20, use_proxy=True)
        self.request_data = {}

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
        response_pages = list(pool.map(lambda url: self.downloader.get(url, **request_data), urls_to_scrape))
        # making prettify_data from response
        pretty_pages = list(map(self.get_prettify_page, response_pages))
        pool.close()
        return pretty_pages

    def forecast_too_old(self, date, scraping_date_limit):
        if scraping_date_limit and date:
            date_limit = datetime.datetime.now() - datetime.timedelta(days=scraping_date_limit)
            date_limit_timestamp = date_limit.timestamp()
            if date < date_limit_timestamp:
                return True

    def scrape_forecasts(self, request_data={}):
        start_page = 1
        all_forecasts = []
        scraping_page_limit = ast.literal_eval(self.config['scraping_page_limit'])
        scraping_date_limit = ast.literal_eval(self.config['scraping_date_limit'])
        while True:
            # creating list of pages we should to scrape
            end_page = start_page + int(self.config['scraping_pool_size'])
            page_numbers = list(range(start_page, end_page))
            prettify_pages = self.get_prettify_pages(page_numbers, request_data)
            is_need_to_reparse = list(filter(self.is_need_to_reparse, prettify_pages))
            if is_need_to_reparse:
                logging.info('received reparse bug')
                time.sleep(90)
                self.login()
                continue
            is_last_page = list(filter(self.is_last_page, prettify_pages))
            # get all forecasts on each page
            batch_forecasts = list(map(self.get_forecasts_on_page, prettify_pages))
            # flatting them
            flat_forecasts = reduce(lambda x, y: x + y, batch_forecasts)
            # get uniq forecast id
            forecasts_id = list(map(self.get_forecast_id, flat_forecasts))
            # check them in db already, means we should stop parse because we already parse that page
            in_db_check = list(filter(self.is_forecast_in_db, forecasts_id))
            # check if date_limit
            over_dates = list(filter(lambda date: self.forecast_too_old(date, scraping_date_limit),
                                list(map(self.get_forecast_date, flat_forecasts))))
            all_forecasts.extend(flat_forecasts)
            logging.info('scraped {} pages'.format(page_numbers[-1]))
            start_page += len(page_numbers)
            if is_last_page:
                logging.info(f'reached last page, is {page_numbers[-1]}')
                break
            if in_db_check:
                logging.info('Next pages already parsed')
                break
            elif scraping_page_limit and end_page >= int(scraping_page_limit):
                logging.info('scraping page limit is reached')
                break
            elif over_dates:
                logging.info('scraping date limit is reached')
                break
        logging.info('all pages scraped, scraping finished, found {} forecasts'.format(len(all_forecasts)))
        return all_forecasts

    def parse_forecasts(self, forecasts):
        pool = ThreadPool(int(self.config['parsing_pool_size']))
        chunks = list(chunkify(forecasts, int(self.config['parsing_pool_size'])))
        for n, chunk in enumerate(chunks):
            logging.info('parsed {}/{} forecasts chunks'.format(n+1, len(chunks)))
            parsed_chunk = [forecast for forecast in list(pool.map(self.parse_single_forecast, chunk)) if forecast is not None]
            self.mdb.add_new_forecasts(parsed_chunk)
        pool.close()
        logging.info('parsing finished')


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
    def is_last_page(self, page):
        pass

    @abstractmethod
    def get_category(self, *args, **kwargs):
        pass

    @abstractmethod
    def get_forecast_link(self, forecast):
        pass

    def get_forecast_id(self, forecast):
        link = self.get_forecast_link(forecast)
        _id = hashlib.md5(link.encode()).hexdigest()
        return _id

    @abstractmethod
    def is_need_to_reparse(self, soup):
        pass

    def login(self):
        pass

    def solve_robot(self):
        pass
