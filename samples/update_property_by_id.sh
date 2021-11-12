#!/bin/bash
# update_property_by_id.sh  obj_id  propertyname=value

set -Eeuo pipefail

function usage {
  echo "$0 entityId 'name=value'"
  echo "    Update property in an entity"
  echo "    (Using curl and bash for demonstration)"
  exit
}

# Alternative using environment variables:
username=$BLUECAT_USERNAME
password=$BLUECAT_PASSWORD
server=$BLUECAT_SERVER
configuration=$BLUECAT_CONFIGURATION
#view=$BLUECAT_VIEW   # used in some scripts

if [ "X" = "X${1:-}" -o "X" = "X${2:-}" ]; then
  usage
fi

entity_id=$1
saveIFS=$IFS
IFS=/
set $2
prop=$1
value=$2
IFS="$saveIFS"

if [ "X" = "X${prop:-}" -o "X" = "X${value:-}" ]; then
  usage
fi

token=`curl -s -k 'https://'$server'/Services/REST/v1/login?username='"$username"'&password='"$password"`
tokenheader=`echo $token | sed -e 's/^"Session Token-> /Authorization: /' -e 's/ <- for User : .*$//'`

obj=`curl -s -k -H "$tokenheader" 'https://'$server'/Services/REST/v1/getEntityById?id='$entity_id`

echo $obj
echo "change property in local copy of the object"
updatedentity=`echo $entity | jq -c '.'"$prop"' |= "'"$value"'" ' `
echo $updatedentity
echo

echo "update the object in bluecat, expect null response"
bam update method=put body="$updatedentity"
echo

newobj=`curl -s -k -H "$tokenheader" 'https://'$server'/Services/REST/v1/getEntityById?id='$entity_id`
echo $new_obj
