import gflags
import httplib2
import datetime

from apiclient.discovery import build
from oauth2client.file import Storage
from oauth2client.client import OAuth2WebServerFlow
from oauth2client.tools import run
from flask import Flask, request, render_template
from rfc3339 import rfc3339  # small library to format dates to rfc3339 strings (format for Google Calendar API requests)
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


# function to turn date and time strings into date/time objects
# returns list with date and time objects
def strp_date_time(date, time):
    apptDate = datetime.datetime.strptime(date, '%Y-%m-%d').date()
    apptTime = datetime.datetime.strptime(time, '%H:%M').time()
    return [apptDate, apptTime]


# function to turn strings of date and time into rfc3339 format for Google Calendar API call
# returns string of datetime in rfc339 format
def datetime_combine_rfc3339(date, time):
    combined = datetime.datetime.combine(date, time)
    rfc3339_datetime = rfc3339(combined)
    return rfc3339_datetime


# function to generate list of suggested free dates for user to choose from
def generate_date_list(startdate, enddate, starttime, endtime, calendarid, pagetoken):
    # strp_date_time returns list: [date object, time object]
    apptStartDateTime = strp_date_time(startdate, starttime)
    apptEndDateTime = strp_date_time(enddate, endtime)
    # td used to increment while loop one day at a time (24 hours)
    td = datetime.timedelta(hours=24)
    # store user's requested start time for use in while loop
    current_date = apptStartDateTime[0]
    # empty list to store suggested free dates
    free_dates = []
    # loop from user's requested start date to end date
    while current_date <= apptEndDateTime[0]:
        # format start and end times for Google Calendar API call
        start_rfc3339 = datetime_combine_rfc3339(current_date, apptStartDateTime[1])
        end_rfc3339 = datetime_combine_rfc3339(current_date, apptEndDateTime[1])
        # Google Calendar API call
        # returns a dictionary of calendar properties
        # one of the properties is a list of events that match the datetime criteria given
        events = service.events().list(calendarId=calendarid, pageToken=pagetoken, timeMax=end_rfc3339, timeMin=start_rfc3339).execute()
        # grab the list of events
        event_items = events.get('items')
        # if there are no events given back, then that time is empty
        # add date to the suggested free time list
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

        # TODO: add check to see if free_dates is empty (no free blocks in specified time period)

        for dates in free_dates:
            free_dates_string.append(dates.strftime("%Y-%m-%d"))

        if not page_token:
            break

    return render_template("suggestions.html", free_dates=free_dates_string, starttime=starttime, endtime=endtime)


@app.route("/schedule_event", methods=['POST'])
def schedule_event():
    # grab user inputs from the schedule_event form
    apptName = request.form['apptName']
    apptLocation = request.form['apptLocation']
    # from apptOptions, grab the start/end date and time user has chosen
    # apptOptions returns in format: 05/05/13, 12:00, 13:00
    # first, turn it into a list
    apptTime = request.form['apptOptions'].split()
    apptDate = apptTime[0]
    apptStartTime = apptTime[1]
    apptEndTime = apptTime[2]
    # convert datetime into rfc3339 format for Google API
    apptStartDateTime = strp_date_time(apptDate, apptStartTime)
    apptEndDateTime = strp_date_time(apptDate, apptEndTime)
    # format start and end times for Google Calendar API call
    start_rfc3339 = datetime_combine_rfc3339(apptStartDateTime[0], apptStartDateTime[1])
    end_rfc3339 = datetime_combine_rfc3339(apptEndDateTime[0], apptEndDateTime[1])

    event = {
      'summary': apptName,
      'location': apptLocation,
      'start': {
        'dateTime': start_rfc3339
      },
      'end': {
        'dateTime': end_rfc3339
      },
      # 'attendees': [
      #   {
      #     'email': 'attendeeEmail',
      #     # Other attendee's data...
      #   },
      #   # ...
      # ],
    }

    print event

    return "done!"

    # created_event = service.events().insert(calendarId='primary', body=event).execute()

    # print created_event['id']


if __name__ == "__main__":
    app.run(debug=True)
