import configparser
from instagram import Account, WebAgent, WebAgentAccount
from instagram.exceptions import InternetException, UnexpectedResponse
from mongodb_storage import MDB
from multiprocessing.pool import ThreadPool
import logging
from proxy_helper import ProxyHelper
import random
import traceback
import requests
import time
logging.basicConfig(format=u'%(filename)s[LINE:%(lineno)d]# %(levelname)-8s [%(asctime)s]  %(message)s',
                    level=logging.DEBUG)
logging.getLogger("requests").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)
logging.getLogger("connectionpool").setLevel(logging.WARNING)



class InstagramParser:
    def __init__(self, resources):
        self.config = configparser.ConfigParser()
        self.config.read('config.ini')
        self.resources = resources
        self.anon_agent = WebAgent()
        self.agent = WebAgentAccount(self.config['instagram']['LOGIN'])
        self.agent.auth(self.config['instagram']['PASSWORD'])
        self.mdb = MDB()
        self.proxy_list = self.get_proxies()
        self.use_proxy = False



    @staticmethod
    def chunkify(l, n):
        for i in range(0, len(l), n):
            yield l[i:i + n]

    def check_proxy(self, proxy):
        try:
            t1 = time.time()
            requests.get('https://www.instagram.com', proxies={
                "http": proxy,
                "https": proxy,
            }, timeout=5)
            request_time = time.time() - t1
            return {'address': proxy, 'is_valid': True, 'request_time': request_time}

            # return {'address': proxy, 'is_valid': True}
        except:
            return {'address': proxy, 'is_valid': False}

    def to_sort_def(self, item):
        if len(item[1]['insta_request_times']) >= 10:
            return sum(item[1]['insta_request_times']) / len(item[1]['insta_request_times'])
        else:
            return item[1]['check_request_time']

    def sort_proxies(self, proxies_list=None):
        chosen_proxies_list = proxies_list if proxies_list else self.proxy_list
        sorted_proxies = {k: v for k, v in sorted(chosen_proxies_list.items(), key=self.to_sort_def)}
        return sorted_proxies

    def get_proxies(self):
        raw_proxies = ProxyHelper().load_proxies_list()
        chunks = list(self.chunkify(raw_proxies, 500))
        valid_proxies = {}
        for n, chunk in enumerate(chunks):
            logging.info('checking {}/{} proxy batch'.format(n+1, len(chunks)))
            proxy_pool = ThreadPool(50)
            checked_proxies = list(proxy_pool.map(self.check_proxy, chunk))
            proxy_pool.close()
            valid_batch_proxies = {proxy['address']: {'check_request_time': proxy['request_time'],
                                                      'error_count': 0,
                                                      'insta_request_times': []} for proxy in checked_proxies if proxy['is_valid']}
            valid_proxies.update(valid_batch_proxies)
        valid_proxies = self.sort_proxies(valid_proxies)
        logging.info('found {} valid proxies'.format(len(valid_proxies)))
        return valid_proxies

    def mark_proxy_as_failed(self, proxy):
        try:
            self.proxy_list[proxy]['error_count'] += 1
        except KeyError:
            pass
        if self.proxy_list.get(proxy, {}).get('error_count') == 5:
            try:
                self.proxy_list.pop(proxy)
            except KeyError:
                pass
        if len(self.proxy_list) == 0:
            logging.info('proxy list is empty, getting new proxies')
            self.proxy_list = self.get_proxies()

    def get_settings(self, proxies_top_perc=100):
        if self.use_proxy and time.time() - self.previous_local_request < 11 * 60:
            self.sort_proxies()
            list_stop_index = int(len(self.proxy_list)//(100/proxies_top_perc))
            chosen_proxy = random.choice(list(self.proxy_list.keys())[:list_stop_index])
        else:
            chosen_proxy = None
            if self.use_proxy:
                self.use_proxy = False
                logging.info('stop to use proxies')
        settings = {
            "proxies": {
                "http": chosen_proxy,
                "https": chosen_proxy,
            }, 'timeout': 60}
        return chosen_proxy, settings

    def insta_request(self, pointer=None, data=None):
        chosen_proxy, settings = self.get_settings(proxies_top_perc=8)
        posts = None
        while True:
            try:
                if data:
                    self.anon_agent.update(data, settings=settings)
                    break
                else:
                    t1 = time.time()
                    posts, pointer = self.anon_agent.get_media(self.resource, pointer=pointer, settings=settings, delay=1)
                    request_time = time.time() - t1
                    if chosen_proxy:
                        self.proxy_list[chosen_proxy]['insta_request_times'].append(request_time)
                    break
            except (InternetException, UnexpectedResponse):
                logging.info('removing proxy')
                if chosen_proxy:
                    self.mark_proxy_as_failed(chosen_proxy)
                else:
                    self.use_proxy = True
                    self.previous_local_request = time.time()
                    logging.info('starting to use proxies')
                chosen_proxy, settings = self.get_settings(proxies_top_perc=8)
        if posts:
            return posts, pointer

    def get_new_posts(self):
        stored_posts = self.get_parsed_posts()
        new_posts = []
        pointer = None
        self.insta_request(data=self.resource)
        posts_count = self.resource.media_count
        posts_scraped = 0
        while posts_count > posts_scraped:
            try:
                posts, pointer = self.insta_request(pointer=pointer)
                posts_scraped += len(posts)
                logging.info(f'scraper {posts_scraped} posts')
                for post in posts:
                    if post.__str__() not in stored_posts:
                        new_posts.append(post)
                    else:
                        raise StopIteration
            except StopIteration:
                break
        return new_posts

    def get_parsed_posts(self):
        return self.mdb.get_instagram_posts(self.resource.__str__())

    def parse_album(self, album):
        album_data = dict()
        album_pages = []
        for album_page in album.album:
            self.insta_request(data=album_page)
            album_pages.append(album_page.resources[-1])
        album_data['album_pages'] = album_pages
        return album_data

    def parse_video(self, video):
        video_data = dict()
        video_data['video_url'] = video.video_url
        return video_data

    def parse_singe_post(self, single_post):
        single_post_data = dict()
        return single_post_data

    def get_mandatory_post_data(self, post):
        post_data = dict()
        post_data['_id'] = post.__str__()
        post_data['preview_image'] = post.resources[-1]
        post_data['description'] = post.caption
        post_data['date'] = post.date
        post_data['liked_count'] = post.likes_count
        post_data['link'] = 'https://www.instagram.com/p/{post_id}'.format(post_id=post_data['_id'])
        post_data['resource'] = self.resource.__str__()
        return post_data

    def parse_post(self, post):
        logging.debug(post.__str__())
        self.insta_request(data=post)
        post_data = self.get_mandatory_post_data(post)
        if post.is_album:
            post_data.update(self.parse_album(post))
        elif post.is_video:
            post_data.update(self.parse_video(post))
        else:
            post_data.update(self.parse_singe_post(post))
        return post_data

    def process_posts(self, posts):
        chunks = list(self.chunkify(posts, 500))
        for n, chunk in enumerate(chunks):
            logging.info('processing {}/{} posts batch'.format(n + 1, len(chunks)))
            pool = ThreadPool(50)
            parsed_posts = pool.map(self.parse_post, chunk)
            self.mdb.add_new_posts(parsed_posts)
            pool.close()

    def run(self):
        for resource in self.resources:
            logging.info(f'start to parse {resource} resource')
            self.resource = Account(resource)
            new_posts = self.get_new_posts()
            self.process_posts(new_posts)
            logging.info(f'{resource} resource is parsed')




InstagramParser(['bogunsa', 'sportsru']).run()

