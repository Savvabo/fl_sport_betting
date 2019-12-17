import requests
import logging
import time
from helpers.helpers import chunkify
from multiprocessing.pool import ThreadPool
from threading import Lock
import random

from requests.exceptions import ProxyError, ConnectTimeout
logging.basicConfig(format=u'%(filename)s[LINE:%(lineno)d]# %(levelname)-8s [%(asctime)s]  %(message)s',
                    level=logging.DEBUG)
logging.getLogger("requests").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)
logging.getLogger("connectionpool").setLevel(logging.WARNING)


class ProxyHelper:
    def __init__(self):
        #self.project_type = project_type
        self.proxies = self.get_valid_proxies()
        self.lock = Lock()

    def mark_proxy_as_failed(self, proxy):
        with self.lock:
            self.proxies[proxy]['error_count'] += 1
            self.proxies[proxy]['previous_error_time'] = time.time()
            self.proxies[proxy]['on_work'] = False
            if self.proxies[proxy]['error_count'] == 5:
                logging.info('removing proxy {}'.format(self.proxies['proxy']))
                self.proxies.pop(proxy)
            if len(self.proxies) == 0:
                logging.info('proxy list is empty, getting new proxies')
                self.proxies = self.get_valid_proxies()

    def exception_decorator(self, func):
        def wrapper(*args, proxy, **kwargs):
            try:
                request_start_time = time.time()
                result = func(proxy, *args, **kwargs)
                request_time = time.time() - request_start_time
                if proxy:
                    with self.lock:
                        self.proxies[proxy]['on_work'] = False
                        self.proxies[proxy]['work_request_times'].append(request_time)
                return result
            except Exception as e:
                if isinstance(e, (ProxyError, ConnectTimeout)) and proxy:
                    self.mark_proxy_as_failed(proxy)
                raise
        return wrapper

    def get_proxy(self, proxies_top_perc=100):
        proxy_to_use = None
        list_stop_index = int(len(self.proxies) // (100 / proxies_top_perc))
        if list_stop_index == 0:
            list_stop_index = 1
        with self.lock:
            self.sort_proxies()
        while not proxy_to_use:
            chosen_proxy = random.choice(list(self.proxies.items())[:list_stop_index])
            if not chosen_proxy[1]['on_work'] and time.time() - chosen_proxy[1]['previous_error_time'] > 10:
                with self.lock:
                    self.proxies[chosen_proxy[0]]['on_work'] = True
                proxy_to_use = chosen_proxy[0]
        return proxy_to_use

    @staticmethod
    def to_sort_def(item):
        if len(item[1]['work_request_times']) >= 10:
            return sum(item[1]['work_request_times']) / len(item[1]['work_request_times'])
        else:
            return item[1]['check_request_time']

    def sort_proxies(self, proxies_list=None):
        chosen_proxies_list = proxies_list if proxies_list else self.proxies
        sorted_proxies = {k: v for k, v in sorted(chosen_proxies_list.items(), key=self.to_sort_def)}
        return sorted_proxies

    def get_valid_proxies(self):
        proxies_list = self.get_proxies_list()[:500]
        chunks = list(chunkify(proxies_list, 500))
        valid_proxies = {}
        for n, chunk in enumerate(chunks):
            logging.info('checking {}/{} proxy batch'.format(n + 1, len(chunks)))
            proxy_pool = ThreadPool(100)
            checked_proxies = list(proxy_pool.map(self.check_proxy, chunk))
            proxy_pool.close()
            valid_batch_proxies = {proxy['address']: {'check_request_time': proxy['request_time'],
                                                      'error_count': 0,
                                                      'work_request_times': [],
                                                      'on_work': False,
                                                      'previous_error_time': 0} for proxy in checked_proxies if
                                   proxy['is_valid']}
            valid_proxies.update(valid_batch_proxies)
        logging.info('proxy checking finished, found {} valid proxies'.format(len(valid_proxies)))
        sorded_proxies = self.sort_proxies(valid_proxies)
        return sorded_proxies

    @staticmethod
    def check_proxy(proxy):
        try:
            t1 = time.time()
            requests.get('https://www.google.com', proxies={
                "http": proxy,
                "https": proxy,
            }, timeout=5)
            request_time = time.time() - t1
            return {'address': proxy, 'is_valid': True, 'request_time': request_time}

        except:
            return {'address': proxy, 'is_valid': False}

    def get_proxies_list(self):
        '''Return list of proxies'''
        proxies_list = self.load_proxies_list()
        if len(proxies_list) == 0:
            logging.error('get 0 proxies, get them from hardcoded')
            proxies_list_hardcoded = ['104.144.176.107:3128',
                                      '104.227.106.190:3128',
                                      '107.152.145.103:3128',
                                      '216.246.49.123:3128',
                                      '23.94.21.30:3128']
            proxies_list.extend(proxies_list_hardcoded)

        return proxies_list

    @staticmethod
    def load_proxies_list():
        proxies_list = []
        try:
            api_url = 'http://64.140.158.34:5000/proxy'
            r = requests.get(api_url, timeout=60)
            if r.status_code == 200:
                proxies_list = r.json()
        except:
            pass
        return proxies_list
