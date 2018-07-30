#!/bin/bash

set -e -o pipefail

# Intended for Ubuntu 18.04. Functionality on other flavors of Ubuntu/Debian not assured.

# This script can accept one arguments:

# $1: the user for which the settings should be changed
#     If this argument is not specified, $(whoami) will be used

# Note that these settings are per-user! This script will need to be run for each user.
# Settings for the user 'gdm' will impact the behavior when at the login screen.
# When changing settings via remote tty, dbus-launch must be called since such sessions
# are not normally attached to the dbus

# If this is Ubuntu Desktop we have gnome available to control power settings
# gsettings comes with gnome, so we can check if it exists...


if hash gsettings 2>/dev/null; then
    if [[ ! -z $1 ]]; then
        USER_TO_CHANGE=$1
    else
        USER_TO_CHANGE=$(whoami)
    fi

    sudo -H -u $USER_TO_CHANGE dbus-launch --exit-with-session gsettings set org.gnome.desktop.peripherals.mouse natural-scroll false
    sudo -H -u $USER_TO_CHANGE dbus-launch --exit-with-session gsettings set org.gnome.desktop.peripherals.touchpad natural-scroll false

else
   echo "Configuring user GUI settings not yet supported in this script for Ubuntu server."
   echo "Requires changing other files such as /etc/systemd/logind.conf"
fi