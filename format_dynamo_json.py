import requests
import json
from os import path
import datetime 

def main():

  #cuisines = ['japanese','indpak', 'chinese', mexican','tradamerican','thai','greek','halal']
  #cuisines = ['thai','greek','halal']
  cuisines = ['japanese','indpak', 'chinese', 'mexican','tradamerican','thai','greek','halal']

  for cuisine in cuisines:
    filename = "dataset/{}.json".format(cuisine)
    with open("{}.json".format(cuisine), 'w') as f:
        with open(filename, 'r') as json_file:
            data=json_file.read()
            # parse file
            data = json.loads(data)
            for d in data:
                d['coordinates']['latitude'] = str(d['coordinates']['latitude'])
                d['coordinates']['longitude'] = str(d['coordinates']['longitude'])
                d['rating'] = str(d['rating'])
                d['review_count'] = str(d['review_count'])
                print(d)
            json.dump(data, f, 
            indent=4,  
            separators=(',',': '))
if __name__ == "__main__":
	main()


