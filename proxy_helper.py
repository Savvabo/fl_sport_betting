import requests


class ProxyHelper:

    def get_proxies_list(self):
        '''Return list of proxies'''
        proxies_list = self.load_proxies_list()
        if len(proxies_list) == 0:
            proxies_list_hardcoded = ['104.144.176.107:3128', '104.227.106.190:3128', '107.152.145.103:3128', '216.246.49.123:3128', '23.94.21.30:3128']
            proxies_list.extend(proxies_list_hardcoded)
        return proxies_list

    def load_proxies_list(self):
        '''Load proxies from API and save to redis.'''
        proxies_list = []
        try:
            api_url = 'http://64.140.158.34:5000/proxy'
            r = requests.get(api_url, timeout=60)
            if r.status_code == 200:
                proxies_list = r.json()
        except:
            pass
        return proxies_list
