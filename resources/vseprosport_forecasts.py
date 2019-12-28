from abc import ABC
from bs4 import BeautifulSoup
import re
import datetime
import logging
from storage.mongodb_storage import Forecast
import pytz
from resources.base_forecasts import BaseExchanger
from helpers.category_translation import category_translation
import os


class VseprosportForecasts(BaseExchanger, ABC):
    def __init__(self):
        self.__resource_name__ = 'vseprosport.ru'
        self.domain = 'https://www.vseprosport.ru'
        super().__init__()
        if not os.path.exists('../stream/vseprosport'):
            os.makedirs('../stream/vseprosport')

    def is_need_to_reparse(self, soup):
        return False

    def is_last_page(self, soup):
        if soup.find('div', class_='list-view').find('div', class_='empty'):
            return True

    def get_prettify_page(self, response):
        return BeautifulSoup(response.text, 'lxml')

    def get_forecasts_on_page(self, page):
        expected_count = 15
        forecasts = page.find('div', class_='list-view').find_all('a', recursive=False)
        if len(forecasts) != expected_count:
            logging.warning('received {} forecasts, but expected {}'.format(len(forecasts), expected_count))
        return forecasts

    def get_forecast_link(self, forecast):
        return forecast['href']

    def create_scrape_url(self, page_num):
        pattern = '{}/news/{}'
        return pattern.format(self.domain, page_num)

    @staticmethod
    def parse_team_description(team_description):
        team_data = dict()
        team_data['team_name'] = team_description.h3.text
        team_data['team_description'] = team_description.find('div', class_='editor').text
        return team_data

    def parse_express_event(self, event, forecast_date):
        event_info = dict()
        game_time = event.a.find('div', class_='bookmaker_express_time').p.text.strip()
        hour = int(game_time.split(':')[0])
        minute = int(game_time.split(':')[1])
        game_date = datetime.datetime.fromtimestamp(forecast_date).replace(minute=minute, hour=hour)
        event_info['event_link'] = self.domain + event.a['href']
        event_info['event_teams'] = self.get_express_event_teams(event)
        images = list(map(lambda image: self.downloader.download_logos(image['src'], 'vseprosport'), event.find_all('img')))
        event_info['event_logos'] = images
        event_info['event_title'] = event.a.find('div', class_='bookmaker_express_item_title_teamsName').text
        event_info['event_date'] = int(game_date.timestamp())
        event_info['event_coefficient'] = float(event.find('div', class_='bookmaker_express_match_coefficient_ui').text)
        event_info['event_outcome'] = event.find('div', class_='bookmaker_express_match_coefficient_pos').text
        event_info['event_description'] = event.find('div', class_='bookmaker_express_time_text').text
        return event_info

    def get_express_events(self, soup, forecast_date):
        raw_events = soup.find_all('div', class_='bookmaker_express_item')
        events = list(map(lambda raw_event: self.parse_express_event(raw_event, forecast_date), raw_events))
        return events

    @staticmethod
    def get_superexpress_maintext(soup):
        return soup.find('section', class_='news_content').text

    def get_events_outcomes(self, soup, forecast_type, teams=(), id_=None):
        events_outcomes = []

        if forecast_type == 'Superexpress':
            for raw_event_outcome in soup.find_all('div', {'style': 'text-align: justify;'}, text=re.compile('[0-9] .*:')):
                event_outcome = raw_event_outcome.text.split(':')[1].strip()
                coefficient = None
                event_name = re.sub('[0-9]', '', raw_event_outcome.text.split(':')[0]).strip()
                events_outcomes.append({'event_outcome': event_outcome,
                                        'coefficient': coefficient,
                                        'event_name': event_name,
                                        'tournament': raw_event_outcome.find_previous('strong').text.strip()})
        elif forecast_type == 'Express':
            for raw_event_outcome in soup.find_all('div', class_='bookmaker_express_time_total'):
                splited_outcome = raw_event_outcome.text.strip().split(', ')
                event_outcome = splited_outcome[2]
                coefficient = splited_outcome[-1]
                event_name = splited_outcome[1]
                events_outcomes.append({'event_outcome': event_outcome,
                                        'coefficient': coefficient,
                                        'event_name': event_name})
        else:
            for raw_event_outcome in soup.find_all('div', class_='news_custom_prognoz_name'):
                event_outcome = raw_event_outcome.find('div', class_='title').text.replace('Ставка: ', '')
                coefficient = float(raw_event_outcome.find_next('ul', class_='news_custom_prognoz_items').li.find_all('p')[-1].span.text)
                event_name = ' - '.join(teams)
                events_outcomes.append({'event_outcome': event_outcome,
                                        'coefficient': coefficient,
                                        'event_name': event_name})

            if not events_outcomes:
                try:
                    bet_block = soup.find('ul', class_='justifyed-list')
                    event_outcome = bet_block.find_all('li')[1].text.replace('\n', '').strip()
                    coefficient = float(bet_block.find_all('li')[-2].text.replace('\n', '').strip())
                    event_name = ' - '.join(teams)
                    events_outcomes.append({'event_outcome': event_outcome,
                                        'coefficient': coefficient,
                                        'event_name': event_name})
                except:

                    events_outcomes.append({'event_outcome': None,
                                            'coefficient': None,
                                            'event_name': None})

        return events_outcomes

    @staticmethod
    def get_solo_statistic(soup):
        return [stat_row.text for stat_row in soup.find('li', id='statistica').find_all('li')]

    @staticmethod
    def get_forecast(soup):
        forecast_summary_block = soup.find('h3', class_='vps-h3', text=' Прогноз ').find_next('li',
                                                                                              class_='col-full').div
        try:
            forecast_red = ' '.join(
                [red_text_block.text for red_text_block in forecast_summary_block.find_all('p', recursive=False)])
        except AttributeError:
            forecast_red = None
        try:
            forecast_green = forecast_summary_block.blockquote.text
        except AttributeError:
            forecast_green = None
        return forecast_red, forecast_green

    def create_express_data(self, soup, forecast_date):
        express_data = dict()
        events = self.get_express_events(soup, forecast_date)
        express_data['events'] = events
        events_outcomes = self.get_events_outcomes(soup, 'Express')
        return express_data, events_outcomes

    def create_superexpress_data(self, soup):
        superexpress_data = dict()
        superexpress_data['main_text'] = self.get_superexpress_maintext(soup)
        superexpress_data['teams'] = self.get_superexpress_teams(soup)
        events_outcomes = self.get_events_outcomes(soup, 'Superexpress')
        return superexpress_data, events_outcomes

    @staticmethod
    def get_express_event_teams(event):
        teams_name_block = event.find_all('div', class_='bookmaker_express_item_title_teamsName')
        teams = [team_name.strip() for team_name_block in teams_name_block for team_name in
                 team_name_block.p.text.split(' - ')]
        return teams

    def get_superexpress_teams(self, soup):
        events_outcomes = self.get_events_outcomes(soup, 'Superexpress')
        teams = []
        for event_outcome in events_outcomes:
            clear_outcome = re.search('[^0-9]+', event_outcome['event_name']).group(0).split(':')[0].replace('–', '-').replace('—', '-').strip()
            outcome_teams = [team.strip() for team in clear_outcome.split(' - ')]
            teams.extend(outcome_teams)
        return teams

    @staticmethod
    def get_solo_teams(soup):
        teams_name_block = soup.find_all('div', class_='news_team')
        teams = [team_name_block.h4.text for team_name_block in teams_name_block]
        return teams

    def create_solo_data(self, soup,  _id):
        solo_data = dict()
        solo_data['teams'] = self.get_solo_teams(soup)
        logos = []
        for image in soup.find_all('a', class_='team_img'):
            image = image.img
            if image['src'].startswith('data:'):
                new_image = self.downloader.download_logos(image['src'], 'vseprosport')
                logos.append(new_image)
            else:
                logos.append(image['src'])
        solo_data['logos'] = logos
        events_outcomes = self.get_events_outcomes(soup, 'solo', solo_data['teams'], _id)
        try:
            about_team_blocks = soup.find_all('div', class_='about_team')[:-1]
            solo_data['about_teams'] = list(map(self.parse_team_description, about_team_blocks))
            solo_data['statistic'] = self.get_solo_statistic(soup)
            solo_data['forecast_red'], solo_data['forecast_green'] = self.get_forecast(soup)
            solo_data['news_text'] = None
        except AttributeError:
            solo_data['about_teams'] = None
            solo_data['statistic'] = None
            solo_data['forecast_red'] = None
            solo_data['forecast_green'] = None
            solo_data['news_text'] = soup.find('section', class_='news_content').text
        return solo_data, events_outcomes

    def get_forecast_add_info(self, link, forecast_date, forecast_type):
        response = self.downloader.get(link, timeout=15)
        if not response or response.status_code >= 400:
            return None, None
        soup = BeautifulSoup(response.text, 'lxml')
        if forecast_type == 'Express':
            additional_info, events_outcomes = self.create_express_data(soup, forecast_date)
        elif forecast_type == 'Superexpress':
            additional_info, events_outcomes = self.create_superexpress_data(soup)
        else:
            additional_info, events_outcomes = self.create_solo_data(soup, link)
        return additional_info, events_outcomes

    @staticmethod
    def get_forecast_type(forecast_title):
        if forecast_title.startswith('Экспресс'):
            return 'Express'
        elif forecast_title.startswith('Суперэкспресс'):
            return 'Superexpress'
        else:
            return 'Solo'

    def get_forecast_title(self, forecast):
        return forecast.find('div', class_='top-article').find('div', class_='vps-h3').text

    def get_forecast_coefficient(self, forecast):
        try:
            coefficient = float(forecast.find('div', class_='current-coefficent').span.text)
        except ValueError:
            coefficient = None
        return coefficient

    @staticmethod
    def get_forecast_tournament(forecast):
        tournament = forecast.find_all('p', class_='time')[1].text.replace('Турнир:', '').strip()
        if not tournament:
            tournament = None
        return tournament

    def get_category(self, forecast):
        try:
            category_raw = forecast.find('img', class_='img-responsive')['title']
            category = category_translation[category_raw]
        except KeyError:
            category = None
        return category

    def get_forecast_date(self, forecast):
        date_string = forecast.find('p', class_='time').text
        time_parts = re.findall('[0-9]{2}', date_string)
        now = datetime.datetime.now().replace(second=0, microsecond=0)
        if 'Завтра' in date_string or 'Сегодня' in date_string or 'Послезавтра' in date_string:
            event_time = now.replace(hour=int(time_parts[0]), minute=int(time_parts[1]))
            if 'Завтра' in date_string:
                event_time += datetime.timedelta(days=1)
            elif 'Послезавтра' in date_string:
                event_time += datetime.timedelta(days=2)
        else:
            event_time = datetime.datetime.strptime(date_string, 'Время: %d/%m/%y в %H:%M МСК')
        pytz.timezone("Europe/Moscow").localize(event_time)
        event_timestamp = int(event_time.timestamp())
        return event_timestamp

    def parse_single_forecast(self, forecast):
        _id = self.get_forecast_id(forecast)
        link = self.get_forecast_link(forecast)
        title = self.get_forecast_title(forecast)
        forecast_type = self.get_forecast_type(title)
        coefficient = self.get_forecast_coefficient(forecast)
        tournament = self.get_forecast_tournament(forecast)
        forecast_date = self.get_forecast_date(forecast)
        additional_info, events_outcomes = self.get_forecast_add_info(link, forecast_date, forecast_type)
        if not additional_info:
            return
        category = self.get_category(forecast)
        forecast_object = Forecast(_id=_id,
                                   link=link,
                                   title=title,
                                   coefficient=coefficient,
                                   resource=self.__resource_name__,
                                   forecast_date=forecast_date,
                                   events_outcomes=events_outcomes,
                                   tournament=tournament,
                                   forecast_type=forecast_type,
                                   category=category,
                                   **additional_info)

        return forecast_object

    def run(self):
        all_forecasts = self.scrape_forecasts({'timeout': 15})
        self.parse_forecasts(all_forecasts)



if __name__ == '__main__':
    VseprosportForecasts().run()
