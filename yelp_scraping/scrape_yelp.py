import requests
import json
from os import path
import datetime 

headers = {
  'Authorization': 'Bearer BEARER TOKEN REMOVED BECAUSE THIS LIVES ON GITHUB'
}

payload = {}
#helper funcitons
def create_file(filename):
  f = open(filename,'w')
  f.write("[]")
  f.close()


def get_num_entries(cuisine):
    url = "https://api.yelp.com/v3/businesses/search?location=nyc&categories={}&offset=0".format(cuisine)
    response = requests.request("GET", url, headers=headers, data=payload).json()
    total = int(response.get('total'))
    return total
    
###############################################################################
def scrape_cuisine(cuisine, num_entries, filename, now):
  #yelp is only going to give us 1000 datapoints per api so limit to 1k
  if(num_entries > 1000):
    num_entries = 1000
  #make API request page by page
  for index in range(0,num_entries,20):

      url = "https://api.yelp.com/v3/businesses/search?location=nyc&categories={}&offset={}".format(cuisine, index)
      print(url)
      response = requests.request("GET", url, headers=headers, data=payload).json()

      business = response.get('businesses')
      
      for b in business:
        b['insertedAtTimestamp'] = now
        b['cuisine'] = cuisine

      with open(filename, 'r') as json_file:
        data=json_file.read()
        # parse file
        data = json.loads(data)
        data = data + business

      with open(filename, 'w') as json_file:
        for r in data:
          #get rid of extraneous fields 
          r.pop('alias', None)
          r.pop('image_url', None)
          r.pop('is_closed', None)
          r.pop('categories', None)
          r.pop('transactions', None)
          r.pop('distance', None)
          r.pop('price', None)

        #write out result to that cuisines .json file
        json.dump(data, json_file, 
        indent=4,  
        separators=(',',': '))


def main():

  cuisines = ['japanese','indpak', 'chinese', 'mexican','tradamerican','thai','greek','halal']
  #cuisines = ['thai','greek','halal']
  #cuisines = ['japanese']
  
  #generate timstamp for dataset
  now = datetime.datetime.now().strftime("%m/%d/%Y, %H:%M:%S")

  for cuisine in cuisines:
    filename = "{}.json".format(cuisine)
    create_file(filename)
    num_entries = get_num_entries(cuisine)
    print(cuisine+ " has this many entries: "+str(num_entries))
    scrape_cuisine(cuisine, num_entries, filename, now)


if __name__ == "__main__":
	main()

