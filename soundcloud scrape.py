'''
saved data should be in 2 dataases. Users and Tracks,  whwere each key is the unique ID, and the value is a dictionary of information that gets saved

Add User to queue, For each user, look at their favorited tracks and add to track_queue
for every track in track queue, look at users who have favorited this track and add to user_queue
'''

import soundcloud 
import threading  # using threading instead of processing since most of the delays will be waiting for network response
import time
from queue import Queue

class SoundCloudScraper:
	def __init__(self, client_id, client_secret, num_threads=3, thread_timeout = 600)
		self.client = soundcloud.Client(client_id='44287f900da9a7355b99356fe0428da5',
			                            client_secret='fde5fba2703158a96554f048688428fe')
			                            # username='elchung',
			                            # password='YOUR_PASSWORD')
		self.user_q = Queue()
		self.track_q = Queue()
		self.user_db = 
		self.track_db = 
		self.user_q_lock = threading.Lock()
		self.track_q_lock = threading.Lock()
		self.user_db_lock = threading.Lock()
		self.track_db_lock = threading.Lock()

		self.timeout_time = thread_timeout # set timeout to defualt 10 min

	def start_scraping(self):
		num_track_threads = self.num_threads // 2
		num_user_threads = num_track_threads - self.num_threads
		for thread in range(num_track_threads):
			t = threading.Thread(target=self.process_tracks) # , arg=(thread,))
			t.daemon = True
			t.start()
		for thread in range(num_user_threads):
			t = threading.Thread(target=self.process_users) # , arg=(thread,))
			t.daemon = True
			t.start()

	def process_users(self):
		file_processed, timeout_started = False, False
		while 1: # if thread has been sitting empty for 10 minutes, kill
			if not file_processed and not timeout_started:
				timeout_start, timeout_started = time.time(), True
			if not file_processed and time.time() - timeout_start > self.timeout_time:
				return

			if self.user_q.empty():
				file_processed = False
			else:
				file_processed, timeout_started = True, False

				with self.user_q_lock:
					user = self.user_q.get()
				process, for all newly found tracks check aginst db before adding to q

	def process_tracks(self):
		file_processed, timeout_started = False, False
		while 1: # if thread has been sitting empty for 10 minutes, kill
			if not file_processed and not timeout_started:
				timeout_start, timeout_started = time.time(), True
			if not file_processed and time.time() - timeout_start > self.timeout_time:
				return

			if self.user_q.empty():
				file_processed = False
			else:
				file_processed, timeout_started = True, False

				with self.track_q_lock:
					track = self.track_q.get()

				process, for all newly found users check against db before adding to q

	def get_user_favorites(self, username):
		# returns list of sc resource objects
		return self.client.get(f'/users/{username}/favorites')

	def get_user_followers(self, username):
		# returns list of sc resource objects of followers
		return self.client.get(f'/users/{username}/followers')

	def get_track_favoriters(self, track):
		# returns list of users who have favorited this track
		return self.client.get(f"/tracks/{track}/favoriters")

	def get_track_info(self, track):
		#in: track id or name
		#out: track info object
		# return self.client.get('')	
		pass

	def build_user_data(self, username):
		# username can be id number or name
		user = self.client.get(f'/users/{username}')
		user_info = user.fields()
		user_info['favorites'] = self.get_user_favorites(username)  #adding list of all favorited tracks by user
		user_info['followers'] = self.get_user_followers(username)
		return user_data

	def build_track_data(self, track):
		#input track should be id
		track = self.client.get(f'tracks/{track}')
		track_info = track.fields()
		track_info['favoriters'] = self.get_track_favoriters(track)


if __name__ == "__main__":
	do stuff
