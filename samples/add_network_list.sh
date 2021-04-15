while read ip prefix vlan name
do
    name=`echo $name | tr -d "'"`
    python3 samples/add_network.py -i $ip/$prefix --vlan $vlan -n "$name"
done
