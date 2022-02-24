"""
My LF1 implementation uses the flowers example as a template:
https://docs.aws.amazon.com/lex/latest/dg/gs-bp.html
"""
#from asyncio.events import _ProtocolFactory
import math
import dateutil.parser
import datetime
import time
import json
import os
import logging
import boto3
import re
from botocore.exceptions import ClientError


#knicknames sourced from: https://en.wikipedia.org/wiki/Nicknames_of_New_York_City
NYC_KNICKNAMES = ['the big apple','the capital of the world',
'the center of the universe','the city so nice they named it twice',
'the city that never sleeps','the empire city','the five boroughs',
'brooklyn','queens','staten island','manhattan','the bronx','fun city',
'gotham','the greatest city in the world','knickerbocker','the melting pot',
'metropolis','the modern gomorrah','new amsterdam','america\'s city',
'the city of neon and chrome','nyc','ny','new york']

CUISINES_DICT = { 'mexican':'mexican', 'american':'tradamerican',
'indian':'indpak', 'chinese':'chinese','japanese':'japanese', 'thai':'thai',
'greek':'greek', 'halal':'halal'}

""" --- Helpers to build responses which match the structure of the necessary dialog actions --- """


def get_slots(intent_request):
    return intent_request['currentIntent']['slots']

#prompt for the slot once more that was violated first in our check
def elicit_slot(session_attributes, intent_name, slots, slot_to_elicit, message):
    return {
        'sessionAttributes': session_attributes,
        'dialogAction': {
            'type': 'ElicitSlot',
            'intentName': intent_name,
            'slots': slots,
            'slotToElicit': slot_to_elicit,
            'message': message
        }
    }


def close(session_attributes, fulfillment_state, message):
    response = {
        'sessionAttributes': session_attributes,
        'dialogAction': {
            'type': 'Close',
            'fulfillmentState': fulfillment_state,
            'message': message
        }
    }

    return response


def delegate(session_attributes, slots):
    return {
        'sessionAttributes': session_attributes,
        'dialogAction': {
            'type': 'Delegate',
            'slots': slots
        }
    }


""" --- Helper Functions --- """


def parse_int(n):
    try:
        return int(n)
    except ValueError:
        return float('nan')


def build_validation_result(is_valid, violated_slot, message_content):
    if message_content is None:
        return {
            "isValid": is_valid,
            "violatedSlot": violated_slot,
        }

    return {
        'isValid': is_valid,
        'violatedSlot': violated_slot,
        'message': {'contentType': 'PlainText', 'content': message_content}
    }


def isvalid_date(date):
    try:
        dateutil.parser.parse(date)
        return True
    except ValueError:
        return False


def validate_reservation(location, date, cuisine, party, time, phone):
    #check location later
    #check phone number later
    
    if party is not None:
        party = parse_int(party)
        if(party < 1):
            return build_validation_result(False,
                                        'Party',
                                        'I cannot make a reservation for a party size of {}. Can you give me a party size '
                                        'greater than zero?'.format(party))

    cuisine_types = [ 'mexican', 'american', 'indian', 'chinese', 'japanese','thai','greek','halal']
    if cuisine is not None and cuisine.lower() not in cuisine_types:
        return build_validation_result(False,
                                       'Cuisine',
                                       'We do not have the ability to book {} restaurants, would you like to try something else?  '
                                       'Our most popular cuisine is Chinese food'.format(cuisine))

    if date is not None:
        #check validity of date
        if not isvalid_date(date):
            return build_validation_result(False, 'Date', 'I did not understand that, what date would you like to make a reservation for?')
        #make sure we are making a reservation for today or later    
        elif (datetime.datetime.strptime(date, '%Y-%m-%d').date() < datetime.datetime.today().date()):
            return build_validation_result(False, 'Date', 'I cannot make a reservation in the past. What future date would you like to make a reservation for?')

    if time is not None:
        #time is just a string in the AWS.time slot needs to be 5 chars long
        if len(time) != 5:
            # Not a valid time; use a prompt defined on the build-time model.
            return build_validation_result(False, 'Time', "please enter a valid time for your reservation")

        hour, minute = time.split(':')
        hour = parse_int(hour)
        minute = parse_int(minute)
        if math.isnan(hour) or math.isnan(minute):
            # Not a valid time; use a prompt defined on the build-time model.
            return build_validation_result(False, 'Time', "Please enter a time for your reservation.")

        #assumption that restaurants open at 9 am and close at 10 pm 
        if hour < 9 or hour > 22:
            # Outside of business hours
            return build_validation_result(False, 'Time', 'Restaurant business hours are typically from nine a m. to ten p m. Can you specify a time during this range?')

        if(datetime.datetime.strptime(date, '%Y-%m-%d').date() == datetime.datetime.today().date()):
            now = datetime.datetime.today().time()
            current_time = now.strftime("%H:%M")
            if(current_time > time): 
                return build_validation_result(False, 'Time', 'It looks like the time you selected has already passed. Are there any times later in the day that work for you?')

    if phone is not None:
        #RFC5322 Compliant regex for checking valid emails
        #CITATION: https://stackabuse.com/python-validate-email-address-with-regular-expressions-regex/
        regex = re.compile(r"([-!#-'*+/-9=?A-Z^-~]+(\.[-!#-'*+/-9=?A-Z^-~]+)*|\"([]!#-[^-~ \t]|(\\[\t -~]))+\")@([-!#-'*+/-9=?A-Z^-~]+(\.[-!#-'*+/-9=?A-Z^-~]+)*|\[[\t -Z^-~]*])")
        if not re.fullmatch(regex, phone):
            return build_validation_result(False, 'Phone', 'It looks like the email you entered is invalid. Could you give me a different email to work with?')
        
    if location is not None:
        if location.lower() not in NYC_KNICKNAMES:
            return build_validation_result(False, 'Location', 'I currently cannnot make reservations in {}. Our most popular location is NYC. Can you give me another location to work with?'.format(location))

    return build_validation_result(True, None, None)
    



def push_to_sqs(msg_body):
    sqs_client = boto3.client('sqs')
    sqs_queue_url = sqs_client.get_queue_url(QueueName="DiningSuggestionsQueue")['QueueUrl']
    try:
        msg = sqs_client.send_message(QueueUrl=sqs_queue_url,
                                      MessageBody=json.dumps(msg_body))
    except ClientError as e:
        logging.error(e)
        return None
    return msg

""" --- Functions that control the bot's behavior --- """


def dining_suggestions_intent(intent_request):
    """
    Performs dialog management and fulfillment for ordering flowers.
    Beyond fulfillment, the implementation of this intent demonstrates the use of the elicitSlot dialog action
    in slot validation and re-prompting.
    """

    location = get_slots(intent_request)["Location"]
    date = get_slots(intent_request)["Date"]
    cuisine = get_slots(intent_request)["Cuisine"]
    party = get_slots(intent_request)["Party"]
    time = get_slots(intent_request)["Time"]
    phone = get_slots(intent_request)["Phone"]



    source = intent_request['invocationSource']
    #case where we need to keep having a convo
    if source == 'DialogCodeHook':
        # Perform basic validation on the supplied input slots.
        # Use the elicitSlot dialog action to re-prompt for the first violation detected.
        slots = get_slots(intent_request)

        validation_result = validate_reservation(location, date, cuisine, party, time, phone)
        #if we have an invalid result elicit the violated response with our message
        if not validation_result['isValid']:
            #clear out the shoddy violated slot value
            slots[validation_result['violatedSlot']] = None
            return elicit_slot(intent_request['sessionAttributes'],
                               intent_request['currentIntent']['name'],
                               slots,
                               validation_result['violatedSlot'],
                               validation_result['message'])

        # Pass the price of the flowers back through session attributes to be used in various prompts defined
        # on the bot model.
        output_session_attributes = intent_request['sessionAttributes'] if intent_request['sessionAttributes'] is not None else {}
        """ if flower_type is not None:
            output_session_attributes['Price'] = len(flower_type) * 5  # Elegant pricing model """
        
        return delegate(output_session_attributes, get_slots(intent_request))

    # Order the flowers, and rely on the goodbye message of the bot to define the message to the end user.
    # In a real bot, this would likely involve a call to a backend service.
    finalSessionAttributes = {
        "location" : location,
        "date" : date,
        "cuisine": CUISINES_DICT[cuisine],
        "party" : party,
        "time" : time,
        "phone": phone
    }
    push_to_sqs(finalSessionAttributes)
    return close(finalSessionAttributes,
                 'Fulfilled',
                 {'contentType': 'PlainText',
                  'content': 'You’re all set. Expect my suggestions shortly! Have a good day.'})


""" --- Intents --- """


def dispatch(intent_request):
    """
    Called when the user specifies an intent for this bot.
    """

    #logger.debug('dispatch userId={}, intentName={}'.format(intent_request['userId'], intent_request['currentIntent']['name']))

    intent_name = intent_request['currentIntent']['name']

    # Dispatch to your bot's intent handlers
    if intent_name == 'DiningSuggestionsIntent':
        return dining_suggestions_intent(intent_request)
        
    elif intent_name == 'GreetingIntent':
        session_attributes = intent_request['sessionAttributes'] if intent_request['sessionAttributes'] is not None else {}
        response = {
            'sessionAttributes': session_attributes,
            'dialogAction': {
                'type': 'Close',
                'fulfillmentState': 'Fulfilled',
                'message': {'contentType': 'PlainText',
                  'content': 'Hi how may I help?'}
            }
        }
        return response
        
    elif intent_name == 'ThankYouIntent':
        session_attributes = intent_request['sessionAttributes'] if intent_request['sessionAttributes'] is not None else {}
        response = {
            'sessionAttributes': session_attributes,
            'dialogAction': {
                'type': 'Close',
                'fulfillmentState': 'Fulfilled',
                'message': {'contentType': 'PlainText',
                  'content': 'You\'re welcome!'}
            }
        }
        return response
    #add additional intent validation if necessary should just be dinging suggestions

    
    else:
        raise Exception('Intent with name ' + intent_name + ' not supported')


""" --- Main handler --- """


def lambda_handler(event, context):
    """
    Route the incoming request based on intent.
    The JSON body of the request is provided in the event slot.
    """
    # By default, treat the user request as coming from the America/New_York time zone.
    os.environ['TZ'] = 'America/New_York'
    time.tzset()
    #logger.debug('event.bot.name={}'.format(event['bot']['name']))
    print(event)
    return dispatch(event)