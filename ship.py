from main import *


class Ship:
    def __init__(self, ID, Token, System, Arrival=None, Completed=None, printID = None):
        self.ID = ID
        self.Token = Token
        self.System = System
        self.Arrival = Arrival
        self.Completed = Completed
        self.printID = printID

    def start(self):
        if self.Completed is not None and self.Completed:
            print("Closing completed thread", self.printID)
            return
        all_waypoints = db_get("Waypoints")
        relevant_waypoints = []
        for wp in all_waypoints:
            if wp[1] == self.System and not wp[2]:
                relevant_waypoints.append(wp)

        all_waypoints = None  # garbage collection go brrrrr

        if not relevant_waypoints:
            db_update("Agents", ["Completed"], [True], ["ID"], [self.ID])
            self.Completed = True
            return

        if self.Arrival is None:
            print("check1", self.printID)
            o = orbit(self.ID, self.Token)
            print("check2", self.printID)
            d = drift(self.ID, self.Token)
            print("check3", self.printID)
            response = warp(self.ID, self.Token, relevant_waypoints[0][0])
            print("check4", self.printID)
            arrival = time_str_to_datetime(response["data"]["nav"]["route"]["arrival"])
            self.Arrival = arrival
            db_update("Agents", ["Arrival"], [arrival], ["ID"], [self.ID])
        print("check5", self.printID)

        now = datetime.datetime.utcnow()
        sleep_time = self.Arrival - now

        sleep_seconds = sleep_time / datetime.timedelta(seconds=1)
        if sleep_seconds > 0:
            if sleep_time > datetime.timedelta(hours=4, minutes=20, seconds=0):
                print("closing incomplete thread", self.printID, sleep_time)
                return
            time.sleep(sleep_seconds)
        print("check6", self.printID)

        c = chart(self.ID, self.Token)
        if not c:
            wp_name = relevant_waypoints[0][0]
            db_update("Waypoints", ["Charted"], [True], ["Waypoint"], [wp_name])

        relevant_waypoints.pop(0)
        for wp in relevant_waypoints:
            print("check7", self.printID)
            wp_name = wp[0]
            n = nav(self.ID, self.Token, wp_name)
            self.Arrival = time_str_to_datetime(n["data"]["nav"]["route"]["arrival"])

            print("check8", self.printID)

            now = datetime.datetime.utcnow()
            sleep_time = self.Arrival - now

            sleep_seconds = sleep_time / datetime.timedelta(seconds=1)
            if sleep_seconds > 0:
                time.sleep(sleep_seconds)

            c = chart(self.ID, self.Token)
            if not c:
                db_update("Waypoints", ["Charted"], [True], ["Waypoint"], [wp_name])

        db_update("Agents", ["Completed"], [True], ["ID"], [self.ID])
        self.Completed = True
        print("check9", self.printID)
