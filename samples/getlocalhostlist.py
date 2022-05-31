#!/usr/bin/env python3

import bluecat_bam
config = bluecat_bam.BAM.argparsecommon("getlocalhostlist")
args = config.parse_args()
with bluecat_bam.BAM(args.server, args.username, args.password) as conn:
    entities = conn.do("searchByCategory", category="RESOURCE_RECORD", start=0, count=1000, keyword="localhost")
    for obj in entities:
        type = obj['type']
        if type == 'ExternalHostRecord':
            print(obj['id'],type,obj['name'])
        else:
            print(obj['id'],type,obj['properties']['absoluteName'])
