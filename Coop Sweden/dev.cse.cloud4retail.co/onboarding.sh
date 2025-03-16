#!/bin/bash

# Parse command line arguments
COMPONENT_TYPE="POS"
base_url="dev.cse.cloud4retail.co"

# Process command line options
while [ $# -gt 0 ]; do
  case "$1" in
    --ComponentType)
      COMPONENT_TYPE="$2"
      shift 2
      ;;
    --base_url)
      base_url="$2"
      shift 2
      ;;
    *)
      echo "Unknown option: $1"
      echo "Usage: $0 [--ComponentType <POS|WDM|FLOW-SERVICE|LPA-SERVICE|STOREHUB-SERVICE>] [--base_url <url>]"
      exit 1
      ;;
  esac
done

# API endpoint
url="https://$base_url/auth-service/tenants/001/oauth/token"

# Basic Auth credentials
username="launchpad"

# Function to Base64 encode
encode_base64() {
  echo -n "$1" | base64
}

# Function to Base64 decode
decode_base64() {
  echo "$1" | base64 --decode
}

# Paths
tokens_path="$PWD/helper/tokens"
onboarding_path="$PWD/helper/onboarding"

# Verify paths exist
if [ ! -d "$tokens_path" ]; then
  echo "Tokens path does not exist: $tokens_path"
  exit 1
fi

if [ ! -d "$onboarding_path" ]; then
  echo "Onboarding path does not exist: $onboarding_path"
  exit 1
fi

# Verify files exist
basic_auth_path="$tokens_path/basic_auth_password.txt"
form_password_path="$tokens_path/form_password.txt"

if [ ! -f "$basic_auth_path" ]; then
  echo "Basic auth password file does not exist: $basic_auth_path"
  exit 1
fi

if [ ! -f "$form_password_path" ]; then
  echo "Form password file does not exist: $form_password_path"
  exit 1
fi

# Load and decode passwords
basic_auth_password=$(decode_base64 "$(cat "$basic_auth_path")")
form_password=$(decode_base64 "$(cat "$form_password_path")")

# Use decoded passwords
base64_auth=$(encode_base64 "${username}:${basic_auth_password}")

# Form data with decrypted password
username_encoded=$(printf %s "1001" | jq -sRr @uri)
password_encoded=$(printf %s "$form_password" | jq -sRr @uri)
form_data="username=${username_encoded}&password=${password_encoded}&grant_type=password"

# Make the API call
response=$(curl -s -X POST "$url" \
  -H "Authorization: Basic $base64_auth" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "$form_data")

if [ $? -ne 0 ]; then
  echo "Error occurred during API call"
  exit 1
fi

# Parse the response for access_token
if command -v jq >/dev/null 2>&1; then
  # Use jq if available
  access_token=$(echo "$response" | jq -r '.access_token // empty')
else
  # Fallback to grep and cut if jq is not available
  access_token=$(echo "$response" | grep -o '"access_token":"[^"]*"' | cut -d'"' -f4)
fi

if [ -z "$access_token" ]; then
  echo "Failed to extract access_token from response:"
  echo "$response"
  exit 1
fi

# Save the access token without extra newline
echo -n "$access_token" > "$tokens_path/access_token.txt"
echo "Access token successfully saved"

# Second API call using the token
onboarding_url="https://$base_url/cims/services/rest/cims/v1/onboarding/tokens"

# Determine JSON file based on ComponentType
case "$COMPONENT_TYPE" in
  'WDM')
    json_file="wdm.onboarding.json"
    ;;
  'FLOW-SERVICE')
    json_file="flow-service.onboarding.json"
    ;;
  'LPA-SERVICE')
    json_file="lpa-service.onboarding.json"
    ;;
  'STOREHUB-SERVICE')
    json_file="storehub-service.onboarding.json"
    ;;
  *)
    json_file="pos.onboarding.json"
    ;;
esac

# Read JSON from selected file
json_path="$onboarding_path/$json_file"
if [ ! -f "$json_path" ]; then
  echo "JSON file does not exist: $json_path"
  exit 1
fi

body=$(cat "$json_path")

# Make the onboarding API call
onboarding_response=$(curl -s -X POST "$onboarding_url" \
  -H "Authorization: Bearer $access_token" \
  -H "Content-Type: application/json" \
  -d "$body")

if [ $? -ne 0 ]; then
  echo "Error occurred during onboarding API call"
  exit 1
fi

# Parse the response for token
if command -v jq >/dev/null 2>&1; then
  # Use jq if available
  onboarding_token=$(echo "$onboarding_response" | jq -r '.token // empty')
else
  # Fallback to grep and cut if jq is not available
  onboarding_token=$(echo "$onboarding_response" | grep -o '"token":"[^"]*"' | cut -d'"' -f4)
fi

if [ -z "$onboarding_token" ]; then
  echo "Error in $COMPONENT_TYPE onboarding request. Response:"
  echo "$onboarding_response"
  exit 1
fi

# Save the onboarding token without extra newline
echo -n "$onboarding_token" > "onboarding.token"
echo "$COMPONENT_TYPE onboarding token successfully saved to onboarding.token" 