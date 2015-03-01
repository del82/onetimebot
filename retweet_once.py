#!/usr/bin/env python
# -*- coding: utf-8 -*-

## Authorize new accounts:
# url = auth.get_authorization_url()
# verifier= "" # the number we got at that url
# t = auth.get_access_token(verifier)

import logging, os.path, json
import tweepy
from tweepy.streaming import StreamListener
from tweepy import OAuthHandler
from tweepy import Stream
import requests


try:
    import cPickle as pickle
except ImportError:
    import pickle

COUNT_DICT_FILE = "counts.pkl"
LOG_FILENAME = "example.log"
NYTIMES_ID = 807095

logging.basicConfig(filename=LOG_FILENAME,level=logging.DEBUG)
logging.debug('initializing')

class SPKVS(dict):
    """ Extremely simple, inefficient, persistant key-value store.

Behaves like a dictionary until the filename attribute is set, at which point every
update causes the entire dictionary to be pickled to filename.

"""

    def __init__(self, *args, **kwargs):
        super(SPKVS, self).__init__(*args, **kwargs)
        self.filename = None

    def __setitem__(self, *args, **kwargs):
        super(SPKVS, self).__setitem__(*args, **kwargs)
        if self.filename:
            pickle.dump(self, open(self.filename, 'w'))


class TargetedRetweetListener(StreamListener):
    """ A listener that retweets NYTimes tweets exactly once.

    """
    def __init__(self, api, counts):
        self.api = api
        self.counts = counts

    def on_error(self, status):
        print status

    def on_status(self, status):
        logging.info("got a status.")
        try:
            if status.user.id == NYTIMES_ID:
                url = status.entities['urls'][0]['expanded_url']
                logging.debug("got a url: %s" % url)
                r = requests.get(url)
                logging.debug("url resolved to %s" % r.url)
                counts = self.counts.get(r.url, 0)
                if counts != 0:
                    logging.info("duplicate url, not retweeting")
                    self.counts[r.url] = counts + 1
                else:
                    self.counts[r.url] = 1
                    logging.info("got a new url, retweeting")
                    self.api.retweet(status.id)
            else:
                logging.info("got tweet from %s, not retweeting" % status.user_name)
        except:
            logging.critical(sys.exc_info()[0])
        finally:
            return True

if __name__ == '__main__':
    keys = json.load(open("secret.json"))
    auth = tweepy.OAuthHandler(keys["app_key"], keys["app_secret"])
    auth.set_access_token(keys["onetime_user_key"], keys["onetime_user_secret"])
    api = tweepy.API(auth)

    # initialize counts dict
    counts = SPKVS()
    if os.path.exists(COUNT_DICT_FILE):
        counts = pickle.load(open(COUNT_DICT_FILE))
    else:
        counts.filename = COUNT_DICT_FILE

    l = TargetedRetweetListener(api, counts)
    stream = Stream(auth, l)
    try:
        stream.userstream()
    except:
        logging.critical(sys.exc_info()[0])

# api.update_status('message')
# or api.retweet(tweet_id)
