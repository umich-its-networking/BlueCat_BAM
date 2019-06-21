#!/bin/bash

# add_next_dhcp_reserved.sh

configurationname=UMNET
viewname='Default View'
networkip=141.213.135.0
mac=02-03-04-05-09-08
hostname=rharoldetry.umnet.umich.edu

configurationobj=`bam getEntityByName method=get parentId=0 name="$configurationname" type=Configuration`
echo $configurationobj
# {"type": "Configuration", "properties": {"sharedNetwork": "1665534"}, "name": "UMNET", "id": 557057}

configurationId=`echo $configurationobj | jq .id`
echo $configurationId
# 557057

viewId=`bam getEntityByName method=get parentId=$configurationId name="$viewname" type=View | jq .id`
echo $viewId
# 1048598

networkobj=`bam getIPRangedByIP method=get containerId=$configurationId type=IP4Network address=141.213.135.0`
echo $networkobj
# {"type": "IP4Network", "properties": {"sharedNetwork": "IPS-ITS-COMM-AL", "inheritPingBeforeAssign": "true", "inheritDNSRestrictions": "true", "reference": "814", "locationInherited": "true", "allowDuplicateHost": "disable", "inheritAllowDuplicateHost": "true", "pingBeforeAssign": "disable", "CIDR": "141.213.135.0/24", "defaultView": "1048598", "gateway": "141.213.135.1", "inheritDefaultDomains": "true", "inheritDefaultView": "true"}, "name": "IPS-ITS-COMM-AL", "id": 8246503}

networkId=`echo $networkobj | jq .id`
echo $networkId
# 8246503

newipobj=`bam assignNextAvailableIP4Address method=post configurationId=$configurationId parentId=$networkId macAddress=$mac hostInfo="$hostname,$viewId,reverseFlag=true,sameAsZoneFlag=false" action=MAKE_DHCP_RESERVED properties=""`
echo $newipobj
# {"type": "IP4Address", "properties": {"macAddress": "02-03-04-05-09-08", "state": "DHCP_RESERVED", "locationInherited": "true", "address": "141.213.135.4"}, "name": null, "id": 20030795}

newipaddress=`echo $newipobj | jq .properties.address`
echo $newipaddress
# "141.213.135.4"
