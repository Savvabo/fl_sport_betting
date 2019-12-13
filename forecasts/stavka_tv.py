import requests
from bs4 import BeautifulSoup
import datetime
import re


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
        forecast_data['forecast_title'] = forecast.find('div', class_='Prediction__header-name').text
        # forecast_data['forecast_logo'] = forecast.find('div', class_='current-coefficent').span.text
        forecast_data['forecast_date'] = forecast.find('b', class_='PredictionContent__date-bold').text
        forecast_data['forecast_coefficient'] = forecast.find('em', class_='PredictionContent__bet-text--em').text
        forecast_data['forecast_description'] = forecast.find('em', class_='PredictionContent__bet-text--em').text
        forecast_data['forecast_link'] = forecast.find('a')['href']
        parsed_forecasts.append(forecast_data)
    return parsed_forecasts


def format_to_string(forecast):
    template = "    1. {forecast_title}     \n " \
               "    2. {forecast_date}     \n " \
               "    3. {forecast_coefficient}     \n " \
               "    4. {forecast_description}     \n " \
               "    5. {forecast_link}     "
    formatted_message = template.format(forecast_title=forecast['forecast_title'],
                                        forecast_value=forecast['forecast_date'],
                                        forecast_summary=forecast['forecast_coefficient'],
                                        forecast_date=forecast['forecast_description'],
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
