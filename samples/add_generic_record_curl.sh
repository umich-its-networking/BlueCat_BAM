#!/bin/bash

# add_generic_record_curl.sh
# example script

hostname=$1
type=$2
data=$3
ttl=$4
viewid=$5

# get config from environment
username=$BLUECAT_USERNAME
password=$BLUECAT_PASSWORD
server=$BLUECAT_SERVER
#configuration=$BLUECAT_CONFIGURATION
#view=$BLUECAT_VIEW

# login, get token
token=`curl -s -k 'https://'$server'/Services/REST/v1/login?username='"$username"'&password='"$password"`
tokenheader=`echo $token | sed -e 's/^"Session Token-> /Authorization: /' -e 's/ <- for User : .*$//'`

echo "add new generic record, response is the id of the new entity"
id=`curl -s -k -X POST -H "$tokenheader" 'https://'$server'/Services/REST/v1/addGenericRecord?absoluteName='$hostname'&ttl='$ttl'&properties=&type='$type'&rdata='$data'&viewId='$viewid`
echo "new id is: $id"
echo

echo "get record just added"
entity=`curl -s -k -H "$tokenheader" 'https://'$server'/Services/REST/v1/getEntityById?id='$id`
echo $entity
echo

echo "done"
