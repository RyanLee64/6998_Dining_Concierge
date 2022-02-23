import json
import boto3
from botocore.exceptions import ClientError

def insert_data(data_list, db=None, table='YelpStorage'):
    if not db:
        db = boto3.resource('dynamodb')
    table = db.Table(table)
    # overwrite if the same index is provided
    for data in data_list:
        response = table.put_item(Item=data)
    print('@insert_data: response', response)
    print("hi")
    return response


def main():
    filename = 'dataset/japanese.json'
    with open(filename, 'r') as json_file:
        data=json_file.read()
        # parse file
        data = json.loads(data)
        insert_data(data)

if __name__ == "__main__":
	main()



