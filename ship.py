from main import *


class Ship:
    def __init__(self, ID, Token, System, Arrival=None, Completed=None, printID = None):
        self.ID = ID
        self.Token = Token
        self.System = System
        self.Arrival = Arrival
        self.Completed = Completed
        self.printID = printID
        self.waypoints = []

    def add_waypoint(self, waypoint):
        if waypoint not in self.waypoints:
            self.waypoints.append(waypoint)

    def start(self):
        if self.Completed is not None and self.Completed:
            print("Closing completed thread", self.printID)
            return
        if self.waypoints:
            all_waypoints = self.waypoints
        else:
            all_waypoints = db_get("Waypoints")
            for wp in all_waypoints:
                if wp[1] == self.System:
                    self.waypoints.append(wp)
        relevant_waypoints = []
        for wp in all_waypoints:
            if wp[1] == self.System and not wp[2]:
                relevant_waypoints.append(wp)

        all_waypoints = None  # garbage collection go brrrrr

        if not relevant_waypoints:
            db_update("Agents", ["Completed"], [True], ["ID"], [self.ID])
            self.Completed = True
            print("closing completed thread", self.printID)
            return

        if self.Arrival is None:
            # print("check1", self.printID)
            o = orbit(self.ID, self.Token)
            # print("check2", self.printID)
            d = drift(self.ID, self.Token)
            # print("check3", self.printID)
            response = warp(self.ID, self.Token, relevant_waypoints[0][0])
            # print("check4", self.printID)
            arrival = time_str_to_datetime(response["data"]["nav"]["route"]["arrival"])
            self.Arrival = arrival
            db_update("Agents", ["Arrival"], [arrival], ["ID"], [self.ID])
        # print("check5", self.printID)

        now = datetime.datetime.utcnow()
        sleep_time = self.Arrival - now

        sleep_seconds = sleep_time / datetime.timedelta(seconds=1)
        if sleep_seconds > 0:
            if sleep_time > datetime.timedelta(hours=0, minutes=20, seconds=0):
                print("closing incomplete thread", self.printID, sleep_time)
                return
            print("continuing thread", self.printID, "in", sleep_time)
            time.sleep(sleep_seconds)

        c = chart(self.ID, self.Token)
        if c:
            wp_name = c["data"]["waypoint"]["symbol"]
            traits = c["data"]["waypoint"]["traits"]
        else:
            wp_name = get_ship(self.ID, self.Token)["data"]["nav"]["waypointSymbol"]
            db_update("Waypoints", ["Charted"], [True], ["Waypoint"], [wp_name])
            wp_data = get_waypoint(self.Token, wp_name, "HIGH")
            traits = wp_data["data"]["traits"]

        for t in traits:
            if t["symbol"] == "MARKETPLACE":
                get_market(self.Token, wp_name)
            elif t["symbol"] == "SHIPYARD":
                get_shipyard(self.Token, wp_name)

        if relevant_waypoints[0][0] == wp_name:
            relevant_waypoints.pop(0)

        for wp in relevant_waypoints:
            # print("check7", self.printID)
            wp_name = wp[0]
            n = nav(self.ID, self.Token, wp_name)
            self.Arrival = time_str_to_datetime(n["data"]["nav"]["route"]["arrival"])

            # print("check8", self.printID)

            now = datetime.datetime.utcnow()
            sleep_time = self.Arrival - now

            sleep_seconds = sleep_time / datetime.timedelta(seconds=1)
            if sleep_seconds > 0:
                time.sleep(sleep_seconds)

            c = chart(self.ID, self.Token)
            if c:
                traits = c["data"]["waypoint"]["traits"]
            else:
                db_update("Waypoints", ["Charted"], [True], ["Waypoint"], [wp_name])
                wp_data = get_waypoint(self.Token, wp_name, "HIGH")
                traits = wp_data["data"]["traits"]

            for t in traits:
                if t["symbol"] == "MARKETPLACE":
                    get_market(self.Token, wp_name)
                elif t["symbol"] == "SHIPYARD":
                    get_shipyard(self.Token, wp_name)

        self.verify_charted()

        db_update("Agents", ["Completed"], [True], ["ID"], [self.ID])
        self.Completed = True
        print("closing completed thread", self.printID)

    def verify_charted(self):
        verified = True
        for waypoint in self.waypoints:
            wp_obj = get_waypoint(self.Token, waypoint[0])
            for trait in wp_obj["data"]["traits"]:
                if trait["symbol"] == "UNCHARTED":
                    db_update("Waypoints", ["Charted"], [False], ["Waypoint"], [waypoint[0]])
                    verified = False
        if not verified:
            print("chart verification failed", self.System)
            self.waypoints = []
            self.start()
        else:
            print("charting verified")

    def update_markets_and_shipyards(self):
        for waypoint in self.waypoints:
            wp_obj = get_waypoint(self.Token, waypoint[0])
            has_market = False
            has_shipyard = False
            for trait in wp_obj["data"]["traits"]:
                if trait["symbol"] == "MARKETPLACE":
                    has_market = True
                elif trait["symbol"] == "SHIPYARD":
                    has_shipyard = True
            if has_shipyard or has_market:
                n = nav(self.ID, self.Token, waypoint[0])
                self.Arrival = time_str_to_datetime(n["data"]["nav"]["route"]["arrival"])

                now = datetime.datetime.utcnow()
                sleep_time = self.Arrival - now

                sleep_seconds = sleep_time / datetime.timedelta(seconds=1)
                if sleep_seconds > 0:
                    time.sleep(sleep_seconds)

                if has_shipyard:
                    get_shipyard(self.Token, waypoint)
                if has_market:
                    get_market(self.Token, waypoint)
