FROM alpine
MAINTAINER Patrick Copeland ptcnop

ENV YARA_VERSION 3.8.1
ENV YARA_PY_VERSION 3.8.1
ENV SSDEEP ssdeep-2.13

COPY requirements.txt /opt/multiscanner/

RUN apk add --no-cache \
        bash \
        bison \
        file \
        jansson \
        jpeg \
        libffi \
        python3 \
        su-exec \
        tini \
        zip \
        zlib \
  && apk add --no-cache -t .build-deps \
       autoconf \
       automake \
       build-base \
       file-dev \
       flex \
       git \
       jansson-dev \
       jpeg-dev \
       libc-dev \
       libffi-dev \
       libtool \
       musl-dev \
       postgresql-dev \
       py3-pip \
       python3-dev \
       zlib-dev \
  # ssdeep
  && echo "Install ssdeep from source..." \
  && cd /tmp \
  && wget -O /tmp/$SSDEEP.tar.gz https://downloads.sourceforge.net/project/ssdeep/$SSDEEP/$SSDEEP.tar.gz \
  && tar zxvf $SSDEEP.tar.gz \
  && cd $SSDEEP \
  && ./configure \
  && make \
  && make install \
  # yara
  && echo "Install Yara from source..." \
  && cd /tmp/ \
  && git clone --recursive --branch v$YARA_VERSION https://github.com/VirusTotal/yara.git \
  && cd /tmp/yara \
  && ./bootstrap.sh \
  && sync \
  && ./configure --with-crypto \
  --enable-magic \
  --enable-cuckoo \
  --enable-dotnet \
  && make \
  && make install \
  && echo "Install yara-python..." \
  && cd /tmp/ \
  && git clone --recursive --branch v$YARA_PY_VERSION https://github.com/VirusTotal/yara-python \
  && cd yara-python \
  && python3 setup.py build --dynamic-linking \
  && python3 setup.py install \
  && echo "Downloading yara signatures..." \
  && git clone --depth 1 https://github.com/Yara-Rules/rules.git /opt/multiscanner/etc/yarasigs/Yara-Rules \
  # install ms dependencies
  && cd /opt/multiscanner \
  && pip3 install --upgrade pip \
  && pip3 install -r requirements.txt \
  # clean up
  && rm -rf /tmp/* \
  && apk del --purge .build-deps

COPY . /opt/multiscanner
COPY ./docker_utils/*.ini /opt/multiscanner/
COPY ./etc/pdf_config.json /opt/multiscanner/
COPY ./etc/ember_model_2017.txt /opt/multiscanner/etc/ember/

WORKDIR /opt/multiscanner

RUN pip3 install .

RUN wget https://raw.githubusercontent.com/vishnubob/wait-for-it/master/wait-for-it.sh -O /wait-for-it.sh \
  && chmod +x /wait-for-it.sh

# Run script
CMD multiscanner
