# input username url copied from address bar when on profile
import heapq
import soundcloud
from pymongo import MongoClient


class SoundCloudRecommender:
	def __init__(self, client_id, client_secret):
		self.client = soundcloud.Client(client_id=client_id, client_secret=client_secret)
		self.dbclient = MongoClient()
		self.db = self.dbclient.sc_scrape
		self.user_db = self.db.sc_user_db
		self.track_db = self.db.sc_track_db

	def get_song_recommendations(self, user_url):
		user_id = self.dbclient.get('/resolve', url=user_url).id
		neighbors = self.get_nearest_neighbors(user_id)
		'''
		several ways to go about doing this. take x neighbors,
			get all favorited tracks in neighbors not in user and return a random number of them
			get all favorited tracks in neighbors and return not favorited artists' tracks
		'''

	def update_user_dimensions(self):
		for user in self.user_db.find():  # iterates through all users
			dimensions = {}
			for track_id in user['favorites']:
				track_artist_id = self.track_db.find_one({'_id': track_id})['user_id']
				if track_artist_id in dimensions.keys():  # don't want to set dimensions as defaultdict so using this
					dimensions[track_artist_id] += 1
				else:
					dimensions[track_artist_id] = 1
			self.user_db.update_one(user['_id'], {"$set": {'dimensions': dimensions}})

	def get_nearest_neighbors(self, user_id):
		dimensions = self.build_user_dimensions(user_id)
		nearest_neighbors = []
		for user in self.user_db.find():  # look at each user in db
			distance = self.get_distance(dimensions, user['dimenisons'])
			if distance:
				heapq.heappush(nearest_neighbors, (distance, user['_id']))
		return nearest_neighbors

	# returns dictionary of {artist: num liked tracks from artist} based on list of user favorites
	def build_user_dimensions(self, user_id):
		def get_track_artist_id(track_id):
			track_artist_id = self.track_db.find_one({'_id': track_id})['user_id']
			if not track_artist_id:  # if not found in database, ping SoundCloud directly
				track_artist_id = self.client.get(f"/tracks/{track_id}").user_id
			return track_artist_id  # TODO what if SoundCloud returns none?

		dimensions = {}
		user_favorites = [i.id for i in self.client.get(f"/users/{user_id}/favorites")]
		for track_id in user_favorites:
			track_artist_id = get_track_artist_id(track_id)
			dimensions[track_artist_id] = dimensions.get(track_artist_id, 0) + 1
		return dimensions

	# get distance from user to comparison user
	def get_distance(self, user_dim, comp_dim):
		matching_artists = [artist for artist in comp_dim.keys() if artist in user_dim.keys()]
		distance = 0
		for artist in matching_artists:
			distance += (comp_dim[artist] - user_dim[artist])**2  # no need to calc sqrt at end of distance formulas
		return distance

