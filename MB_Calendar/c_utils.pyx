import itertools
from operator import itemgetter

def find_best_monthly_planner(events, routes, max_days_in_week, base):
    best_planner = {}
    if len(events)>8:
        permutations = itertools.permutations(events)
        list_permutated = list(permutations)
    else:
        list_permutated = find_best_permutation(events, routes)
    min_time = float('inf')
    max_days_in_week = int(max_days_in_week)
    tot_combo = len(list_permutated)
    idx_combo = 1
    for combo in list_permutated:
        current_planner = {}
        week = 1
        day = 1
        current_planner = {
            week:{
                day: []
            }
        }
        hour_now = 8.0                   # ora del giorno
        total_time = 0                  # tempo totale del planner
        from_loc = base

        for event in combo:
            if total_time > min_time:
                break

            r_to_ev = find_right_route(routes, from_loc, event["location"])
            r_to_ev_duration = float(r_to_ev["duration"])
            ev_duration = float(event["duration"])
            r_to_base = find_right_route(routes, base, event["location"])
            r_to_base_duration = float(r_to_base["duration"])
            if base!=from_loc:
                r_from_loc_to_base = find_right_route(routes, base, from_loc)
                r_from_loc_to_base_duration = float(r_from_loc_to_base["duration"])
            else:
                r_from_loc_to_base = {}
                r_from_loc_to_base_duration = 0

            hour_toev_ev_back = r_to_ev_duration+ev_duration+r_to_base_duration
            if (hour_now+hour_toev_ev_back)>17:
                # viaggio fino all'evento + durata evento + ritorno non possibile in giornata
                time_left_today = 17-hour_now
                time_to_finish = hour_toev_ev_back-time_left_today
                days_to_finish = int(time_to_finish // 8)
                if (days_to_finish+day) >= max_days_in_week:
                    # Non possibile neanche in settimana
                    current_planner, day, hour_now = add_activity_to_planner_helper(current_planner, day, week, hour_now, r_from_loc_to_base)
                    week += 1
                    day = 1
                    hour_now = 8
                    current_planner[week] = { day:[]}
                    r_to_ev = r_to_base.copy()
                    total_time += r_from_loc_to_base_duration

            # viaggio fino all'evento + durata evento + ritorno sicuramente in giornata o settimana corrente
            current_planner, day, hour_now = add_activity_to_planner_helper(current_planner, day, week, hour_now, r_to_ev)
            total_time += r_to_ev_duration

            current_planner, day, hour_now = add_activity_to_planner_helper(current_planner, day, week, hour_now, event)
            total_time += ev_duration

            from_loc = event["location"]

        current_planner, day, hour_now = add_activity_to_planner_helper(current_planner, day, week, hour_now, r_to_base)
        idx_combo += 1
        if total_time < min_time:
            min_time = total_time
            best_planner = current_planner
            right_combo_idx = idx_combo-2
        else:
            del current_planner


    for w in best_planner:
        best_planner[w] = reorganize_week(best_planner[w])

    best_planner = format_order_monthly_planner(best_planner, base)
    return best_planner


def add_activity_to_planner_helper(planner, day, week, hour_now, activity):
    if bool(activity)==False:
      return planner, day, hour_now
    if (float(activity["duration"])+hour_now)<17:
        # activity in giornata
        planner[week][day].append(activity)
        hour_now += float(activity["duration"])
    else:
        # activity non si conclude in giornata
        time_left_today = 17 - hour_now
        if time_left_today>1:
            activity_today = activity.copy()
            activity_today["duration"] = time_left_today
            planner[week][day].append(activity_today)
        else:
            time_left_today = 0

        time_still_needed = float(activity["duration"]) - time_left_today
        days_of_activity_after_today = int(time_still_needed // 8)
        time_left_last_day = time_still_needed % 8
        day += 1
        planner[week][day] = []
        for _d in range(days_of_activity_after_today):
            activity_helper = activity.copy()
            activity_helper["duration"] = 8
            planner[week][day].append(activity_helper)
            day += 1
            planner[week][day] = []

        if time_left_last_day>1:
            final_activity= activity.copy()
            final_activity["duration"] = time_left_last_day
            planner[week][day].append(final_activity)
            hour_now = 8+time_left_last_day
        else:
            if planner[week][day-1][-1]["text"]==activity["text"]:
                planner[week][day-1][-1]["duration"] = float(planner[week][day-1][-1]["duration"])+time_left_last_day

            else:
                planner[week][day-1].append(activity)

            hour_now = 8

    return planner, day, hour_now



def format_order_monthly_planner(planner, base):
    final_planner = {}
    from_loc = base
    for week in planner:
        final_planner[week] = []
        trip_splitted = False
        for day in planner[week]:
            for act in planner[week][day]:
                activity = {
                    "day": str(day),
                    "text": act["text"],
                    "duration":  round(float(act["duration"]), 2),
                    "rowspan": len(planner[week][day])
                }
                if act["text"].startswith("->"):
                    activity["type"] = "trip"
                    # activity["geometry"] = act["geometry"] GEOMETRY NON SERVE
                    if act["from"] != from_loc:
                        activity["from"] = from_loc
                        activity["to"] = act["from"]
                    else:
                        activity["from"] = act["from"]
                        activity["to"] = act["to"]
                    if trip_splitted:
                        activity["from"] =  final_planner[week][-1]["from"]
                        activity["to"] = final_planner[week][-1]["to"]
                    from_loc = activity["to"]
                    activity["description"] = "{0} ➔ {1}".format(activity["from"], activity["to"])
                    trip_splitted = True
                else:
                    activity["type"] = "event"
                    activity["description"] = act["subject"]
                    activity["location"] =  act["location"]
                    activity["info"] =  act.get("info", "")
                    trip_splitted = False
                final_planner[week].append(activity)
    return final_planner

def reorganize_week(old_week):
    if len(old_week.get(max(old_week.keys()))) == 0:
        last_trip = old_week.get(max(old_week.keys())-1)[-1]
    else:
        last_trip = old_week.get(max(old_week.keys()))[-1]

    if old_week.get(1)[0]["distance"]>last_trip["distance"]:
        return old_week
    else:
        # scambio sequenza di eventi
        reordered_list = []
        old_text = []
        for key, value in old_week.items():
            for act in value:
                if act["text"] != old_text:
                    reordered_list.insert(0, act.copy())
                    old_text = act["text"]
                else:
                    reordered_list[0]["duration"] += act["duration"]
        week = 1
        day = 1
        new_planner = {
            week: {
                day: []
            }
        }
        hour_now = 8

        for activity in reordered_list:
            new_planner, day, hour_now = add_activity_to_planner_helper(new_planner, day, week, hour_now, activity)
        return new_planner[1]

def find_right_route(routes, from_loc, to_loc):
    """
    Find route (already evaluated) between two points
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


def find_best_permutation(events, routes):
  best_list = [events, events[::-1]]
  for ev in events:
    remaining_evs = events.copy()
    current_list = [ev]
    remaining_evs.remove(ev)
    remaining_orded = order_remaining_events(ev["location"], remaining_evs, routes)
    current_list.extend(remaining_orded)
    best_list.append(current_list)
    best_list.append(current_list[::-1])

  return best_list

def order_remaining_events(start_loc, remaining_evs, routes):
  all_routes_from_start = []
  for ev in remaining_evs:
    right_route = find_right_route(routes, start_loc, ev["location"])
    all_routes_from_start.append(right_route)

  list_routes_ordered = sorted(all_routes_from_start, key=itemgetter('duration'))
  list_ev_ordered = []
  for r in list_routes_ordered:
    if r["from"] == start_loc:
      location = r["to"]
    else:
      location = r["from"]

    list_ev_ordered.append(get_event_from_location(remaining_evs, location))
  return list_ev_ordered

def get_event_from_location(events, location):
  for ev in events:
    if ev["location"]==location:
      return ev
  return ev