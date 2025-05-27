import os
import calendar
from datetime import datetime, timedelta
import time
import pytz
from caldav import DAVClient
from caldav.elements import dav, cdav
from ics import Calendar


# Configuration
CALDAV_URL = "http://192.168.8.187:8080/remote.php/dav/public-calendars/YbrfxqBZssDM8krB?export"
USERNAME = "your-username"
PASSWORD = "your-password"
TIMEZONE = "UTC"
OUTPUT_FOLDER = "calendar"

def connect_to_caldav():
    client = DAVClient(url=CALDAV_URL, username=USERNAME, password=PASSWORD)
    principal = client.principal()
    calendars = principal.calendars()
    if not calendars:
        raise RuntimeError("No calendars found for this account.")
    return calendars[0]  # Use the first calendar found

def fetch_events(calendar, start, end):
    events = calendar.date_search(start, end)
    parsed_events = []
    for event in events:
        cal = Calendar(event.data)
        for e in cal.events:
            parsed_events.append(e)
    return parsed_events

def group_events_by_date(events):
    grouped = {}
    for event in events:
        date = event.begin.astimezone(pytz.timezone(TIMEZONE)).date()
        grouped.setdefault(date, []).append(event)
    return grouped

def init_index():
    filename = os.path.join(OUTPUT_FOLDER, "index.mu")
    with open(filename, "w", encoding="utf-8") as f:
        f.write(f"> Calendar\n")

def append_month_to_index(year, month):
    filename = os.path.join(OUTPUT_FOLDER, "index.mu")
    with open(filename, "a", encoding="utf-8") as f:
        f.write(f"`F00a`_`[{year}-{month:02}`:/page/calendar/{year}-{month:02}.mu]`_`f\n")

def generate_monthly_micron_table(year, month, events_by_date):
    os.makedirs(OUTPUT_FOLDER, exist_ok=True)
    month_filename = os.path.join(OUTPUT_FOLDER, f"{year}-{month:02}.mu")
    with open(month_filename, "w", encoding="utf-8") as f:
        f.write(f"> 📅 {calendar.month_name[month]} {year}\n\n")
        f.write("| Mon | Tue | Wed | Thu | Fri | Sat | Sun |\n")
        f.write("|-----|-----|-----|-----|-----|-----|-----|\n")

        # Get first weekday of the month (0=Monday) and number of days
        month_calendar = calendar.Calendar(firstweekday=0).monthdatescalendar(year, month)

        for week in month_calendar:
            f.write("|")
            for day in week:
                if day.month != month:
                    f.write("     |")
                else:
                    if day.day < 10:
                        f.write(" ")
                    day_events = events_by_date.get(day, [])
                    if day_events:
                        f.write(f" `F00a`_`[{day.day}`:/page/calendar/days/{day}.mu]`_`f  |")
                    else:
                        f.write(f" {day.day}  |")
            f.write("\n")

def generate_day_files(events_by_date):
    day_folder = os.path.join(OUTPUT_FOLDER, "days")
    os.makedirs(day_folder, exist_ok=True)

    for date, events in events_by_date.items():
        with open(os.path.join(day_folder, f"{date}.mu"), "w", encoding="utf-8") as f:
            f.write(f"> Events for {date}\n\n")
            for event in events:
                title = event.name or "Untitled Event"
                start = event.begin.to('local').format("YYYY-MM-DD HH:mm")
                end = event.end.to('local').format("YYYY-MM-DD HH:mm") if event.end else "No end"
                description = event.description or "No description"

                f.write(f">> {title}\n")
                f.write(f">>> `!Start:`! {start}\n")
                f.write(f">>> `!End:`! {end}\n")
                f.write(f">>> `!Description:`! \n{description}")

def main():
    now = datetime.now(pytz.timezone(TIMEZONE))
    current_year = now.year
    current_month = now.month
    months = []
    #add months for the rest of the year
    for current_year_month in range(current_month, 13):
        months.append(current_year_month)
    #add months for next year
    for next_year_month in range(1, current_month):
        months.append(next_year_month)

    start = datetime(current_year, current_month, 1, tzinfo=pytz.timezone(TIMEZONE))
    end = (start + timedelta(days=365)).replace(day=1)

    calendar_obj = connect_to_caldav()
    events = fetch_events(calendar_obj, start, end)
    events_by_date = group_events_by_date(events)

    init_index()

    for month in months:
        if month >=  current_month:
            year = current_year
        else:
            year = current_year + 1
        generate_monthly_micron_table(year, month, events_by_date)
        append_month_to_index(year, month)

    generate_day_files(events_by_date)

    print("Micron calendar generated.")

if __name__ == "__main__":
    while True:
        main()
        time.sleep(24 * 60 * 60 * 1000) # one day
