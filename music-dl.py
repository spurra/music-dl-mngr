# This script requires ffmpeg
from ytPlaylistdlMngr import dlMngr
import os
import sys
import argparse

parser = argparse.ArgumentParser(prog="music-dl", description="Downloads and \
    manages music in the youtube playlists specified in playlists.txt")
parser.add_argument('-r', '--reset', action="store_true", help="Resets the library")
parser.add_argument('dldir', nargs='?', default=None, help="Music download directory")
args = parser.parse_args()

dbfile = "songDatabase"
plfile = "playlists.txt"

# Check if environment variables is set
downloadPath = os.environ.get('MUSIC_DL_DATAPATH')
if downloadPath is None:
    downloadPath = args.dldir
# If not, check if download path is set.
if downloadPath is None:
    print("WARNING: MUSIC_DL_DATAPATH environment variable not set and no download \
        directory given as argument. Using default location")

filePath = os.path.dirname(os.path.realpath(__file__))

# Check if the reset argument has been set.
if args.reset and os.path.isfile(filePath + "/" + dbfile):
    os.remove(filePath + "/" + dbfile)
    if os.path.isfile(filePath + "/" + dbfile + "_backup"):
        os.remove(filePath + "/" + dbfile + "_backup")


# Initialise the manager
mngr = dlMngr(downloadPath, plfile, dbfile)

# Start the manager
mngr.startManager()