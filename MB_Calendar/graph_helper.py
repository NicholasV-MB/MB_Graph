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
