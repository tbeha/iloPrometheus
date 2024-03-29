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
 #
 # v2.1 - August 2022; Thomas Beha, HPE Technology Competence Center DACH
 #        added the temperature state = enabled filter
 # v3  -  August 2022, Thomas Beha, HPE Technology Competence Center DACH
 #        added Rack Location
 # v3.1 - October 2022; Thomas Beha, HPE Technology Competence Center DACH
 #        Minor Bug fixes
 #

# -*- coding: utf-8 -*-
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

def get_resource_directory(redfishobj, lfile):

    try:
        resource_uri = redfishobj.root.obj.Oem.Hpe.Links.ResourceDirectory['@odata.id']
        response = redfishobj.get(resource_uri)
        return response.dict["Instances"]
    except KeyError as ex:
        sys.stderr.write("Resource directory is only available on HPE servers.\n")
        log=logopen(lfile)
        logwriter(log,'Exception')
        logwriter(log,str(ex))
        logclose(log)
        return None


def get_server_urls( login_account, login_password, server, lfile):

    server_urls={}

    for s in server:
        ilo_url="https://"+s['ilo']
        s["url"]=ilo_url
        try:
            # Create a Redfish client object
            REDFISHOBJ = RedfishClient(base_url=ilo_url, username=login_account, password=login_password)
            # Login with the Redfish client
            REDFISHOBJ.login()
            s["redfish"]=REDFISHOBJ
            resource_instances = get_resource_directory(REDFISHOBJ, lfile)
            for instance in resource_instances:
                if '#ComputerSystem.' in instance ['@odata.type']:
                    s["ComputerSystem"]=instance['@odata.id'] 
                if '#Power.' in instance ['@odata.type']:
                    s["Power"]=instance['@odata.id'] 
                if '#Thermal.' in instance ['@odata.type']:
                    s["Thermal"]=instance['@odata.id']
            if len(s) > 4:
                server_urls[s['ilo']]=s
        except Exception as ex:
            log=logopen(lfile)
            logwriter(log,'Exception - get_server_urls: '+s['ilo'])
            logwriter(log,str(ex.__context__))
            logclose(log)
            if len(s) > 4:
                server_urls[s['ilo']]=s
            pass
    return server_urls;

def get_server_data( login_account, login_password, server, lfile):

    server_data={}
    try:
        REDFISHOBJ = server["redfish"]
        # System Data
        server_data['System'] = REDFISHOBJ.get(server["ComputerSystem"]).obj
        # Power Data
        uri = REDFISHOBJ.get(server["Power"]).obj.Oem.Hpe['Links']['PowerMeter']['@odata.id']
        server_data["PowerMeter"] = REDFISHOBJ.get(uri).obj
        # Temperatures
        server_data['Temperatures'] = REDFISHOBJ.get(server["Thermal"]).obj["Temperatures"]
        return server_data;
    
    except Exception as ex:
        sys.stderr.write("ERROR during get_server_date: "+server["url"])
        if ex.status == 401:
            REDFISHOBJ = RedfishClient(base_url=server["url"], username=login_account, password=login_password)
            REDFISHOBJ.login()
            server["redfish"] = REDFISHOBJ
        log=logopen(lfile)
        logwriter(log,'Exception')
        logwriter(log,str(ex.__context__))
        logclose(log)        
        pass

def display_results( node, inode, server_metrics, server):
    hostname = (server_metrics['System']['HostName']).split('.')[0].replace('-','_')
    cn = server['ilo']
    inode.labels(cn).info({"Model":server_metrics['System']["Model"],"Manufacturer":server_metrics['System']["Manufacturer"],"SerialNumber":server_metrics['System']["SerialNumber"],"Hostname":hostname})
    node.labels(cn,server['Rack'],'Power','State').set(power_state[server_metrics['System']["PowerState"]]) 
    node.labels(cn,server['Rack'],'Power','Average').set(server_metrics["PowerMeter"]['Average'])           
    node.labels(cn,server['Rack'],'Power','Maximum').set(server_metrics["PowerMeter"]['Maximum'])
    node.labels(cn,server['Rack'],'Power','Minimum').set(server_metrics["PowerMeter"]['Minimum'])
    for temperature in server_metrics['Temperatures']:
        if temperature['Status']['State'] == 'Enabled': 
            node.labels(cn,server['Rack'],'Temperature',temperature["Name"]).set(temperature['ReadingCelsius'])
    return 0

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
    lfile=path+(tree.find("logfile")).text
    port=int((tree.find("port")).text)
    mintervall = int((tree.find("monitoringintervall")).text) 
    #sx=tree.findall("server")  # List of all server
    server=[]
    for s in tree.findall("server"):
        server.append({"ilo":s.find("ILO_ip").text,"Rack":s.find("Rack").text,"Loc":s.find("Loc").text})

    # Get the monitoring URLs of the server
    monitor_urls = get_server_urls(user, password, server, lfile)

    # open the logfile
    log=logopen(lfile)
    logwriter(log,"Started ILO Prometheus Connector Test")
    
    # Start the http_server and the counters, gauges
    start_http_server(port)
    c = Counter('ilorest_sample','ILO REST sample number')
    node = Gauge('ilorest_node','ILO Node Data',['nodename','rack','nodemetric','metricdetail'])
    delta = Gauge('ConnectorRuntime','Time required for last data collection in seconds')
    inode = Info('node','Additional Node Info',['node'])

    # Start the endless loop
    while True:
        try:
            t0 = time.time()         
            c.inc()
            for server in monitor_urls:
                server_metrics = get_server_data(user, password, monitor_urls[server], lfile)
                display_results(node, inode, server_metrics, monitor_urls[server])
            t1 = time.time()
            delta.set((t1-t0))
            while ((t1-t0) < mintervall):
                time.sleep(1.0)
                t1 = time.time()    

        except Exception as ex:
            log=logopen(lfile)
            logwriter(log,'Exception')
            logwriter(log,str(ex.__context__))
            logclose(log)
            pass       