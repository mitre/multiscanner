#!/bin/bash
#This script attempts to install the required packages for MultiScanner and its modules

CWD=`pwd`
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

#Install requirements for Redhat derivatives
if [ -e /etc/redhat-release ]; then
  yum install -y epel-release
  yum install -y autoconf automake curl gcc libffi-devel libtool make python-devel python-pip ssdeep-devel tar git
fi

#Install requirements for Debian derivatives
if [ -e /etc/debian_version ]; then
  apt-get update
  apt-get install -y build-essential curl dh-autoreconf gcc libffi-dev libfuzzy-dev python-dev python-pip git
fi

#Install requirements for Python 2.x
if [[ $(python -V 2>&1) == Python\ 2* ]]; then
  pip install -r $DIR/requirements2.txt
fi

#Install requirements for Python 3.x
if [[ $(python -V 2>&1) == Python\ 3* ]]; then
  pip install -r $DIR/requirements3.txt
fi

#Code to compile and install yara
read -p "Compile yara 3.5.0? <y/N> " prompt
if [[ $prompt == "y" ]]; then
  cd /tmp
  curl -L https://github.com/VirusTotal/yara/archive/v3.5.0.tar.gz | tar -xz
  cd yara-3.5.0
  ./bootstrap.sh
  ./configure --prefix=/usr
  make && make install
  cd yara-python
  python setup.py install
  cd ../../
  rm -rf yara-3.5.0
  ln -s /usr/lib/libyara.so.3 /lib64/libyara.so.3
  cd "$CWD"
fi


read -p "Download yararules.com signatures? <y/N> " prompt
if [[ $prompt == "y" ]]; then
  git clone --depth 1 https://github.com/Yara-Rules/rules.git $DIR/etc/yarasigs/Yara-Rules
  echo You can update these signatures by running cd $DIR/etc/yarasigs/Yara-Rules \&\& git pull
fi
