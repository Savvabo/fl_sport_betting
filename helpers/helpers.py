import configparser


def parse_config(part):
    config = configparser.ConfigParser()
    config.read('../config.ini')
    if part != 'ALL':
        config = config[part]
    return config


def chunkify(l, n):
    for i in range(0, len(l), n):
        yield l[i:i + n]


HEADERS = [{
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_12_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/61.0.3163.100 Safari/537.36',
    'Accept': 'application/json,text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'en-us',
    'Accept-Encoding': 'gzip, deflate',
    'Content-Type': 'application/json,text/html,application/x-www-form-urlencoded'
},
    {
    'User-Agent': "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.12; rv:50.0) Gecko/20100101 Firefox/50.0",
    'Accept': "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    'Accept-Language': "en-US;q=0.7,en;q=0.3",
    'Accept-Encoding': "gzip, deflate",
    'cache-control': "no-cache",
    'Connection': "keep-alive"
}
]