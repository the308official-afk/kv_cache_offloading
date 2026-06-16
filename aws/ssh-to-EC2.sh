#!/bin/bash

# ./ssh-to-EC2 0

# Define your public IPs in an array
IPS=(
  ""   
  "3.87.216.209"
  ""
)

# Check if an argument was passed
if [ -z "$1" ]; then
  echo "Usage: $0 <0-3>"
  exit 1
fi

INDEX=$1

# Validate input (must be between 0 and 3)
if [ "$INDEX" -lt 0 ] || [ "$INDEX" -ge ${#IPS[@]} ]; then
  echo "Error: index must be between 0 and $((${#IPS[@]}-1))"
  exit 1
fi

# Pick the right IP
PUBLIC_IP=${IPS[$INDEX]}

echo "Connecting to ${PUBLIC_IP} ..."
# ssh -i "/Users/oluwolejaiyeoba/Documents/project_one/AWS/projectone.pem" ec2-user@"${PUBLIC_IP}"
ssh -i "/Users/oluwolejaiyeoba/Documents/GitHub/secrets/projectonekeypair.pem" ec2-user@"${PUBLIC_IP}"



