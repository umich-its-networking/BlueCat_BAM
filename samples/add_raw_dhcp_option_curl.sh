#!/bin/bash

# add_raw_dhcp_option_curl.sh  DHCP_server_id "raw-option-text"

if [ "X$2" = "X" ]; then
  echo "usage: $0 "'DHCP_server_id "raw-option-text"'
  exit 1
fi

DHCP_SERVER_ID=$1
RAW_OPTION_TEXT="$2"

# get config from environment
username=$BLUECAT_USERNAME
password=$BLUECAT_PASSWORD
server=$BLUECAT_SERVER

# login, get token
token=`curl -s -k 'https://'$server'/Services/REST/v1/login?username='"$username"'&password='"$password"`
tokenheader=`echo $token | sed -e 's/^"Session Token-> /Authorization: /' -e 's/ <- for User : .*$//'`

echo "add raw option, response is the id of the new raw option"
id=`curl -s -k -X POST -d '{"type": "DHCP_RAW", "value": "'"$RAW_OPTION_TEXT"'"}' -H "$tokenheader" -H "Content-Type: application/json" 'https://'$server'/Services/REST/v1/addRawDeploymentOption?parentId='$DHCP_SERVER_ID`
echo "new id is: $id"
