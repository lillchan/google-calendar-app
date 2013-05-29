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
from datetime import date, timedelta as td
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


@app.route("/search_events", methods=['POST'])
def search_events():
    page_token = None
    apptStartDate = datetime.datetime.strptime(request.form['apptStartDate'], '%Y-%m-%d')
    apptStartTime = datetime.datetime.strptime(request.form['apptStartTime'], '%H:%M').time()
    start = datetime.datetime.combine(apptStartDate, apptStartTime)
    start_rfc3339 = rfc3339(start)

    apptEndDate = datetime.datetime.strptime(request.form['apptEndDate'], '%Y-%m-%d')
    apptEndTime = datetime.datetime.strptime(request.form['apptEndTime'], '%H:%M').time()
    end = datetime.datetime.combine(apptEndDate, apptEndTime)
    end_rfc3339 = rfc3339(end)

    print start_rfc3339
    print end_rfc3339
    print request.form

    # now = datetime.datetime.utcnow()
    # now_rfc3339 = now.isoformat("T") + "Z"
    # three_weeks = now + datetime.timedelta(weeks=3)
    # three_weeks_rfc3339 = three_weeks.isoformat("T") + "Z"
    while True:
        events = service.events().list(calendarId=request.form['calendarlist'], pageToken=page_token, timeMax=end_rfc3339, timeMin=start_rfc3339).execute()
        event_items = events.get('items')
        if not event_items:
            event_items = []  # there are no events during that time frame?
        print "event items:"
        print event_items
        events_start_end_hours = []
        # tenoclock = datetime.datetime.strptime('10:00', '%H:%M').time()
        for item in event_items:
            if 'date' in item['start']:
                start_date = datetime.datetime.strptime(item['start']['date'], '%Y-%m-%d')  # format of item['start']: 2009-09-10
                end_date = datetime.datetime.strptime(item['end']['date'], '%Y-%m-%d')
                for x in range((end_date - start_date).days * 24):
                    events_start_end_hours.append(start_date + td(0, x * 60 * 60))
            elif 'dateTime' in item['start']:
                start_date = datetime.datetime.strptime(item['start']['dateTime'][:16], '%Y-%m-%dT%H:%M')  # format: 2007-05-29T21:00:00-07:00, so must slice out date and time only (no time zone info)
                end_date = datetime.datetime.strptime(item['end']['dateTime'][:16], '%Y-%m-%dT%H:%M')
                print start_date
                print end_date
                for x in range((end_date - start_date).seconds / 60 / 60):
                    events_start_end_hours.append(start_date + td(0, x * 60 * 60))
        print "events_start_end_hours:"
        print set(events_start_end_hours)
        date_set = set(start + td(0, x * 60 * 60) for x in range((end - start).days * 24))
        # timedelta(days, seconds)
        # multiplying days by 24 should give the number of hours between start and end, which is made into a range
        # finally, we loop through each hour, starting with start
        print "date_set:"
        print date_set
        free_dates = sorted(date_set - set(events_start_end_hours))  # all the dates that don't have an event scheduled
        print "free_dates:"
        print free_dates
        page_token = events.get('nextPageToken')
        if not page_token:
            break
    return render_template("suggestions.html", free_dates=free_dates)

if __name__ == "__main__":
    app.run(debug=True)
