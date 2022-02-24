import json
from os import path
import datetime 

def main():

  #cuisines = ['japanese','indpak', 'chinese', mexican','tradamerican','thai','greek','halal']
  #cuisines = ['thai','greek','halal']
  cuisines = ['japanese','indpak', 'chinese', 'mexican','tradamerican','thai','greek','halal']
  index = "{\"index\": {\"_index\": \"yelp\", \"_id\": " 
  close = "}}"
  print(close)
  filename = "csv.json"
  with open(filename, 'r') as f:
      with open("test2.json", 'w') as json_file:
          data=f.read()
          # parse file
          data = json.loads(data)
          i = 0
          for d in data:
            s1 = index + str(i) + close
            s2 = json.dumps(d)
            s1 = s1+"\n"+s2+"\n"
            json_file.write(s1)
            i = i+1
if __name__ == "__main__":
	main()
