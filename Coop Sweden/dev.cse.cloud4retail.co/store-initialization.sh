#!/bin/bash

# Exit on any error
set -e

# Default values will be overridden by command line arguments
COMPONENT_TYPE=""
base_url=""
STORE_ID=""
WORKSTATION_ID=""

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
    --StoreId)
      STORE_ID="$2"
      shift 2
      ;;
    --WorkstationId)
      WORKSTATION_ID="$2"
      shift 2
      ;;
    *)
      echo "Unknown option: $1"
      echo "Usage: $0 [--ComponentType <type>] [--base_url <url>] [--StoreId <id>] [--WorkstationId <id>]"
      exit 1
      ;;
  esac
done

# Verify all required parameters are provided
if [ -z "$COMPONENT_TYPE" ] || [ -z "$base_url" ] || [ -z "$STORE_ID" ] || [ -z "$WORKSTATION_ID" ]; then
  echo "Error: All parameters are required"
  echo "Usage: $0 --ComponentType <type> --base_url <url> --StoreId <id> --WorkstationId <id>"
  exit 1
fi

# Paths
tokens_path="$PWD/helper/tokens"

# Verify paths exist
if [ ! -d "$tokens_path" ]; then
  echo "Tokens path does not exist: $tokens_path"
  exit 1
fi

# Read the access token created by onboarding.sh
access_token_path="$tokens_path/access_token.txt"
if [ ! -f "$access_token_path" ]; then
  echo "Access token file does not exist. Please run onboarding.sh first."
  exit 1
fi

access_token=$(cat "$access_token_path")

# Common headers for all API calls
headers=(
  -H "Authorization: Bearer $access_token"
  -H "Content-Type: application/json; variant=Plain; charset=UTF-8"
  -H "Accept: application/json; variant=Plain; charset=UTF-8"
  -H "GK-Accept-Redirect: 308"
)

# First API call - Get Business Unit
bu_url="https://$base_url/swee-sdc/tenants/001/services/rest/master-data/v1/business-units/$STORE_ID"
bu_response=$(curl -s -f -X GET "$bu_url" "${headers[@]}")
if [ $? -ne 0 ]; then
  echo "Error occurred during business unit API call"
  exit 1
fi

echo "Successfully retrieved business unit information"

# Parse the business unit response for businessUnitGroupID from the key object
if command -v jq >/dev/null 2>&1; then
  # Use jq if available
  business_unit_group_id=$(echo "$bu_response" | jq -r '.key.businessUnitGroupID // empty')
else
  # Fallback to grep and cut if jq is not available - this is more complex for nested JSON
  business_unit_group_id=$(echo "$bu_response" | grep -o '"key":{[^}]*"businessUnitGroupID":"[^"]*"' | grep -o '"businessUnitGroupID":"[^"]*"' | cut -d'"' -f4)
fi

if [ -z "$business_unit_group_id" ]; then
  echo "Failed to get businessUnitGroupID from response:"
  echo "$bu_response"
  exit 1
fi

echo "Found businessUnitGroupID: $business_unit_group_id"

# Second API call - Try to Get Workstation first
ws_url="https://$base_url/swee-sdc/tenants/001/services/rest/master-data/v1/workstations/(businessUnitGroupId=$business_unit_group_id,workstationId=$WORKSTATION_ID)"
ws_response=$(curl -s -f -X GET "$ws_url" "${headers[@]}" || echo "HTTP_ERROR")

if [ "$ws_response" = "HTTP_ERROR" ]; then
  # Check if it's a 404 error
  status_code=$(curl -s -o /dev/null -w "%{http_code}" "$ws_url" "${headers[@]}")
  
  if [ "$status_code" = "404" ]; then
    echo "Workstation not found, creating new workstation..."
    
    # Determine workstation type based on ComponentType
    case "$COMPONENT_TYPE" in
      'LPA-SERVICE')
        type_code="LPAS"
        ;;
      'STOREHUB-SERVICE')
        type_code="SH"
        ;;
      'POS')
        type_code="POS"
        ;;
      'WDM')
        type_code="WDM"
        ;;
      *)
        type_code="POS"
        ;;
    esac

    # Create workstation payload
    current_time=$(date -u +"%Y-%m-%dT%H:%M:%S.000Z")
    ws_payload="{\"workstation\":{\"key\":{\"workstationID\":\"$WORKSTATION_ID\",\"businessUnitGroupID\":\"$business_unit_group_id\"},\"typeCode\":\"$type_code\",\"createTimestampUTC0\":\"$current_time\"}}"
    
    ws_create_url="https://$base_url/swee-sdc/tenants/001/services/rest/master-data/v1/workstations"
    ws_response=$(curl -s -f -X POST "$ws_create_url" "${headers[@]}" -d "$ws_payload")
    
    if [ $? -ne 0 ]; then
      echo "Error creating workstation"
      echo "Response: $ws_response"
      exit 1
    fi
    echo "Successfully created new workstation"
  else
    echo "Error accessing workstation. Status code: $status_code"
    echo "Response: $ws_response"
    exit 1
  fi
else
  echo "Successfully retrieved existing workstation information"
fi

# Save responses to files
echo "$bu_response" > "business-unit.json"
echo "$ws_response" > "workstation.json"
echo "Saved response data to business-unit.json and workstation.json"

# Get store information using get_store.json
init_path="$PWD/helper/init"
get_store_json_path="$init_path/get_store.json"

# Create init directory if it doesn't exist
mkdir -p "$init_path"

if [ ! -f "$get_store_json_path" ]; then
  echo "Warning: get_store.json not found at: $get_store_json_path"
else
  echo "Making API call to get store information..."
  
  # Make the API call to get store information
  store_url="https://$base_url/config-service/services/rest/infrastructure/v1/structure/child-nodes/search"
  
  # Add content-type header for this specific call
  content_type_header=(-H "Content-Type: application/json; variant=Plain; charset=UTF-8")
  
  store_response=$(curl -s -f -X POST "$store_url" "${headers[@]}" "${content_type_header[@]}" -d @"$get_store_json_path")
  
  if [ $? -eq 0 ]; then
    echo "Successfully retrieved store information"
    
    # Save the response to storemanager.json
    storemanager_path="$init_path/storemanager.json"
    echo "$store_response" > "$storemanager_path"
    echo "Store information saved to: $storemanager_path"
    
    # Only proceed with configuration update for StoreHub components
    if [ "$COMPONENT_TYPE" = "STOREHUB-SERVICE" ] || [ "$COMPONENT_TYPE" = "SH" ]; then
      # Now update the configuration using update_config.json from the storehub directory
      storehub_dir="$init_path/storehub"
      update_config_path="$storehub_dir/update_config.json"
      
      # Create storehub directory if it doesn't exist
      mkdir -p "$storehub_dir"
      
      if [ -f "$update_config_path" ]; then
        echo "Updating StoreHub configuration using update_config.json..."
        
        # Get system type for StoreHub
        system_type="CSE-sh-cloud"
        
        # Get hostname
        hostname=$(hostname)
        if [ -z "$hostname" ]; then
          hostname="localhost"
        fi
        
        # Get version from config
        version="v1.1.0"  # Default version
        
        # Get structure unique name from storemanager.json if available
        if [ -f "$storemanager_path" ]; then
          # Use jq to extract the structure unique name that matches our system type
          if command -v jq >/dev/null 2>&1; then
            structure_unique_name=$(jq -r ".childNodeList[] | select(.systemName == \"$system_type\") | .structureUniqueName" "$storemanager_path")
            
            if [ -n "$structure_unique_name" ]; then
              echo "Found matching structure: $structure_unique_name"
            else
              # Construct a default structure name
              structure_unique_name="ENTERPRISE.TENANT.SWEDEN.INSTALLATION_TEST_STORE.$STORE_ID.STOREHUB"
              echo "Using default structure name: $structure_unique_name"
            fi
          else
            echo "jq not found, using default structure name"
            structure_unique_name="ENTERPRISE.TENANT.SWEDEN.INSTALLATION_TEST_STORE.$STORE_ID.STOREHUB"
            echo "Using default structure name: $structure_unique_name"
          fi
        else
          # Construct a default structure name
          structure_unique_name="ENTERPRISE.TENANT.SWEDEN.INSTALLATION_TEST_STORE.$STORE_ID.STOREHUB"
          echo "Using default structure name: $structure_unique_name"
        fi
        
        # Create a temporary file with the replacements
        temp_config_file=$(mktemp)
        
        # Replace placeholders in the template
        sed -e "s/@STRUCTURE_UNIQUE_NAME@/$structure_unique_name/g" \
            -e "s/@HOSTNAME@/$hostname/g" \
            "$update_config_path" > "$temp_config_file"
        
        # Write the updated content back to the original file
        cat "$temp_config_file" > "$update_config_path"
        echo "Updated update_config.json with structure unique name and hostname"
        
        # Make the API call to update the configuration
        config_url="https://$base_url/config-service/services/rest/config-management/v1/parameter-contents/plain"
        
        config_response=$(curl -s -f -X POST "$config_url" "${headers[@]}" "${content_type_header[@]}" -d @"$temp_config_file")
        
        if [ $? -eq 0 ]; then
          echo "Successfully updated configuration"
          
          # Save the response to config_response.json
          config_response_path="$storehub_dir/config_response.json"
          echo "$config_response" > "$config_response_path"
          echo "Configuration response saved to: $config_response_path"
        else
          echo "Error updating configuration"
          echo "Response: $config_response"
          # Continue execution even if this call fails
        fi
        
        # Remove the temporary file
        rm -f "$temp_config_file"
      else
        echo "Warning: StoreHub update_config.json not found at: $update_config_path"
      fi
    else
      echo "Skipping configuration update - not a StoreHub component"
    fi
  else
    echo "Error retrieving store information"
    echo "Response: $store_response"
    # Continue execution even if this call fails
  fi
fi

# Exit successfully
exit 0 