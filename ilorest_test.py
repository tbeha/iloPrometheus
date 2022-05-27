 # Copyright 2020 Hewlett Packard Enterprise Development LP
 #
 # Licensed under the Apache License, Version 2.0 (the "License"); you may
 # not use this file except in compliance with the License. You may obtain
 # a copy of the License at
 #
 #      http://www.apache.org/licenses/LICENSE-2.0
 #
 # Unless required by applicable law or agreed to in writing, software
 # distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
 # WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
 # License for the specific language governing permissions and limitations
 # under the License.

# -*- coding: utf-8 -*-
"""
An example of gathering the power metrics average on HPE iLO systems
"""

import sys
import json
from redfish import RedfishClient
from redfish.rest.v1 import ServerDownOrUnreachableError

def get_resource_directory(redfishobj):

    try:
        resource_uri = redfishobj.root.obj.Oem.Hpe.Links.ResourceDirectory['@odata.id']
    except KeyError:
        sys.stderr.write("Resource directory is only available on HPE servers.\n")
        return None

    response = redfishobj.get(resource_uri)
    resources = []

    if response.status == 200:
        sys.stdout.write("\tFound resource directory at /redfish/v1/resourcedirectory" + "\n\n")
        resources = response.dict["Instances"]
    else:
        sys.stderr.write("\tResource directory missing at /redfish/v1/resourcedirectory" + "\n")

    return resources


def get_server_data( uri, login_account, login_password):
    server_data={}

    try:
        # Create a Redfish client object
        REDFISHOBJ = RedfishClient(base_url=uri, username=login_account, password=login_password)
        # Login with the Redfish client
        REDFISHOBJ.login()
    except ServerDownOrUnreachableError as excp:
        sys.stderr.write("ERROR: server not reachable or does not support RedFish.\n")
        sys.exit()        
    
    resource_instances = get_resource_directory(REDFISHOBJ)
    for instance in resource_instances:
        if '#Power.' in instance ['@odata.type']:
            uri = REDFISHOBJ.get(instance['@odata.id']).obj.Oem.Hpe['Links']['PowerMeter']['@odata.id']
            server_data["PowerMeter"] = REDFISHOBJ.get(uri).obj
            """
            power_metrics_data = REDFISHOBJ.get(uri).obj
            server_data['Power_Average'] = power_metrics_data['Average']
            server_data['Power_Maximum'] = power_metrics_data['Maximum']
            server_data['Power_Minimum'] = power_metrics_data['Minimum']
            """
        if '#Thermal.' in instance ['@odata.type']:
            server_data['Temperatures'] = REDFISHOBJ.get(instance['@odata.id']).obj["Temperatures"]
            """
            for temperature in thermal_data:
                server_data[temperature['Name']] = { \
                    'ReadingCelsius':temperature['ReadingCelsius'],\
                    'Status':temperature['Status'],\
                    'UpperThresholdCritical':temperature["UpperThresholdCritical"],\
                    "UpperThresholdFatal":temperature["UpperThresholdFatal"] }
            """
        if '#ComputerSystem.' in instance ['@odata.type']:
            server_data['System'] = REDFISHOBJ.get(instance['@odata.id']).obj
            """
            system_data = REDFISHOBJ.get(instance['@odata.id']).obj
            server_data['Host_Name'] = system_data['HostName']}
            server_data['Manufacturer'] = system_data["Manufacturer"]
            server_data["Model"] = system_data["Model"]
            server_data["PowerState"] = system_data["PowerState"]
            server_data["SKU"] = system_data["SKU"]
            server_data["SerialNumber"] = system_data["SerialNumber"]
            server_data["Status"] = system_data["Status"]
            """


    REDFISHOBJ.logout()

    return server_data;

"""
def get_server_data( uri, login_account, login_password):
    server_data={}
    power_uri = "/redfish/v1/Chassis/1/Power/PowerMeter/"
    temperature_uri =  

    return server_data
"""

if __name__ == "__main__":
    # When running on the server locally use the following commented values
    #SYSTEM_URL = None
    #LOGIN_ACCOUNT = None
    #LOGIN_PASSWORD = None

    # When running remotely connect using the secured (https://) address,
    # account name, and password to send https requests
    # SYSTEM_URL acceptable examples:
    # "https://10.0.0.100"
    # "https://ilo.hostname"
    SYSTEM_URL = "https://10.1.40.7"
    LOGIN_ACCOUNT = "thomasb"
    LOGIN_PASSWORD = "We95sms!!"
    #logfile = 'ilo_resource_instances.log'
    #f = open(logfile,'w')

    # flag to force disable resource directory. Resource directory and associated operations are
    # intended for HPE servers.
    DISABLE_RESOURCE_DIR = False

    server_metrics = get_server_data(SYSTEM_URL, LOGIN_ACCOUNT, LOGIN_PASSWORD)
    print(json.dumps(server_metrics, indent=4, sort_keys=True))
   
    #f.close()
