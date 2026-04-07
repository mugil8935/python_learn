import datetime
import os
import subprocess
import sys

os.chdir('h:/python/python_learn')

# Get current timestamp
current_time = datetime.datetime.now()
timestamp = current_time.strftime('%Y%m%d_%H%M%S')

# Create filename with timestamp
filename = f"output_{timestamp}.txt"

# Get absolute path
absolute_path = os.path.abspath(filename)

# Create content
content = f"""Execution Time: {current_time}
Timestamp: {timestamp}
Created at: {current_time.strftime('%Y-%m-%d %H:%M:%S.%f')}
Absolute Path: {absolute_path}"""

# Write to file
with open(filename, 'w') as f:
    f.write(content)

# Write path info to a log file
with open('last_file_location.txt', 'w') as f:
    f.write(f"Last created file: {absolute_path}\n")
    f.write(f"Filename: {filename}\n")
    f.write(f"Timestamp: {timestamp}\n")

# Display output
sys.stdout.write(f"File created: {filename}\n")
sys.stdout.write(f"Absolute path: {absolute_path}\n")
sys.stdout.flush()
