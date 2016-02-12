#!/bin/bash

set -e -o pipefail

# Intended for Ubuntu 15.10. Functionality on other flavors of Ubuntu/Debian not assured.

# This script can accept two arguments:

# $1: defines the path to the hibernation policy file.
#     If the path is set and the file exists, hibernate on critical battery will be enabled.
#     Otherwise the machine will shut down on when the battery level is critically low.

# $2: the user for which the settings should be changed
#     If this argument is not specified, $(whoami) will be used

# Note that these settings are per-user! This script will need to be run for each user.
# Settings for the user 'lightdm' will impact the behavior when at the login screen.
# When changing settings via remote tty, dbus-launch must be called since such sessions
# are not normally attached to the dbus

# If this is Ubuntu Desktop we have gnome available to control power settings
# gsettings comes with gnome, so we can check if it exists...
if hash gsettings 2>/dev/null; then
    if [[ ! -z $2 ]]; then
        USER_TO_CHANGE=$2
    else
        USER_TO_CHANGE=$(whoami)
    fi

    # if the hibernation policy file exists, hibernation is enabled
    if [[ ! -z $1 && -f $1 ]]; then
        # on critically low battery, hibernate if possible
        sudo -H -u $USER_TO_CHANGE dbus-launch --exit-with-session gsettings set org.gnome.settings-daemon.plugins.power critical-battery-action hibernate
    else
        # otherwise shutdown gracefully
        sudo -H -u $USER_TO_CHANGE dbus-launch --exit-with-session gsettings set org.gnome.settings-daemon.plugins.power critical-battery-action shutdown
    fi
    # Now set the remainder of the power settings
    sudo -H -u $USER_TO_CHANGE dbus-launch --exit-with-session gsettings set org.gnome.settings-daemon.plugins.power percentage-critical 5
    sudo -H -u $USER_TO_CHANGE dbus-launch --exit-with-session gsettings set org.gnome.settings-daemon.plugins.power lid-close-battery-action nothing
    sudo -H -u $USER_TO_CHANGE dbus-launch --exit-with-session gsettings set org.gnome.settings-daemon.plugins.power lid-close-ac-action nothing
    sudo -H -u $USER_TO_CHANGE dbus-launch --exit-with-session gsettings set org.gnome.settings-daemon.plugins.power idle-dim false
    sudo -H -u $USER_TO_CHANGE dbus-launch --exit-with-session gsettings set org.gnome.settings-daemon.plugins.power sleep-inactive-ac-type nothing
    sudo -H -u $USER_TO_CHANGE dbus-launch --exit-with-session gsettings set org.gnome.settings-daemon.plugins.power sleep-inactive-battery-type nothing
else
   echo "Configuring power settings not yet supported in this script for Ubuntu server."
   echo "Requires changing other files such as /etc/systemd/logind.conf"
fi

