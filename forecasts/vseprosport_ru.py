import requests
from bs4 import BeautifulSoup
import re
import datetime


def get_forecasts_off_all_pages():
    website = 'https://www.vseprosport.ru/news/{}/'
    all_pages = []
    page = 1
    while True:
        print(page)
        response = requests.get(website.format(page))
        soup = BeautifulSoup(response.text, 'lxml')
        if not soup.find('div', class_='list-view') or page == 2:
            return all_pages
        else:
            all_pages.append(soup)
            page += 1


def get_forecast_event_outcome(forecast_link):
    response = requests.get(forecast_link)
    soup = BeautifulSoup(response.text, 'lxml')
    forecast_event_outcome = soup.find('blockquote').text
    return forecast_event_outcome


def get_date_from_str(date_str):
    now = datetime.datetime.now()
    task_date = now
    all_int = re.findall('\d{1,2}', date_str)
    current_day = all_int[0]
    current_minutes = all_int[4]
    current_hours = all_int[3]
    current_year = '20' + all_int[2]
    current_month = all_int[1]
    task_date = now.replace(minute=int(current_minutes), hour=int(current_hours), year=int(current_year),
                            month=int(current_month), day=int(current_day))
    date_time = task_date.strftime("%d-%m-%Y, %H:%M")
    return date_time


def get_forecast_date(forecast_link):
    response = requests.get(forecast_link)
    soup = BeautifulSoup(response.text, 'lxml')
    forecast_date = get_date_from_str(soup.find('a', class_='date_and_time').text.strip())
    return forecast_date
    # BeautifulSoup(requests.get(forecast.find_parent('a')['href']).text, 'lxml').find('a', class_='date_and_time').text


def get_forecast_description(forecast_link):
    response = requests.get(forecast_link)
    soup = BeautifulSoup(response.text, 'lxml')
    # ('div', class_='about_team')
    # ('section', class_='news-content')
    # raw_description_list = forecast.find('div', class_='PredictionContent').find_all('p', dir="ltr")[0:3]
    # clear_description = map(lambda raw_desc: raw_desc.text, raw_description_list)
    # forecast_data['forecast_description'] = ' '.join(clear_description)
    forecast_description = soup.find('div', class_='about_team').text.strip()
    return forecast_description
    # BeautifulSoup(requests.get(forecast.find_parent('a')['href']).text, 'lxml').find('div', class_='about_team').text
    # BeautifulSoup(requests.get(forecast.find_parent('a')['href']).text, 'lxml').find('div', class_='news-content').text


def parse_forecasts(page):
    parsed_forecasts = []
    forecasts = page.find('div', class_='list-view').find_all('div', class_='hidden-xs')
    for forecast in forecasts:
        forecast_data = dict()
        if ':' or '.':
            forecast_data['forecast_title'] = \
                forecast.find('div', class_='top-article').find('div', class_='vps-h3').text.split(':')[0].split('.')[0]
        else:
            forecast_data['forecast_title'] = forecast.find('div', class_='top-article').find('div',
                                                                                              class_='vps-h3').text
        # forecast_data['forecast_logo'] = forecast.find('div', class_='current-coefficent').span.text
        forecast_data['forecast_coefficient'] = forecast.find('div', class_='current-coefficent').span.text
        forecast_data['forecast_link'] = forecast.find_parent('a')['href']
        try:
            forecast_data['forecast_event_outcome'] = get_forecast_event_outcome(forecast_data['forecast_link']).strip()
        except AttributeError:
            forecast_data['forecast_event_outcome'] = None
        try:
            forecast_data['forecast_date'] = get_forecast_date(forecast_data['forecast_link'])
        except AttributeError:
            forecast_data['forecast_date'] = None
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
