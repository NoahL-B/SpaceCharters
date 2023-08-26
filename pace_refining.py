from main import rh


def main():
    rh.start_pacing()
    for i in range(1, 181):
        rh.get("")
        print("\ri = " + str(i), end="")
    print()
    rapm = rh.get_rpm(False, True)
    rspm = rh.get_rpm(True, True)

    print("Attempted pace (/min, /sec):", rapm, rapm / 60)
    print("Succeeded pace: (/min, /sec)", rspm, rspm / 60)
    print("Success Percentage:", rh.pacing_src / rh.pacing_rc * 100)
    if rh.pacing_rc != rh.pacing_src:
        print("Failed Attempts:", rh.pacing_rc - rh.pacing_src)
    print("******************************************")


if __name__ == '__main__':
    while True:
        main()