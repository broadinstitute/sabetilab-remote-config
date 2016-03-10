#!/bin/sh

# This script fakes the amount of total and available storage by adding an offset
# to the true number of 1K blocks present and free.
#
# This is used to deceive a MiSeq into thinking a samba share has 100GB free
# when in reality it needs a lesser amount.
#
# It must be copied to the samba server machine, and
# used via the samba config option:
#   [global]
#      dfree command = /opt/faked_dfree.sh

TOTAL_BLOCKS=$(/bin/df $1 | tail -1 | awk '{print $2}')
FREE_BLOCKS=$(/bin/df $1 | tail -1 | awk '{print $4}')

# number of 1k blocks to add
OFFSET=90000000

TOTAL_WITH_OFFSET=$(expr $TOTAL_BLOCKS + $OFFSET)
FREE_WITH_OFFSET=$(expr $FREE_BLOCKS + $OFFSET)

echo "$TOTAL_WITH_OFFSET $FREE_WITH_OFFSET"