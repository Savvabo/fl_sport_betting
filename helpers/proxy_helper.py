import requests
import logging
import time
from helpers.helpers import chunkify, parse_config
from multiprocessing.pool import ThreadPool
from threading import Lock
from requests.exceptions import ProxyError, ConnectTimeout
from instagram.exceptions import InternetException, UnexpectedResponse
import pandas as pd


class ProxyHelper:
    def __init__(self, check_url, use_proxy=True):
        self.check_url = check_url
        self.config = parse_config('server')
        if use_proxy:
            self.get_valid_proxies()
        self.lock = Lock()

    def mark_proxy_as_failed(self, proxy):
        self.proxies.at[proxy, 'error_count'] += 1
        self.proxies.at[proxy, 'previous_error_time'] = time.time()
        if int(self.proxies.at[proxy, 'error_count']) == 5:
            logging.info('removing proxy {}'.format(proxy))
            self.proxies = self.proxies.drop(index=proxy)
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
                        self.proxies.at[proxy, 'on_work'] = False
                        self.proxies.at[proxy, 'previous_request_time'] = request_time
                return result
            except Exception as e:
                if proxy:
                    with self.lock:
                        if isinstance(e, (ProxyError, ConnectTimeout, InternetException, UnexpectedResponse)):
                            self.mark_proxy_as_failed(proxy)
                        self.proxies.at[proxy, 'on_work'] = False
                raise
        return wrapper

    def get_proxy(self):
        attempt = 0
        while True:
            try:
                with self.lock:
                    self.sort_proxies()
                    chosen_proxy = list(self.proxies.loc[(self.proxies['on_work'] == False) & (time.time() - self.proxies['previous_error_time'] > 60)].iterrows())[0][0]
                    self.proxies.at[chosen_proxy, 'on_work'] = True
                    break
            except IndexError:
                logging.debug(f"Can\'t get proxy on {attempt} retry")
                time.sleep(0.5)
                attempt += 1
        return chosen_proxy

    def sort_proxies(self):
        self.proxies = self.proxies.sort_values('on_work').sort_values('previous_request_time')
        return

    def get_valid_proxies(self):
        proxies_list = self.get_proxies_list()
        chunks = list(chunkify(proxies_list, 500))
        valid_proxies = {}
        for n, chunk in enumerate(chunks):
            logging.info('checking {}/{} proxy batch'.format(n + 1, len(chunks)))
            proxy_pool = ThreadPool(100)
            checked_proxies = list(proxy_pool.map(self.check_proxy, chunk))
            proxy_pool.close()
            valid_batch_proxies = {proxy['address']: {'previous_request_time': proxy['request_time'],
                                                      'error_count': 0,
                                                      'on_work': False,
                                                      'previous_error_time': 0} for proxy in checked_proxies if
                                   proxy['is_valid']}
            valid_proxies.update(valid_batch_proxies)
        self.proxies = pd.DataFrame.from_dict(valid_proxies, orient='index')
        logging.info('proxy checking finished, found {} valid proxies'.format(len(self.proxies)))
        self.sort_proxies()

    def check_proxy(self, proxy):
        try:
            t1 = time.time()
            requests.get(self.check_url, proxies={
                "http": proxy,
                "https": proxy,
            }, timeout=10)
            request_time = time.time() - t1
            return {'address': proxy, 'is_valid': True, 'request_time': request_time}
        except:
            return {'address': proxy, 'is_valid': False}

    def get_proxies_list(self):
        '''Return list of proxies'''
        key = self.config['proxy_key']
        proxies_list = self.load_proxies_list(key)
        if len(proxies_list) == 0:
            logging.error('get 0 proxies, get them from hardcoded')
            proxies_list_hardcoded = ['104.144.176.107:3128',
                                      '104.227.106.190:3128',
                                      '107.152.145.103:3128',
                                      '216.246.49.123:3128',
                                      '23.94.21.30:3128']
            proxies_list.extend(proxies_list_hardcoded)

        return proxies_list

    def load_proxies_list(self, key):
        proxies_list = []
        try:
            api_url = f'https://api.best-proxies.ru/proxylist.txt?key={key}&type=http,https&limit=0'
            r = requests.get(api_url, timeout=60)
            if r.status_code == 200:
                proxies_list = r.text.split('\r\n')
        except:
            pass
        return proxies_list
