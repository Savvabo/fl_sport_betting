from pymongo import MongoClient, UpdateOne
from helpers.helpers import parse_config
import ast


class MongoDBStorage:
    def __init__(self):
        self.config = parse_config('db')
        self.client = self.connect_to_db()

    def connect_to_db(self):
        if ast.literal_eval(self.config['TEST_ENV']) is True:
            client = MongoClient('mongodb://localhost', connect=False)[self.config['NAME']]
        else:
            client = MongoClient('mongodb://{login}:{password}@{ip}/{db_name}'.format(login=self.config['LOGIN'],
                                                                                      password=self.config['PASSWORD'],
                                                                                      ip=self.config['IP'],
                                                                                      db_name=self.config['NAME']),
                                 connect=False)[self.config['NAME']]
        return client

    def get_instagram_posts(self, resource):
        medias = self.client[self.config['INSTAGRAM_COLLECTION']].find({'resource': resource}, {'_id': 1})
        media_list = [media['_id'] for media in medias]
        return media_list

    def get_forecasts(self, resource):
        forecasts = self.client[self.config['FORECASTS_COLLECTION']].find({'resource': resource}, {'_id': 1})
        forecasts_list = [forecast['_id'] for forecast in forecasts]
        return forecasts_list

    def add_new_forecasts(self, forecasts):
        forecasts_list = [forecast.get_data() for forecast in forecasts]
        docs = [UpdateOne({'_id': forecast_data['_id']}, {'$set': forecast_data}, upsert=True) for forecast_data in forecasts_list]
        if docs:
            self.client[self.config['FORECASTS_COLLECTION']].bulk_write(docs)

    def add_new_posts(self, posts):
        docs = [UpdateOne({'_id': post['_id']}, {'$set': post}, upsert=True) for post in posts]
        if docs:
            self.client[self.config['INSTAGRAM_COLLECTION']].bulk_write(docs)


class Forecast(MongoDBStorage, dict):
    def __init__(self, *, _id, link, title, coefficient, resource, forecast_date, events_outcomes, forecast_type, category, **kwargs):
        super().__init__()
        self.data = {'additional_info': {}}
        self['_id'] = _id
        self['link'] = link
        self['title'] = title
        self['coefficient'] = coefficient
        self['resource'] = resource
        self['date'] = forecast_date
        self['events_outcomes'] = events_outcomes
        self['forecast_type'] = forecast_type
        self['category'] = category
        self.data['additional_info'].update(kwargs)

    def __setitem__(self, key, value):
        self.data[key] = value

    def save(self):
        self.client[self.config['FORECASTS_COLLECTION']].update_one({'_id': self.data['_id']},
                                                                    {'$set': self.data},
                                                                    upsert=True)

    def get_data(self):
        return self.data


