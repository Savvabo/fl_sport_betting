import configparser
from instagram import Account, WebAgent, WebAgentAccount
from instagram.exceptions import InternetException, UnexpectedResponse
from mongodb_storage import MDB
from multiprocessing.pool import ThreadPool
import logging
from proxy_helper import ProxyHelper
import random
import traceback

logging.basicConfig(format=u'%(filename)s[LINE:%(lineno)d]# %(levelname)-8s [%(asctime)s]  %(message)s',
                    level=logging.DEBUG)
logging.getLogger("requests").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)


class InstagramParser:
    def __init__(self, resource):
        self.config = configparser.ConfigParser()
        self.config.read('config.ini')
        self.resource = Account(resource)
        self.anon_agent = WebAgent()
        self.agent = WebAgentAccount(self.config['instagram']['LOGIN'])
        self.agent.auth(self.config['instagram']['PASSWORD'])
        self.mdb = MDB()
        self.proxy_list = ProxyHelper().load_proxies_list()

    def mark_proxy_as_failed(self, proxy):
        try:
            self.proxy_list.remove(proxy)
        except ValueError:
            pass
        if len(self.proxy_list) == 0:
            logging.info('proxy list is empty, getting new proxies')
            self.proxy_list = ProxyHelper().load_proxies_list()

    def insta_request(self, pointer=None, data=None):
        settings = {}
        chosen_proxy = None
        while True:
            try:
                if data:
                    self.anon_agent.update(data, settings=settings)
                    return
                else:
                    posts, pointer = self.anon_agent.get_media(self.resource, pointer=pointer, settings=settings)
                    return posts, pointer
            except (InternetException, UnexpectedResponse):
                if chosen_proxy:
                    self.mark_proxy_as_failed(chosen_proxy)
                chosen_proxy = random.choice(self.proxy_list)
                settings = {
                    "proxies": {
                        "http": chosen_proxy,
                        "https": chosen_proxy,
                    },
                    'timeout': 15}

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
                posts_scraped += 12
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
        pool = ThreadPool(1)
        parsed_posts = pool.map(self.parse_post, posts)
        self.mdb.add_new_posts(parsed_posts)

    def run(self):
        new_posts = self.get_new_posts()
        self.process_posts(new_posts)




InstagramParser('sportsru').run()

