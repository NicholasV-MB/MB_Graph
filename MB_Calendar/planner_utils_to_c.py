import itertools
from operator import itemgetter

START_HOUR_WORKING = 8.0
END_HOUR_WORKING = 17.5
TOLERATION_TIME = 2.0

def find_best_monthly_planner(events, routes, max_days_in_week, base):
    best_planner = {}
    if len(events)<10:
        permutations = itertools.permutations(events)
        list_permutated = list(permutations)
    else:
        list_permutated = find_best_permutation(events, routes)

    # list_permutated = [list_permutated[600]]
    # list_permutated = [events]
    min_time = float('inf')
    max_days_in_week = int(max_days_in_week)
    tot_combo = len(list_permutated)
    idx_combo = 1
    right_combo_idx = 0
    for combo in list_permutated:
        current_planner = {}
        week = 1
        day = 1
        current_planner = {
            week:{
                day: []
            }
        }
        hour_now = START_HOUR_WORKING        # ora del giorno
        total_time = 0                       # tempo totale del planner
        from_loc = base
        skip = False
        for event in combo:
            # ciclo per ogni evento della combinazione
            if total_time > min_time:
                # se il tempo del planner è già maggiore del minimo non continuo
                # print("se il tempo del planner è già maggiore del minimo non continuo")
                skip = True
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
            if (hour_now+hour_toev_ev_back)>(END_HOUR_WORKING+TOLERATION_TIME) or day>max_days_in_week:
                # viaggio fino all'evento + durata evento + ritorno non possibile in giornata
                # print("viaggio fino all'evento + durata evento + ritorno non possibile in giornata")
                time_left_today = TOLERATION_TIME+END_HOUR_WORKING-hour_now
                time_to_finish = hour_toev_ev_back-time_left_today
                days_to_finish = 1 + int(time_to_finish // 8)
                if (days_to_finish+day) > max_days_in_week:
                    # Non possibile neanche in settimana
                    # print("Non possibile neanche in settimana")
                    # Aggiungo strada per il ritorno
                    current_planner, day, hour_now = add_activity_to_planner_helper(current_planner, day, week, hour_now, r_from_loc_to_base)
                    time_wasted = 0
                    if day>1 and len(current_planner[week].get(day, current_planner[week][day-1]))==1:
                        # Se sto usando una giornata per fare solo viaggio è una soluzione da scartare
                        # print("Se sto usando una giornata per fare solo viaggio è una soluzione da scartare")
                        skip = True
                        break

                    # calcolo il tempo sprecato
                    if day < max_days_in_week:
                      time_wasted += 8*(max_days_in_week-day)
                    time_wasted += (END_HOUR_WORKING-hour_now)
                    total_time += time_wasted
                    week += 1
                    day = 1
                    hour_now = START_HOUR_WORKING
                    current_planner[week] = { day:[]}
                    r_to_ev = r_to_base.copy()
                    total_time += r_from_loc_to_base_duration

                    # aggiungo strada ripatartendo da casa
                    current_planner, day, hour_now = add_activity_to_planner_helper(current_planner, day, week, hour_now, r_to_base)
                    total_time += r_to_base_duration
                else:
                    current_planner, day, hour_now = add_activity_to_planner_helper(current_planner, day, week, hour_now, r_to_ev)
                    total_time += r_to_ev_duration
            else:
                current_planner, day, hour_now = add_activity_to_planner_helper(current_planner, day, week, hour_now, r_to_ev)
                total_time += r_to_ev_duration

            # viaggio fino all'evento + durata evento + ritorno sicuramente in giornata o settimana corrente
            total_time += r_to_ev_duration
            day_before_add = day
            hour_before_add = hour_now
            current_planner, day, hour_now = add_activity_to_planner_helper(current_planner, day, week, hour_now, event)
            if day != day_before_add and ev_duration<=8:
                # attività effettuata il giorno dopo sprecando tempo il giorno prima
                hours_wasted = (END_HOUR_WORKING-hour_before_add)
                total_time += hours_wasted
            if day>1 and day<=max_days_in_week and len(current_planner[week][day-1])==1 and \
                current_planner[week][day-1][0]["text"].startswith("->")==True:
                # giorno precedente solo viaggio soluzione da scartare
                # print("giorno precedente solo viaggio soluzione da scartare")
                skip = True
                break


            total_time += ev_duration
            from_loc = event["location"]

        if skip:
            # se ho trovato un break nel ciclo degli eventi skippo la combinazione
            # print("skip")
            idx_combo += 1
            continue

        current_planner, day, hour_now = add_activity_to_planner_helper(current_planner, day, week, hour_now, r_to_base)
        total_time += r_to_base_duration


        if total_time < min_time and total_time>0:
            min_time = total_time
            best_planner = current_planner
            right_combo_idx = idx_combo-1
        else:
            del current_planner
        idx_combo += 1

    # print("right_combo_idx: "+str(right_combo_idx))
    for w in best_planner:
        best_planner[w] = reorganize_week(best_planner[w], max_days_in_week, base, routes)

    best_planner = format_order_monthly_planner(best_planner, base)
    return best_planner


def add_activity_to_planner_helper(planner, day, week, hour_now, activity):
    # print("------------------------")
    # print("Aggiungo activity")
    # print(activity["text"])
    # print("hour_now: "+str(hour_now))
    # print("day: "+str(day))
    # print("week: "+str(week))
    if bool(activity)==False:
      return planner, day, hour_now
    hour_event_in_day = 0
    for _act_in_day in planner[week][day]:
        if _act_in_day["text"].startswith("->")==False:
            hour_event_in_day += _act_in_day["duration"]
    # print("hour_event_in_day: "+str(hour_event_in_day))
    if (activity["text"].startswith("->") and \
        (float(activity["duration"])+hour_now)<(END_HOUR_WORKING+TOLERATION_TIME) ) or \
        (activity["text"].startswith("->")==False and \
        (float(activity["duration"])+hour_now)<(END_HOUR_WORKING+(TOLERATION_TIME/4))  and \
        (float(activity["duration"])+hour_event_in_day)<=8):
        # activity in giornata
        # print("activity in giornata")
        planner[week][day].append(activity)
        hour_now += float(activity["duration"])
        if hour_now > END_HOUR_WORKING and activity["text"].startswith("->"):
          day += 1
          planner[week][day] = []
          hour_now = START_HOUR_WORKING
    else:
        # activity non si conclude in giornata
        # print("activity non si conclude in giornata")
        time_left_today = END_HOUR_WORKING - hour_now
        # split solo se è strada oppure evento in base al modulo 8
        # print("split solo se è strada oppure evento in base al modulo 8")
        if activity["text"].startswith("->")==False:
          # è un evento
          time_left_today += (TOLERATION_TIME/4)
          # print("è un evento")
          event_days_of_work = int(activity["duration"]//8)
          # print("event_days_of_work: "+str(event_days_of_work))
          hours_ev_remaining = activity["duration"] - (event_days_of_work*8)
          if hours_ev_remaining <= time_left_today and hours_ev_remaining>0 and \
             time_left_today<8 and (hours_ev_remaining+hour_event_in_day)<=8:
              today_activity = activity.copy()
              today_activity["duration"] = time_left_today
              planner[week][day].append(today_activity)
              hours_ev_remaining = 8-(time_left_today-hours_ev_remaining)
              event_days_of_work -= 1
          elif event_days_of_work>=1 and time_left_today>=8:
              today_activity = activity.copy()
              today_activity["duration"] = 8
              planner[week][day].append(today_activity)
              event_days_of_work -= 1
          day += 1
          planner[week][day] = []
          for _d in range(event_days_of_work):
              _act = activity.copy()
              _act["duration"] = 8
              planner[week][day].append(_act)
              day += 1
              planner[week][day] = []
          if hours_ev_remaining>0:
              final_act = activity.copy()
              final_act["duration"] = hours_ev_remaining
              planner[week][day].append(final_act)
          hour_now = START_HOUR_WORKING + hours_ev_remaining
        else:
          # strada che non si conclude in giornata
          # print("strada che non si conclude in giornata")
          time_left_today += TOLERATION_TIME
          activity_today = activity.copy()
          activity_today["duration"] = time_left_today
          planner[week][day].append(activity_today)
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

          if time_left_last_day>TOLERATION_TIME:
              final_activity = activity.copy()
              final_activity["duration"] = time_left_last_day
              planner[week][day].append(final_activity)
              hour_now = START_HOUR_WORKING+time_left_last_day
          else:
              if planner[week][day-1][-1]["text"]==activity["text"]:
                  planner[week][day-1][-1]["duration"] = float(planner[week][day-1][-1]["duration"])+time_left_last_day

              else:
                  planner[week][day-1].append(activity)

              hour_now = START_HOUR_WORKING

    return planner, day, hour_now



def format_order_monthly_planner(planner, base):
    final_planner = {}
    from_loc = base

    for week in planner:
        final_planner[week] = []
        trip_splitted = False
        for day in planner[week]:
            hour_now = START_HOUR_WORKING
            for act in planner[week][day]:
                activity = {
                    "day": str(day),
                    "text": act["text"],
                    "duration":  round(float(act["duration"]), 2),
                    "rowspan": len(planner[week][day]),
                    "start_time": round(hour_now, 2)
                }
                hour_now += round(float(act["duration"]), 2)
                activity["end_time"] = round(hour_now, 2)
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

def reorganize_week(old_week, max_days_in_week, base, routes):
    if len(old_week.get(max(old_week.keys()))) == 0:
        old_week.pop(max(old_week.keys()))
        # last_trip = old_week.get(max(old_week.keys())-1)[-1]
    # else:
    last_trip = old_week.get(max(old_week.keys()))[-1]

    days_out = len(old_week)

    # print("first trip: "+old_week.get(1)[0]["text"])
    # print("last trip: "+last_trip["text"])
    distance_remaining = float(old_week.get(1)[0]["distance"]) - float(last_trip["distance"])+50
    # print("distance_remaining: "+str(distance_remaining))
    if days_out>max_days_in_week:
      reordered_list = []
      old_text = ""
      for key, value in old_week.items():
          for act in value:
              if act["text"].startswith("->")==False:
                  if act["text"] != old_text:
                      reordered_list.insert(0, act.copy())
                      old_text = act["text"]
                  else:
                      reordered_list[0]["duration"] += act["duration"]

      permutations = itertools.permutations(reordered_list)
      list_permutated = list(permutations)

      for combo in list_permutated:
          current_planner = {}
          week = 1
          day = 1
          current_planner = {
              week:{
                  day: []
              }
          }
          hour_now = START_HOUR_WORKING        # ora del giorno
          from_loc = base
          for event in combo:
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

              current_planner, day, hour_now = add_activity_to_planner_helper(current_planner, day, week, hour_now, r_to_ev)
              current_planner, day, hour_now = add_activity_to_planner_helper(current_planner, day, week, hour_now, event)
              from_loc = event["location"]

          current_planner, day, hour_now = add_activity_to_planner_helper(current_planner, day, week, hour_now, r_to_base)
          if len(current_planner[week])<=max_days_in_week:
            old_week = current_planner[week]

    if distance_remaining>0:
        return old_week
    else:
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
        hour_now = START_HOUR_WORKING
        for activity in reordered_list:
            new_planner, day, hour_now = add_activity_to_planner_helper(new_planner, day, week, hour_now, activity)

        if day>max_days_in_week:
            return old_week
        # quando rigiro il planner gli eventi in una giornata devono essere alemno 3 ore
        for day in new_planner[1]:
          ev_time_in_day = 0
          for activity in new_planner[1][day]:
            if activity["text"].startswith("->")==False:
              ev_time_in_day += activity["duration"]
          if ev_time_in_day<3 and day<max_days_in_week:
            return old_week
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

    return right_route.copy()


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
    for r_ev in remaining_evs:
      new_list = [ev, r_ev]
      rr_evs = remaining_evs.copy()
      rr_evs.remove(r_ev)
      remaining_orded = order_remaining_events(r_ev["location"], rr_evs, routes)
      new_list.extend(remaining_orded)
      best_list.append(new_list)
      best_list.append(new_list[::-1])

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
