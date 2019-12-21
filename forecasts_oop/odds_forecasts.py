from abc import ABC
from bs4 import BeautifulSoup
import re
import datetime
import logging
from storage.mongodb_storage import Forecast
import pytz
from forecasts_oop.base_forecasts import BaseExchanger
import json
from helpers.category_translation import category_translation
import random

HEADERS = [{
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_12_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/61.0.3163.100 Safari/537.36',
    'Accept': 'application/json,text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'en-us',
    'Accept-Encoding': 'gzip, deflate',
    'Content-Type': 'application/json,text/html,application/x-www-form-urlencoded'
},
    {
    'User-Agent': "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.12; rv:50.0) Gecko/20100101 Firefox/50.0",
    'Accept': "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    'Accept-Language': "en-US;q=0.7,en;q=0.3",
    'Accept-Encoding': "gzip, deflate",
    'cache-control': "no-cache",
    'Connection': "keep-alive"
}
]


class OddsForecasts(BaseExchanger, ABC):
    def __init__(self):
        self.__resource_name__ = 'odds.ru'
        self.domain = 'https://odds.ru'
        super().__init__()

    def is_need_to_reparse(self, soup):
        return False

    def get_forecasts_on_page(self, page):
        expected_count = 25
        forecasts = page.find_all('div', class_='forecast-item')
        if len(forecasts) != expected_count:
            logging.warning('received {} forecasts, but expected {}'.format(len(forecasts), expected_count))
        return forecasts

    def get_forecast_link(self, forecast):
        link = self.domain + forecast.find('div', class_='forecast-preview__title').a['href']
        return link

    def is_last_page(self, soup):
        if not soup.find_all('div', class_='forecast-item'):
            return True

    def create_scrape_url(self, page_num):
        pattern = '{}/forecasts/?page={}&per_page=25'
        return pattern.format(self.domain, page_num)

    def get_prettify_page(self, response):
        page_html = json.loads(response.text)['html']
        soup = BeautifulSoup(page_html, 'lxml')
        return soup

    def get_forecast_title(self, forecast):
        title = forecast.find('div', class_='forecast-preview__title').text.strip()
        return title

    def get_forecast_coefficient(self, soup, event_outcomes=()):
        try:
            raw_coefficient = soup.find('a', class_='forecast-bet__info-item forecast-bet__info-item--coeff').text
            coefficient = float(re.sub('коэф\.', '', raw_coefficient,
                                       flags=re.IGNORECASE).replace(':', '').replace('\n', '').strip())
        except AttributeError:
            if event_outcomes:
                coefficient = event_outcomes[0]['coefficient']
            else:
                coefficient = None
        return coefficient

    def get_forecast_date(self, forecast):
        try:
            date_string = forecast.find('div', class_='forecast-preview__date').text.strip()
        except AttributeError:
            try:
                date_string = forecast.find('div', class_='match-start-date').text.strip()
            except AttributeError:
                return
        now = datetime.datetime.now()
        month_dict = {'января': 1, 'февраля': 2, 'марта': 3, 'апреля': 4, 'мая': 5, 'июня': 6, 'июля': 7, 'августа': 8,
                      'сентября': 9, 'октября': 10, 'ноября': 11, 'декабря': 12}
        all_int = re.findall('\d{1,2}', date_string)
        current_day = all_int[0]
        current_minutes = all_int[4]
        current_hours = all_int[3]
        current_year = ''.join(all_int[1:3])
        current_month = 1
        for month, month_index in month_dict.items():
            if month in date_string:
                current_month = month_index
        event_time = now.replace(minute=int(current_minutes), hour=int(current_hours), year=int(current_year),
                                 month=int(current_month), day=int(current_day))
        pytz.timezone("Europe/Moscow").localize(event_time)
        event_timestamp = int(event_time.timestamp())
        return event_timestamp

    @staticmethod
    def get_forecast_logos(soup):
        logos = ['https:' + logo.img['src'] for logo in soup.find_all('div', class_='forecast-bet__team-logo')]
        return logos

    def get_events_outcomes(self, soup):
        event_outcomes_raw = soup.find_all('div', class_='bet-data')
        event_outcomes = []
        if event_outcomes_raw:
            event_name = soup.find('div', class_='bet-main-info').contents[-1]
            for raw_event_outcome in event_outcomes_raw:
                event_outcome = raw_event_outcome.find('div', class_='rate-name-text').text
                raw_coefficient = raw_event_outcome.find('div', class_='rate-value').text.replace('коэф.\n', '').strip()
                coefficient = float(
                    re.sub('коэф\.', '', raw_coefficient, flags=re.IGNORECASE).replace(':', '').replace('\n',
                                                                                                        '').strip())
                event_outcomes.append(
                    {'event_outcome': event_outcome, 'coefficient': coefficient, 'event_name': event_name})
        return event_outcomes

    @staticmethod
    def get_teams(soup):
        try:
            teams = [team.strip() for team in soup.find('div', class_='forecast-bet__match-name').text.split('-')]
        except AttributeError:
            try:
                teams = [team.strip() for team in soup.find('div', class_='bet-main-info').contents[-1].split('-')]
            except AttributeError:
                teams = []
        return teams

    @staticmethod
    def get_forecast(soup, _id):
        all_shity_divs = soup.find('div', class_='forecast-text post-main-content').find_all('div', recursive=False)
        for div in all_shity_divs:
            div.decompose()
        forecast = soup.find('div', class_='forecast-text post-main-content').text
        return forecast

    def get_category(self, soup):
        category_raw = soup.find_all('li', typeof='v:Breadcrumb')[1].text.split(' ')[-1].replace('\n', '').strip().title()
        category = category_translation[category_raw]
        return category

    def get_forecast_add_info(self, link):
        additional_info = dict()
        headers = random.choice(HEADERS)
        response = self.downloader.get(link, timeout=15, headers=headers)
        if response.status_code >= 400:
            raise Exception
        soup = BeautifulSoup(response.text, 'lxml')
        additional_info['logos'] = self.get_forecast_logos(soup)
        additional_info['forecast'] = self.get_forecast(soup, link)
        additional_info['teams'] = self.get_teams(soup)
        event_outcomes = self.get_events_outcomes(soup)
        coefficient = self.get_forecast_coefficient(soup, event_outcomes)
        category = self.get_category(soup)
        return additional_info, event_outcomes, coefficient, category

    def parse_single_forecast(self, forecast):
        _id = self.get_forecast_id(forecast)
        link = self.get_forecast_link(forecast)
        title = self.get_forecast_title(forecast)
        try:
            additional_info, event_outcomes, coefficient, category = self.get_forecast_add_info(link)
        except Exception as e:
            print('exsection {}'.format(str(e)))
            return
        forecast_date = self.get_forecast_date(forecast)
        forecast_object = Forecast(_id=_id,
                                   link=link,
                                   title=title,
                                   coefficient=coefficient,
                                   resource=self.__resource_name__,
                                   forecast_date=forecast_date,
                                   events_outcomes=event_outcomes,
                                   forecast_type='Solo',
                                   category=category,
                                   **additional_info)
        return forecast_object

    def run(self):
        request_data = {'headers': {'X-Requested-With': 'XMLHttpRequest'}, 'timeout': 15}
        all_forecasts = self.scrape_forecasts(request_data=request_data)
        self.parse_forecasts(all_forecasts)


if __name__ == '__main__':
    OddsForecasts().run()