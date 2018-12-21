#!/bin/bash
#This script attempts to install the required packages for MultiScanner and its modules

CWD=`pwd`
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

#Install requirements for Redhat derivatives
#Keep these in sync with .travis.yml
if [ -e /etc/redhat-release ]; then
  yum install -y epel-release
  yum install -y autoconf automake curl gcc libffi-devel libtool make python-devel ssdeep-devel tar git unzip openssl-devel file-devel
fi

#Install requirements for Debian derivatives
#Keep these in sync with .travis.yml
if [ -e /etc/debian_version ]; then
  apt-get update
  apt-get install -y build-essential curl dh-autoreconf gcc libffi-dev libfuzzy-dev python-dev git libssl-dev unzip libmagic-dev
fi

# Install multiscanner library and dependencies
curl -k https://bootstrap.pypa.io/get-pip.py | python
pip install --upgrade $DIR

#Code to compile and install yara
YARA_VER=3.8.1
YARA_PY_VER=3.8.1
JANSSON_VER=2.11
read -p "Compile yara $YARA_VER? <y/N> " prompt
if [[ $prompt == "y" ]]; then
  #Because apparently the one in the repos does not work...
  curl -L https://github.com/akheron/jansson/archive/v$JANSSON_VER.tar.gz | tar -xz
  cd jansson-$JANSSON_VER
  autoreconf -fi
  ./configure --prefix=/usr
  make install
  cd ..
  rm -rf jansson-$JANSSON_VER
  ln -s /usr/lib/libjansson.so.4 /lib64/libjansson.so.4
  #We get yara-python as well
  # git clone -b v$YARA_VER https://github.com/VirusTotal/yara-python.git
  curl -L https://github.com/VirusTotal/yara-python/archive/v$YARA_PY_VER.tar.gz | tar -xz
  cd yara-python-$YARA_PY_VER
  # git clone -b v$YARA_VER https://github.com/VirusTotal/yara.git
  curl -L https://github.com/VirusTotal/yara/archive/v$YARA_VER.tar.gz | tar -xz
  cd yara-$YARA_VER
  # TEMPORARY work around for yara/libtool/centos7 issue
  # Add AC_CONFIG_AUX_DIR to configure.ac if not already there
  grep -q -F 'AC_CONFIG_AUX_DIR([build-aux])' configure.ac || sed -i'' -e 's/AM_INIT_AUTOMAKE/AC_CONFIG_AUX_DIR([build-aux])\
\
AM_INIT_AUTOMAKE/g' configure.ac
  ./bootstrap.sh
  ./configure --prefix=/usr --enable-magic --enable-cuckoo --enable-dotnet --with-crypto
  make && make install
  cd ../
  python setup.py build --dynamic-linking
  python setup.py install
  cd ../
  rm -rf yara-python-$YARA_PY_VER
  ln -s /usr/lib/libyara.so.3 /lib64/libyara.so.3
fi

read -p "Download yararules.com signatures? <y/N> " prompt
if [[ $prompt == "y" ]]; then
  git clone --depth 1 https://github.com/Yara-Rules/rules.git ~/.multiscanner/yarasigs/Yara-Rules
  echo You can update these signatures by running cd ~/.multiscanner/yarasigs/Yara-Rules \&\& git pull
fi

read -p "Download SupportIntelligence's Icewater yara signatures? <y/N> " prompt
if [[ $prompt == "y" ]]; then
  git clone --depth 1 https://github.com/SupportIntelligence/Icewater.git ~/.multiscanner/yarasigs/Icewater
  echo You can update these signatures by running cd ~/.multiscanner/yarasigs/Icewater \&\& git pull
fi

read -p "Download TrID? <y/N> " prompt
if [[ $prompt == "y" ]]; then
  mkdir -p /opt/trid
  cd /opt/trid
  curl -f --retry 3 http://mark0.net/download/trid_linux_64.zip > trid.zip
  if [[ $? -ne 0 ]]; then
    echo -e "\nFAILED\nTrying alternative mirror ..."
    curl -f --retry 3 https://web.archive.org/web/20170711171339/http://mark0.net/download/trid_linux_64.zip > trid.zip
  fi
  unzip trid.zip
  rm -f trid.zip
  curl -f --retry 3 http://mark0.net/download/triddefs.zip > triddefs.zip
  if [[ $? -ne 0 ]]; then
    echo -e "\nFAILED\nTrying alternative mirror ..."
    curl -f --retry 3 https://web.archive.org/web/20170827141200/http://mark0.net/download/triddefs.zip > triddefs.zip
  fi
  unzip triddefs.zip
  rm -f triddefs.zip
  chmod 755 trid
  cd $CWD
fi

read -p "Download FLOSS? <y/N> " prompt
if [[ $prompt == "y" ]]; then
  curl -f --retry 3 https://s3.amazonaws.com/build-artifacts.floss.flare.fireeye.com/travis/linux/dist/floss > /opt/floss
  chmod 755 /opt/floss
fi

read -p "Download NSRL database? This will take ~4GB of disk space. <y/N> " prompt
if [[ $prompt == "y" ]]; then
  # Download the unique set
  mkdir ~/.multiscanner/nsrl
  curl -k https://s3.amazonaws.com/rds.nsrl.nist.gov/RDS/current/rds_modernu.zip > rds_modernu.zip
  unzip rds_modernu.zip
  rm rds_modernu.zip
  python $DIR/multiscanner/utils/nsrl_parse.py -o ~/.multiscanner/nsrl RDS_*/NSRLFile.txt
  rm -fr RDS_*
fi

# Initialize multiscanner
multiscanner init
