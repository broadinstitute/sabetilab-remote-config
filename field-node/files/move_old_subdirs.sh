#!/bin/bash

# Args are as follows:

# $1 source directory (directory to look within)
# $2 destination directory (directory to move old directories to)
# $3 older-than time (15m, 17d, etc.)

if [ "$#" -ne 3 ] || ! [ -d "$1" ] || ! [ -d "$2" ]; then
  echo "Usage: $(basename $0) dir_to_search/ dir_to_move_to/ age" >&2
  echo ""
  echo "Where:" 
  echo "        dir_to_search is the source directory (directory to look within)"
  echo "        dir_to_move_to is the destination directory (directory to move old directories to)"
  echo "        age is the older-than time (in days); directories older than this will be moved"
  exit 1
fi

SOURCE_DIR="$1"
DEST_DIR="$2"
MOVE_OLDER_THAN_DAYS="$3"

if [ -d "$DEST_DIR" ]; then
    #  - On OSX we can use -Btime to use the inode birth time, but on Linux mtime is the best we can check
    #  - Note the use of the wildcard in "$SOURCE_DIR/*" and "-maxdepth 0", and "-d": this limits the search
    #    to only directories within the source dir (but not the source dir itself)
    find $SOURCE_DIR/* -maxdepth 0 -type d -mtime +$MOVE_OLDER_THAN_DAYS -exec cp -R --no-preserve=mode,ownership "{}" $DEST_DIR \; -exec rm -r "{}" \;
fi

