FROM ubuntu:22.04

RUN apt-get update && apt-get install --no-install-recommends -y python3.11 \
    python3-dev python3-pip build-essential \
    autoconf pkg-config wget ghostscript

RUN apt-get update && apt-get install -y wget && \
    apt-get install -y build-essential curl libpng-dev && \
    wget https://github.com/ImageMagick/ImageMagick/archive/refs/tags/7.1.0-31.tar.gz && \
    tar xzf 7.1.0-31.tar.gz && \
    rm 7.1.0-31.tar.gz && \
    apt-get clean && \
    apt-get autoremove

RUN sh ./ImageMagick-7.1.0-31/configure --prefix=/usr/local --with-bzlib=yes --with-fontconfig=yes --with-freetype=yes --with-gslib=yes --with-gvc=yes --with-jpeg=yes --with-jp2=yes --with-png=yes --with-tiff=yes --with-xml=yes --with-gs-font-dir=yes && \
    make -j && make install && ldconfig /usr/local/lib/

WORKDIR /tmp


RUN pip install --upgrade pip

WORKDIR /app

ADD ./requirements.txt .
RUN pip install -r requirements.txt

ADD ./Backend ./backend
ADD ./Frontend ./frontend
ADD ./fonts ./fonts