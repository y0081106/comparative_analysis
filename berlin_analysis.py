import time
import calendar
import codecs
import datetime
import json
import sys
import gzip
import string
import glob
import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt



global_tweet_counter = 0
time_format = "%a %b %d %H:%M:%S +0000 %Y"
reader = codecs.getreader("utf-8")
local_tweet_list = []
tweets_data_path = 'berlin_attacks_berlin.json'
tweets_file = open(tweets_data_path, "r")
frequency_map = {}
        
for line in tweets_file:

    # Try to read tweet JSON into object
    tweet_obj = None
    try:
        tweet_obj = json.loads(line)
    except Exception as e:
        continue

    # Deleted status messages and protected status must be skipped
    if ( "delete" in tweet_obj.keys() or "status_withheld" in tweet_obj.keys() ):
        continue

    # Try to extract the time of the tweet
    try:
        current_time = datetime.datetime.strptime(tweet_obj['created_at'], time_format)
    except:
        print (line)
        raise

    current_time = current_time.replace(second=0)

    # Increment tweet count
    global_tweet_counter += 1

    # If our frequency map already has this time, use it, otherwise add
    if ( current_time in frequency_map.keys() ):
        time_map = frequency_map[current_time]
        time_map["count"] += 1
        time_map["list"].append(tweet_obj)
    else:
        frequency_map[current_time] = {"count":1, "list":[tweet_obj]}

# Fill in any gaps
times = sorted(frequency_map.keys())
first_time = times[0]
last_time = times[-1]
this_time = first_time

time_interval_step = datetime.timedelta(0, 60)    # Time step in seconds
while ( this_time <= last_time ):
    if ( this_time not in frequency_map.keys() ):
        frequency_map[this_time] = {"count":0, "list":[]}
        
    this_time = this_time + time_interval_step

print ("Processed Tweet Count:", global_tweet_counter)

fig, ax = plt.subplots()
fig.set_size_inches(18.5,10.5)

plt.title("Tweet Frequency")

# Sort the times into an array for future use
sorted_times = sorted(frequency_map.keys())

# What time span do these tweets cover?
print ("Time Frame:", sorted_times[0], sorted_times[-1])

# Get a count of tweets per minute
post_freq_list = [frequency_map[x]["count"] for x in sorted_times]

# We'll have ticks every thirty minutes (much more clutters the graph)
smaller_xticks = range(0, len(sorted_times), 30)
plt.xticks(smaller_xticks, [sorted_times[x] for x in smaller_xticks], rotation=90)

# Plot the post frequency
ax.plot(range(len(frequency_map)), [x if x > 0 else 0 for x in post_freq_list], color="blue", label="Posts")
ax.grid(b=True, which=u'major')
ax.legend()

plt.show()

# Create maps for holding counts and tweets for each user
global_user_counter = {}
global_user_map = {}

# Iterate through the time stamps
for t in sorted_times:
    time_obj = frequency_map[t]
    
    # For each tweet, pull the screen name and add it to the list
    for tweet in time_obj["list"]:
        user = tweet["user"]["screen_name"]
        
        if ( user not in global_user_counter ):
            global_user_counter[user] = 1
            global_user_map[user] = [tweet]
        else:
            global_user_counter[user] += 1
            global_user_map[user].append(tweet)

print ("Unique Users:", len(global_user_counter.keys()))

sorted_users = sorted(global_user_counter, key=global_user_counter.get, reverse=True)
print ("Top Ten Most Prolific Users:")
for u in sorted_users[:10]:
    print (u, global_user_counter[u], "\n\t", "Random Tweet:", global_user_map[u][0]["text"], "\n----------")
	

# A map for hashtag counts
hashtag_counter = {}

# For each minute, pull the list of hashtags and add to the counter
for t in sorted_times:
    time_obj = frequency_map[t]
    
    for tweet in time_obj["list"]:
        hashtag_list = tweet["entities"]["hashtags"]
        
        for hashtag in hashtag_list:
            
            # We lowercase the hashtag to avoid duplicates (e.g., #MikeBrown vs. #mikebrown)
            hashtag_str = hashtag["text"].lower()
            
            if ( hashtag_str not in hashtag_counter ):
                hashtag_counter[hashtag_str] = 1
            else:
                hashtag_counter[hashtag_str] += 1

print ("Unique Hashtags:", len(hashtag_counter.keys()))
sorted_hashtags = sorted(hashtag_counter, key=hashtag_counter.get, reverse=True)
print ("Top Twenty Hashtags:")
for ht in sorted_hashtags[:20]:
    print ("\t", "#" + ht, hashtag_counter[ht])
	
# A map for counting each language
language_counter = {}

for t in sorted_times:
    time_obj = frequency_map[t]
    
    for tweet in time_obj["list"]:
        lang = tweet["lang"]
        
        if ( lang not in language_counter ):
            language_counter[lang] = 1
        else:
            language_counter[lang] += 1

languages = sorted(language_counter.keys(), key=language_counter.get, reverse=True)

for l in languages:
    print (l, language_counter[l])
	
plt.figure(figsize=(16,8))
    
# the histogram of the data
plt.bar(
    np.arange(len(languages)),
    [language_counter[x] for x in languages],
    log=True)

plt.xticks(np.arange(len(languages)) + 0.5, languages)
plt.xlabel('Languages')
plt.ylabel('Counts (Log)')
plt.title("Language Frequency")
plt.grid(True)

plt.show()

# A frequency map for timestamps to geo-coded tweets
geo_frequency_map = {}
geo_count = 0

# Save only those tweets with tweet['coordinate']['coordinate'] entity
for t in sorted_times:
    geos = list(filter(lambda tweet: tweet["coordinates"] != None and "coordinates" in tweet["coordinates"], frequency_map[t]["list"]))
    geo_count += len(geos)
    
    # Add to the timestamp map
    geo_frequency_map[t] = {"count": len(geos), "list": geos}

print ("Number of Geo Tweets:", geo_count)

import matplotlib

from mpl_toolkits.basemap import Basemap

# Create a list of all geo-coded tweets
temp_geo_list = [geo_frequency_map[t]["list"] for t in sorted_times]
geo_tweets = reduce(lambda x, y: x + y, temp_geo_list)

# For each geo-coded tweet, extract its GPS coordinates
geo_coord = [x["coordinates"]["coordinates"] for x in geo_tweets]

# Now we build a map of the world using Basemap
land_color = 'lightgray'
water_color = 'lightblue'

fig, ax = plt.subplots(figsize=(18,18))
world_map = Basemap(projection='merc', llcrnrlat=-80, urcrnrlat=80,
                   llcrnrlon=-180, urcrnrlon=180, resolution='l')

world_map.fillcontinents(color=land_color, lake_color=water_color, zorder=1)
world_map.drawcoastlines()
world_map.drawparallels(np.arange(-90.,120.,30.))
world_map.drawmeridians(np.arange(0.,420.,60.))
world_map.drawmapboundary(fill_color=water_color, zorder=0)
ax.set_title('World Tweets')

# Convert points from GPS coordinates to (x,y) coordinates
conv_points = [world_map(p[0], p[1]) for p in geo_coord]
x = [p[0] for p in conv_points]
y = [p[1] for p in conv_points]
world_map.scatter(x, y, s=100, marker='x', color="red", zorder=2)

plt.show()
