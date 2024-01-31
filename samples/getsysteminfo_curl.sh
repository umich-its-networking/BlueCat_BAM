#!/bin/bash

# getsysteminfo_curl.sh
# example script

# get config from environment
username=$BLUECAT_USERNAME
password=$BLUECAT_PASSWORD
server=$BLUECAT_SERVER
configuration=$BLUECAT_CONFIGURATION
view=$BLUECAT_VIEW

# login, get token
token=`curl -s -k 'https://'$server'/Services/REST/v1/login?username='"$username"'&password='"$password"`
tokenheader=`echo $token | sed -e 's/^"Session Token-> /Authorization: /' -e 's/ <- for User : .*$//'`

info=`curl -s -k -H "$tokenheader" 'https://'$server'/Services/REST/v1/getSystemInfo'`
echo $info

logout=`curl -s -k -H "$tokenheader" 'https://'$server'/Services/REST/v1/logout'`
echo "logout $logout"

