import azapi

# apps = azapi.call_graph(resource='applications', filter="startswith(displayName,'s')")

vnet_result = azapi.call_rest(
    verb = 'GET',
    scope=f'/subscriptions/<subscriptionId>/resourceGroups/rg-testnets', 
    resource = f'Microsoft.Network/virtualNetworks/vnet-removnet', 
    api_version='2022-07-01'
)



getuser = azapi.call_graph(resource='users/<objectId>')

subs = azapi.call_rest(resource='subscriptions', api_version = '2022-09-01')

rest_paging_test = azapi.call_rest(
    resource = 'Microsoft.Authorization/policyDefinitions ',
    scope='subscriptions/<subscriptionId>',
    api_version = '2021-06-01'
    )

print(":")