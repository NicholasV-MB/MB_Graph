from django.shortcuts import render
from django.http import HttpResponse, HttpResponseRedirect
from django.urls import reverse
from datetime import datetime, timedelta
from MB_Calendar.auth_helper import get_sign_in_flow, get_token_from_code, store_user, remove_user_and_token, get_token
from MB_Calendar.graph_helper import *
from MB_Calendar.utils_views import *
from MB_Calendar.common_utils import MB_HEADQUARTER_LATITUDE, MB_HEADQUARTER_LONGITUDE
from MB_Calendar.excel_utils import *
from MB_Calendar.word_utils import *
from MB_Calendar.c_utils import find_best_monthly_planner
import os

def home(request):
  """
  Method for render the home interface
  @param: request
  """
  context = initialize_context(request)

  return render(request, 'home.html', context)

def sign_in(request):
  """
  Method for sing in
  @param: request
  """
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
  """
  Callback method called by Azure after autentication
  @param: request
  """
  # Make the token request
  result = get_token_from_code(request)
  #Get the user's profile
  user = get_user(result['access_token'])

  # Store user
  store_user(request, user)
  return HttpResponseRedirect(reverse('home'))

def sign_out(request):
  """
  Method for sing out
  @param: request
  """
  # Clear out the user and token
  remove_user_and_token(request)

  return HttpResponseRedirect(reverse('home'))

def calendar(request):
  """
  Method for render the calendar interface
  @param: request
  """
  context = get_events_context_from_request(request)
  context["str_start"] = context["start"].strftime('%Y-%m-%dT%H:%M')
  context["str_end"] = context["end"].strftime('%Y-%m-%dT%H:%M')
  return render(request, 'calendar.html', context)

def newevent(request):
  """
  Method for render the new event form or send data to Microsoft Graph
  @param: request
  """
  context = initialize_context(request)
  user = context['user']

  if request.method == 'POST':
    # Validate the form values
    # Required values
    if (not request.POST['ev-subject']) or \
       (not request.POST['ev-start']) or \
       (not request.POST['ev-end']) :

      context['errors'] = [
        { 'message': 'Invalid values', 'debug': 'The subject, start, and end fields are required.'}
      ]
      return render(request, 'newevent.html', context)
    elif datetime.fromisoformat( request.POST['ev-start'] ) > datetime.fromisoformat( request.POST['ev-end'] ):
      context['errors'] = [
        { 'message': 'Invalid values', 'debug': 'Start date can not be greater than End date.'}
      ]
      return render(request, 'newevent.html', context)

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

    context["ti-start"] = request.POST["ti-start"]
    context["ti-end"] = request.POST["ti-end"]

    # Redirect back to calendar view
    return HttpResponseRedirect(reverse('calendar')+"?ti-start="+request.POST["ti-start"]+"&ti-end="+request.POST["ti-end"])
  else:
    # Render the form
    context["ti_start"] = request.GET["ti-start"]
    context["ti_end"] = request.GET["ti-end"]
    return render(request, 'newevent.html', context)

def editevent(request, id):
  """
  Method for render the edit event form or send data to Microsoft Graph
  @param: request
  @param: id
  """
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
  str_after = event["body"]["content"].split("<div")[1:][0]
  str_after = ">".join(str_after.split(">")[1:])
  final_string = str_after.split("</div")[0]
  final_string = final_string.replace("<br>", "")
  final_string = final_string.replace("&nbsp;", " ")
  context['event']["str_body"] = final_string

  if request.POST:
      # Validate the form values
      # Required values
      if (not request.POST['ev-subject']) or \
         (not request.POST['ev-start']) or \
         (not request.POST['ev-end']):
        context['errors'] = [
          { 'message': 'Invalid values', 'debug': 'The subject, start, and end fields are required.'}
        ]
        return render(request, 'editevent.html', context)
      elif datetime.fromisoformat( request.POST['ev-start'] ) > datetime.fromisoformat( request.POST['ev-end'] ):
        context['errors'] = [
          { 'message': 'Invalid values', 'debug': 'Start date can not be greater than End date.'}
        ]
        return render(request, 'editevent.html', context)

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
      return HttpResponseRedirect(reverse('calendar')+"?ti-start="+request.POST["ti-start"]+"&ti-end="+request.POST["ti-end"])
  else:
      context["ti_start"] = request.GET["ti-start"]
      context["ti_end"] = request.GET["ti-end"]
      return render(request, 'editevent.html', context)


def delevent(request, id):
  """
  Method for delete the event sending data to Microsoft Graph and redirect to the calendar inerface
  @param: request
  @param: id
  """
  token = get_token(request)
  delete_event(token, id)
  return HttpResponseRedirect(reverse('calendar')+"?ti-start="+request.GET["ti-start"]+"&ti-end="+request.GET["ti-end"])


def viewmap(request):
    """
    Method for render the map interface
    @param: request
    """
    context = get_events_context_from_request(request)
    context["str_start"] = context["start"].strftime('%H:%M %d/%m/%Y')
    context["str_end"] = context["end"].strftime('%H:%M %d/%m/%Y')
    events_min = []
    errors = []
    if context["events"]:
        events = context["events"]
        for event in events:
            # find latitute and longitude
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
    # event_min now contains all event data useful to render them in the map
    context["events"] = events_min
    context["events_info"]= {
        "tot_duration": sum(ev["duration"] for ev in  events_min )
    }
    context["headquarter"] = {
        "latitude": MB_HEADQUARTER_LATITUDE,
        "longitude": MB_HEADQUARTER_LONGITUDE
    }
    routes, new_errors = get_all_routes(events_min)
    errors.extend(new_errors)

    context["routes"] = [r for r in routes]
    context["maps_errors"] = errors
    if len(routes)>0:
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
        planner = find_planner(best_time_routes, events_min)
        context["planner"] = planner
        context["planner_info"]= {
            "tot_duration": round(sum(el["duration"] for el in  planner ), 2)
        }


    return render(request, 'map.html', context)


def planner(request):
  """
  Method for render the planner interface
  @param: request
  """
  context = initialize_context(request)
  return render(request, 'planner.html', context)

def elaboratePlanner(request):
    """
    Method for evaluate best planner and render result
    @param: request
    """
    context = initialize_context(request)
    if request.POST:
        context["year"] = request.POST.get("year")
        tot_rows = int(request.POST.get("tot_rows"))
        monthinteger = int(request.POST.get("month"))
        month = datetime(1900, monthinteger, 1).strftime('%B')
        context["month"] = month
        events_min = []
        errors = []
        tot_ev_duration = 0
        for idx in range(tot_rows):
            location = request.POST.get("address_"+str(idx+1))
            lat, long = get_lat_long_from_location(location)
            if (lat==None or long==None):
                errors.append({"message": "Could not find Coordinates for location "+location})
                continue

            duration = request.POST.get("duration_"+str(idx+1))
            tot_ev_duration += float(duration)
            subject = request.POST.get("title_"+str(idx+1))
            text = subject + "<br>" + location + "<br>Duration: " + str(duration)+" Hours"
            event_min = {
                "subject": subject,
                "text": text,
                "latitude": lat,
                "longitude": long,
                "duration": duration,
                "location": location,
                "info": request.POST.get("info_"+str(idx+1))
            }
            events_min.append(event_min)

        context["events"] = events_min
        context["events_info"]= {
            "tot_duration": tot_ev_duration
        }
        context["headquarter"] = {
            "latitude": MB_HEADQUARTER_LATITUDE,
            "longitude": MB_HEADQUARTER_LONGITUDE
        }
        print("find all routes")
        routes, new_errors = get_all_routes(events_min)
        errors.extend(new_errors)
        context["routes"] = routes
        max_days = request.POST.get("max_days")
        context["max_days"] = max_days
        planner = find_best_monthly_planner(events_min, routes, max_days, "ModulBlok Headquarter")

        context["planner"] = planner
        context["planner_info"] = get_planner_info(planner)

        if len(errors)>0:
            context["errors"] = errors
    else:
        context["errors"] = [{"message": "Method error"}]
    return render(request, 'best_planner.html', context)



def uploadFile(request):
    """
    Method for upload info from excel file
    @param: request
    """
    context = initialize_context(request)
    rows = extract_rows_from_excel(request.FILES.get("file"))
    context["rows_from_file"] = rows
    context["row_number"] = len(rows)
    return render(request, 'planner.html', context)

def saveWord(request):
    """
    Method for save week in word file
    @param: request
    """
    year = request.GET.get("year", None)
    month = request.GET.get("month", None)
    week = request.GET.get("week", None)
    max_days = request.GET.get("max_days", None)
    if year==None or month==None or week==None or max_days==None:
        return HttpResponse("<script>alert('Month, Week, Year or Max Days not found!'); history.back()</script>")
    week_str_list = request.GET.get("data", [])
    first_day = 1+(int(week)-1)*7
    date_start = datetime.strptime(str(first_day)+" "+month+", "+year, '%d %B, %Y')
    week_day = date_start.weekday()
    if(week_day>0):
        delta = 7-week_day
        date_start = date_start+timedelta(days=delta)

    week_str_list = request.GET.get("data", [])
    if len(week_str_list)>0:
        json_acceptable_string = week_str_list.replace("{'", "{\"")
        json_acceptable_string = json_acceptable_string.replace("': '", "\": \"")
        json_acceptable_string = json_acceptable_string.replace("':", "\":")
        json_acceptable_string = json_acceptable_string.replace("', '", "\", \"")
        json_acceptable_string = json_acceptable_string.replace(", '", ", \"")
        json_acceptable_string = json_acceptable_string.replace("'}", "\"}")
        week_list = json.loads(json_acceptable_string)
        data_to_write = []
        for el in week_list:
            if el["type"]=="event":
                info = {
                    "day": el["day"],
                    "description": el["description"],
                    "location": el["location"],
                    "duration": el["duration"],
                    "info": el.get("info", "")
                }
                data_to_write.append(info)
        file_name = write_to_word_doc(year=year, month=month, week=week, start_date=date_start, max_days=max_days, data=data_to_write)

    return HttpResponse("<a href='../static/"+file_name+"' download id='download'></a><script>document.getElementById('download').click(); history.back()</script>")
