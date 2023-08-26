# SPACE CHARTERS
A SpaceTraders API repository for charting every single system.

## Navigating the codebase

### README.md
Read it. That's literally in the name.

### requirements.txt
Sets out the external packages used in the rest of the codebase.

### reset.py
Resets the database to be fresh accounts, systems, and waypoints each week, 
or resets just systems and waypoints for verification purposes.


### main.py
Holds functions shared across all other files (database access, API call wrappers), 
and a main() method that creates accounts for every system and spawns threads for every account.
Wrapper functions handle most database writing and API error handling.


### make_requests.py
Creates a RequestHandler class that *should* be thread-safe for ratelimiting API calls. 
Handles the API calls that have wrappers in main.py.

I wrote this because I was frustrated by the fact that the SpacePyTraders module was designed for V1 not V2 of the SpaceTraders API.


### pace_refining.py
Used for speed-testing make_requests.py. 
Last I checked I get ~160 requests per minute out of a theoretical 180 rpm cap.


### ship.py
Holds the logic for what each created account is supposed to do.
Most of this is figuring out where the ship left off and figuring out how to resume prior operations in the highly likely case the program is closed sometime during the week.


### SpaceCharters.accdb
The database. I can't be bothered to write a better description. Probably excluded from the repo due to file size.

### SpaceChartersSample.accdb
A copy of the database structure of SpaceCharters.accdb, but with all the information removed so I can actually put it on GitHub.
Rename to SpaceCharters.accdb before use.

## Strategy
* Spawn one account for each uncharted system in the universe. This account's faction is chosen to be the closest to the target system.
* Orbit the command ship, set it to drift to eliminate fuel concerns, and warp it to any waypoint in the system.
  * If the trip is expected to take more than ~4 hours, close the thread to conserve RAM. 
  If not, sleep until arrival time.
* (Attempt to) chart the current waypoint.
  * It doesn't matter if this call succeeds or fails, because the goal is simply to have the whole universe charted.
* If there are more uncharted waypoints in the system, navigate to the next one, set the arrival time accordingly, and go back up one bullet point.

Typically, the universe has 12000 systems, and 65000-70000 waypoints. This strategy takes roughly 175000 API calls, or 18.87 hours of one IP address's time, assuming 160 API calls per minute. 
Waiting for warping will take a lot longer than that.

Accounts and threads are spawned in order of furthest-to-closest distances between spawn system and destination. This gives the maximum time for warping of longer range ships.


## TODO:
Refactor ship.py to separate out the initial orbit/drift/warp procedure from the wait/chart/nav procedure

Refactor make_reqests.py to use a priority queue and set the initial orbit/drift/warp to a higher priority than the system charting.

Solve the Traveling Salesman Problem to reduce the number of accounts needed to chart the entire universe in a one-week period.