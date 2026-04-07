import datetime

current_time = datetime.datetime.now()
output = f"""Current Date and Time: {current_time}
Time only: {current_time.strftime('%H:%M:%S')}
Date only: {current_time.strftime('%Y-%m-%d')}"""

print(output)

# Also write to file
with open('time_output.txt', 'w') as f:
    f.write(output)
