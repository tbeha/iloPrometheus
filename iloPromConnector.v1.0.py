# -*- coding: utf-8 -*-
"""
Created on July 22, 2020
Version 4.1
Used for a Kubernetes deployment with configmaps instead of runtime arguments.

Copyright (c) 2020 Thomas Beha

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.
    https://www.gnu.org/licenses/gpl-3.0.en.html 

    This release of the Prometheus Connector requires: SimpliVityClass v4.0

"""

from cryptography.fernet import *
from lxml import etree 
import time
from datetime import datetime
from prometheus_client import Counter, Gauge, start_http_server, Info
import sys
from redfish import RedfishClient
from redfish.rest.v1 import ServerDownOrUnreachableError

BtoGB=pow(1024,3)
BtoMB=pow(1024,2)

power_state={
    'Unknown': 0,
    'On': 1,
    'Off': 2,
    'Suspended': 3
}

def logwriter(f, text):
        output=str(datetime.today()) +": "+text+" \n"
        print(output)
        f.write(output)
    
def logopen(filename):
        f = open(filename,'a')
        f.write(str(datetime.today())+": Logfile opened \n")
        return f

def logclose(f):
        f.write(str(datetime.today())+": Logfile closed \n")
        f.close()

def get_resource_directory(redfishobj):

    try:
        resource_uri = redfishobj.root.obj.Oem.Hpe.Links.ResourceDirectory['@odata.id']
    except KeyError:
        sys.stderr.write("Resource directory is only available on HPE servers.\n")
        return None

    response = redfishobj.get(resource_uri)
    resources = []

    if response.status == 200:
        #sys.stdout.write("\tFound resource directory at /redfish/v1/resourcedirectory" + "\n\n")
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
        if '#Thermal.' in instance ['@odata.type']:
            server_data['Temperatures'] = REDFISHOBJ.get(instance['@odata.id']).obj["Temperatures"]
        if '#ComputerSystem.' in instance ['@odata.type']:
            server_data['System'] = REDFISHOBJ.get(instance['@odata.id']).obj



    REDFISHOBJ.logout()

    return server_data;

### Main ###########################################################################

if __name__ == "__main__":
    
    """ read the key and input file""" 

    path = '.'
    #path = '/opt/prometheus/data' 
    keyfile = path + '/iloprometheus.key'  
    xmlfile = path + '/iloprometheus.xml'

    """ Read keyfile """
    f = open(keyfile, 'r')
    k2=f.readline()
    f.close()
    key2=k2.encode('ASCII')

    """ Read the parameter file """
    tree = etree.parse(xmlfile)
    u2=(tree.find("user")).text
    p2=(tree.find("password")).text
    f = Fernet(key2)
    user = f.decrypt(u2.encode('ASCII')).decode('ASCII')
    password = f.decrypt(p2.encode('ASCII')).decode('ASCII')
    lfile=(tree.find("logfile")).text
    port=int((tree.find("port")).text)
    mintervall = int((tree.find("monitoringintervall")).text) 
    ilos=tree.findall("ILO_ip")  # List of all ILOs


    log=logopen(path+lfile)
    logwriter(log,"Started ILO Prometheus Connector Test")
    
    start_http_server(port)
    c = Counter('ilorest_sample','ILO REST sample number')
    node = Gauge('ilorest_node','ILO Node Data',['nodename','nodemetric','metricdetail'])
    delta = Gauge('ConnectorRuntime','Time required for last data collection in seconds')
    #icon = Info('Connector','Connector Paramter Info')
    inode = Info('node','Additional Node Info',['node'])
    mintervall = 60

    while True:
        try:
            t0 = time.time()         
            c.inc()
            for ilo in ilos:
                ilo_url="https://"+ilo.text
                server_metrics = get_server_data(ilo_url, user, password)
                cn = (server_metrics['System']['HostName']).split('.')[0].replace('-','_')
                inode.labels(cn).info({"Model":server_metrics['System']["Model"],"Manufacturer":server_metrics['System']["Manufacturer"],"SerialNumber":server_metrics['System']["SerialNumber"]})
                node.labels(cn,'Power','State').set(power_state[server_metrics['System']["PowerState"]]) 
                node.labels(cn,'Power','Average').set(server_metrics["PowerMeter"]['Average'])           
                node.labels(cn,'Power','Maximum').set(server_metrics["PowerMeter"]['Maximum'])
                node.labels(cn,'Power','Minimum').set(server_metrics["PowerMeter"]['Minimum'])
                for temperature in server_metrics['Temperatures']:
                    node.labels(cn,'Temperature',temperature["Name"]).set(temperature['ReadingCelsius'])
            t1 = time.time()
            delta.set((t1-t0))
            while ((t1-t0) < mintervall):
                time.sleep(1.0)
                t1 = time.time()    

        except Exception as ex:
            print(ex)
            log=logopen(path+lfile)
            logwriter(log,'Exception')
            logwriter(log,str(ex))
            logclose(log)
            pass
