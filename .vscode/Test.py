import urllib2
import json

url = "http://10.0.0.23/current-sample"
data = None

request = urllib2.Request(url, data)
response = urllib2.urlopen(request)
parsed_json = json.loads(response.read())
print parsed_json

sample = parsed_json
channels = ""; consumption = ""; generation = ""; watts = ""
for key, value in sample.iteritems():
    if key == "channels":
        channels = sample[key]
for channel in channels:
    for key, value in channel.iteritems():
        if key == "type":
            if channel[key] == "CONSUMPTION":
                consumption = channel
            if channel[key] == "GENERATION":
                generation = channel
for key, value in consumption.iteritems():
    if key == "p_W":
        watts = consumption[key]
consumption = watts
print watts