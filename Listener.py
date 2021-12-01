import datetime
import logging
import threading
import random
from requests import get
from dateutil import parser
from bs4 import BeautifulSoup
import time

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

formatter = logging.Formatter('%(asctime)s:%(name)s:%(levelname)s:%(message)s')

file_handler = logging.FileHandler('listener.log')
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(formatter)

logger.addHandler(file_handler)

# --------------------


class Listener():

    def __init__(self, user_links=None):
        self._is_started = False
        self._start_time = None
        self._last_query_time = None
        self._links_to_query = user_links or {}
        self._secs_to_next_query = 300
        self._next_query_base_secs = 420
        self._last_query_results = []
        self._parsersDispatcher = {
            'craigslist': self.__parseCraigsList,
        }

        self._first_start = True
        self._previous_ids = []


    def start(self, container=None):
        self._is_started = True
        self._first_start = True

        self._start_time = datetime.datetime.now()
        self._last_query_time = datetime.datetime.now()

        self._tread = threading.Thread(target=self.query_loop, args=[container])
        self._tread.start()


    def query_loop(self, container=None):
        while self._is_started:
            logger.debug('New query loop run')
            self.__query()
            if container != None: container.extend(self._last_query_results)

            self._secs_to_next_query = self._next_query_base_secs + random.randint(-10, 60)
            time.sleep(self._secs_to_next_query)


    def stop(self):
        self._is_started = False
        self._first_start = False


    def add(self, name, link):
        if name in self._links_to_query.keys():
            logger.error(f"couldn't add new link {name} already exist!")
            return None
        self._links_to_query[name] = link

        # if already running
        if self._is_started:
            resp = get(link)
            results = None
            if resp.status_code == 200:
                results = self.__parse(resp)
            else:
                logger.error(f'Server returned status code {resp.status_code}. skipping {name} query')
            self._previous_ids.extend([x['id'] for x in results])

        return 1


    def remove(self, name):
        if name in self._links_to_query.keys():
            return self._links_to_query.pop(name)
        else: return None


    def list(self):
        for name, link in self._links_to_query.items():
            logger.info(f'In list: {name}: {link}')
        return self._links_to_query


    def setWaitingTime(self):
        pass


    def uptime(self):
        print(datetime.datatime.now() - self._start_time)


    def get_last_query_postings(self):
        logger.debug(f'Returning last query results')
        return self._last_query_results


    def is_running(self):
        return self._is_started

    # this could be a sepparate class of parcers for different web pages
    # and every instance of listener could attach a unique parcer to it
    def __query(self):
        tmp_query_start_time = datetime.datetime.now() # to include time between start and queries finish
        tmp_query_results = []
        tmp_new_ids = []

        for name, link in self._links_to_query.items():
            linkSplit = link.split('://')[1].split('/')[0].split('.')
            web_src = [src for src in linkSplit if src in self._parsersDispatcher.keys()]
            if len(web_src) < 1:
                logger.error(f'skipping.. Couldn\'t find a parser for the {link}')
                continue
            if len(web_src) > 1: logger.error(f'Multiple parser found, something went wrong with {link}')
            web_src = web_src[0]

            try:
                resp = get(link)
            except Exception as e:
                logger.error(f'Request failed')
                logger.exception(e)
                return

            results = None
            if resp.status_code == 200:
                try:
                    results = self._parsersDispatcher[web_src](resp)
                except:
                    logger.error(f'Something went wrong during html parcing for {link}')
                    continue
            else:
                logger.error(f'Server returned status code {resp.status_code}. skipping {name} query')
                continue

            tmp_new_ids.extend([x['id'] for x in results])

            if not self._first_start:
                # tmp_query_results.extend(list(filter(lambda x: x['date'] > self._last_query_time, results)))
                filtered_results = list(filter(lambda x: x['id'] not in self._previous_ids, results))
                tmp_query_results.extend(filtered_results)
                logger.debug(f"Number of new postings for {name}: {len(filtered_results)}")

        logger.debug(f'Checked postings on: {datetime.datetime.now()}\n')

        self._last_query_results = tmp_query_results
        self._last_query_time = tmp_query_start_time
        self._previous_ids = tmp_new_ids
        self._first_start = False


    def __parseCraigsList(self, resp):
        html_soup = BeautifulSoup(resp.text, 'html.parser')
        posts = html_soup.find_all('li', class_= 'result-row')
        results = []

        for post in posts:
            post_one_price_raw = post.find(class_='result-price')
            post_one_price = post_one_price_raw.text if post_one_price_raw else 'No Info'
            post_one_title_raw = post.find('a', class_='result-title hdrlnk')
            post_one_title = post_one_title_raw.text if post_one_title_raw else 'No Info'
            post_one_link_raw = post.find('a', class_='result-title hdrlnk')
            post_one_link = post_one_link_raw['href'] if post_one_link_raw else 'No Info'
            post_one_date_raw = post.find('time', class_='result-date')
            post_one_date = parser.parse(post_one_date_raw['datetime']) if post_one_date_raw else 'No Info'
            post_one_id_raw = post.find('a', class_='result-title hdrlnk')
            post_one_id = post_one_id_raw['data-id'] if post_one_id_raw else 'No Info'

            results.append({
                'title': post_one_title,
                'price': post_one_price,
                'link': post_one_link,
                'date': post_one_date,
                'id': post_one_id,
            })

        return results



# TEST

# test = Listener()
# test.add('MDX', 'https://sfbay.craigslist.org/search/cta?query=acura+Mdx&sort=rel&purveyor-input=all&srchType=T&hasPic=1&min_price=4000&max_price=15000')
# test.start()
# time.sleep(25)
# test.add('RDX', 'https://sfbay.craigslist.org/search/cta?query=acura+Mdx&sort=rel&purveyor-input=all&srchType=T&hasPic=1&min_price=4000&max_price=15000')
# time.sleep(65)
# test.stop()
#
#
# print(f'stopped {datetime.datetime.now()}')
# time.sleep(35)
# print(f'sarted again {datetime.datetime.now()}')
#
# test.start()
# time.sleep(45)
# test.stop()
#
# print(f'stopped 2 {datetime.datetime.now()}')