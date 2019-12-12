from pymongo import MongoClient, UpdateOne
import configparser


class MDB:
    def __init__(self):
        self.parse_config()
        self.client = self.connect_to_db()

    def parse_config(self):
        self.config = configparser.ConfigParser()
        self.config.read('config.ini')
        self.config = self.config['db']

    def connect_to_db(self):
        if self.config['TEST_ENV']:
            client = MongoClient('mongodb://localhost', connect=False)[self.config['NAME']]
        else:
            client = None
        return client

    def get_instagram_posts(self, resource):
        medias = self.client[self.config['INSTAGRAM_COLLECTION']].find({'resource': resource}, {'id_': 'id_'})
        media_list = [media['_id'] for media in medias]
        return media_list

    def add_new_posts(self, posts):
        docs = [UpdateOne({'_id': post['_id']}, {'$set': post}, upsert=True) for post in posts]
        if docs:
            self.client[self.config['INSTAGRAM_COLLECTION']].bulk_write(docs)