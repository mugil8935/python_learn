import datetime
import os

# Get current timestamp
current_time = datetime.datetime.now()
timestamp = current_time.strftime('%Y%m%d_%H%M%S')

# Create filename with timestamp
filename = f"output_{timestamp}.txt"

# Create content
content = f"""Execution Time: {current_time}
Timestamp: {timestamp}
Created at: {current_time.strftime('%Y-%m-%d %H:%M:%S.%f')}"""

# Write to file
with open(filename, 'w') as f:
    f.write(content)

print(f"File created: {filename}")
print(content)
