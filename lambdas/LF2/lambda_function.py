import json
import boto3
import json
import requests
import inspect
from requests_aws4auth import AWS4Auth
from requests.auth import HTTPBasicAuth
from botocore.exceptions import ClientError


region = 'us-east-1' 
service = 'es'
credentials = boto3.Session().get_credentials()
awsauth = AWS4Auth(credentials.access_key, credentials.secret_key, region, service, session_token=credentials.token)

host = 'https://search-restaurants-7mi44lfnz7i2f4krsrcoo4tplu.us-east-1.es.amazonaws.com' # The OpenSearch domain endpoint with https://
index = 'yelp'
url = host + '/' + index + '/_search'
auth=HTTPBasicAuth("master","t@T0gnL3rLI7")
CUISINES_DICT = { 'mexican':'Mexican', 'tradamerican':'American',
'indpak':'Indian', 'chinese':'Chinese','japanese':'Japanese', 'thai':'Thai',
'greek':'Greek', 'halal':'Jalal'}


def remove_fufilled_request(rh):
    sqs_client = boto3.client('sqs')
    sqs_queue_url = sqs_client.get_queue_url(QueueName="DiningSuggestionsQueue")['QueueUrl']
    try:
        msg = sqs_client.delete_message(QueueUrl=sqs_queue_url, ReceiptHandle=rh)
    except ClientError as e:
        logging.error(e)
        return None
    return msg
    
def get_relevant_values(data):
    #TODO: OPTIONAL ADD CHECK TO MAKE SURE ADDR IS NOT NULL
    name = data['Item']['name']['S']
    addr_pt_1 = data['Item']['location']['M']['display_address']['L'][0]['S']
    addr_pt_2 = data['Item']['location']['M']['display_address']['L'][1]['S']
    address = addr_pt_1 + " "+addr_pt_2
    return name, address

def send_email(email_addr, party_size, date, time, cuisine, restaurants):
    ses_client = boto3.client("ses", region_name="us-east-1")
    CHARSET = "UTF-8"
    
    restaurant1 = restaurants[0]
    restaurant2= restaurants[1]
    restaurant3= restaurants[2]
    cuisine = CUISINES_DICT[cuisine]
    
    body = """Hello! Here are my {} restaurant suggestions for {} people, 
    for {} at {}: 1. {}, located at {}, 2. {}, located at {}, 3. {} 
    located at {}. Enjoy your meal!""".format(cuisine, party_size,
    date, time, restaurant1[0], restaurant1[1], restaurant2[0], restaurant2[1],
    restaurant3[0], restaurant3[1])
    body = inspect.cleandoc(body).replace("\n", "")
    response = ses_client.send_email(
        Destination={
            "ToAddresses": [
               email_addr,
            ],
        },
        Message={
            "Body": {
                "Text": {
                    "Charset": CHARSET,
                    "Data": body,
                }
            },
            "Subject": {
                "Charset": CHARSET,
                "Data": "Your Dining Concierge Recommendations",
            },
        },
        Source="dbl2127@columbia.edu",
    )
def query_dynamodb(query_id):
    client = boto3.client('dynamodb')
    data = client.get_item(TableName='YelpStorage',
    Key={
        'id': {
          'S': str(query_id)
        }
    }
    )
    return get_relevant_values(data)

def query_elasticsearch(message):
    message_body = json.loads((message.get('Messages'))[0].get('Body'))
    desired_cuisine = message_body.get('cuisine')
    #return three random results 
    #https://www.elastic.co/guide/en/elasticsearch/reference/current/query-dsl-function-score-query.html#function-random
    query = {
        "size": 3,
        "query": {
            "function_score": {
                "query": {  
                    "match": {
                        "cuisine": desired_cuisine
                    }
                },
                "random_score": {}
            }
        }
    }   
    # Elasticsearch 6.x requires an explicit Content-Type header
    headers = { "Content-Type": "application/json" }
    # Make the signed HTTP request
    r = requests.get(url, auth=auth, headers=headers, data=json.dumps(query))
    json_data = json.loads(r.text)
    query_id_1 = (json_data.get('hits').get('hits'))[0].get('_source').get('id')
    query_id_2 = (json_data.get('hits').get('hits'))[1].get('_source').get('id')
    query_id_3 = (json_data.get('hits').get('hits'))[2].get('_source').get('id')

    return [query_id_1,query_id_2, query_id_3]
        
def pull_sqs_message():
    sqs_client = boto3.client('sqs')
    sqs_queue_url = sqs_client.get_queue_url(QueueName="DiningSuggestionsQueue")['QueueUrl']
    try:
        msg = sqs_client.receive_message(QueueUrl=sqs_queue_url)
    except ClientError as e:
        logging.error(e)
        return None
    return msg
    
def lambda_handler(event, context):
   
    # Lambda execution starts here
    # Put the user query into the query DSL for more accurate search results.
    # Note that certain fields are boosted (^).
    queue_message = pull_sqs_message()
    print(queue_message)
    #in the case that we have a client request to satsisfy go ahead and search
    if('Messages' in queue_message):
        rh = queue_message['Messages'][0]['ReceiptHandle']
        restaurant_ids = query_elasticsearch(queue_message)
        email_addr = (json.loads(queue_message['Messages'][0]['Body']))['phone']
        party_size =  (json.loads(queue_message['Messages'][0]['Body']))['party']
        date = (json.loads(queue_message['Messages'][0]['Body']))['date']
        time =  (json.loads(queue_message['Messages'][0]['Body']))['time']
        cuisine =  (json.loads(queue_message['Messages'][0]['Body']))['cuisine']



        data = []
        name_addr_tuples = []
        for restaurant_id in restaurant_ids:
            name_addr_tuples.append(query_dynamodb(restaurant_id))
        try:
            send_email(email_addr, party_size, date, time, cuisine, name_addr_tuples)
            remove_fufilled_request(rh)
            
        except:
            print("something with sending went wrong message not removed from queue")
    
    
    


