import datetime

current_time = datetime.datetime.now()
print(f"Current Date and Time: {current_time}")
print(f"Time only: {current_time.strftime('%H:%M:%S')}")
print(f"Date only: {current_time.strftime('%Y-%m-%d')}")
