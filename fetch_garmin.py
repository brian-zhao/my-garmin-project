import json

from garmin_auth import garmin_login

client = garmin_login()

activities = client.get_activities(0, 1)

if not activities:
    print("No activities found.")
else:
    print(json.dumps(activities[0], indent=2, default=str))
