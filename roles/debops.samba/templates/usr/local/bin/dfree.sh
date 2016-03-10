#!/bin/sh
/bin/df $1 | tail -1 | awk '{print $2" "$4}'