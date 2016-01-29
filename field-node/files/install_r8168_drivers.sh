#!/bin/bash

set -e -o pipefail

DRIVER_PACKAGE_STRING="r8168-8.041.01"

wget http://12244.wpc.azureedge.net/8012244/drivers/rtdrivers/cn/nic/0004-$DRIVER_PACKAGE_STRING.tar.bz2 -O $DRIVER_PACKAGE_STRING.tar.bz2
tar vjxf $DRIVER_PACKAGE_STRING.tar.bz2
cd $DRIVER_PACKAGE_STRING
./autorun.sh
cd ../
rm -rf ./$DRIVER_PACKAGE_STRING*