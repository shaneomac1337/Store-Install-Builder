#!/bin/bash

# Parse command line arguments
COMPONENT_TYPE="POS"
base_url="test.cse.cloud4retail.co"
tenant_id="001"
username="launchpad"
form_username="1001"

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
    --tenant_id)
      tenant_id="$2"
      shift 2
      ;;
    *)
      echo "Unknown option: $1"
      echo "Usage: $0 [--ComponentType <POS|WDM|FLOW-SERVICE|LPA-SERVICE|STOREHUB-SERVICE>] [--base_url <url>] [--tenant_id <tenant_id>]"
      exit 1
      ;;
  esac
done

# API endpoint
url="https://$base_url/auth-service/tenants/${tenant_id}/oauth/token"

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

# Basic Auth credentials
username="launchpad"
# Use the decoded password from the file instead of hardcoding it
password="$basic_auth_password"

# Encode credentials
auth_string=$(echo -n "$username:$password" | base64)

# URL encoding function that doesn't rely on jq
urlencode() {
  # URL encode a string
  local string="$1"
  local length="${#string}"
  local encoded=""
  local i char

  for ((i=0; i<length; i++)); do
    char="${string:i:1}"
    case "$char" in
      [a-zA-Z0-9.~_-]) encoded="$encoded$char" ;;
      *) printf -v encoded '%s%%%02X' "$encoded" "'$char" ;;
    esac
  done
  echo "$encoded"
}

# Form data with decrypted password using our native URL encoding
username_encoded=$(urlencode "$form_username")
password_encoded=$(urlencode "$form_password")
form_data="username=${username_encoded}&password=${password_encoded}&grant_type=password"

# Make the API call
response=$(curl -s -X POST "$url" \
  -H "Authorization: Basic $auth_string" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "$form_data")

if [ $? -ne 0 ]; then
  echo "Error occurred during API call"
  exit 1
fi

# Parse the response for access_token
if command -v jq >/dev/null 2>&1; then
  # Use jq if available
  echo "JQ is available. Using JQ for access token extraction."
  access_token=$(echo "$response" | jq -r '.access_token // empty')
else
  # Improved fallback that handles JSON more reliably
  echo "JQ was not detected. Falling back to bash-native JSON parsing methods."
  access_token=$(echo "$response" | grep -o '"access_token":"[^"]*"' | sed 's/"access_token":"//g' | sed 's/"//g')
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
  echo "JQ is available. Using JQ for onboarding token extraction."
  onboarding_token=$(echo "$onboarding_response" | jq -r '.token // empty')
else
  # Improved fallback that handles JSON more reliably
  echo "JQ was not detected. Falling back to bash-native JSON parsing methods."
  onboarding_token=$(echo "$onboarding_response" | grep -o '"token":"[^"]*"' | sed 's/"token":"//g' | sed 's/"//g')
fi

if [ -z "$onboarding_token" ]; then
  echo "Error in $COMPONENT_TYPE onboarding request. Response:"
  echo "$onboarding_response"
  exit 1
fi

# Save the onboarding token without extra newline
echo -n "$onboarding_token" > "onboarding.token"
echo "$COMPONENT_TYPE onboarding token successfully saved to onboarding.token" 