import math
import threading
import time

import pyodbc
import os
import datetime

from make_requests import RequestHandler

base_path = os.path.dirname(__file__)
db_path = os.path.join(base_path, "SpaceCharters.accdb")

driver = 'Driver={Microsoft Access Driver (*.mdb, *.accdb)};DBQ=' + db_path
conn = pyodbc.connect(driver)
conn.autocommit = True

cursor = conn.cursor()

rh = RequestHandler()

db_lock = threading.Lock()


def time_str_to_datetime(time_str: str or datetime.datetime) -> datetime.datetime:
    if type(time_str) == datetime.datetime:
        return time_str

    dt = datetime.datetime.strptime(time_str, "%Y-%m-%dT%H:%M:%S.%fZ")
    return dt


def register(agent_name, faction, system):
    payload = {
        "faction": faction,
        "symbol": agent_name
    }
    response = rh.post("register", payload, token=None).json()

    db_insert("Agents", ["ID", "Token", "System"], [agent_name, response["data"]["token"], system])

    return response


def orbit(agent, token):
    ship_name = agent + "-1"
    endpoint = "my/ships/" + ship_name + "/orbit"
    return rh.post(endpoint, token=token).json()


def drift(agent, token):
    ship_name = agent + "-1"
    endpoint = "my/ships/" + ship_name + "/nav"
    payload = {"flightMode": "DRIFT"}

    response = rh.patch(endpoint, payload, token=token).json()
    return response


def warp(agent, token, waypoint):
    ship_name = agent + "-1"
    endpoint = "my/ships/" + ship_name + "/warp"
    payload = {"waypointSymbol": waypoint}

    response = rh.post(endpoint, payload, token=token).json()
    try:
        arrival_time = time_str_to_datetime(response["data"]["nav"]["route"]["arrival"])
    except KeyError:
        if response["error"]["code"] == 4236:  # not in orbit
            orbit(agent, token)
            drift(agent, token)
            return warp(agent, token, waypoint)
        elif response["error"]["code"] == 4203:  # not enough fuel
            drift(agent, token)
            return warp(agent, token, waypoint)
        elif response["error"]["code"] == 4214:  # in transit
            response = {"data": {"nav": {"route": {"arrival": response["error"]["data"]["arrival"]}}}}
            arrival_time = time_str_to_datetime(response["data"]["nav"]["route"]["arrival"])
        elif response["error"]["code"] == 4235:  # destination in same system
            return nav(agent, token, waypoint)
        else:
            print(response["error"])
            raise KeyError

    db_update("Agents", ["Arrival"], [arrival_time], ["ID"], [agent])

    return response


def chart(agent, token):
    ship_name = agent + "-1"
    endpoint = "my/ships/" + ship_name + "/chart"

    response = rh.post(endpoint, token=token)
    if response.status_code == 201:
        data = response.json()["data"]
        waypoint = data["waypoint"]["symbol"]
        db_update("Waypoints", ["Charted"], [True], ["Waypoint"], [waypoint])
        return response.json()
    return False


def nav(agent, token, waypoint):
    ship_name = agent + "-1"
    endpoint = "my/ships/" + ship_name + "/navigate"
    payload = {"waypointSymbol": waypoint}

    response = rh.post(endpoint, payload, token=token).json()
    try:
        arrival_time = time_str_to_datetime(response["data"]["nav"]["route"]["arrival"])
    except KeyError:
        if response["error"]["code"] == 4214:  # in transit
            response = {"data": {"nav": {"route": {"arrival": response["error"]["data"]["arrival"]}}}}
            arrival_time = time_str_to_datetime(response["data"]["nav"]["route"]["arrival"])
        elif response["error"]["code"] == 4204:  # already at destination
            response = {"data": {"nav": {"route": {"arrival": datetime.datetime.utcnow()}}}}
            arrival_time = datetime.datetime.utcnow()
        else:
            print(response["error"])
            raise KeyError
    db_update("Agents", ["Arrival"], [arrival_time], ["ID"], [agent])
    return response


def db_insert(table_name, column_name_list, value_list):
    db_lock.acquire()

    cmd = "INSERT INTO " + table_name + "(" + column_name_list[0]
    for col_name in column_name_list[1:]:
        cmd += ", " + col_name
    cmd += ") VALUES ('" + str(value_list[0])
    for value in value_list[1:]:
        cmd += "', '" + str(value)
    cmd += "');"
    cursor.execute(cmd)

    db_lock.release()


def db_update(table_name, update_column_name_list, update_value_list, where_column_name_list, where_value_list):
    db_lock.acquire()

    cmd = "UPDATE " + table_name + " SET " + table_name + "." + update_column_name_list[0] + ' = ?'
    for i in range(1, len(update_column_name_list)):
        cmd += ", " + table_name + "." + update_column_name_list[i] + ' = ?'
    cmd += " WHERE (((" + table_name + "." + where_column_name_list[0] + ')=?)'
    for i in range(1, len(where_column_name_list)):
        cmd += " AND ((" + table_name + "." + where_column_name_list[i] + ')=?)'
    cmd += ");"
    params = tuple(update_value_list + where_value_list)
    cursor.execute(cmd, params)

    db_lock.release()


def db_get(table_name):
    db_lock.acquire()

    cmd = "SELECT * FROM " + table_name
    cursor.execute(cmd)
    data = []
    for x in cursor:
        data.append(x)
    db_lock.release()
    return data


def get_factions():
    endpoint = "factions"
    querystring = {"limit": "20"}

    response = rh.get(endpoint, querystring).json()
    return response


def populate_systems():
    endpoint = "systems.json"
    systems = rh.get(endpoint).json()
    factions = get_factions()["data"]
    for f in factions:
        hq = f["headquarters"]
        system = waypoint_to_system(hq)
        x = None
        y = None
        for s in systems:
            if s["symbol"] == system:
                x = s["x"]
                y = s["y"]
        f["x"] = x
        f["y"] = y

    print("Populating Systems:")
    clear_table("Systems")
    for s in systems:
        x = s["x"]
        y = s["y"]

        closest = ""
        distance = 120000

        for f in factions:
            fx = f["x"]
            fy = f["y"]

            f_distance = math.sqrt((x - fx) ** 2 + (y - fy) ** 2)
            if f_distance < distance:
                distance = f_distance
                closest = f["symbol"]

        db_insert("Systems", ["System"], [s["symbol"]])
        db_update("Systems", ["x", "y", "closestFaction", "distanceFromFaction"], [x, y, closest, distance], ["System"], [s["symbol"]])


def populate_waypoints():
    systems = db_get("Systems")
    querystring = {"limit": "20"}
    counter = 0
    print("Populating Waypoints:")
    clear_table("Waypoints")
    for s in systems:
        s_name = s[0]
        endpoint = "systems/" + s_name + "/waypoints"
        wps = rh.get(endpoint, querystring).json()["data"]
        for wp in wps:
            db_insert("Waypoints", ["Waypoint", "System"], [wp["symbol"], wp["systemSymbol"]])
            if "chart" in wp.keys():
                db_update("Waypoints", ["Charted"], [True], ["Waypoint"], [wp["symbol"]])
        print("\r" + str(counter), end="")
        counter += 1


def clear_table(table_name):
    cmd = "DELETE FROM " + table_name
    cursor.execute(cmd)


def waypoint_to_system(waypoint):
    return waypoint[:-7]


def main():
    from ship import Ship
    systems_agents_dict = {}
    all_waypoints = db_get("Waypoints")
    for wp in all_waypoints:
        if not wp[2] and wp[1] not in systems_agents_dict.keys():
            systems_agents_dict[wp[1]] = None
    existing_agents = db_get("Agents")
    printID = 1
    for agent in existing_agents:
        s = Ship(agent[0], agent[1], agent[2], agent[3], agent[4], printID=printID)
        printID += 1
        if s.System in systems_agents_dict.keys():
            systems_agents_dict[s.System] = s
        elif not s.Completed:
            s.Completed = True
            db_update("Agents", ["Completed"], [True], ["ID"], [s.ID])

    j = []
    for k in systems_agents_dict.keys():
        j.append(k)
    j.sort()

    cmd = "SELECT System, closestFaction, distanceFromFaction FROM Systems ORDER BY distanceFromFaction DESC;" # noqa
    cursor.execute(cmd)
    all_systems = []
    for x in cursor:
        all_systems.append(x)

    threads = []
    print(len(systems_agents_dict))

    for sys in all_systems:
        if sys[0] in systems_agents_dict.keys():
            system = sys[0]
            if systems_agents_dict[system] is None:
                agent_name = "ZCHART-" + system
                faction = sys[1]
                try:
                    registration = register(agent_name, faction, system)
                except KeyError:
                    agent_name = "ZCHAR2-" + system
                    registration = register(agent_name, faction, system)
                token = registration["data"]["token"]
                s = Ship(agent_name, token, system, printID=printID)
                printID += 1
                systems_agents_dict[system] = s
                time.sleep(1.5)
            x = threading.Thread(target=systems_agents_dict[system].start, daemon=True)
            threads.append(x)
            x.start()

    count = 0
    for t in threads:
        # t.start()
        print(t)
        count += 1
    if __name__ == '__main__':
        for t in threads:
            t.join()
    else:
        return threads


if __name__ == '__main__':
    while True:
        main()