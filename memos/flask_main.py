"""
Flask web app connects to Mongo database.
Keep a simple list of dated memoranda.

Representation conventions for dates: 
   - We use Arrow objects when we want to manipulate dates, but for all
     storage in database, in session or g objects, or anything else that
     needs a text representation, we use ISO date strings.  These sort in the
     order as arrow date objects, and they are easy to convert to and from
     arrow date objects.  (For display on screen, we use the 'humanize' filter
     below.) A time zone offset will 
   - User input/output is in local (to the server) time.  
"""

import flask
from flask import g
from flask import render_template
from flask import request
from flask import url_for

import json
import logging

import sys

# Date handling 
import arrow   
from dateutil import tz  # For interpreting local times

# Mongo database
import pymongo
from pymongo import MongoClient

import config
CONFIG = config.configuration()

MONGO_CLIENT_URL = "mongodb://{}:{}@{}:{}/{}".format(
    CONFIG.DB_USER,
    CONFIG.DB_USER_PW,
    CONFIG.DB_HOST, 
    CONFIG.DB_PORT, 
    CONFIG.DB)

print("Using URL '{}'".format(MONGO_CLIENT_URL))

###
# Globals
###

app = flask.Flask(__name__)
app.secret_key = CONFIG.SECRET_KEY
global tokencounter

####
# Database connection per server process
###

try: 
    dbclient = MongoClient(MONGO_CLIENT_URL)
    db = getattr(dbclient, CONFIG.DB)
    collection = db.dated

except:
    print("Failure opening database.  Is Mongo running? Correct password?")
    sys.exit(1)

###
# Pages
###

@app.route("/")
@app.route("/index")
def index():
  app.logger.debug("Main page entry")
  g.memos = get_memos()
  for memo in g.memos: 
      app.logger.debug("Memo: " + str(memo))
  return flask.render_template('index.html')

# Make an interface for creating memos
@app.route("/create")
def create():
    app.logger.debug("Create")
    return flask.render_template('create.html')

@app.errorhandler(404)
def page_not_found(error):
    app.logger.debug("Page not found")
    return flask.render_template('page_not_found.html',
                                 badurl=request.base_url,
                                 linkback=url_for("index")), 404

#################
#
# Functions used within the templates
#
#################

@app.template_filter( 'humanize' )
def humanize_arrow_date( date ):
    """
    Date is internal UTC ISO format string.
    Output should be "today", "yesterday", "in 5 days", etc.
    Arrow will try to humanize down to the minute, so we
    need to catch 'today' as a special case. 
    """
    try:
        then = arrow.get(date).to('local')
        now = arrow.utcnow().to('local')
        if then.date() == now.date():
            human = "Today"
        else: 
            human = then.humanize(now)
            if human == "in a day":
                human = "Tomorrow"
    except: 
        human = date
    return human

@app.route("/delete/<token>", methods=['POST'])
def delete_memo(token):
  """
  Args:
    memo: text of the memo the user wants to erase
  Returns:
    Calls get-memos for updated records
  """
  #bad_record = collection.find( { "token" : token } )
  #logging.info(bad_record)
  collection.delete_one({ "token" : token }) # currently in form of cursor, need in form of {"token": token}
  return index()

@app.route("/add")
def add_memo(memo, date):
  """
  Args:
    memo: text for the new memo
    date: date of memo
  Returns:
    Calls get_memos for updated records
  """
  tokencounter += 1
  record = { "type": "dated_memo", 
           "date":  arrow.utcnow().naive, # FIXME: make an arrow object of the given date
           "text": memo,
           "token": "sampletoken{}".format(tokencounter)
          }
  collection.insert(record)
  return index()

#############
#
# Functions available to the page code above
#
##############

def get_memos():
    """
    Returns all memos in the database, in a form that
    can be inserted directly in the 'session' object.
    """
    records = [ ]
    for record in collection.find( { "type": "dated_memo" } ):
        record['date'] = arrow.get(record['date']).isoformat()
        del record['_id']
        records.append(record)
    return records 

if __name__ == "__main__":
    app.debug=CONFIG.DEBUG
    app.logger.setLevel(logging.DEBUG)
    app.run(port=CONFIG.PORT,host="0.0.0.0")
