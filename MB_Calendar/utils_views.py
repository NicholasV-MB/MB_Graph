from MB_Calendar.utils_graph_helper import *
from dateutil import tz, parser
from datetime import datetime, timedelta
from MB_Calendar.auth_helper import *
from MB_Calendar.graph_helper import get_calendar_events
import requests
import json

nominatim_base_url = "https://nominatim.openstreetmap.org/search"

def get_events_context_from_request(request):
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

    context["start"] = start
    context["end"] = end

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
    return context

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

def get_lat_long_from_location(address):
    r = requests.get('{0}?q={1}&format=jsonv2'.format(nominatim_base_url, address))
    json_resp = r.json()[0]
    lat = json_resp.get("lat")
    long = json_resp.get("lon")
    return lat, long
