#!/usr/bin/python3
#   about: general REST API function wrapper module
#  author: Peter Karacsonyi <peter.karacsonyi85@gmail.com>
#    date: 24 Jan 2024
# license: GNU General Public License, version 2
#####

from msal import ConfidentialClientApplication
import sys, atexit, pickle
import urllib.parse
import inspect
import urllib3
import ujson
import os

# supress printing of called functions to stdout
def blockPrint():
    sys.stdout = open(os.devnull, 'w')

# restore printing of called functions to stdout
def enablePrint():
    sys.stdout = sys.__stdout__


def auth(api_type : str = "rest") -> str:

  http_cache_filename = sys.argv[0] + ".http_cache_" + api_type
  try:
      with open(http_cache_filename, "rb") as f:
          persisted_http_cache = pickle.load(f)  # Take a snapshot
  except (
          FileNotFoundError,
          pickle.UnpicklingError,  # A corrupted http cache file
          ):
      persisted_http_cache = {}  # Recover by starting afresh
  atexit.register(lambda: pickle.dump(
      persisted_http_cache, open(http_cache_filename, "wb")))

  config = {
          "graph": "https://graph.microsoft.com/.default",
          "rest": "https://management.azure.com/.default",
          "CLIENT_ID" : os.environ["ARM_CLIENT_ID"],
          "CLIENT_CREDENTIAL" : os.environ["ARM_CLIENT_SECRET"],
          "AUTHORITY" : f'https://login.microsoftonline.com/{os.environ["ARM_TENANT_ID"]}'
  }

  client_instance = ConfidentialClientApplication(
      client_id=config["CLIENT_ID"],
      client_credential=config["CLIENT_CREDENTIAL"],
      authority=config["AUTHORITY"],
      http_cache=persisted_http_cache,
  )

  result = client_instance.acquire_token_for_client(scopes=config[api_type])

  if "access_token" in result:
      return result["access_token"] # Yay!
  else:
      print('failed to acquire token, abandoning context')
      print(result.get("error_description"))
      print(result.get("correlation_id"))  # need this when reporting a bug
      os._exit(-1)


# Print formatted json to stdout
def jprint(input):
    print(jdump(input))

    
# Dump dictonary to string with formatting
def jdump(input):
    return ujson.dumps(input, indent=4)


# Writes out a dict to json file
def jwrite(input, filename: str = None):
    if not filename:
        filename = 'dump.json'
    with open(filename, 'w') as f:
      ujson.dump(input, f, indent=4)


# Get the calling function's name and arguments for debugging
def func_args():
    caller = inspect.stack()
    args, _, _, values = inspect.getargvalues(caller[1][0])
    return (caller[2].code_context,[(i, values[i]) for i in args])


def call_rest(
    api_version : str, 
    resource: str = None, 
    scope: str = None, 
    verb: str = 'GET', 
    url: str = None, 
    verbosity : str = 'INFO', 
    ignore_errors: bool = True,
    silent: bool = False
    ):

    """
    :param resource:      e.g. 'Microsoft.Authorization/roleAssignmentScheduleInstances'
    :param scope:         The scope of the operation or resource. Valid scopes are: subscription (format: '/subscriptions/{subscriptionId}'), resource group (format: '/subscriptions/{subscriptionId}/resourceGroups/{resourceGroupName}', or resource (format: '/subscriptions/{subscriptionId}/resourceGroups/{resourceGroupName}/providers/{resourceProviderNamespace}/[{parentResourcePath}/]{resourceType}/{resourceName}'
    :param url:           instead of scope & resource, full request url can be provided (no need for 'https://management.azure.com' prefix)
    :param api_version:   e.g. '2020-10-01'
    :param ignore_errors: 'True' do not exit on failure (default)
    :param silent:        'False' do not print errors to stdout (default)
    :param verbosity:     can use 'VERBOSE' to print full request URLs for debugging
    :return               json data or full HTTPResponse on unsuccessful json conversion (fyi successful DELETE returns no json as well)

    for scoped requests the url format is https://management.azure.com{scope}/providers/{resource}?api-version={api_version}
    for not scoped https://management.azure.com/{resource}?api-version={api_version}
    """

    rest_api_prefix = 'https://management.azure.com'

    if 'access_token_rest' not in globals():
      global access_token_rest
      access_token_rest = auth(api_type='rest')

    if url is None:
        if "skiptoken" not in resource:
            request_url = f'{rest_api_prefix}/{resource}?api-version={api_version}'
            if scope:
                if scope[0] != '/':
                    scope = '/' + scope
                request_url = f'{rest_api_prefix}{scope}/providers/{resource}?api-version={api_version}'
        else:
            request_url = resource
    else:
        if rest_api_prefix not in url:
            request_url = rest_api_prefix + url
        else:
            request_url = url

    if verbosity == 'VERBOSE':
        f = func_args()
        print(f'\r\nfunc: {f[0]}\r\nargs: {f[1]}\r\nrequest URL: {request_url}\r\n')

    http = urllib3.PoolManager(
        retries=urllib3.Retry(3, redirect=2)
    )

    if silent:
        blockPrint()

    try:
        response = http.request(verb, request_url, headers={'Authorization': 'Bearer ' + access_token_rest})
    except urllib3.exceptions.NewConnectionError:
        print('Connection failed.')
        if not ignore_errors: 
          os._exit(-1)
    
    if silent:
        enablePrint()

    try:
        data = ujson.loads(response.data.decode('utf-8'))
    except ValueError:
        return response

    if verbosity == 'DEBUG':
        print(f'{func_args()}: {request_url}')
        jprint(data)

    if data.get('error'):
        print(f'Error in {request_url} called by {func_args()}')
        print(data.get('error').get('code'), data.get('error').get('message'))
        if not ignore_errors: 
          os._exit(-1)
        else:
          return data

    values = data.get('value')
    if values is not None:
        if data.get('nextLink'):
          values = values + call_rest(resource=data.get('nextLink'),api_version=api_version)
        return values
    else:
        return data



def call_graph(resource: str, verb: str = 'GET', api_version: str = 'v1.0', verbosity : str = 'INFO', filter: str = None, ignore_errors: bool = True):

    """
    :param resource:        e.g. 'users/principalId'
    :param filter           e.g. "startswith(displayName,'s')" /url encoding is automatic/
    :param ignore_errors:   'True' by default, does not exit on failure
    :param api_version:     'v1.0' by default
    :return                 list data or null & prints error to stdout 
    """

    if 'access_token_graph' not in globals():
      global access_token_graph
      access_token_graph = auth(api_type='graph')

    request_url = f'https://graph.microsoft.com/{api_version}/{resource}'
    if filter is not None:
        filter_urlencoded = urllib.parse.quote_plus(filter)
        request_url+= f'?$filter={filter_urlencoded}'

    if "skiptoken" in resource:
        request_url = resource

    if verbosity == 'VERBOSE':
        f = func_args()
        print(f'\r\nfunc: {f[0]}\r\nargs: {f[1]}\r\nrequest URL: {request_url}\r\n')

    http = urllib3.PoolManager(
        retries=urllib3.Retry(3, redirect=2)
    )

    try:
        response = http.request(verb, request_url, headers={'Authorization': 'Bearer ' + access_token_graph})
    except urllib3.exceptions.NewConnectionError:
        print('Connection failed.')
        if not ignore_errors: 
          os._exit(-1)

    data = ujson.loads(response.data.decode('utf-8'))

    if verbosity == 'DEBUG':
        print(f'{func_args()}: {request_url}')
        jprint(data)

    if data.get('error'):
        print(f'Error in {request_url} called by {func_args()}')
        print(data.get('error').get('code'), data.get('error').get('message'))
        if not ignore_errors: 
          os._exit(-1)  
        else:
          return data

    values = data.get('value')
    if values is not None:
        if data.get('@odata.nextLink'):        
          values = values + call_graph(resource=data.get('@odata.nextLink'))
        return values
    else:
        return data
    
    

