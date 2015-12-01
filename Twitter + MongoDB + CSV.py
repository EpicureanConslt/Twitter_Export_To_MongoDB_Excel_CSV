# ========================= Refer to requirements.txt =================================================================================================================

import requests
import simplejson as json
import pymongo
import subprocess
from pymongo import MongoClient
from requests_oauthlib import OAuth1
from subprocess import Popen, PIPE





# ========================= Function to change PK to _id =============================================================================================================

#I want to re-use the id field returned by Twitter as the primary key (PK)
#in MongoDB. However, there is one problem: Twitter uses the field "id", while
#MongoDB uses the standard "_id". So, this function tries to bridge this gap.

def replaceid(q):
    new_json=q
    for j in range(0,len(q)):
        for key in q[j]:
            if (key == "id"):
                new_key = "_id"                       #Replace "id" key in Tweet with "_id"
                new_json[j][new_key] = q[j][key]      #Copy over contents to new json
                del new_json[j][key]                  #Delete old "id" field & value 
    return new_json





# ========================= Twitter & MongoDB Initialization ========================================================================================================

#Get input from user. Loop until input is valid i.e. first character is @ or #
#Initialize the Twitter API URL, based on whether the input is a hashtag or Twitter handle
#Initialize Twitter API & MongoDB connection parameters

twitter_input = input("Enter Twitter Hashtag with # or Twitter Handle with @: ")
while (twitter_input[0:1] != "@" and twitter_input[0:1] != "#"):
    twitter_input = input("Invalid input. Please enter Twitter Hashtag with # or Twitter Handle with @: ")
if(twitter_input[0:1] == "@"):
    hashtag_ind = 0
    print("Twitter Handle: " + twitter_input)
    #Using Twitter API GET statuses/user_timeline. Refer to https://dev.twitter.com/rest/reference/get/statuses/user_timeline
    url="https://api.twitter.com/1.1/statuses/user_timeline.json?screen_name=" + \
            twitter_input[1:len(twitter_input)] + "&count=1000&include_rts=1"      
else:
    hashtag_ind = 1
    print("Twitter Hashtag: " + twitter_input)
    #Using Twitter API GET search/tweets. Refer to https://dev.twitter.com/rest/reference/get/search/tweets
    url="https://api.twitter.com/1.1/search/tweets.json?q=" + twitter_input[1:len(twitter_input)] + \
             "&count=1000"                                                                  

consumer_key=""                                                                             #Replace with your consumer key 
consumer_secret=""                                                                          #Replace with your consumer secret 
access_token=""                                                                             #Replace with your access token 
access_token_secret=""                                                                      #Replace with your access token secret 

client = MongoClient("localhost", 27017)                                                    #Assuming a local instance of MongoDB is running
db = client["TwitterOnMongoDB"]                                                             #My DB is called "TwitterOnMongoDB"
collection = db[twitter_input]                                                              #Using a collection named the inputted Twitter Handle or Hashtag
auth=OAuth1(consumer_key, consumer_secret, access_token, access_token_secret)               #Initialize OAuth connection parameters





# ========================= Twitter Extraction + MongoDB Loading =====================================================================================================

tweet=requests.get(url, auth=auth).json()                                                         
tweet_count = 0                                                                                     
#Each Twitter API call returns 100-200 tweets. So, we loop to send sequential API requests
#Limiting to ~3000 Tweets (15*200)
for j in range(1,16):
    #Break loop if Twitter returns empty result set.
    if(len(tweet)>1):          
        if(hashtag_ind == 1):                                                                      
            #Only applicable for hashtags - GET search/tweets API. #search_metadata contains the next URL that we need to use
            search_metadata = tweet['search_metadata']                                            
            tweet = tweet['statuses']                                                        
        tweet_count = tweet_count + len(tweet)                                                
        print("Extracted " + str(tweet_count) + " Tweets...")
        #Call function to replace the "id" to "_id"
        new_json = replaceid(tweet)                                                               
        for doc in new_json:
            collection.save(doc)                                                                       
        if(hashtag_ind == 0):
            #Only applicable for Twitter handle - GET statuses/user_timeline
            #Find the oldest tweet with the lowest value and use it as the input for the max_id field
            cursor = collection.find({}, {"_id":1}).sort([("_id", pymongo.ASCENDING)]).limit(1)   
            for doc in cursor:
                min_id = doc['_id']                                                                 
            url1 = url + "&max_id=" + str(min_id)
        else:
            #Only applicable for Twitter Hashtag - GET search/tweets
            if 'next_results' not in search_metadata:
                url1 = "https://api.twitter.com/1.1/search/tweets.json"
            #Extract the URL specified by twitter in search_metadata and append to our url
            else:
                next_results = search_metadata['next_results']
                url1 = "https://api.twitter.com/1.1/search/tweets.json" + next_results
        #Send subsequent request to Twitter, using the modified URL    
        tweet=requests.get(url1, auth=auth).json()





# ========================= Export to CSV =============================================================================================================================

#Using the mongoexport functionality to export the collection inserted/updated
#in CSV format. MongoDB expects you to specify the fields required, since some of
#them can be NULL or non-existent. Output CSV will be saved in the same folder
#as this Python file (i.e. same directory)

cmd = "mongoexport --db TwitterOnMongoDB --collection " + twitter_input + " --type=csv --fields text," + \
            "favorite_count,retweet_count,created_at,lang,user.screen_name,user.name,user.time_zone," + \
            "user.followers_count,user.statuses_count,_id " + \
            "--out " + twitter_input[1:len(twitter_input)] + ".csv"
#Filename set to inputted Twitter handle or hashtag
#Using Popen to run the shell command above
p = subprocess.Popen(cmd, shell=True, stdin=PIPE, stdout=PIPE, close_fds=False)                               

print("Done!")
