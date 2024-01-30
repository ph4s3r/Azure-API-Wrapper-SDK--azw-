# Azure API Wrapper SDK (azw)

Author: Peter Karacsonyi

Lightweight Azure SDK for REST and GRAPH API as a Python pip module

There are two main functions to call GET requests on the 2 APIs: call_rest() and call_graph() respectively to list resources or get information about one specific resource.

Just find a resource you would like to get  
REST API reference: https://learn.microsoft.com/en-us/rest/api/azure/  
Graph API reference: https://learn.microsoft.com/en-us/graph/api/overview?view=graph-rest-1.0

## Features & default ettings

- authentication with msal, http token caching, persistent token cache (one file per type rest/graph)
- pagination (functions give all results back at once)
- error handling: functions return None and logs error to stdout in case of resource could not be queried
- automatic retries (3)
- logging the full api call with setting verbosity == 'VERBOSE'

## Install

```bash
pip install msal
pip install ujson
pip install azw  -I --trusted-host gitlab.ch.domain.net --extra-index-url https://__token__:<your personal acccess token here>@gitlab.ch.domain.net/api/v4/projects/2623/packages/pypi/simple
```
## Setup

you need ARM_CLIENT_ID, ARM_CLIENT_SECRET, ARM_TENANT_ID set as env variables to authenticate to Azure

## Use

##### List Azure AD applications where the displayname starts with 's'

link: https://learn.microsoft.com/en-us/graph/api/application-list?view=graph-rest-1.0&tabs=http  

```python3
import azw
apps = azw.call_graph(resource='applications', filter="startswith(displayName,'s')")
```

##### Get one user's data from AAD

https://learn.microsoft.com/en-us/graph/api/user-get?view=graph-rest-1.0&tabs=http

```python3
import azw
user = azw.call_graph(resource='users/<objectId>')
```

##### Get subscriptions

link: https://learn.microsoft.com/en-us/rest/api/resources/subscriptions/list?tabs=HTTP  

```python3
import azw
subs = azw.call_rest(resource = 'subscriptions', api_version='2020-01-01')
```

##### Filter subscriptions by displayName and Status
```python3
subscriptions_Filtered = dict()
for s in subs:
    if(
        ((('landingzone') in s.get('displayName')) or (('platform') in s.get('displayName')) or (('etwas') in s.get('displayName'))) and
        s.get('state') == 'Enabled'
    ):
        item = {s.get('id') : s.get('displayName')}
        subscriptions_Filtered.update(item)
del s
```

##### Dump a dict to json file
```python3
azw.jwrite(subs, 'subscriptions.json')
```

##### Get Role Assignments and do some filtering
this example is looping through the subscriptions gathered above
link: https://learn.microsoft.com/en-us/rest/api/authorization/role-assignments/list-for-scope?tabs=HTTP
```python3
roleAssignments = list()
for s in subscriptions_Filtered.keys():
    roleAssignments += azw.call_rest(
            resource='Microsoft.Authorization/roleAssignments',
            scope = s,
            api_version='2022-04-01'
        ).get('value')
del s

roleAssignments_Filtered = dict()
for r in roleAssignments:
    if(
        r.get('properties').get('principalType') == 'User' and
        r.get('properties').get('principalId') != '<principalId>' # filter
    ):
        key = f"{r.get('properties').get('principalId')}"
        roleAssignments_Filtered.update({key: r})
del r
```

## Reference

```python3
def call_rest(resource: str, scope: str = None, api_version : str = '2020-10-01', verbosity : str = 'INFO', ignore_errors: bool = True):
    """
    the function calls azure arm API

    :param resource:        'Microsoft.Authorization/roleAssignmentScheduleInstances'
    :param scope:           '/subscriptions/<subscriptionId>'
    :param api_version:     '2020-10-01' (default)
    :param ignore_errors:   'True' do not exit on failure (default)
    :return                 json data

    for scoped requests the url format is https://management.azure.com{scope}/providers/{resource}?api-version={api_version}
    for not scoped https://management.azure.com/{resource}?api-version={api_version}
    """
```

```python3
def call_graph(resource: str, api_version : str = 'v1.0', verbosity : str = 'INFO', filter: str = None, ignore_errors: bool = True):

    """
    :param resource:        'users/principalId' or 'applications'
    :param filter           "startswith(displayName,'s')" url encoding is automatic
    :param ignore_errors:   'True' do not exit on failure (default)
    :return                 list or json data depending on the type of resource

    """
```

```python3
    # Print formatted json to stdout
    def jprint(input):
        print(jdump(input))
```

```python3
    # Dump dictonary to string with formatting
    def jdump(input):
        return ujson.dumps(input, indent=4)
```

```python3
  # Writes out a dict to json file
  def jwrite(input, filename: str = None):
      if not filename:
          filename = 'dump.json'
      with open(filename, 'w') as f:
        ujson.dump(input, f, indent=4)
```
## Contributing

### Build & Publish

- [Gitlab Tutorial](https://docs.gitlab.com/ee/user/packages/workflows/build_packages.html#pypi)

#### Prerequirements

```bash
pip install build
pip install twine
```

#### Build

go to the folder where the pyproject.toml resides and hit

```bash
python -m build
```

#### Publish

if getting HTTP 400, name already taken, that's because a version cannot be overwritten so need to bump the version in the .toml file, rebuild and remove the earlier version from dist dir

```bash
python3 -m twine upload --repository gitlab dist/*
```

==================================================================
