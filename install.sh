#!/bin/bash
if [ -e /etc/redhat-release ]; then
  yum install -y epel-release
  yum install -y autoconf automake curl gcc libffi-devel libtool make python-devel python-pip ssdeep-devel tar
fi

if [ -e /etc/debian_version ]; then
  apt-get update
  apt-get install -y build-essential curl dh-autoreconf gcc libffi-dev libfuzzy-dev python-dev python-pip
fi

if [[ $(python -V 2>&1) == Python\ 2* ]]; then
  pip install -r requirements2.txt
fi

if [[ $(python -V 2>&1) == Python\ 3* ]]; then
  pip install -r requirements3.txt
fi

CWD=`pwd`
read -p "Compile yara 3.4.0? <y/N> " prompt
if [[ $prompt == "y" ]]; then
  cd /tmp
  curl -L https://github.com/plusvic/yara/archive/v3.4.0.tar.gz | tar -xz
  cd yara-3.4.0
  ./bootstrap.sh
  ./configure --prefix=/usr
  make && make install
  cd yara-python
  python setup.py install
  cd ../../
  rm -rf yara-3.4.0
  ln -s /usr/lib/libyara.so.3 /lib64/libyara.so.3
  cd "$CWD"
fi