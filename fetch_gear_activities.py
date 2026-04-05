import json

from garmin_auth import garmin_login

GEAR_UUID = "f179eaf9-474a-4b16-9514-a2d3e7ae242d"

client = garmin_login()

activities = client.get_gear_activities(GEAR_UUID)

if not activities:
    print(f"No activities found for gear {GEAR_UUID}.")
else:
    print(f"Found {len(activities)} activities for gear {GEAR_UUID}:\n")
    for activity in activities:
        print(json.dumps(activity, indent=2, default=str))
