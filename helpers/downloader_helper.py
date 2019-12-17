import requests
from helpers.proxy_helper import ProxyHelper
import os
import csv
import logging
import random
logging.basicConfig(format=u'%(filename)s[LINE:%(lineno)d]# %(levelname)-8s [%(asctime)s]  %(message)s',
                    level=logging.DEBUG)
logging.getLogger("requests").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)
logging.getLogger("connectionpool").setLevel(logging.WARNING)


class Downloader:
    def __init__(self, use_proxy=True, attempts=20, use_user_agents=True, use_session=False):
        self.use_proxy = use_proxy
        self.request_maker = requests.Session() if use_proxy else requests
        self.use_session = use_session
        if use_proxy:
            self.proxy_helper = ProxyHelper()
        self.attempts = attempts
        self.use_user_agents = use_user_agents
        self.user_agents_list = self.load_user_agents()

    def create_request(self, method, url, cookies={}, data={}, headers={}, timeout=60, files=None, top_proxies=100):
        @self.proxy_helper.exception_decorator
        def request_to_page(proxy, **kwargs):
            proxies = {'https': proxy, 'http': proxy}
            response = self.request_maker.request(proxies=proxies, **kwargs)
            if response.status_code >= 400:
                logging.debug('get 400 response_code')
                raise
            return response

        if self.use_user_agents:
            headers.update({'user-agent': self.get_random_user_agent()})
        attempts = self.attempts
        while attempts > 0:
            attempts -= 1
            # try without proxies last time
            raw_proxy = self.proxy_helper.get_proxy(top_proxies) if self.use_proxy and attempts != 1 else None
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

    def get(self, url, cookies={}, data={},  headers={}, timeout=60, top_proxies=100):
        return self.create_request(method='GET',
                                   url=url,
                                   cookies=cookies,
                                   data=data,
                                   headers=headers,
                                   timeout=timeout,
                                   top_proxies=top_proxies)

    def post(self, url, cookies={}, data={}, headers={}, timeout=60, files=None, top_proxies=100):
        return self.create_request(method='POST',
                                   url=url,
                                   cookies=cookies,
                                   data=data,
                                   headers=headers,
                                   timeout=timeout,
                                   files=files,
                                   top_proxies=top_proxies)

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