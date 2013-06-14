import datetime
import json
import urllib
import urllib2
import requests
import os

from flask import Flask, request, render_template, session, url_for, redirect, flash, send_from_directory
from rfc3339 import rfc3339  # small library to format dates to rfc3339 strings (format for Google Calendar API requests)
from flask_oauth import OAuth
from dateutil import parser

#environment variables
PORT = int(os.environ.get('PORT', 5000))
GOOGLE_API_KEY = os.environ.get('GOOGLE_API_KEY')
GOOGLE_CLIENT_ID = os.environ.get('GOOGLE_CLIENT_ID')
GOOGLE_CLIENT_SECRET = os.environ.get('GOOGLE_CLIENT_SECRET')
REDIRECT_URI = os.environ.get('REDIRECT_URI')
SECRET_KEY = os.environ.get('SECRET_KEY')
DEBUG = os.environ.get('DEBUG')

app = Flask(__name__)
app.debug = DEBUG
app.secret_key = SECRET_KEY
app.port = PORT
app.host = '0.0.0.0'
oauth = OAuth()

# to connect to a remote app create a OAuth object and register a remote app using remote_app()
google = oauth.remote_app('google',
    base_url='https://www.google.com/accounts/',
    authorize_url='https://accounts.google.com/o/oauth2/auth',
    request_token_url=None,
    request_token_params={'scope': 'https://www.googleapis.com/auth/calendar',
        'response_type': 'code'},
    access_token_url='https://accounts.google.com/o/oauth2/token',
    access_token_method='POST',
    access_token_params={'grant_type': 'authorization_code'},
    consumer_key=GOOGLE_CLIENT_ID,
    consumer_secret=GOOGLE_CLIENT_SECRET)


@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404


@app.route('/favicon.ico')
def favicon():
    return send_from_directory("/static", "favicon.ico")


# welcome page has user log in to their google account
@app.route("/")
def welcome():
    return render_template('index.html')

# trying to clean up code, but it doesn't work - not sure why?
# def google_calendar_request(url, data):
#     access_token = session.get('access_token')
#     print access_token
#     if access_token is None:
#         return redirect(url_for('login'))

#     access_token = access_token[0]

#     headers = {'Authorization': 'OAuth ' + access_token}
#     req = urllib2.Request(url, data, headers)
#     print req
#     try:
#         res = urllib2.urlopen(req)
#         print res
#     except (urllib2.URLError,), e:
#         if e.code == 401 or e.code == 403:
#             # Unauthorized - bad token
#             session.pop('access_token', None)
#             return redirect(url_for('login'))
#         return str(e.code)
#     response = res.read()
#     return response


@app.route("/search")
def search():
    # url = 'https://www.googleapis.com/calendar/v3/users/me/calendarList'
    # data = None
    # response = json.dumps(google_calendar_request(url, data))
    # print response

    # check if there is already an access token stored in session
    access_token = session.get('access_token')
    # if not, then redirect user to log in with google
    if access_token is None:
        return redirect(url_for('login'))

    # access_token is returned as a tuple, but since there is no secret, just use the first element
    access_token = access_token[0]

    # create header for the get request (a dictionary)
    headers = {'Authorization': 'OAuth ' + access_token}
    # urllib2.Request(url, data, headers)
    # HTTP request will be POST instead of GET when data provided
    # request to get a list of the user's google calendars
    req = urllib2.Request('https://www.googleapis.com/calendar/v3/users/me/calendarList', None, headers)
    try:
        # open a url, which can either be a string or Request object
        # urllib2.urlopen(url, data)
        res = urllib2.urlopen(req)
    except (urllib2.URLError,), e:
        if e.code == 401 or e.code == 403:
            # Unauthorized - bad token
            # delete token from session and redirect user to log in with google
            session.pop('access_token', None)
            return redirect(url_for('login'))
        # return the error code
        return str(e.code)
    # returns a string of the http response (list of user's calendars)
    response = res.read()
    # turn the response into a JSON object
    # pull out the 'items', which is an array of calendar id's
    calendar_list = json.loads(response)['items']
    # send the list of calendar id's to the search form
    return render_template('search.html', calendar_list=calendar_list)


@app.route("/login")
def login():
    # callback is the authorized route
    callback = url_for('authorized', _external=True)
    # sign in with google - takes a callback that indicates where user will be redirected
    # alternatively, it redirects to route decorated as authorized_handler()
    return google.authorize(callback=callback)


# redirect_uri = '/authorized'
@app.route(REDIRECT_URI)
@google.authorized_handler
def authorized(resp):
    # error handling, in case resp is empty - user didn't give app access to their calendar
    # will return user to the welcome page and flash an error message
    if resp is None:
        flash(u'Whoops, you denied us access to your Google Calendar. We can not help you schedule without access! Please sign in again.')
        return redirect(url_for('welcome'))
    access_token = resp['access_token']
    # store the access token in the session
    session['access_token'] = access_token, ''
    return redirect(url_for('search'))


# tokengetter as required by flask-oauth module
# must return a tuple of (token, secret) - google only gives a token, so it returns (token, '')
@google.tokengetter
def get_access_token():
    return session.get('access_token')


@app.route("/logout")
def logout():
    # remove the username from the session if it's there and redirect to welcome/sign in page
    session.pop('access_token', None)
    return redirect(url_for('welcome'))


# function to turn date and time strings into date/time objects
# returns list with date and time objects
# def strp_date_time(date, time):
#     apptDate = datetime.datetime.strptime(date, '%Y-%m-%d').date()
#     apptTime = datetime.datetime.strptime(time, '%H:%M').time()
#     return [apptDate, apptTime]


# function to turn strings of date and time into rfc3339 format for Google Calendar API call
# returns string of datetime in rfc339 format
def datetime_combine_rfc3339(date, time):
    combined = datetime.datetime.combine(date, time)
    rfc3339_datetime = rfc3339(combined)
    return rfc3339_datetime


# function to generate list of suggested free dates for user to choose from
def generate_date_list(startdate, enddate, starttime, endtime, calendarid):
    apptStartDate = datetime.datetime.strptime(startdate, '%Y-%m-%d').date()
    apptStartTime = datetime.datetime.strptime(starttime, '%H:%M').time()
    apptEndDate = datetime.datetime.strptime(enddate, '%Y-%m-%d').date()
    apptEndTime = datetime.datetime.strptime(endtime, '%H:%M').time()
    # td used to increment while loop one day at a time (24 hours)
    td = datetime.timedelta(hours=24)
    # store user's requested start time for use in while loop
    current_date = apptStartDate
    # empty list to store suggested free dates
    free_dates = []
    access_token = session.get('access_token')
    access_token = access_token[0]
    headers = {'Authorization': 'OAuth ' + access_token}
    # loop from user's requested start date to end date
    while current_date <= apptEndDate:
        # format start and end times for Google Calendar API call
        start_rfc3339 = datetime_combine_rfc3339(current_date, apptStartTime)
        end_rfc3339 = datetime_combine_rfc3339(current_date, apptEndTime)
        # create dictionary of data to send with request
        data = {}
        data['key'] = GOOGLE_API_KEY
        data['timeMin'] = start_rfc3339
        data['timeMax'] = end_rfc3339
        # url encode the data sending with the request
        # urlencode converts a mapping object or a sequence of two-element tuples to a "percent-encoded" string
        url_values = urllib.urlencode(data)
        # form the url for the request, including any required variables
        # want a GET request, so data parameter is None - data is passed as part of url
        url = 'https://www.googleapis.com/calendar/v3/calendars/'
        full_url = url + calendarid + '/events?' + url_values
        req = urllib2.Request(full_url, None, headers)
        try:
            res = urllib2.urlopen(req)
        except (urllib2.URLError,), e:
            if e.code == 401 or e.code == 403:
                # Unauthorized - bad token
                session.pop('access_token', None)
                return redirect(url_for('login'))
            return str(e.code)
        response = res.read()
        event_list = json.loads(response)['items']
        # if there are no events given back, then that time is empty
        # add date to the suggested free time list
        if not event_list:
            free_dates.append(current_date)
        # if the length of the free_dates array has reached 5, then break from loop
        if len(free_dates) == 5:
            break
        # increment current_date by 1 day to continue while loop
        current_date += td
    return free_dates


@app.route("/search_events", methods=['POST'])
def search_events():
    startdate = request.form['apptStartDate']
    starttime = request.form['apptStartTime']
    enddate = request.form['apptEndDate']
    endtime = request.form['apptEndTime']
    calendarid = request.form['calendarlist']
    # format start and end times
    start_dt = datetime.datetime.strptime(starttime, '%H:%M').time()
    end_dt = datetime.datetime.strptime(endtime, '%H:%M').time()
    start_formatted = start_dt.strftime("%I:%M%p")
    end_formatted = end_dt.strftime("%I:%M%p")
    # get list of free dates (datetime objects)
    free_dates = generate_date_list(startdate, enddate, starttime, endtime, calendarid)
    print free_dates
    free_dates_string = []
    # convert free dates into a more reader friendly string
    for date in free_dates:
        free_dates_string.append(date.strftime("%m/%d/%Y"))
    # send list of free dates to render on suggestions page
    return render_template("suggestions.html", free_dates=free_dates_string, starttime=start_formatted, endtime=end_formatted, calendarid=calendarid)


@app.route("/schedule_event", methods=['POST'])
def schedule_event():
    # grab user inputs from the schedule_event form
    apptName = request.form['apptName']
    apptLocation = request.form['apptLocation']
    apptCalendarId = request.form['apptCalendarId']
    # from apptOptions, grab the start/end date and time user has chosen
    # apptOptions returns in format: 05/05/13, 12:00, 13:00
    # first, turn it into a list
    apptTime = request.form['apptOptions'].split()
    apptDate = apptTime[0]
    apptStartTime = apptTime[1]
    apptEndTime = apptTime[2]
    # convert datetime into rfc3339 format for Google API
    apptDate = datetime.datetime.strptime(apptDate, '%m/%d/%Y').date()
    apptStartTime = datetime.datetime.strptime(apptStartTime, '%I:%M%p').time()
    apptEndTime = datetime.datetime.strptime(apptEndTime, '%I:%M%p').time()
    # format start and end times for Google Calendar API call
    start_rfc3339 = datetime_combine_rfc3339(apptDate, apptStartTime)
    end_rfc3339 = datetime_combine_rfc3339(apptDate, apptEndTime)
    # put all the data needed with the post request into a dictionary
    event = {}
    event['summary'] = apptName
    event['location'] = apptLocation
    event['start'] = {'dateTime': start_rfc3339}
    event['end'] = {'dateTime': end_rfc3339}
    access_token = session.get('access_token')
    access_token = access_token[0]
    # form url for post request, including any variables that are required (calendar id)
    url = 'https://www.googleapis.com/calendar/v3/calendars/'
    full_url = url + apptCalendarId + '/events?'
    # don't forget to include the content type with the header, otherwise google won't be able to parse the data
    headers = {'Content-Type': 'application/json; charset=UTF-8', 'Authorization': 'OAuth ' + access_token}
    # use requests module to do a post request
    # json.dumps turns a list into a string (don't need to url encode this request)
    r = requests.post(full_url, data=json.dumps(event), headers=headers)
    # if successful, the response will include all the schedule event's details
    # first turn into a string
    response = r.text
    # then, turn into dictionary, so can pull out elements
    resJSON = json.loads(response)
    newApptName = resJSON['summary']
    newApptStart = resJSON['start']['dateTime']
    newApptEnd = resJSON['end']['dateTime']
    newApptLoc = resJSON['location']
    # format datetimes
    start_formatted = parser.parse(newApptStart).strftime("%m/%d/%Y at %I:%M%p")
    end_formatted = parser.parse(newApptEnd).strftime("%m/%d/%Y at %I:%M%p")
    print response
    return render_template("success.html", res=resJSON, apptName=newApptName, apptStart=start_formatted, apptEnd=end_formatted, apptLoc=newApptLoc)


if __name__ == "__main__":
    app.run()
