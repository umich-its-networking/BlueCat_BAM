#!/bin/bash
# getdhcprangesinsubnetbyip.sh

set -Eeuo pipefail

# Alternative using environment variables:

username=$BLUECAT_USERNAME
password=$BLUECAT_PASSWORD
server=$BLUECAT_SERVER
configuration=$BLUECAT_CONFIGURATION
#view=$BLUECAT_VIEW   # used in some scripts

if [ "X" = "X${1:-}" ]; then
  echo "usage: $0  subnetip"
  exit 2
fi

subnetip=$1
# if cidr, gut just the ip
saveIFS=$IFS
IFS=/
set $subnetip
subnetip=$1
IFS="$saveIFS"

token=`curl -s -k 'https://'$server'/Services/REST/v1/login?username='"$username"'&password='"$password"`
tokenheader=`echo $token | sed -e 's/^"Session Token-> /Authorization: /' -e 's/ <- for User : .*$//'`

subnetobj=`curl -s -k -H "$tokenheader" 'https://'$server'/Services/REST/v1/getIPRangedByIP?containerId=557057&type=IP4Network&address='$subnetip`

#echo $subnetobj

subnetid=`echo $subnetobj | jq .id`

dhcpranges=`curl -s -k -H "$tokenheader" 'https://'$server'/Services/REST/v1/getEntities?parentId='$subnetid'&type=DHCP4Range&start=0&count=1000'`

echo $dhcpranges | jq -c .[]
