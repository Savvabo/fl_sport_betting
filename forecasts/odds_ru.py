import requests
from bs4 import BeautifulSoup
import json
import datetime
import re


def get_forecasts_off_all_pages():
    website = 'https://odds.ru/forecasts/?page={}&per_page=200'
    all_pages = []
    page = 1
    while True:
        print(page)
        headers = {'X-Requested-With': 'XMLHttpRequest'}
        response = requests.get(website.format(page), headers=headers, proxies={'https': '178.62.81.107:3128'})
        page_html = json.loads(response.text)['html']
        soup = BeautifulSoup(page_html, 'lxml')
        all_forecasts = soup.find_all('div', class_='forecast-item')
        if not all_forecasts or page == 2:
            return all_pages
        else:
            all_pages.append(soup)
            page += 1


def get_forecast_event_outcome(forecast_link):
    response = requests.get(forecast_link)
    soup = BeautifulSoup(response.text, 'html.parser')
    forecast_event_outcome = soup.find('div', class_='rate-name-text').text
    return forecast_event_outcome
    # BeautifulSoup(requests.get('https://odds.ru{}'.format(forecast.find('div', class_='forecast-preview__title').a['href'])).text, 'html.parser').find('forecast-bet__info-item').text


# def get_forecast_description(forecast_link):
#     response = requests.get(forecast_link)
#     soup = BeautifulSoup(response.text, 'html.parser')
#     forecast_description = soup.find('div', 'forecast-text').text
#     return forecast_description
#     # BeautifulSoup(requests.get('https://odds.ru{}'.format(forecast.find('div', class_='forecast-preview__title').a['href'])).text, 'html.parser').find('div', 'forecast-text').text


def get_date_from_str(date_str):
    now = datetime.datetime.now()
    task_date = now
    month_dict = {'января': 1, 'февраля': 2, 'марта': 3, 'апреля': 4, 'мая': 5, 'июня': 6, 'июля': 7, 'августа': 8,
                  'сентября': 9, 'октября': 10, 'ноября': 11, 'декабря': 12}
    all_int = re.findall('\d{1,2}', date_str)
    current_day = all_int[0]
    current_minutes = all_int[4]
    current_hours = all_int[3]
    current_year = ''.join(all_int[1:3])
    current_month = 1
    for month, month_index in month_dict.items():
        if month in date_str:
            current_month = month_index
    task_date = now.replace(minute=int(current_minutes), hour=int(current_hours), year=int(current_year),
                            month=int(current_month), day=int(current_day))
    date_time = task_date.strftime("%d-%m-%Y, %H:%M")
    return date_time


def parse_forecasts(page):
    parsed_forecasts = []
    forecasts = page.find_all('div', class_='forecast-item')
    for forecast in forecasts:
        forecast_data = dict()
        forecast_data['forecast_title'] = forecast.find('div', class_='forecast-preview__title').text.strip()
        # forecast_data['forecast_logo'] = forecast.find('div', class_='current-coefficent').span.text
        try:
            forecast_data['forecast_date'] = get_date_from_str(
                forecast.find('div', class_='forecast-preview__date').text.strip())
        except AttributeError:
            forecast_data['forecast_date'] = None
        try:
            forecast_data['forecast_coefficient'] = forecast.find('span', class_='forecast-preview__rate').text.replace(
                'коэф.:', '').strip()
        except AttributeError:
            forecast_data['forecast_coefficient'] = None
        forecast_data['forecast_link'] = 'https://odds.ru{}'.format(
            forecast.find('div', class_='forecast-preview__title').a['href'])
        # forecast_data['forecast_description'] = get_forecast_description(forecast_data['forecast_link'])
        forecast_data['forecast_description'] = None
        try:
            forecast_data['forecast_event_outcome'] = get_forecast_event_outcome(forecast_data['forecast_link'])
        except AttributeError:
            forecast_data['forecast_event_outcome'] = None
        parsed_forecasts.append(forecast_data)
    return parsed_forecasts


def format_to_string(forecast):
    template = "    1. {forecast_title}     \n " \
               "    2. {forecast_date}     \n " \
               "    3. {forecast_coefficient}     \n " \
               "    4. {forecast_event_outcome}     \n " \
               "    4. {forecast_description}     \n " \
               "    5. {forecast_link}     "
    formatted_message = template.format(forecast_title=forecast['forecast_title'],
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
