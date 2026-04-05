import json

from garmin_auth import garmin_login

client = garmin_login()

profile_number = client.get_user_profile()["id"]
gear_list = client.get_gear(profile_number)

if not gear_list:
    print("No gear found.")
else:
    for item in gear_list:
        uuid = item.get("uuid")
        print(f"\n--- {item.get('displayName', 'Unknown')} ({item.get('gearTypeName', '')}) ---")
        print(json.dumps(item, indent=2, default=str))

        if uuid:
            stats = client.get_gear_stats(uuid)
            if stats:
                print("  Stats:")
                print(json.dumps(stats, indent=2, default=str))
