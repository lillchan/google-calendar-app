# user input from form is passed to this route

# alternative:
# store start and end datetime (in rfc3339 format) from user input into variables
# use start/end datetimes in events request to get object with array of events within start and end times
# grab array of events and store in a variable
# define empty dictionary
# loop through events and for each event:
    # grab the start time
    # strip out the start date
    # does start time already exist in dictionary?
        # yes - append entire event to the list associated with the date
        # no - create new key:value with date as key, store entire event into a list
    # return dictionary
# store start and end times (no date) into variables
# for each date in dictionary
    # for each event in date
        # if it has a start datetime
            # grab time
            # if start time from user is greater than start time of event
                # if end time of event


# input - start date, end date, start time, end time
# initialize empty list to store potential times
# for day in range(start date to end date):
    # create datetime from start/end date and start/end time from user inputs
    # google calendar api call with start date and end date created in last line (stored in var)
    # if var from last line is empty:
        # store start datetime in list as a suggested free slot
    # if potential times reaches three items, break from loop
def daterange(start, end):
    daterange = []
    for n in range(int ((end - start).days)):
        yield start + timedelta(n)
    for single_date in daterange(start, end):
        daterange.append(strftime("%Y-%m-%d", single_date.timetuple()))
    return daterange


def generate_dates(start_date, end_date):
    td = datetime.timedelta(hours=24)
    daterange = []
    current_date = start_date
    while current_date <= end_date:
        daterange.append(current_date)
        current_date += td
    return daterange

start_date = datetime.date(2010, 1, 25)
end_date = datetime.date(2010, 3, 5)
generate_dates(start_date, end_date)


def google_calendar_call(startdate, enddate, starttime, endtime):
    apptStartDate = datetime.datetime.strptime(startdate, '%Y-%m-%d').date()
    apptStartTime = datetime.datetime.strptime(starttime, '%H:%M').time()
    start = datetime.datetime.combine(apptStartDate, apptStartTime)
    start_rfc3339 = rfc3339(start)

    apptEndDate = datetime.datetime.strptime(enddate, '%Y-%m-%d').date()
    apptEndTime = datetime.datetime.strptime(endtime, '%H:%M').time()
    end = datetime.datetime.combine(apptEndDate, apptEndTime)
    end_rfc3339 = rfc3339(end)

    daterange = generate_dates(start, end)

    print daterange



@app.route("/search_events", methods=['POST'])
def search_events():
    page_token = None

    startdate = request.form['apptStartDate']
    starttime = request.form['apptStartTime']
    enddate = request.form['apptEndDate']
    endtime = request.form['apptEndTime']

    google_calendar_call(startdate, enddate, starttime, endtime)

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