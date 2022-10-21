# ILO Redfish Connector for Prometheus

A Prometheus connector for HPE ILO interface that will expose the power consumption and temperature metrics of the monitored systems. 

The ILO Redfish API (https://developer.hpe.com/platform/ilo-restful-api/home/) provides access to HPE ILO 4 and ILO 5 interfaces to manage the complete lifecylce of HPE Gen9 and Gen10 server. A complete API reference documentation is available at https://hewlettpackard.github.io/ilo-rest-api-docs/ilo5/. 

The ILO Redfish connector is a Python script that utilizes the HPE ILO Redfish Python library (https://github.com/HewlettPackard/python-ilorest-library) and the Prometheus Python Client (https://github.com/prometheus/client_python). 

![image](https://user-images.githubusercontent.com/38065422/173775970-f06eecd1-4932-4a0b-9c20-4f4f43a2e4fd.png)


## Content:

| File          | Description                     |
|---------------|-------------------------------|
| [iloPromConnector.v1.0.py](https://github.com/tbeha/iloPrometheus/blob/main/iloPromConnector.v1.0.py) | ILO Redfish Connector for Prometheus Python script |
| [createILOcredentials.v1.0.py](https://github.com/tbeha/iloPrometheus/blob/main/createILOcredentials.v1.0.py) | Python script to create the Kubernetes configmap (<Name>.yml), the encryption key file (<Name>.key) and the configuration parameter file (<Name>.xml). |
| README.md  | This readme file |
| [License](https://github.com/tbeha/iloPrometheus/blob/main/LICENSE)    | GPL-3.0 license |
| __JupyterNotebooks__ | Example Jupyter Notebooks  |
| [JupyterNotebooks/ILO-Redfish.ipynb](https://github.com/tbeha/iloPrometheus/blob/main/JupyterNotebooks/ILO-Redfish.ipynb)  | Jupyter Notebook example for a Kubernetes pod deployment of the ILO Redfish Connector for Prometheus |
| [JupyterNoteboosk/iloprometheus.Dockerfile](https://github.com/tbeha/iloPrometheus/blob/main/JupyterNotebooks/iloprometheus.Dockerfile) | Dockerfile to build a ILO Redfish Connector for Prometheus container image |
| __GrafanaDashboards__ | Grafana Dashboard Examples |
  | [GrafanaDashboards/Power Consumption-1655219362362.json](https://github.com/tbeha/iloPrometheus/blob/main/GrafanaDashboards/Power%20Consumption-1655219362362.json) | Power consumption dashboard |
  | [GrafanaDashboards/Temperature Overview-1655219338454.json](https://github.com/tbeha/iloPrometheus/blob/main/GrafanaDashboards/Temperature%20Details-1655219598166.json) | Temperature overview dashboard |
  | [GrafanaDashboards/Temperature Details-1655219598166.json](https://github.com/tbeha/iloPrometheus/blob/main/GrafanaDashboards/Temperature%20Overview-1655219338454.json)  | Temperature details dashboard |

