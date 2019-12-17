from storage.mongodb_storage import MongoDBStorage
from abc import ABC
from bs4 import BeautifulSoup
from forecasts_oop.base_forecasts import BaseExchanger
import logging
from storage.mongodb_storage import Forecast
import pytz
import datetime
import re


class StavkaTV(BaseExchanger, ABC):
    def __init__(self):
        self.__resource_name__ = 'stavka.tv'
        self.domain = 'https://stavka.tv'
        super().__init__()

    def create_scrape_url(self, page_num):
        pattern = '{}/predictions?page={}'
        return pattern.format(self.domain, page_num)

    def get_prettify_page(self, response):
        return BeautifulSoup(response.text, 'lxml')

    def get_forecasts_on_page(self, page):
        expected_count = 20
        forecasts = page.find_all('div', class_='Predictions__item')
        if len(forecasts) != expected_count:
            logging.warning('received {} forecasts, but expected {}'.format(len(forecasts), expected_count))
        return forecasts

    def get_forecast_id(self, forecast):
        return self.domain + forecast.a['href']

    def get_forecast_title(self, forecast):
        return forecast.find('div', class_='Prediction__header-name').text.strip()

    def get_forecast_coefficient(self, forecast):
        return forecast.find_all('em', class_='PredictionContent__bet-text--em')[1].text.strip()

    def get_event_outcomes(self, forecast):
        return [forecast.find_all('em', class_='PredictionContent__bet-text--em')[0].text.strip()]

    def get_forecast_date(self, forecast):
        date_string = forecast.find('b', class_='PredictionContent__date-bold').text.strip()
        month_dict = {'января': 1, 'февраля': 2, 'марта': 3, 'апреля': 4, 'мая': 5,
                      'июня': 6, 'июля': 7, 'августа': 8, 'сентября': 9, 'октября': 10,
                      'ноября': 11, 'декабря': 12}
        now = datetime.datetime.now()
        all_int = re.findall('\d{1,2}', date_string)
        current_day = all_int[0]
        current_minutes = all_int[2]
        current_hours = all_int[1]
        current_month = 1
        for month, month_index in month_dict.items():
            if month in date_string:
                current_month = month_index
        event_time = now.replace(minute=int(current_minutes), hour=int(current_hours), month=int(current_month),
                                 day=int(current_day))
        pytz.timezone("Europe/London").localize(event_time)
        event_timestamp = int(event_time.timestamp())
        return event_timestamp

    @staticmethod
    def get_forecast_logos(soup):
        raw_logos = soup.find_all('img', class_='UMatchTeam__image')
        if not raw_logos:
            raw_logos = soup.find_all('img', class_='PredictHeader__img')
        return [img['src'] for img in raw_logos]

    @staticmethod
    def get_forecast_text(forecast):
        raw_forecast_text_list = forecast.find('div', class_='PredictionContent').find_all('p')
        clear_forecast_text = map(lambda raw_desc: raw_desc.text, raw_forecast_text_list)
        forecast_text = ' '.join(clear_forecast_text)
        return forecast_text

    def get_forecast_add_info(self, link):
        additional_info = dict()
        response = self.downloader.get(link, top_proxies=10)
        soup = BeautifulSoup(response.text, 'lxml')
        additional_info['logos'] = self.get_forecast_logos(soup)
        return additional_info

    @staticmethod
    def get_teams(forecast):
        return [team_name.text for team_name in forecast.find_all('div',class_='PredictionContent__team-name')]

    def parse_single_forecast(self, forecast):
        logging.info('parsing forecast')
        _id = self.get_forecast_id(forecast)
        title = self.get_forecast_title(forecast)
        coefficient = float(self.get_forecast_coefficient(forecast))
        event_outcomes = self.get_event_outcomes(forecast)
        forecast_date = self.get_forecast_date(forecast)
        additional_info = self.get_forecast_add_info(_id)
        additional_info['forecast'] = self.get_forecast_text(forecast)
        additional_info['teams'] = self.get_teams(forecast)
        forecast_object = Forecast(_id=_id,
                                   title=title,
                                   coefficient=coefficient,
                                   resource=self.__resource_name__,
                                   forecast_date=forecast_date,
                                   event_outcomes=event_outcomes,
                                   **additional_info)
        return forecast_object

    def run(self):
        all_forecasts = self.scrape_forecasts()
        parsed_forecasts = self.parse_forecasts(all_forecasts)
        self.mdb.add_new_forecasts(parsed_forecasts)

if __name__ == '__main__':
    StavkaTV().run()
