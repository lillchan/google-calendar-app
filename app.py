import gflags
import httplib2
import datetime
import dateutil.parser
import random
import string
import json

from apiclient.discovery import build
from oauth2client.file import Storage
from oauth2client.client import OAuth2WebServerFlow
from oauth2client.tools import run
from flask import Flask, request, render_template, session, make_response
from datetime import date, timedelta
from rfc3339 import rfc3339  #small library to format dates to rfc3339 strings (format for Google Calendar API requests)
# from flask.ext.wtf import Form, TextField, TextAreaField, SubmitField

app = Flask(__name__)
app.secret_key = "development key"  # secret key for wtforms, so someone can't create and submit a malicious form to server
FLAGS = gflags.FLAGS

# Set up a Flow object to be used if we need to authenticate. This
# sample uses OAuth 2.0, and we set up the OAuth2WebServerFlow with
# the information it needs to authenticate. Note that it is called
# the Web Server Flow, but it can also handle the flow for native
# applications
# The client_id and client_secret are copied from the API Access tab oauth2client
# the Google APIs Console

FLOW = OAuth2WebServerFlow(
    client_id='524876334284.apps.googleusercontent.com',
    client_secret='_yi1QfD2NJrKAX5u4cceFKj5',
    scope='https://www.googleapis.com/auth/calendar',
    user_agent='Schedule It/v1')

# To disable the local server feature, uncomment the following line:
# FLAGS.auth_local_webserver = False

# If the Credentials don't exist or are invalid, run through the native client_secret
# flow. The Storage object will ensure that if successful the good
# Credentials will get written back to a file.
storage = Storage('calendar.dat')
credentials = storage.get()
if credentials is None or credentials.invalid == True:
    credentials = run(FLOW, storage)

# Create an httplib2.Http object to handle our HTTP requests and authorize it
# with our good Credentials.
http = httplib2.Http()
http = credentials.authorize(http)

# Build a service object for interacting with the API. Visit
# the Google API Console
# to get a developKey for your own application
service = build(serviceName='calendar', version='v3', http=http, developerKey='AIzaSyD2rYjoab1qlDJNifetNZun-qaLFvNvcJ4')


@app.route("/", methods=["GET", "POST"])
def search_calender():
    page_token = None

    # class ContactForm(Form):
    #     searchStartDate = DateField("Date to Start Searching")
    #     searchEndDate = DateField("Date to Stop Searching")
    #     subject = TextField("Subject")
    #     message = TextAreaField("Message")
    #     submit = SubmitField("Send")

    if request.method == 'POST':
        return 'Form posted.'
    elif request.method == 'GET':
        while True:
            # form = ContactForm()
            calendar_list = service.calendarList().list(pageToken=page_token).execute()
            calendar_list_items = calendar_list['items']
            # if calendar_list['items']:
            #     for calendar_list_entry in calendar_list['items']:
            #         print calendar_list_entry['summary']
            page_token = calendar_list.get('nextPageToken')
            if not page_token:
                break
        return render_template("index.html", calendar_list=calendar_list_items)

# pseudo code
# input - start date, end date, start time, end time
# initialize empty list to store potential times
# for day in range(start date to end date):
    # create datetime from start/end date and start/end time from user inputs
    # google calendar api call with start date and end date created in last line (stored in var)
    # if var from last line is empty:
        # store start datetime in list as a suggested free slot
    # if potential times reaches three items, break from loop


def generate_date_list(startdate, enddate, starttime, endtime, calendarid, pagetoken):
    apptStartDate = datetime.datetime.strptime(startdate, '%Y-%m-%d').date()
    apptStartTime = datetime.datetime.strptime(starttime, '%H:%M').time()

    apptEndDate = datetime.datetime.strptime(enddate, '%Y-%m-%d').date()
    apptEndTime = datetime.datetime.strptime(endtime, '%H:%M').time()

    td = datetime.timedelta(hours=24)
    current_date = apptStartDate
    free_dates = []

    while current_date <= apptEndDate:
        start_combined = datetime.datetime.combine(current_date, apptStartTime)
        start_rfc3339 = rfc3339(start_combined)

        end_combined = datetime.datetime.combine(current_date, apptEndTime)
        end_rfc3339 = rfc3339(end_combined)

        events = service.events().list(calendarId=calendarid, pageToken=pagetoken, timeMax=end_rfc3339, timeMin=start_rfc3339).execute()
        event_items = events.get('items')
        if not event_items:
            free_dates.append(current_date)
        current_date += td
    return free_dates


@app.route("/search_events", methods=['POST'])
def search_events():
    page_token = None
    while True:
        startdate = request.form['apptStartDate']
        starttime = request.form['apptStartTime']
        enddate = request.form['apptEndDate']
        endtime = request.form['apptEndTime']
        calendarid = request.form['calendarlist']

        free_dates = generate_date_list(startdate, enddate, starttime, endtime, calendarid, page_token)
        free_dates_string = []

        for dates in free_dates:
            free_dates_string.append(dates.strftime("%m/%d/%y"))

        if not page_token:
            break

    return render_template("suggestions.html", free_dates=free_dates_string)

if __name__ == "__main__":
    app.run(debug=True)
