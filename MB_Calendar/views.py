from django.shortcuts import render
from django.http import HttpResponse, HttpResponseRedirect
from django.urls import reverse
from datetime import datetime, timedelta
from MB_Calendar.auth_helper import get_sign_in_flow, get_token_from_code, store_user, remove_user_and_token, get_token
from MB_Calendar.graph_helper import *
from MB_Calendar.utils_views import *
from  MB_Calendar.common_utils import MB_HEADQUARTER_LATITUDE, MB_HEADQUARTER_LONGITUDE

def home(request):
  context = initialize_context(request)

  return render(request, 'home.html', context)

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
  context = get_events_context_from_request(request)
  context["str_start"] = context["start"].strftime('%Y-%m-%dT%H:%M')
  context["str_end"] = context["end"].strftime('%Y-%m-%dT%H:%M')
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

def editevent(request, id):
  token = get_token(request)
  context = initialize_context(request)
  user = context['user']
  event = get_calendar_event(token, id,  user['timeZone'])
  context['event'] = event
  attendees = ""
  if event.get('attendees'):
    attendees_list = []
    for attendee in event["attendees"]:
        if attendee.get("emailAddress") and attendee.get("emailAddress").get("address"):
            attendees_list.append(attendee["emailAddress"]["address"])
    attendees = ';'.join([att for att in attendees_list])

  context['event']['attendees_list'] = attendees
  context['event']["start"]["dateTime"] = event["start"]["dateTime"].split(".")[0]
  context['event']["end"]["dateTime"] = event["end"]["dateTime"].split(".")[0]
  str_after = event["body"]["content"].split("<div")[1]
  str_after = str_after.split(">")[1]
  context['event']["str_body"] = str_after.split("</div")[0]

  if request.POST:
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
      update_event(
        token,
        id,
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
      return render(request, 'editevent.html', context)


def delevent(request, id):
  token = get_token(request)
  delete_event(token, id)
  return HttpResponseRedirect(reverse('calendar'))


def viewmap(request):
    context = get_events_context_from_request(request)
    context["str_start"] = context["start"].strftime('%H:%M %d/%m/%Y')
    context["str_end"] = context["end"].strftime('%H:%M %d/%m/%Y')
    events_min = []
    errors = []
    if context["events"]:
        events = context["events"]
        for event in events:
            if len(event["locations"]) > 0 and event["locations"][0].get("coordinates"):
                location = event["locations"][0]
                lat = location["coordinates"]["latitude"]
                long = location["coordinates"]["longitude"]
            elif event["location"].get("displayName"):
                lat, long = get_lat_long_from_location(event["location"].get("displayName"))
            else:
                lat = None
                long = None

            if (lat==None or long==None):
                errors.append("Could not find Coordinates for location "+event["location"].get("displayName"))
                continue

            days_int = event["end"]["dateTime"].day - event["start"]["dateTime"].day
            if days_int>0:
                end_d1 = event["start"]["dateTime"]
                end_d1 = end_d1.replace(hour=18, minute=0)
                h_d1 = end_d1-event["start"]["dateTime"]

                start_ld = event["end"]["dateTime"]
                start_ld = start_ld.replace(hour=9, minute=0)
                h_ld = event["end"]["dateTime"]-start_ld

                duration = (days_int-1)*8 + h_d1.seconds/3600 + h_ld.seconds/3600
            else:
                duration = (event["end"]["dateTime"]-event["start"]["dateTime"]).seconds/3600

            duration = round(duration, 2)
            text = event["subject"] + "<br>" + event["location"].get("displayName") + "<br>Duration: " + str(duration)+" Hours"
            event_min = {
                "subject": event["subject"],
                "text": text,
                "latitude": lat,
                "longitude": long,
                "duration": duration,
                "location": event["location"].get("displayName")
            }
            events_min.append(event_min)
    context["events"] = events_min
    context["events_info"]= {
        "tot_duration": sum(ev["duration"] for ev in  events_min )
    }
    context["headquarter"] = {
        "latitude": MB_HEADQUARTER_LATITUDE,
        "longitude": MB_HEADQUARTER_LONGITUDE
    }
    routes = []
    remaining_evs = [e for e in events_min ]
    for ev in events_min:
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
            errors.append("Could not find route from ModulBlok Headquarter to latitude:"+ev["latitude"]+" longitude:"+ev["longitude"])
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
                errors.append("Could not find route from latitude:"+ev["latitude"]+" longitude:"+ev["longitude"] +" to latitude:"+r_ev["latitude"]+" longitude:"+r_ev["longitude"])


    context["routes"] = [r for r in routes]
    best_dist_routes, best_time_routes = find_best_routes(routes, events_min, "ModulBlok Headquarter")
    context["best_dist_routes"] = best_dist_routes
    tot_duration_bd = sum(d_route["duration"] for d_route in  best_dist_routes )
    tot_distance_bd = sum(d_route["distance"] for d_route in  best_dist_routes )
    context["best_dist_routes_info"] = {
        "tot_duration": round(tot_duration_bd, 2),
        "tot_distance": round(tot_distance_bd, 2)
    }
    context["best_time_routes"] = best_time_routes
    tot_duration_bt = sum(t_route["duration"] for t_route in  best_time_routes )
    tot_distance_bt = sum(t_route["distance"] for t_route in  best_time_routes )
    context["best_time_routes_info"] = {
        "tot_duration": round(tot_duration_bt, 2),
        "tot_distance": round(tot_distance_bt, 2)
    }
    context["maps_errors"] = errors

    planner = find_planner(best_time_routes, events_min)
    context["planner"] = planner
    context["planner_info"]= {
        "tot_duration": sum(el["duration"] for el in  planner )
    }

    return render(request, 'map.html', context)
