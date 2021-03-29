from MB_Calendar.utils_graph_helper import *
from dateutil import tz, parser
from datetime import datetime, timedelta
from MB_Calendar.auth_helper import *
from MB_Calendar.graph_helper import get_calendar_events
from  MB_Calendar.common_utils import MB_HEADQUARTER_LATITUDE, MB_HEADQUARTER_LONGITUDE
import requests
import json
import itertools

# BASE URLS
nominatim_base_url = "https://nominatim.openstreetmap.org/search"
osrm_base_url = "http://router.project-osrm.org/route/v1/car"
# osrm_base_url = "http://127.0.0.1:5000/route/v1/car" # SERVER LOCALE


def get_events_context_from_request(request):
    """
    Extract events between dates in context or a months form now
    @param: request
    """
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
      context['events'] = events['value']
    return context

def initialize_context(request):
  """
  Method for initialize contex, get errors and user authentication
  @param: request
  """
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
    """
    Request to Nominatim Latitude and Longitude from given address
    @param address: string
    @output Lat, Long: string
    """
    r = requests.get('{0}?q={1}&format=jsonv2'.format(nominatim_base_url, address))
    if str(r.status_code)=="200":
        json_resp = r.json()
        json_resp = json_resp[0] if len(json_resp)>0 else {}
        lat = json_resp.get("lat", None)
        long = json_resp.get("lon", None)
    else:
        lat = None
        long = None
    return lat, long


def get_route(lat1, long1, lat2, long2):
    """
    Request to OSRM route from given points
    @params lat1, long1: latitude and longitude of start point
    @params lat2, long2: latitude and longitude of end point
    @output route: dict
    """
    url = '{0}/{1},{2};{3},{4}?overview=full'.format(
        osrm_base_url,
        long1,
        lat1,
        long2,
        lat2)
    try:
        r = requests.get(url)

        if str(r.status_code)=="200":
            r_json = r.json()
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
            print(url)
            resp = None
    except Exception as e:
        print(e)
        resp = None
    return resp

def find_best_routes(routes, events, start):
    """
    Evalutate from all the routes the best paths for distance and duration
    @param routes: list of dicts that represent all possible routes
    @param events: list of dicts that represent all events to show
    @param start: string with name of start point
    @output best_dist_routes: list of dicts of routes which sum of distances is minumum
    @output best_time_routes: list of dicts of routes which sum of duration is minumum
    """
    best_dist_routes = []
    best_time_routes = []
    permutations = itertools.permutations(events)
    list_permutated = list(permutations)
    min_dist = float('inf')
    min_time = float('inf')
    for combo in list_permutated:
        current_routes = []
        if len(combo):
            route = find_right_route(routes, start, combo[0]["location"])
            current_time = route["duration"] + combo[0]["duration"]
            current_km = route["distance"]
            current_routes.append(route)
            idx = 1;

            for ev in combo:
                from_loc = ev["location"]
                if len(combo)>idx:
                    to_loc = combo[idx]["location"]
                    ev_duration = combo[idx]["duration"]
                    idx += 1
                else:
                    to_loc = start
                    ev_duration = 0

                route = find_right_route(routes, from_loc, to_loc)
                current_routes.append(route)
                km = route["distance"]
                current_km += km
                h = route["duration"]
                current_time += h
                current_time += ev_duration

            if current_km<min_dist:
                min_route = current_km
                best_dist_routes = current_routes

            if current_time<min_time:
                min_time = current_time
                best_time_routes = current_routes


    best_dist_routes = order_routes(best_dist_routes)
    best_time_routes = order_routes(best_time_routes)
    return best_dist_routes, best_time_routes


def find_right_route(routes, from_loc, to_loc):
    """
    Find route (alredy evaluated) between two points
    @param routes: list of dicts that represent all possible routes
    @param from_loc: string of start point
    @param to_loc: string with of end point
    @output right_route: dict of route
    """
    right_route = None
    for r in routes:
        if (r["from"] == from_loc and  r["to"] == to_loc) or \
            (r["to"] == from_loc and  r["from"] == to_loc):
            right_route = r

    return right_route

def order_routes(routes):
    """
    Switch attributes from & to atributes of routes to make them consecutive in the path
    @param routes: list of dicts that represent routes
    @output route: list of dicts that represent routes with right from & to attributes
    """
    idx = 1
    for r in routes:
        actual_to = r["to"]
        if len(routes)>idx:
            next_from = routes[idx]["from"]
            if actual_to != next_from:
                next_to = routes[idx]["to"]
                new_route = {
                    "from": next_to,
                    "to": next_from,
                    "text": routes[idx]["text"],
                    "geometry": routes[idx]["geometry"],
                    "duration": routes[idx]["duration"],
                    "distance": routes[idx]["distance"]
                }
                routes[idx] = new_route
            idx += 1
    return routes

def find_planner(routes, events):
    """
    Define a planner of given events and routes
    @param routes: list of dicts that represent routes of the best path
    @param events: list of dicts that represent events
    @output planner: list of dicts that represent activites to do, both routes and events, grouped by day
    """
    planner = {
        "1": []
    }
    idx = 0
    total_time = 0
    day = 1
    current_time = 0
    for event in events:
        route = routes[idx]
        current_time += route["duration"]
        if current_time<10:
            current_time += event["duration"]
            planner[str(day)].append(route)
            current_time, planner, day = split_event_helper(current_time, event, planner, day)

        else:
            current_time -= route["duration"]
            time_free = 10-current_time
            time_route_left = route["duration"]-time_free
            short_route = route.copy()
            short_route["duration"] = round(time_free, 2)
            planner[str(day)].append(short_route)
            while (time_route_left>8):
                day +=1
                planner[str(day)] = []
                short_route = route.copy()
                short_route["duration"] = 8
                time_route_left = route["duration"]-time_free
                planner[str(day)].append(short_route)

            day +=1
            planner[str(day)] = []
            short_route = route.copy()
            short_route["duration"] = time_route_left
            planner[str(day)].append(short_route)
            current_time = time_route_left
            current_time += event["duration"]
            current_time, planner, day = split_event_helper(current_time, event, planner, day)
        idx += 1

    planner[str(day)].append(routes[idx])

    final_planner = []
    for day in planner:
        values = planner[day]
        for val in values:
            if val["text"].startswith("->"):
                type = "Trip"
                descr = val["from"] +" => "+val["to"]
            else:
                type = "Event"
                descr = val["text"].split("<br>")[0]

            duration = round(val["duration"], 2)

            info = {
                "day": day,
                "type": type,
                "description": descr,
                "duration": duration,
                "rowspan": len(values)
            }
            final_planner.append(info)
    return final_planner


def split_event_helper(current_time, event, planner, day):
    """
    Methot to split an events in 2 or more days
    @param current_time: float of current time occupied in this day
    @param event: dict that represent the event to evenutally split
    @param planner: dict that represent current planner
    @param day: int of day
    @output current_time: float of current time occupied in this day
    @output planner: dict that represent current planner
    @output day: int of day
    """
    if current_time<10:
        planner[str(day)].append(event)
    else:
        current_time -= event["duration"]
        time_free = 10-current_time
        time_ev_left = event["duration"]-time_free
        short_event = event.copy()
        short_event["duration"] = time_free
        planner[str(day)].append(short_event)
        while (time_ev_left>8):
            day += 1
            planner[str(day)] = []
            new_ev = event.copy()
            new_ev["duration"] = 8
            time_ev_left = time_ev_left-8
            planner[str(day)].append(new_ev)

        day +=1
        planner[str(day)] = []
        short_event = event.copy()
        short_event["duration"] = time_ev_left
        planner[str(day)].append(short_event)
        current_time = time_ev_left

    return current_time, planner, day


def get_all_routes(events_min):
    """
    Method for get every possible route between given events
    @param events_min: list of dicts with event info
    @return routes: lisf of dicts of routes found
    @return errors: list of dicts of error (routes not found)
    """
    errors = []
    routes = []
    remaining_evs = [e for e in events_min ]
    idx_ev = 1
    for ev in events_min:
        print(str(idx_ev)+"/"+str(len(events_min)))
        idx_ev+=1
        # find all routes between events' locations and start point
        route = get_route(
            MB_HEADQUARTER_LATITUDE,
            MB_HEADQUARTER_LONGITUDE,
            ev["latitude"],
            ev["longitude"]
        )
        if(route!=None):
            f = "ModulBlok Headquarter"
            to = ev["text"].split("<br>")[1]
            route["text"] = "-> "+f+"<br>-> "+to+"<br>"+route["text"]
            route["from"] = f
            route["to"] = to
            routes.append(route)
        else:
            errors.append({
                "message":"Could not find route from ModulBlok Headquarter to latitude:"+ev["latitude"]+" longitude:"+ev["longitude"]
            })
        remaining_evs.remove(ev)
        for r_ev in remaining_evs:
            route = get_route(
                ev["latitude"],
                ev["longitude"],
                r_ev["latitude"],
                r_ev["longitude"]
            )

            if(route!=None):
                f = ev["text"].split("<br>")[1]
                to = r_ev["text"].split("<br>")[1]
                route["text"] = "-> "+f +"<br>-> "+to+ "<br>"+route["text"]
                route["from"] = f
                route["to"] = to
                routes.append(route)
            else:
                errors.append({
                    "message":"Could not find route from latitude:"+ev["latitude"]+" longitude:"+ev["longitude"] +" to latitude:"+r_ev["latitude"]+" longitude:"+r_ev["longitude"]
                    })

    return routes, errors



def get_planner_info(planner):
    """
    Method for getting information about duration of events, trips and total of week activites
    @param planner: dict of activities
    @return planner_info: dict with duration info
    """
    planner_info = {}
    for week in planner:
        tot_duration = sum((el["duration"] for el in planner[week]))
        trip_duration = sum((el["duration"]  for el in planner[week]  if el["type"]=="trip"))
        ev_duration = sum((el["duration"]  for el in planner[week]  if el["type"]=="event" ))
        planner_info[week] = {
            "tot_duration": round(tot_duration, 2),
            "trip_duration": round(trip_duration, 2),
            "ev_duration": round(ev_duration, 2)
        }
    return planner_info
