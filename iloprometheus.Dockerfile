# User Ubuntu as the base Image
FROM ubuntu
#
LABEL maintainer="Thomas Beha"
LABEL version="4.0"
LABEL copyright="Thomas Beha, 2023"
LABEL license="GNU General Public License v3"
LABEL DESCRIPTION="CTC ILO Redfish Prometheus Connector Python container based on Ubuntu"
#
RUN apt-get update
RUN apt-get -y install python3.6 && \
	apt-get -y install python3-pip
RUN /usr/bin/pip3 install requests && \
	/usr/bin/pip3 install fernet && \
	/usr/bin/pip3 install cryptography && \
	/usr/bin/pip3 install lxml && \
	/usr/bin/pip3 install python-ilorest-library && \
	/usr/bin/pip3 install prometheus_client && \
	/usr/bin/pip3 install icmplib
# copy the necessary python files to the container
RUN mkdir /opt/prometheus
COPY ./iloPromConnector.v4.0.py /opt/prometheus

