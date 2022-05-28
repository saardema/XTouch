import requests
import time
import json
from threading import Thread

REQUEST_RATE_LIMIT = 0.0025
API_URL = 'http://localhost:1280/0001f2fffe00be6a/datastore'

datastore = {}
datastore_patch = {}
time_last_patch = time.time()

def patch_datastore(path, value):
    global datastore, datastore_patch, time_last_patch
    datastore[path] = value
    datastore_patch[path] = value
    time_last_patch = time.time()

def push_datastore_patches():
    global datastore_patch
    while True:
        if datastore_patch:
            datastore_patch_copy = datastore_patch.copy()
            datastore_patch = {}
            requests.post(API_URL + '/mix', data={'json': json.dumps(datastore_patch_copy)})
            # print(datastore_patch_copy)
        time.sleep(REQUEST_RATE_LIMIT)

def fetch_datastore():
    global datastore
    try:
        datastore = requests.get(API_URL + '/mix').json()
    except Exception as e:
        print(e)

fetch_datastore()
Thread(target=push_datastore_patches).start()