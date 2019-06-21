#!/bin/bash

# add_update_get_delete.sh

CONFIG_ID=557057
TEST_MAC=0200deadbeef

echo "check if mac address exists, should get id=0 if not"
oldmac=`bam getMACAddress method=get configurationId=$CONFIG_ID macAddress=$TEST_MAC`
echo "old mac is: $oldmac"
id=`echo $oldmac | jq .id`
echo "old id is: $id"
if [ "X$id" != "X0" ]; then
  echo "ERROR - mac address already exists"
  exit 1
fi
echo

echo "add new mac address, response is the id of the new entity"
id=`bam addMACAddress method=post configurationId=$CONFIG_ID macAddress=$TEST_MAC properties="" `
echo "new id is: $id"
echo

echo "get mac address just added"
entity=`bam getMACAddress method=get configurationId=$CONFIG_ID macAddress=$TEST_MAC`
echo $entity
echo

echo "change name in local copy of the mac address"
updatedentity=`echo $entity | jq -c '.name |= "testmac" ' `
echo $updatedentity
echo

echo "update the mac address in bluecat, expect null response"
bam update method=put body="$updatedentity"
echo

echo "get mac address from bluecat"
bam getMACAddress method=get configurationId=$CONFIG_ID macAddress=$TEST_MAC
echo

echo "delete mac address, expect null response"
bam delete method=delete objectId=$id
echo

echo "check if mac address exists, should get id=0"
bam getMACAddress method=get configurationId=$CONFIG_ID macAddress=$TEST_MAC
echo

echo "done"
