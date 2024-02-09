# Dockerfile
FROM python:3
RUN apt-get -y update && apt-get -y install ffmpeg imagemagick procps
RUN apt-get -y install fonts-liberation
RUN pip install --upgrade pip
# Install some special fonts we use in testing, etc..

RUN apt-get install -y locales && \
    locale-gen C.UTF-8 && \
    /usr/sbin/update-locale LANG=C.UTF-8

ENV LC_ALL C.UTF-8
# modify ImageMagick policy file so that Textclips work correctly.
RUN sed -i 's/none/read,write/g' /etc/ImageMagick-6/policy.xml 

WORKDIR /home/app

COPY requirements.txt requirements.txt
COPY  . .
RUN pip install -r requirements.txt

WORKDIR /home/app/Backend
CMD ["python", "main.py"]
