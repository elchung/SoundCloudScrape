'''
saved data should be in 2 dataases. Users and Tracks,  whwere each key is the unique ID, and the value is a dictionary of information that gets saved

Add User to queue, For each user, look at their favorited tracks and add to track_queue
for every track in track queue, look at users who have favorited this track and add to user_queue
'''

import soundcloud
import threading  # using threading instead of processing since most of the delays will be waiting for network response
import time
from queue import Queue
from pymongo import MongoClient
import logging
import random

# logging.basicConfig(filename="SC_Logs.log", format='%(asctime)s %(message)s', filemode='w')
logging.basicConfig()
logger = logging.getLogger()
logger.setLevel(logging.INFO)


class SoundCloudScraper:
    def __init__(self, client_id, client_secret, double_threads=3, test_timeout=float('inf'), thread_timeout=10):
        self.client = soundcloud.Client(client_id=client_id, client_secret=client_secret)
        self.dbclient = MongoClient()
        self.db = self.dbclient.sc_scrape
        self.user_db = self.db.sc_user_db
        self.track_db = self.db.sc_track_db
        self.user_q = Queue()
        self.track_q = Queue()
        self.user_q_lock = threading.Lock()
        self.track_q_lock = threading.Lock()
        self.user_db_lock = threading.Lock()
        self.track_db_lock = threading.Lock()
        self.time_lock = threading.Lock()
        self.last_sc_query = time.time()
        self.num_user_threads = double_threads
        self.num_track_threads = double_threads
        self.threads = []
        self.test_timeout = test_timeout

        self.user_q_db = self.db.sc_user_q_db
        self.track_q_db = self.db.sc_track_q_db
        self.current_process_count = 0
        self.sc_call_lock = threading.Lock()
        self.num_sc_calls = 0
        self.max_sc_calls = 5000

        self.timeout_time = thread_timeout  # set timeout to default 10 min

        self.last_call_time = time.time()  # prevent DDoSing SoundCloud
    #
    # def clear_dbs(self):
    #     # test method to clear created dbs
    #     self.user_db.drop()
    #     self.track_db.drop()

    def start_scraping(self):
        for thread in range(self.num_track_threads):
            t = threading.Thread(target=self.process_tracks)  # , arg=(thread,))
            t.setDaemon(True)
            logging.debug(f"Spinning up thread {thread} for tracks")
            t.start()
            self.threads.append(t)
        for thread in range(self.num_user_threads):
            t = threading.Thread(target=self.process_users)  # , arg=(thread,))
            t.setDaemon(True)
            logging.debug(f"Spinning up thread {thread} for users")
            t.start()
            self.threads.append(t)
        ct = time.time()
        counter = 0
        while time.time() - self.last_call_time < self.test_timeout:  # test run for 30 seconds
            if time.time() - ct > 5:
                counter += 5
                logging.info(f"Users Processed for this instance after {counter} seconds: {self.current_process_count}")
                logging.info(f"Current SC Calls: {self.num_sc_calls}")
                ct = time.time()
                print(f"Users Processed for this instance after {counter} seconds: {self.current_process_count}")
            if self.num_sc_calls >= self.max_sc_calls:
                sys.exit()
        return

    def process_users(self):
        print("Starting process users")
        file_processed, timeout_start = False, time.time()
        while 1:  # if thread has been sitting empty for 10 minutes, kill
            if file_processed:
                timeout_start = time.time()  # reset timeout time if new file processed in this thread
            elif time.time() - timeout_start >= self.timeout_time:
                return

            user = self.get_next_user()
            if not user:
                file_processed = False
            else:
                logging.info(f"Processing user: {user}")
                self.current_process_count += 1
                file_processed = True
                data = self.get_user_data(user)
                with self.user_db_lock:
                    self.user_db.insert_one(data)
                with self.track_q_lock:  # get all favorited tracks by user and put unprocessed tracks into queue
                    for track in data['favorites']:  # tracks in data['favorites'] are saved as int ids
                        if not self.track_db.find_one({"_id": track}) and not self.track_q_db.find_one({"_id": track}):  # if not in track database and q
                            # logging.info(f"Adding track {track} to track queue")
                            self.track_q_db.insert_one({"_id": track})

    def process_tracks(self):
        print("Starting process tracks")
        file_processed, timeout_start = False, time.time()
        while 1:  # if thread has been sitting empty for 10 minutes, kill
            if file_processed:
                timeout_start = time.time()
            elif time.time() - timeout_start >= self.timeout_time:
                return

            track = self.get_next_track()
            if not track:
                file_processed = False
            else:
                logging.debug(f"Processing track {track}")
                file_processed = True
                data = self.get_track_data(track)
                with self.track_db_lock:  # insert user info into database
                    self.track_db.insert_one(data)
                with self.user_q_lock:  # get all favorited tracks by user and put unprocessed tracks into queue
                    for user in data['favoriters']:
                        if not self.user_db.find_one({"_id": user}) and not self.user_q_db.find_one({"_id": user}):
                            # logging.info(f"Adding user {user} to user queue")
                            self.user_q_db.insert_one({"_id": user})
    def get_next_user(self):
        # finds and retrieves user from queue, dropping it. returns None if no user
        with self.user_q_lock:
            logging.info("Getting next user")
            user = self.user_q_db.find_one()
            if user:
                self.user_q_db.delete_one(user)
        return user["_id"] if user else user  # else None, same thing

    def get_next_track(self):
        # finds and retrieves user from queue, dropping it. returns none if no user
        with self.track_q_lock:
            logging.info("Getting next track")
            track = self.track_q_db.find_one()
            if track:
                self.track_q_db.delete_one(track)
        return track["_id"] if track else track

    def get_user_data(self, username):
        # username can be id number or name
        logging.debug(f"Querying {username} for general info")
        user = self._sc_get(f'/users/{username}')

        user_info = user.fields()
        user_info['favorites'] = self.get_user_favorites(username)  #adding list of all favorited tracks by user
        user_info['followers'] = self.get_user_followers(username)
        user_info['_id'] = user_info['id']
        return user_info

    def get_track_data(self, track_id):
        #input track should be id
        logging.debug(f"Querying {track_id} for general info")
        track = self._sc_get(f'tracks/{track_id}')
        track_info = track.fields()
        track_info['favoriters'] = self.get_track_favoriters(track_id)
        track_info['_id'] = track_info['id']
        return track_info

    def get_user_favorites(self, username):
        # returns list of sc resource objects
        logging.debug(f"Querying {username} for favorites")
        favorites = self._sc_get(f'/users/{username}/favorites')
        return [i.id for i in favorites]

    def get_user_followers(self, username):
        # returns list of sc resource objects of followers
        logging.debug(f"Querying {username} for followers")
        followers = self._sc_get(f'/users/{username}/followers')
        return [i.id for i in followers.collection]

    def get_track_favoriters(self, track):
        # returns list of users who have favorited this track
        logging.debug(f"Querying {track} for favoriters")
        favoriters = self._sc_get(f"/tracks/{track}/favoriters")
        return [i.id for i in favoriters]

    # scan all users and look at favorites, add to queue_db if not in track list
    def find_unused_favorites(self):
        for user in self.user_db.find():
            for track in user['favorites']:
                # track is track id num
                if not self.track_db.find_one({"_id":track}) and not self.track_q_db.find_one({"_id":track}):
                    logging.debug(f"Adding {track} to User queue db")
                    self.track_q_db.insert_one({"_id":track})

    # scan all tracks and look at favoriters, add to queue_db if not in track list
    def find_unused_users(self):
        for track in self.track_db.find():
            for user in track['favoriters']:
                # track is track id num
                if not self.user_db.find_one({"_id":user}) and not self.user_q_db.find_one({"_id":user}):
                    logging.debug(f"Adding {user} to User queue db")
                    self.user_q_db.insert_one({"_id":user})

    def _sc_get(self, query):
        self._delay_query()
        with self.sc_call_lock:
            self.num_sc_calls += 1
        data = self.client.get(query)
        return data

    def _delay_query(self):
        time_delay = random.random() * 0.3
        with self.time_lock:
            while time.time() - self.last_sc_query < time_delay:
                pass
            self.last_sc_query = time.time()


if __name__ == "__main__":
    scraper = SoundCloudScraper(client_id='44287f900da9a7355b99356fe0428da5',
                                client_secret='fde5fba2703158a96554f048688428fe',
                                double_threads=10)
    # scraper.find_unused_favorites()
    scraper.start_scraping()