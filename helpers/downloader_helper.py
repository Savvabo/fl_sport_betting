import requests
from helpers.proxy_helper import ProxyHelper
import os
import csv
import logging
import random
from hashlib import sha256
import base64


class Downloader:
    def __init__(self, check_url, use_proxy=True, attempts=20, use_user_agents=True, use_session=False):
        self.check_url = check_url
        self.use_proxy = use_proxy
        self.use_session = use_session
        self.update_request_maker()
        self.proxy_helper = ProxyHelper(check_url, use_proxy)
        self.attempts = attempts
        self.use_user_agents = use_user_agents
        self.user_agents_list = self.load_user_agents()

    def update_request_maker(self):
        if self.use_session:
            self.request_maker = requests.Session()
        else:
            self.request_maker = requests

    def create_request(self, method, url, cookies=None, data={}, headers={}, timeout=60, files=None):
        @self.proxy_helper.exception_decorator
        def request_to_page(proxy, **kwargs):
            proxies = {'https': proxy, 'http': proxy}
            response = self.request_maker.request(proxies=proxies, **kwargs)
            if response.status_code >= 400:
                logging.debug('get 400 response_code')
                raise
            return response

        attempts = self.attempts
        while attempts > 0:

            if self.use_user_agents:
                headers.update({'user-agent': self.get_random_user_agent()})
            attempts -= 1
            # try without proxies last time
            raw_proxy = self.proxy_helper.get_proxy() if self.use_proxy and attempts != 1 else None
            if attempts == 1:
                raw_proxy = None
            elif attempts == 2:
                raw_proxy = '167.172.60.144:3128'
            try:
                request_response = request_to_page(proxy=raw_proxy,
                                                   method=method,
                                                   url=url,
                                                   cookies=cookies,
                                                   data=data,
                                                   headers=headers,
                                                   timeout=timeout,
                                                   files=files)
                return request_response
            except Exception as e:
                logging.debug('received exception on request on {} try'.format(self.attempts - attempts))

    def get(self, url, cookies=None, data={},  headers={}, timeout=60):
        return self.create_request(method='GET',
                                   url=url,
                                   cookies=cookies,
                                   data=data,
                                   headers=headers,
                                   timeout=timeout)

    def post(self, url, cookies=None, data={}, headers={}, timeout=60, files=None):
        return self.create_request(method='POST',
                                   url=url,
                                   cookies=cookies,
                                   data=data,
                                   headers=headers,
                                   timeout=timeout,
                                   files=files)

    @staticmethod
    def load_user_agents():
        cd = os.path.dirname(os.path.abspath(__file__))
        csvFile = os.path.join(cd, 'valid_user_agents.csv')
        with open(csvFile, 'r') as f:
            reader = csv.reader(f)
            user_agent_list = list(reader)
            user_agent_list = [x[0] for x in user_agent_list]
        return user_agent_list

    def get_random_user_agent(self):
        '''Get random user-agent'''
        try:
            user_agent = random.choice(self.user_agents_list)
            return user_agent
        except:
            logging.error('Cannot get random user-agent', exc_info=True)
            return ''

    def download_file(self, link, response_format, timeout=60):
        try:
            response = self.get(link, timeout=timeout)
            file_id = sha256(response.content).hexdigest() + f'.{response_format}'
            file = open(f'../stream/instagram/{file_id}', 'wb')
            file.write(response.content)
            file.close()
        except AttributeError:
            return None
        return file_id

    @staticmethod
    def download_logos(image, resource):
        image = image.split('base64,')[1]
        bytes_image = base64.b64decode(image)
        file_id = sha256(image.encode()).hexdigest() + '.png'
        file = open(f'../stream/{resource}/{file_id}', 'wb')
        file.write(bytes_image)
        file.close()
        return file_id
