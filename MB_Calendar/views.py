from django.shortcuts import render
from django.http import HttpResponse, HttpResponseRedirect
from django.urls import reverse
from datetime import datetime, timedelta
from dateutil import tz, parser
from MB_Calendar.auth_helper import get_sign_in_flow, get_token_from_code, store_user, remove_user_and_token, get_token
from MB_Calendar.graph_helper import *
from MB_Calendar.utils_graph_helper import *

def home(request):
  context = initialize_context(request)

  return render(request, 'home.html', context)


def initialize_context(request):
  context = {}

  # Check for any errors in the session
  error = request.session.pop('flash_error', None)

  if error != None:
    context['errors'] = []
    context['errors'].append(error)

  # Check for user in the session
  context['user'] = request.session.get('user', {'is_authenticated': False})
  return context

def sign_in(request):
  # Get the sign-in flow
  flow = get_sign_in_flow()
  # Save the expected flow so we can use it in the callback
  try:
    request.session['auth_flow'] = flow
  except Exception as e:
    print(e)
  # Redirect to the Azure sign-in page
  return HttpResponseRedirect(flow['auth_uri'])

def auth_callback(request):
  # Make the token request
  result = get_token_from_code(request)

  #Get the user's profile
  user = get_user(result['access_token'])

  # Store user
  store_user(request, user)
  return HttpResponseRedirect(reverse('home'))

def sign_out(request):
  # Clear out the user and token
  remove_user_and_token(request)

  return HttpResponseRedirect(reverse('home'))

def calendar(request):
  context = initialize_context(request)
  user = context['user']

  # Load the user's time zone
  # Microsoft Graph can return the user's time zone as either
  # a Windows time zone name or an IANA time zone identifier
  # Python datetime requires IANA, so convert Windows to IANA
  time_zone = get_iana_from_windows(user['timeZone'])
  tz_info = tz.gettz(time_zone)
  if (
    request.GET.get("ti-start")==None or
    request.GET.get("ti-start")=="" or
    request.GET.get("ti-end")==None or
    request.GET.get("ti-end")=='' ):
      # Get midnight today in user's time zone
      start = datetime.now(tz_info).replace(
        hour=0,
        minute=0,
        second=0,
        microsecond=0)

      end = start + timedelta(days=31)

  else:
      print(request.GET.get("ti-start"))
      start_dt = datetime.fromisoformat(request.GET.get("ti-start"))
      start = datetime(
        start_dt.year,
        start_dt.month,
        start_dt.day,
        start_dt.hour,
        start_dt.minute,
        start_dt.second,
        start_dt.microsecond,
        tz_info)
      end_dt = datetime.fromisoformat(request.GET.get("ti-end"))
      end = datetime(
         end_dt.year,
         end_dt.month,
         end_dt.day,
         end_dt.hour,
         end_dt.minute,
         end_dt.second,
         end_dt.microsecond,
         tz_info)

  context["str_start"] = start.strftime('%Y-%m-%dT%H:%M')
  context["str_end"] = end.strftime('%Y-%m-%dT%H:%M')

  token = get_token(request)

  events = get_calendar_events(
    token,
    start.isoformat(timespec='seconds'),
    end.isoformat(timespec='seconds'),
    user['timeZone'])

  if events:
    # Convert the ISO 8601 date times to a datetime object
    # This allows the Django template to format the value nicely
    for event in events['value']:
      event['start']['dateTime'] = parser.parse(event['start']['dateTime'])
      event['end']['dateTime'] = parser.parse(event['end']['dateTime'])
      """
      accesso alle coordinate fornite da graph
      locations = event["locations"]
      if len(locations) > 0 and locations[0].get("coordinates"):
          location = locations[0]
          latitude = str(location["coordinates"]["latitude"])
          longitude = str(location["coordinates"]["longitude"])
      else:
          latitude = ""
          longitude = ""
      event['coordinates'] = {}
      event['coordinates']['latitude'] = latitude
      event['coordinates']['longitude'] = longitude
      """

    context['events'] = events['value']

  return render(request, 'calendar.html', context)

def newevent(request):
  context = initialize_context(request)
  user = context['user']

  if request.method == 'POST':
    # Validate the form values
    # Required values
    if (not request.POST['ev-subject']) or \
       (not request.POST['ev-start']) or \
       (not request.POST['ev-end']):
      context['errors'] = [
        { 'message': 'Invalid values', 'debug': 'The subject, start, and end fields are required.'}
      ]
      return render(request, 'tutorial/newevent.html', context)

    attendees = None
    if request.POST['ev-attendees']:
      attendees = request.POST['ev-attendees'].split(';')
    body = request.POST['ev-body']

    # Create the event
    token = get_token(request)

    create_event(
      token,
      request.POST['ev-subject'],
      request.POST['ev-start'],
      request.POST['ev-end'],
      request.POST['ev-location'],
      attendees,
      request.POST['ev-body'],
      user['timeZone'])

    # Redirect back to calendar view
    return HttpResponseRedirect(reverse('calendar'))
  else:
    # Render the form
    return render(request, 'newevent.html', context)
