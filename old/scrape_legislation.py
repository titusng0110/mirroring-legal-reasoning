import re
import requests
import os
import time
import random
import sys

# Check if correct number of arguments are provided
if len(sys.argv) != 3:
    print("Usage: python script.py <input_file_path> <output_directory>")
    sys.exit(1)

# Get input file path and output directory from command line arguments
input_file_path = sys.argv[1]
output_directory = sys.argv[2]

# Define the regex pattern
pattern = r'https://www\.elegislation\.gov\.hk/hk/cap([0-9A-Z]+)!en\.assist\.rtf\?FROMCAPINDEX=Y'

# Define a list of user agents with randomized OS
user_agents = [
    # Chrome
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
    # Firefox
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:128.0) Gecko/20100101 Firefox/128.0",
    "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:128.0) Gecko/20100101 Firefox/127.0",
    # Safari
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15"
]

# Open and read the file
with open(input_file_path, 'r', encoding='utf-8') as file:
    content = file.read()

# Find all matches
matches = re.findall(pattern, content)
print(f"Total {len(matches)} matches.")

# Create the output directory to store the RTF files
os.makedirs(output_directory, exist_ok=True)

# Download and save each RTF file
for match in matches:
    url = f'https://www.elegislation.gov.hk/hk/cap{match}!en.assist.rtf?FROMCAPINDEX=Y'
    filename = f'{match}.rtf'
    
    # Random wait time between 0.2 and 1 second
    wait_time = random.uniform(0.2, 1)
    time.sleep(wait_time)
    
    # Randomly select a user agent
    headers = {'User-Agent': random.choice(user_agents)}
    
    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        with open(os.path.join(output_directory, filename), 'wb') as file:
            file.write(response.content)
        print(f'Downloaded: {filename}')
    else:
        print(f'Failed to download: {filename}')