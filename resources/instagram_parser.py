from instagram import Account, WebAgent, WebAgentAccount
from instagram.exceptions import InternetException, UnexpectedResponse
from storage.mongodb_storage import MongoDBStorage
from multiprocessing.pool import ThreadPool
import logging
from helpers.downloader_helper import Downloader
import ast
import time
from helpers.helpers import parse_config, chunkify
import os
import datetime


class InstagramParser:
    def __init__(self, resources):
        self.config = parse_config('instagram')
        self.resources = resources
        self.anon_agent = WebAgent()
        self.agent = {'agent': self.anon_agent, 'set_time': time.time()}
        # self.logged_agent = WebAgentAccount(self.config['LOGIN'])
        # self.logged_agent.auth(self.config['PASSWORD'])
        self.logged_agent = self.anon_agent
        self.agent = {'agent': self.logged_agent, 'set_time': time.time()}

        self.mdb = MongoDBStorage()
        self.downloader = Downloader('https://www.instagram.com')
        self.proxy_helper = self.downloader.proxy_helper
        self.use_proxy = False
        self.date_limit = False
        self.old_datetime = datetime.datetime.now() - datetime.timedelta(
            days=ast.literal_eval(self.config['scraping_date_limit']))
        if not os.path.exists('../stream/instagram'):
            os.makedirs('../stream/instagram')

    def get_settings(self, request_start_time,  proxy_only=False):
        if proxy_only or self.use_proxy and time.time() - self.previous_local_request < 11 * 60:
            chosen_proxy = self.proxy_helper.get_proxy()
        else:
            chosen_proxy = None
            if self.use_proxy and self.agent['set_time'] < request_start_time:
                with self.proxy_helper.lock:
                    self.agent = {'agent': self.anon_agent, 'set_time': time.time()}
                    self.use_proxy = False
                    logging.info('stop to use proxies')
        settings = {
            "proxies": {
                "http": chosen_proxy,
                "https": chosen_proxy,
            }, 'timeout': 30}
        return chosen_proxy, settings

    def swap_agent(self):
        if self.agent == self.anon_agent:
            self.agent = {'agent': self.logged_agent, 'set_time': time.time()}
        else:
            self.agent = {'agent': self.anon_agent, 'set_time': time.time()}

    def insta_request(self, pointer=None, data=None, proxy_only=False):
        @self.proxy_helper.exception_decorator
        def request_to_instagram(proxy, setting, pointer=None,posts=None):
            if data:
                self.agent['agent'].update(data, settings=setting)
            else:
                posts, pointer = self.agent['agent'].get_media(self.resource, pointer=pointer, settings=setting, delay=1)
            return posts, pointer
        request_start_time = time.time()
        while True:
            chosen_proxy, settings = self.get_settings(proxy_only=proxy_only, request_start_time=request_start_time)
            request_start_time = time.time()
            try:
                posts, pointer = request_to_instagram(proxy=chosen_proxy, setting=settings, pointer=pointer)
                break
            except (InternetException, UnexpectedResponse) as e:
                with self.proxy_helper.lock:
                    if self.agent['set_time'] < request_start_time:
                        if isinstance(e, UnexpectedResponse):
                            self.swap_agent()
                        if not chosen_proxy:
                            self.use_proxy = True
                            self.previous_local_request = time.time()
                            logging.info('start to use proxies')
                            self.agent = {'agent': self.logged_agent, 'set_time': time.time()}
        if posts:
            return posts, pointer

    def get_new_posts(self, resource):
        self.resource = Account(resource)
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
        video_data['video_url'] = self.downloader.download_file(video.video_url, 'mp4')
        return video_data

    def parse_singe_post(self, single_post):
        single_post_data = dict()
        return single_post_data

    def get_mandatory_post_data(self, post):
        post_data = dict()
        post_data['_id'] = post.__str__()
        post_data['preview_image'] = self.downloader.download_file(post.resources[-1], 'jpg') if post.is_video else post.resources[-1]
        post_data['description'] = post.caption
        post_data['date'] = post.date
        post_data['likes_count'] = post.likes_count
        post_data['link'] = 'https://www.instagram.com/p/{post_id}'.format(post_id=post_data['_id'])
        post_data['resource'] = self.resource.__str__()
        post_data['icon'] = self.resource.profile_pic_url
        post_data['is_album'] = post.is_album
        post_data['is_video'] = post.is_video

        return post_data

    def parse_post(self, post):
        self.insta_request(data=post)
        post_data = self.get_mandatory_post_data(post)
        if post_data['date'] < self.old_datetime.timestamp():
            self.date_limit = True
        if post.is_album:
            post_data.update(self.parse_album(post))
        elif post.is_video:
            post_data.update(self.parse_video(post))
        else:
            post_data.update(self.parse_singe_post(post))
        return post_data

    def process_posts(self, posts):
        pool_size = ast.literal_eval(self.config['pool_size'])
        chunks = list(chunkify(posts, pool_size))
        for n, chunk in enumerate(chunks):
            logging.info('processing {}/{} posts batch'.format(n + 1, len(chunks)))
            chunk = chunk[::-1]
            pool = ThreadPool(pool_size)
            parsed_posts = [post for post in pool.map(self.parse_post, chunk) if post['date'] > self.old_datetime.timestamp()]
            pool.close()
            self.mdb.add_new_posts(parsed_posts)
            if self.date_limit:
                logging.info('instagram resource {} reach day limit'.format(self.resource))
                return

    def run(self):
        for resource in self.resources:
            logging.info(f'start to parse {resource} instagram resource')
            self.resource = Account(resource)
            new_posts = self.get_new_posts()
            self.process_posts(new_posts)
            logging.info(f'{resource} instagram resource is parsed')

if __name__ == '__main__':
    InstagramParser(['fcsm_official']).run()
