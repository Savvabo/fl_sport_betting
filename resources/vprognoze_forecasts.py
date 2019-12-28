from abc import ABC
from bs4 import BeautifulSoup
from resources.base_forecasts import BaseExchanger
import logging
from storage.mongodb_storage import Forecast
import pytz
import datetime
import re
from helpers.category_translation import category_translation


class VprognozeForecasts(BaseExchanger, ABC):
    def __init__(self):
        self.__resource_name__ = 'vprognoze.ru'
        self.domain = 'https://vprognoze.ru'
        super().__init__()
        self.login()

    def is_need_to_reparse(self, soup):
        if not soup.find('div', id='dle-content'):
            return True

    def is_last_page(self, soup):
        if not soup.find('div', id='dle-content').find_all('div', class_='news_boxing', recursive=False):
            return True

    def create_scrape_url(self, page_num):
        pattern = '{}/forecast/pro/page/{}'
        return pattern.format(self.domain, page_num)

    def get_prettify_page(self, response):
        return BeautifulSoup(response.text, 'lxml')

    def get_forecasts_on_page(self, page):
        forecasts = page.find('div', id='dle-content').find_all('div', class_='news_boxing')
        return forecasts

    def get_forecast_link(self, forecast):
        link = forecast.find('div', class_='title_news').a['href']
        return link

    def get_forecast_title(self, forecast):
        return forecast.find('div', class_='title_news').a['title']

    def get_forecast_coefficient(self, forecast, forecast_type):
        if forecast_type == 'Express':
            index = 0
        else:
            index = 1
        try:
            forecast_coefficient = float(forecast.find_all('span', class_='predict_info_value')[index].text.strip())
        except:
            with self.downloader.proxy_helper.lock:
                print('b')
        return forecast_coefficient

    def get_events_outcomes(self, soup, forecast_type):
        if forecast_type == 'Express':
            events_outcomes = []
            raw_events_outcomes = soup.find('table', class_='expresstable').find_all('tr')[1::2]
            for raw_event_outcome in raw_events_outcomes:
                event_name = raw_event_outcome.find('td', class_='express_command')
                event_outcome = event_name.find_next('td')
                coefficient = raw_event_outcome.find('td', class_='express_kef')
                events_outcomes.append({'event_outcome': event_outcome.text,
                                        'coefficient': float(coefficient.text),
                                        'event_name': event_name.text})

        else:
            try:
                events_outcomes = [{'event_outcome': soup.find('span', class_='predict_info_value').text.strip(),
                                    'coefficient': self.get_forecast_coefficient(soup, 'Solo'),
                                    'event_name': soup.h1.text}]
            except:
                events_outcomes = 'bug'

        return events_outcomes

    def get_forecast_date(self, forecast):
        date_string = forecast.find('div', class_='game_start').find_all('span')[-1].text.strip().replace('(', '').replace(')', '')
        now = datetime.datetime.now()
        all_int = re.findall('\d{1,2}', date_string)
        current_minutes = all_int[5]
        current_hours = all_int[4]
        current_day = all_int[3]
        current_month = all_int[2]
        current_year = ''.join(all_int[0:2])
        event_time = now.replace(minute=int(current_minutes), hour=int(current_hours), day=int(current_day), month=int(current_month), year=int(current_year))
        pytz.timezone("Europe/Moscow").localize(event_time)
        event_timestamp = int(event_time.timestamp())
        return event_timestamp

    def get_solo_logos(self, soup):
        try:
            logos = [self.domain + logo.img['src'] for logo in soup.find_all('div', class_='event__info_player__logo')]
        except TypeError:

            logos = []
        return logos

    @staticmethod
    def get_forecast_text(forecast):
        forecast_text = forecast.find('div', class_='info down').find_previous('div', class_='clr').text
        return forecast_text

    def create_express_data(self, soup):
        express_data = dict()
        events = self.get_express_events(soup)
        express_data['events'] = events
        events_outcomes = self.get_events_outcomes(soup, 'Express')
        return express_data, events_outcomes

    def create_solo_data(self, soup):
        solo_data = dict()
        events_outcomes = self.get_events_outcomes(soup, 'solo')
        solo_data['teams'] = self.get_solo_teams(soup)
        solo_data['logos'] = self.get_solo_logos(soup)
        return solo_data, events_outcomes

    @staticmethod
    def parse_express_event(event_outcome):
        event_outcome['event_teams'] = [team.strip() for team in event_outcome['event_name'].split('-')]
        return event_outcome

    def get_express_events(self, soup):
        events_outcomes = self.get_events_outcomes(soup, 'Express')
        events = list(map(self.parse_express_event, events_outcomes))
        return events

    def get_forecast_add_info(self, link, forecast_type):
        response = self.downloader.get(link, timeout=15)
        soup = BeautifulSoup(response.text, 'lxml')
        if forecast_type == 'Express':
            additional_info, events_outcomes = self.create_express_data(soup)
        else:
            additional_info, events_outcomes = self.create_solo_data(soup)
        coefficient = self.get_forecast_coefficient(soup, forecast_type)
        return additional_info, events_outcomes, coefficient

    @staticmethod
    def get_solo_teams(soup):
        teams = [team_name.text for team_name in soup.find_all('div', class_='event__info_player__name')]
        return teams

    @staticmethod
    def get_tourname(forecast):
        tourname = forecast.find('div', class_='championship').text
        return tourname

    @staticmethod
    def get_forecast_type(tourname):
        if tourname == 'Экспресс':
            forecast_type = 'Express'
        else:
            forecast_type = 'Solo2'
        return forecast_type

    def get_category(self, link, forecast):
        splited_link = link.split('/')
        try:
            if link.split('/')[5] == 'fcuall':
                category_raw = forecast.find('div', class_='championship').text.split('.')[0].strip()
            else:
                category_raw = splited_link[5]
            category_raw = category_raw.replace('fcp', '').replace('fcu', '')
            category = category_translation.get(category_raw, category_raw.title())
        except IndexError:
            category = 'Express'
        return category

    def parse_single_forecast(self, forecast):
        _id = self.get_forecast_id(forecast)
        link = self.get_forecast_link(forecast)
        title = self.get_forecast_title(forecast)
        forecast_date = self.get_forecast_date(forecast)
        tourname = self.get_tourname(forecast)
        forecast_type = self.get_forecast_type(tourname)
        additional_info, events_outcomes, coefficient = self.get_forecast_add_info(link, forecast_type)
        forecast_text = self.get_forecast_text(forecast)
        category = self.get_category(link, forecast)
        forecast_object = Forecast(_id=_id,
                                   link=link,
                                   title=title,
                                   coefficient=coefficient,
                                   resource=self.__resource_name__,
                                   forecast_date=forecast_date,
                                   events_outcomes=events_outcomes,
                                   forecast_type=forecast_type,
                                   forecast=forecast_text,
                                   category=category,
                                   **additional_info)
        return forecast_object

    def solve_robot(self):
        response = self.downloader.get(self.domain)
        response.html.render()
        return

    def login(self):
        self.downloader.use_session = True
        self.downloader.update_request_maker()
        response = self.downloader.get(self.domain, timeout=15)
        login_user_token = response.cookies.get_dict()['login_user_token']
        login_data = {'login_name': self.config['login'],
                      'login_password': self.config['password'],
                      'login': 'submit',
                      'login_user_token': login_user_token}
        headers = {'Content-Type': 'application/x-www-form-urlencoded'}
        login_response = self.downloader.post(self.domain, headers=headers, data=login_data)
        soup = BeautifulSoup(login_response.text, 'lxml')
        if not soup.find('div', class_='nameuser'):
            logging.info('Login doesn\'t work')
            raise
        else:
            logging.info('Logged successfully')

    def run(self):
        all_forecasts = self.scrape_forecasts()
        self.parse_forecasts(all_forecasts)


if __name__ == '__main__':
    VprognozeForecasts().run()
