from MB_Calendar.utils_graph_helper import *
from dateutil import tz, parser
from datetime import datetime, timedelta
from MB_Calendar.auth_helper import *
from MB_Calendar.graph_helper import get_calendar_events
import requests
import json
import itertools

nominatim_base_url = "https://nominatim.openstreetmap.org/search"
osrm_base_url = "http://router.project-osrm.org/route/v1/car"

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
    json_resp = r.json()
    if len(json_resp)>0:
        json_resp = json_resp[0]
        lat = json_resp.get("lat")
        long = json_resp.get("lon")
    else:
        lat = None
        long = None
    return lat, long


def get_route(lat1, long1, lat2, long2):
    r = requests.get('{0}/{1},{2};{3},{4}?overview=full'.format(
        osrm_base_url,
        long1,
        lat1,
        long2,
        lat2))
    r_json = r.json()
    if len(r_json)>0:
        duration = round(r_json["routes"][0]["duration"]/3600, 2)
        distance = round(r_json["routes"][0]["distance"]/1000, 2)
        text = str(distance) + " KM<br>"+ str(duration)+" Hours"
        geometry = r_json["routes"][0]["geometry"]
        resp = {
            "text": text,
            "geometry": r_json["routes"][0]["geometry"].replace("\\", "\\\\"),
            "duration": duration,
            "distance": distance
        }
    else:
        resp = None
    return resp

def find_best_dist_routes(routes, locations, start):
    best_routes = []
    permutations = itertools.permutations(locations)
    list_permutated = list(permutations)
    min_dist = float('inf')
    for combo in list_permutated:
        current_routes = []
        route = find_right_route(routes, start, combo[0])
        current_km = route["distance"]
        current_routes.append(route)
        idx = 1;
        for from_loc in combo:
            if len(combo)>idx:
                to_loc = combo[idx]
                idx += 1
            else:
                to_loc = start

            route = find_right_route(routes, from_loc, to_loc)
            current_routes.append(route)
            km = route["distance"]
            current_km += km

        if current_km<min_dist:
            min_route = current_km
            best_routes = current_routes

    return best_routes


def find_right_route(routes, from_loc, to_loc):
    right_route = None
    for r in routes:
        if (r["from"] == from_loc and  r["to"] == to_loc) or \
            (r["to"] == from_loc and  r["from"] == to_loc):
            right_route = r

    return right_route
