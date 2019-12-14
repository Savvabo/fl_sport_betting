import requests
from bs4 import BeautifulSoup
import datetime
import re


def get_date_from_str(date_str):
    now = datetime.datetime.now()
    task_date = now
    month_dict = {'января': 1, 'февраля': 2, 'марта': 3, 'апреля': 4, 'мая': 5, 'июня': 6, 'июля': 7, 'августа': 8,
                  'сентября': 9, 'октября': 10, 'ноября': 11, 'декабря': 12}
    all_int = re.findall('\d{1,2}', date_str)
    current_day = all_int[0]
    current_minutes = all_int[2]
    current_hours = all_int[1]
    current_month = 1
    for month, month_index in month_dict.items():
        if month in date_str:
            current_month = month_index
    task_date = now.replace(minute=int(current_minutes), hour=int(current_hours), month=int(current_month), day=int(current_day))
    date_time = task_date.strftime("%d-%m-%Y, %H:%M")
    return date_time

def get_forecasts_off_all_pages():
    website = 'https://stavka.tv/predictions?page={}'
    all_pages = []
    page = 1
    while True:
        print(page)
        response = requests.get(website.format(page))
        soup = BeautifulSoup(response.text, 'lxml')
        if not soup.find('div', class_='Predictions__container') or page == 5:
            return all_pages
        else:
            all_pages.append(soup)
            page += 1


def parse_forecasts(page):
    parsed_forecasts = []
    forecasts = page.find_all('div', class_='Predictions__item')
    for forecast in forecasts:
        forecast_data = dict()
        # forecast_data['forecast_title'] = (re.match("(.*?):", forecast.find('div', class_='top-article').find('div', class_='vps-h3').text).group()).replace(':', '')
        forecast_data['forecast_title'] = forecast.find('div', class_='Prediction__header-name').text.strip()
        # forecast_data['forecast_logo'] = forecast.find('div', class_='current-coefficent').span.text
        forecast_data['forecast_date'] = get_date_from_str(forecast.find('b', class_='PredictionContent__date-bold').text.strip())
        forecast_data['forecast_coefficient'] = forecast.find_all('em', class_='PredictionContent__bet-text--em')[1].text.strip()
        forecast_data['forecast_description'] = forecast.find_all('em', class_='PredictionContent__bet-text--em')[0].text.strip()
        forecast_data['forecast_link'] = 'https://stavka.tv{}'.format(forecast.find('a')['href'])
        parsed_forecasts.append(forecast_data)
    return parsed_forecasts


def format_to_string(forecast):
    template = "    1. {forecast_title}     \n " \
               "    2. {forecast_date}     \n " \
               "    3. {forecast_coefficient}     \n " \
               "    4. {forecast_description}     \n " \
               "    5. {forecast_link}     "
    formatted_message = template.format(forecast_title=forecast['forecast_title'],
                                        forecast_date=forecast['forecast_date'],
                                        forecast_coefficient=forecast['forecast_coefficient'],
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
