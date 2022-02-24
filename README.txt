---------------------
RYAN LEE
DBL2127
6998_Dining_Concierge
2/23/22
---------------------

1. Citations are present within the codebase where applicable. 

2. The frontend URL is: 
http://dining-conceierge-frontend.s3-website-us-east-1.amazonaws.com/

3. All code related to scraping and formatting the json for bulk upload to
dynamodb and elasticsearch can be found in 'yelp_scraping/'. If you are purely
interested in the yelp scraping that file is scrape_yelp.py

4. I have included screenshots of relevant statistics from my dynamodb table as
well as elasticsearch index to highlight the presence of 5000+ items/documents.
The dataset is guaranteed not to have duplicates because the yelp id is
specified in their documentation to be unique to each restaurant.  This id is
then used as the partition key for the dynamodb table eliminating any duplicates
that may have been originally present due to having multiple cuisines listed
inside of their yelp json. The elasticsearch table was generated directly off of
the back of the dynamodb data and simply contains a subset of that tables fields
(id, cuisine).

5. All of the functionality was implemented. I send emails via SES.

END OF README
-------------------------------------------------------------------------------
