import requests

class Downloader:

    def get(self, url):
        response = requests.get(url)
        return response