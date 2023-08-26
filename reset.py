from main import *


if __name__ == '__main__':
    weekly_reset = False
    if weekly_reset:
        x = input("Are you sure you want to reset agents? (Y/n): ")
        if x != "Y":
            weekly_reset = False
    if weekly_reset:
        i = 10
        while i > 0:
            print("Clearing agents in", i)
            i -= 1
            time.sleep(1)
        clear_table("Agents")

    populate_systems()
    populate_waypoints()
    print('\n')
    print(rh.get_rpm(False))
    print(rh.get_rpm())
