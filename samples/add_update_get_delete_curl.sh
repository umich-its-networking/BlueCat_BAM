#!/bin/bash

# add_update_get_delete.sh

CONFIG_ID=557057
TEST_MAC=0200deadbeef

# get config from environment
username=$BLUECAT_USERNAME
password=$BLUECAT_PASSWORD
server=$BLUECAT_SERVER
configuration=$BLUECAT_CONFIGURATION
view=$BLUECAT_VIEW

# login, get token
token=`curl -s -k 'https://'$server'/Services/REST/v1/login?username='"$username"'&password='"$password"`
tokenheader=`echo $token | sed -e 's/^"Session Token-> /Authorization: /' -e 's/ <- for User : .*$//'`

echo "check if mac address exists, should get id=0 if not"
oldmac=`curl -s -k -H "$tokenheader" 'https://'$server'/Services/REST/v1/getMACAddress?configurationId='$CONFIG_ID'&macAddress='$TEST_MAC`
echo "old mac is: $oldmac"
id=`echo $oldmac | jq .id`
echo "old id is: $id"
if [ "X$id" != "X0" ]; then
  echo "ERROR - mac address already exists"
  exit 1
fi
echo

echo "add new mac address, response is the id of the new entity"
id=`curl -s -k -X POST -H "$tokenheader" 'https://'$server'/Services/REST/v1/addMACAddress?configurationId='$CONFIG_ID'&macAddress='$TEST_MAC'&properties='`
echo "new id is: $id"
echo

echo "get mac address just added"
entity=`curl -s -k -H "$tokenheader" 'https://'$server'/Services/REST/v1/getMACAddress?configurationId='$CONFIG_ID'&macAddress='$TEST_MAC`
echo $entity
echo

echo "change name in local copy of the mac address"
updatedentity=`echo $entity | jq -c '.name |= "testmac" ' `
echo $updatedentity
echo

echo "update the mac address in bluecat, expect null response"
curl -s -k -X PUT -H "$tokenheader" -H "Content-Type: application/json" -d "$updatedentity" 'https://'$server'/Services/REST/v1/update'
echo

echo "get mac address from bluecat"
obj=`curl -s -k -H "$tokenheader" 'https://'$server'/Services/REST/v1/getMACAddress?configurationId='$CONFIG_ID'&macAddress='$TEST_MAC`
echo $obj
echo

echo "delete mac address, expect null response"
curl -s -k -X DELETE -H "$tokenheader" 'https://'$server'/Services/REST/v1/delete?objectId='$id
echo

echo "check if mac address exists, should get id=0"
obj=`curl -s -k -H "$tokenheader" 'https://'$server'/Services/REST/v1/getMACAddress?configurationId='$CONFIG_ID'&macAddress='$TEST_MAC`
echo $obj
echo

echo "done"
