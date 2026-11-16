#!/usr/bin/env python3
"""Download the Nutrition5k photos used in dataset.json into benchmark/images/.

Branded product photos come from Wikimedia Commons; their page links and
licenses are in dataset.json (field "photo_page"). Download them manually and
save as images/<id>.jpg using the ids from dataset.json.
"""
import json
import os
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = "https://storage.googleapis.com/nutrition5k_dataset/nutrition5k_dataset/imagery/realsense_overhead"

os.makedirs(os.path.join(HERE, "images"), exist_ok=True)
for item in json.load(open(os.path.join(HERE, "dataset.json"))):
    if not item["id"].startswith("dish_"):
        print("manual:", item["id"], item.get("photo_page", ""))
        continue
    path = os.path.join(HERE, "images", item["id"] + ".png")
    if os.path.exists(path):
        continue
    urllib.request.urlretrieve(f"{BASE}/{item['id']}/rgb.png", path)
    print("downloaded", item["id"])
