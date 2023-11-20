 # Copyright 2023 Hewlett Packard Enterprise Development LP
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
 # v3.2 - May 2023, Thomas Beha, HPE Technology Competence Center DACH
 #        Changes in the program flow, to better handle removed server
 # v4.0 - October 2023, Thomas Beha, HPE Technology Competence Center DACH
 #        Data Collector writing the data into Redis Lists
 #        A second data analyzer component will publish the data to Prometheus

# -*- coding: utf-8 -*-
from cryptography.fernet import *
from lxml import etree 
import time
from datetime import datetime
from prometheus_client import Counter, Gauge, start_http_server, Info
import sys
import redfish

LINUX=False

if LINUX:
    import os
else:
    from icmplib import ping


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
        resource_uri = redfishobj.root['@odata.id']+'ResourceDirectory/'
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
    if LINUX:
        cmd='ping -c 2 '
    log=logopen(lfile)
    logwriter(log,'get_server_urls')
    for s in server:
        ilo_url="https://"+s['ilo']
        s["url"]=ilo_url
        if LINUX:
            response=os.system(cmd+s['ilo'])   # works on Linux without root priviliges
        else:
            response = ping(address=s['ilo'],count=1)  # requires root priviliges on Linux
            if(response.is_alive):
                response = 0
            else:
                response = 256
        if (response == 0):        
            try:
                # Create a Redfish client object
                REDFISHOBJ = redfish.redfish_client(base_url=ilo_url, username=login_account, password=login_password)  
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
                    logwriter(log,s['ilo']+' completed')
            except Exception as ex:
                logwriter(log,'Exception - get_server_urls: '+s['ilo'])
                logwriter(log,str(ex.__context__))
                if len(s) > 4:
                    server_urls[s['ilo']]=s
                pass
        else:
            logwriter(log,'Exception - ILO is not reachable: '+s['ilo'])
    logclose(log)
    return server_urls

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
            REDFISHOBJ = redfish.redfish_client(base_url=server["url"], username=login_account, password=login_password)
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

def getServerList():
    result={}
    """ read the key and input file"""
    if(LINUX):
        path = '/opt/prometheus/data'
    else:
        path = '.'
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
    result['user'] = f.decrypt(u2.encode('ASCII')).decode('ASCII')
    result['password'] = f.decrypt(p2.encode('ASCII')).decode('ASCII')
    result['lfile'] =path+(tree.find("logfile")).text
    result['port'] =int((tree.find("port")).text)
    result['mintervall'] = int((tree.find("monitoringintervall")).text) 
    #sx=tree.findall("server")  # List of all server
    server=[]
    for s in tree.findall("server"):
        server.append({"ilo":s.find("ILO_ip").text,"Rack":s.find("Rack").text,"Loc":s.find("Loc").text})
    result['server'] = server
    return result

if __name__ == "__main__":

    input = getServerList()    

    # Get the monitoring URLs of the server
    monitor_urls = get_server_urls(input['user'], input['password'], input['server'], input['lfile'])

    # open the logfile
    log=logopen(input['lfile'])
    logwriter(log,"Started ILO Prometheus Connector Test")
    logclose(log)

    # Start the http_server and the counters, gauges
    start_http_server(input['port'])
    c = Counter('ilorest_sample','ILO REST sample number')
    node = Gauge('ilorest_node','ILO Node Data',['nodename','rack','nodemetric','metricdetail'])
    delta = Gauge('ConnectorRuntime','Time required for last data collection in seconds')
    inode = Info('node','Additional Node Info',['node'])

    # Start the endless loop
    log=logopen(input['lfile'])
    logwriter(log,"Start Loop")
    logclose(log)   
    while True: 
        t0 = time.time()
        start0 = t0
        c.inc()      
        for server in monitor_urls:
            try:
                server_metrics = get_server_data(input['user'], input['password'], monitor_urls[server], input['lfile'])
                display_results(node, inode, server_metrics, monitor_urls[server])
            except Exception as ex:
                log=logopen(input['lfile'])
                logwriter(log,'Exception')
                logwriter(log,str(ex.__context__))
                logclose(log)
                pass
        t1 = time.time()
        delta.set((t1-t0))
        while ((t1-t0) < input['mintervall']):
            time.sleep(1.0)
            t1 = time.time()   
        # update once per day the input
        if ( t1 - start0 > 42200):
            start0 = t1
            input = getServerList() 
            monitor_urls = get_server_urls(input['user'], input['password'], input['server'], input['lfile'])
            log=logopen(input['lfile'])
            logwriter(log,'Updated Monitor URL List')
            logclose(log)