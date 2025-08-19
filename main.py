feedings = []


def _normalize_date(s: str) -> str:
    return s.strip()


def _normalize_time(s: str) -> str:
    s = s.strip()
    if ":" in s:
        h, m = s.split(":", 1)
        return f"{int(h):02d}:{int(m):02d}"
    return s


def add_feeding():
    date = _normalize_date(input("insert date (YYYY-MM-DD): "))
    time = _normalize_time(input("insert time (HH:MM): "))
    milk_type = input("insert type (me/pre/sct): ").strip().lower()
    amount = int(input("insert amount (ml): "))

    feeding = {"date": date, "time": time, "milk_type": milk_type, "amount": amount}
    feedings.append(feeding)
    feedings.sort(key=lambda f: (f["date"], f["time"]))
    print("added:", feeding)


def list_feeding(date):
    date = _normalize_date(date)
    total_pre = 0
    total_sct = 0
    total_me = 0

    has_any = False
    for feeding in feedings:
        if feeding["date"] == date:
            has_any = True
            print(f"- {feeding['time']}: {feeding['amount']}ml ({feeding['milk_type']})")
            if feeding["milk_type"] == "pre":
                total_pre += feeding["amount"]
            elif feeding["milk_type"] == "sct":
                total_sct += feeding["amount"]
            elif feeding["milk_type"] == "me":
                total_me += feeding["amount"]

    if not has_any:
        print(f"(no data on {date})")
        return

    total = total_pre + total_sct + total_me
    print("\nNote: Day", date, "the baby has been fed:")
    print("-", total_pre, "ml of pre")
    print("-", total_sct, "ml of sct")
    print("-", total_me, "ml of me")
    print("->", total, "ml in total")


def main():
    while True:
        print("\n1. Add")
        print("2. Show the list (by date)")
        print("3. Exit")
        choice = input("choose: ").strip()
        if choice == "1":
            add_feeding()
        elif choice == "2":
            date = input("choose date (YYYY-MM-DD): ")
            list_feeding(date)
        elif choice == "3":
            break
        else:
            print("error, try again")


if __name__ == "__main__":
    main()
