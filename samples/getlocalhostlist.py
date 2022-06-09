#!/usr/bin/env python3
"""get a list of localhost.<domain> entries from the BAM"""

import bluecat_bam

config = bluecat_bam.BAM.argparsecommon("getlocalhostlist")
args = config.parse_args()
with bluecat_bam.BAM(args.server, args.username, args.password) as conn:
    entities = conn.do(
        "searchByCategory",
        category="RESOURCE_RECORD",
        start=0,
        count=1000,
        keyword="localhost",
    )
    for obj in entities:
        obj_type = obj["type"]
        if obj_type == "ExternalHostRecord":
            print(obj["id"], obj_type, obj["name"])
        else:
            print(obj["id"], obj_type, obj["properties"]["absoluteName"])
