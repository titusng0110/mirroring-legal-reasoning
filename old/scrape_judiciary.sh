#!/bin/bash
mkdir data/judiciary/
# Define the base URL and the range of IDs
BASE_URL="https://legalref.judiciary.hk/lrs/common/search/search_result_detail_body.jsp?ID=&DIS="
START_ID=100000
END_ID=109019

# Iterate over the range of IDs
for (( ID=$START_ID; ID<=$END_ID; ID++ ))
do
    # Construct the full URL
    URL="${BASE_URL}${ID}&QS=%2E"
    
    # Output filename
    FILENAME="data/judiciary/${ID}.html"
    
    # Use curl to fetch the URL and save to the output file
    curl -o "${FILENAME}" "${URL}"
    
    # Optional: Add a delay to avoid hammering the server
    # sleep 1
done