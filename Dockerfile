FROM ubuntu:artful

RUN apt-get update && apt-get install -y python3 python3-pip python-setuptools apache2 ssh
RUN service apache2 start && service ssh start

ENV JAVA_HOME /usr/lib/jvm/java-8-openjdk-amd64

ADD . /service-scout
WORKDIR /service-scout

RUN python3 setup.py install

CMD service apache2 start && \
    service ssh start && \
    service-scout