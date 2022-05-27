# -*- coding: utf-8 -*-
"""
Created on May 1 2022

@author: Thomas Beha
"""

from cryptography.fernet import Fernet
import getpass
from lxml import etree 

uname = input("Username: ")
password = getpass.getpass()
logfile = input("Logfile: ")
port = input("Connector Port: ")
fname = input("Filename: ")
mintervall = input("Monitoringintervall: ")

keyfile=fname+'.key'
xmlfile=fname+'.xml'
key = Fernet.generate_key()
k1 = key.decode('ASCII')
f = open(keyfile,'w')
f.write(key.decode('ASCII'))
f.close()

f = Fernet(key)
token = f.encrypt(password.encode('ASCII'))
user = f.encrypt(uname.encode('ASCII'))

root = etree.Element("data")
etree.SubElement(root,"username").text=uname
etree.SubElement(root,"user").text=user
etree.SubElement(root,"password").text=token
etree.SubElement(root,"logfile").text=logfile
etree.SubElement(root,"port").text=port
etree.SubElement(root,"monitoringintervall").text=mintervall

print("Enter the ILO IP addresses - stop by entering: 0 as the IP address")
ilo_ip = input("ILO IP Address: ")
while ilo_ip != "0":
    etree.SubElement(root,"ILO_ip").text = ilo_ip
    ilo_ip = input("ILO IP Address: ")

xmloutput = etree.tostring(root, pretty_print=True)
f = open(xmlfile,'w')
f.write(xmloutput.decode('ASCII'))
f.close()

""" Test the keys """ 
""" Read keyfile """
f = open(keyfile, 'r')
k2=f.readline()
f.close()
key2=k2.encode('ASCII')

""" Parse XML File """

tree = etree.parse(xmlfile)
u2=(tree.find("user")).text
p2=(tree.find("password")).text


f = Fernet(key2)
user = f.decrypt(u2.encode('ASCII')).decode('ASCII')
password = f.decrypt(p2.encode('ASCII')).decode('ASCII')
print(user,password)