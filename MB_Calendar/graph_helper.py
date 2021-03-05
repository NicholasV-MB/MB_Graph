import requests
import json

graph_url = 'https://graph.microsoft.com/v1.0'

def get_user(token):
  # Send GET to /me
  user = requests.get(
    '{0}/me'.format(graph_url),
    headers={
      'Authorization': 'Bearer {0}'.format(token)
    },
    params={
      '$select': 'displayName,mail,mailboxSettings,userPrincipalName'
    })
  # Return the JSON result
  return user.json()

def get_calendar_events(token, start, end, timezone):
  # Set headers
  headers = {
    'Authorization': 'Bearer {0}'.format(token),
    'Prefer': 'outlook.timezone="{0}"'.format(timezone)
  }

  # Configure query parameters to
  # modify the results
  query_params = {
    'startDateTime': start,
    'endDateTime': end,
    #'$select': 'subject,organizer,start,end',
    '$orderby': 'start/dateTime'
    #'$top': '50'
  }

  # Send GET to /me/events
  events = requests.get('{0}/me/calendarview'.format(graph_url),
    headers=headers,
    params=query_params)

  # Return the JSON result
  return events.json()

def get_calendar_event(token, id, timezone="UTC"):
  # Set headers
  headers = {
    'Authorization': 'Bearer {0}'.format(token),
    'Prefer': 'outlook.timezone="{0}"'.format(timezone)
  }

  # Send GET to /me/events
  event = requests.get(
    '{0}/me/events/{1}'.format(graph_url, id),
    headers=headers)

  # Return the JSON result
  return event.json()


def create_event(token, subject, start, end, location=None, attendees=None, body=None, timezone='UTC'):
  # Create an event object
  # https://docs.microsoft.com/graph/api/resources/event?view=graph-rest-1.0
  new_event = {
    'subject': subject,
    'start': {
      'dateTime': start,
      'timeZone': timezone
    },
    'end': {
      'dateTime': end,
      'timeZone': timezone
    },
    'location':{
      'displayName': location
    }

  }

  if attendees:
    attendee_list = []
    for email in attendees:
      # Create an attendee object
      # https://docs.microsoft.com/graph/api/resources/attendee?view=graph-rest-1.0
      attendee_list.append({
        'type': 'required',
        'emailAddress': { 'address': email }
      })

    new_event['attendees'] = attendee_list

  if body:
    # Create an itemBody object
    # https://docs.microsoft.com/graph/api/resources/itembody?view=graph-rest-1.0
    new_event['body'] = {
      'contentType': 'text',
      'content': body
    }

  # Set headers
  headers = {
    'Authorization': 'Bearer {0}'.format(token),
    'Content-Type': 'application/json'
  }

  requests.post('{0}/me/events'.format(graph_url),
    headers=headers,
    data=json.dumps(new_event))


def update_event(token, id, subject, start, end, location=None, attendees=None, body=None, timezone='UTC'):
  # Create an event object
  # https://docs.microsoft.com/graph/api/resources/event?view=graph-rest-1.0
  event = {
    'subject': subject,
    'start': {
      'dateTime': start,
      'timeZone': timezone
    },
    'end': {
      'dateTime': end,
      'timeZone': timezone
    },
    'location':{
      'displayName': location
    }

  }

  if attendees:
    attendee_list = []
    for email in attendees:
      # Create an attendee object
      # https://docs.microsoft.com/graph/api/resources/attendee?view=graph-rest-1.0
      attendee_list.append({
        'type': 'required',
        'emailAddress': { 'address': email }
      })

    event['attendees'] = attendee_list

  if body:
    # Create an itemBody object
    # https://docs.microsoft.com/graph/api/resources/itembody?view=graph-rest-1.0
    event['body'] = {
      'contentType': 'text',
      'content': body
    }

  # Set headers
  headers = {
    'Authorization': 'Bearer {0}'.format(token),
    'Content-Type': 'application/json'
  }

  req = requests.patch('{0}/me/events/{1}'.format(graph_url, id),
    data=json.dumps(event),
    headers=headers)


def delete_event(token, id):
    headers = {
      'Authorization': 'Bearer {0}'.format(token),
      'Content-Type': 'application/json'
    }
    req = requests.delete(
      '{0}/me/events/{1}'.format(graph_url, id),
      headers=headers)
