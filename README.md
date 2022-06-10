bluecat_bam

BlueCat Address Manager (BAM) REST API Python module and CLI

Author Bob Harold, rharolde@umich.edu  
Started 2018/05/11  
Copyright (C) 2018,2019 Regents of the University of Michigan  
Apache License Version 2.0, see LICENSE file  
This is a community supported open source project, not endorsed by BlueCat.  
"BlueCat Address Manager" is a trademark of BlueCat Networks (USA) Inc. and its
affiliates.

See installation instructions below.

Use as a Python module like:
```
import json
import bluecat_bam
with BAM(server, username, password) as conn:
    r = conn.do('getEntityByName', parentId=0, name='admin', type='User')
    print(json.dumps(r))
```
Sample output:
```
{"type": "User", "properties": {"firstname": "admin", "lastname": "admin",
"userType": "ADMIN", "userAccessType": "GUI", "email": "admin@domain.example"},
"name": "admin", "id": 3}
```

Or use on the command line as a CLI, putting the setup in the environment:
```
touch bluecat.env
chmod 700 bluecat.env
cat >> bluecat.env <<EOF
export BLUECAT_SERVER=bluecatservername.domain.example
export BLUECAT_USERNAME=myusername
export BLUECAT_PASSWORD=mypassword
EOF
source bluecat.env
bam getEntityByName parentId=0 name=admin type=User
```
Sample output:
```
{"type": "User", "properties": {"firstname": "admin", "lastname": "admin",
"userType": "ADMIN", "userAccessType": "GUI", "email": "admin@domain.example"},
"name": "admin", "id": 3}
```

The CLI includes verbose options, and can read server,username, and password from
environment variables.  See help:
```
bam -h
```

Output from an API call can be any of:
- JSON dictionary (usually an entity)
- JSON list of dictionaries (like a list of entities)
- JSON string (in quotes)
- boolean (true or false)
- long integer (id of an entity, no quotes)
- null - returned as those 4 characters, without quotes
    (null does not indicate success, only that the syntax was correct)
- Error message, like:
    "HTTPError: 500 Server Error" (can be caused by lack of access rights)

If the dictionary has id: 0, that usually means that nothing was returned.  
The output, if JSON, can be fed to "jq" to further process the data.



## Requirements, if not already installed ##
Python2 or Python3  
pip
```
pip install setuptools
```

## Normal Installation ##
Download with git as shown, or with curl or wget or web browser
```
git clone git@gitlab.umich.edu:its-public/bluecat_bam.git
cd bluecat_bam
pip install wheel
pip install .
```
If installed as a user, you might need to add "~/.local/bin" to your PATH

## Dev Installation in virtualenv ##
```
git clone git@gitlab.umich.edu:its-public/bluecat_bam.git
cd bluecat_bam
python3 -m venv venv
source ./venv/bin/activate
pip install wheel
pip install -e ".[test]"
```

If installed as a user, you might need to add "~/.local/bin" to your PATH

See "samples" directory, and also try running quicktest.sh
.gitlab-ci.yml assumes a gitlab repo, will be different on github.

Written to run under both Python2 and Python3, since the BAM (v9.1.0 and before)
defaults to Python2.  (BAM 8.2.0 has only Python2)
(Removed python2 tests because new versions of Python2 fail for unknown reasons.
  But it should still work on a BAM.)
Using 'black' to enforce format, line width 88.  
This passes pylint and flake8 with minor exceptions, see .pylintrc and .flake8  
Also passes "bandit" security linter.  

See FUTURE for plans to improve this.
