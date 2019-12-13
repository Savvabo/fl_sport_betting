import requests
from bs4 import BeautifulSoup
import datetime
import re
import json


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
        if not all_forecasts or page == 5:
            return all_pages
        else:
            all_pages.append(soup)
            page += 1


def parse_forecasts(page):
    parsed_forecasts = []
    forecasts = page.find('div', class_='list-view').find_all('div', class_='hidden-xs')
    for forecast in forecasts:
        forecast_data = dict()
        # forecast_data['forecast_title'] = (re.match("(.*?):", forecast.find('div', class_='top-article').find('div', class_='vps-h3').text).group()).replace(':', '')
        forecast_data['forecast_title'] = forecast.find('div', class_='top-article').find('div', class_='vps-h3').text
        # forecast_data['forecast_logo'] = forecast.find('div', class_='current-coefficent').span.text
        forecast_data['forecast_date'] = forecast.find('p', class_='time').text
        forecast_data['forecast_coefficient'] = forecast.find('div', class_='current-coefficent').span.text

        def get_forecast_description():
            forecast_link = forecast.find_parent('a')['href']
            response = requests.get(forecast_link)
            soup = BeautifulSoup(response.text, 'lxml')
            forecast_description = soup.find('blockquote').text
            return forecast_description

        forecast_data['forecast_description'] = get_forecast_description()
        forecast_data['forecast_link'] = forecast.find_parent('a')['href']
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
