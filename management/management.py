import sys
sys.path.append("..")
import logging
import os
import sys
import datetime
import glob
import ast
from resources.resources import RESOURCES
from storage.mongodb_storage import MongoDBStorage
from helpers.helpers import parse_config
logging.basicConfig(filename='forecasts.log', filemode='a', format=u'%(filename)s[LINE:%(lineno)d]# %(levelname)-8s [%(asctime)s]  %(message)s',
                    level=logging.INFO)
logging.getLogger("requests").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)
logging.getLogger("connectionpool").setLevel(logging.WARNING)


class ManagementHelper:
    def __init__(self, resource, insta_resources):
        self.config = parse_config('server')
        self.resource = resource
        self.insta_resources = insta_resources
        self.mdb = MongoDBStorage()
        self.old_datetime = datetime.datetime.now() - datetime.timedelta(days=ast.literal_eval(self.config['old_remove']))
        if not os.path.exists('../stream'):
            os.makedirs('../stream')

    def delete_old_db_records(self):
        self.mdb.client[self.mdb.config['INSTAGRAM_COLLECTION']].delete_many({'date': {'$lt': self.old_datetime.timestamp()}})
        self.mdb.client[self.mdb.config['FORECASTS_COLLECTION']].delete_many(
            {'date': {'$lt': self.old_datetime.timestamp()}})
        logging.info('old db records deleted')

    def delete_old_files(self):
        for file in glob.glob('../stream/*/*', recursive=True):
            if os.path.getmtime(file) < self.old_datetime.timestamp():
                os.remove(file)
        logging.info('old files deleted')

    def run(self):
        self.delete_old_db_records()
        self.delete_old_files()
        resource_class = RESOURCES.get(self.resource)
        if not resource_class:
            raise Exception(f'Resource {self.resource} not found')
        if resource_class == RESOURCES.get('instagram'):
            instant = resource_class(self.insta_resources)
            for insta_resource in instant.resources:
                logging.info(f'start to parse {insta_resource} instagram resource')
                scraped_objects = instant.get_new_posts(insta_resource)
                instant.process_posts(scraped_objects)
                logging.info(f'{insta_resource} instagram resource is parsed')
        else:
            instant = resource_class()
            scraped_objects = instant.scrape_forecasts(request_data=instant.request_data)
            instant.parse_forecasts(scraped_objects)
        logging.info(f'{self.resource} resource is parsed')

if __name__ == '__main__':
    args = sys.argv[1:]
    insta_resources = args[1:]
    resources = args[0]
    mh = ManagementHelper(resources, insta_resources)
    mh.run()