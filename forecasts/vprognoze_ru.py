import requests
from bs4 import BeautifulSoup
import datetime
import pytz


def get_forecast_logo(forecast_link):
    response = requests.get(forecast_link)
    soup = BeautifulSoup(response.text, 'lxml')
    first_forecast_logo = 'https://vprognoze.ru{}'.format(soup.find_all('div', class_='event__info_player__logo')[0].img['src'])
    second_forecast_logo = 'https://vprognoze.ru{}'.format(soup.find_all('div', class_='event__info_player__logo')[1].img['src'])
    return first_forecast_logo, second_forecast_logo
# '{https://vprognoze.ru}'.format(BeautifulSoup(requests.get('{}'.format(forecast.find('div', class_='title_news').a['href'])).text, 'lxml').find('div', class_='event__info_player__logo').img['src'])


# def get_date_from_str(date_str):
#     d = datetime.datetime.now()
#     timezone = pytz.timezone("Russia/Moscow")
#     d_aware = timezone.localize(d)
#     print(d_aware.tzinfo)

def get_forecasts_off_all_pages():
    website = 'https://vprognoze.ru/forecast/page/{}'
    all_pages = []
    page = 1
    while True:
        print(page)
        response = requests.get(website.format(page))
        soup = BeautifulSoup(response.text, 'lxml')
        if not soup.find('div', id='dle-content') or page == 20:
            return all_pages
        else:
            all_pages.append(soup)
            page += 1


def parse_forecasts(page):
    parsed_forecasts = []
    forecasts = page.find('div', id='dle-content').find_all('div', class_='news_boxing')
    for forecast in forecasts:
        forecast_data = dict()
        command_names = forecast.find('span', class_='commands__name')
        if command_names is not None:
            forecast_data['forecast_title'] = forecast.find('span', class_='commands__name').text.strip()
        else:
            forecast_data['forecast_title'] = forecast.find('div', class_='title_news').text.strip()
        forecast_data['forecast_date'] = forecast.find('div', class_='game_start').find_all('span')[-1].text.strip().replace('(', '').replace(')', '')
        try:
            forecast_data['forecast_coefficient'] = forecast.find_all('div', class_='info_match')[1].text.strip()
        except IndexError:
            forecast_data['forecast_coefficient'] = None
        try:
            forecast_data['forecast_event_outcome'] = forecast.find_all('div', class_='info_match')[0].text.strip()
        except IndexError:
            forecast_data['forecast_event_outcome'] = None
        forecast_data['forecast_description'] = forecast.find('div', class_='info down').find_previous('div', class_='clr').text
        forecast_data['forecast_link'] = forecast.find('div', class_='title_news').a['href']
        try:
            forecast_data['forecast_logo'] = get_forecast_logo(forecast_data['forecast_link'])
        except IndexError:
            forecast_data['forecast_logo'] = None
        except TypeError:
            forecast_data['forecast_logo'] = None
        parsed_forecasts.append(forecast_data)
    return parsed_forecasts


def format_to_string(forecast):
    template = "    1. {forecast_title}     \n " \
               "    2. {forecast_logo}     \n " \
               "    3. {forecast_date}     \n " \
               "    4. {forecast_coefficient}     \n " \
               "    5. {forecast_event_outcome}     \n " \
               "    6. {forecast_description}     \n " \
               "    7. {forecast_link}     "
    formatted_message = template.format(forecast_title=forecast['forecast_title'],
                                        forecast_logo=forecast['forecast_logo'],
                                        forecast_date=forecast['forecast_date'],
                                        forecast_coefficient=forecast['forecast_coefficient'],
                                        forecast_event_outcome=forecast['forecast_event_outcome'],
                                        forecast_description=forecast['forecast_description'],
                                        forecast_link=forecast['forecast_link'])
    return formatted_message


def run():
    parsed_forecasts = []
    all_pages = get_forecasts_off_all_pages()
    for page in all_pages:
        parsed_forecasts.extend(parse_forecasts(page))
    print(parsed_forecasts)
    for parsed_forecast in parsed_forecasts:
        formatted_forecast = format_to_string(parsed_forecast)
        print(formatted_forecast)


if __name__ == '__main__':
    run()
