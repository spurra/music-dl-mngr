# music-dl-mngr
A small script which downloads youtube videos of all playlists specified in playlists.txt

Requirements:
Python2
ffmpeg
bs4
pytube

Usage: music-dl [-h] [-r] [dldir]

Downloads and manages music in the youtube playlists specified in
playlists.txt

positional arguments:
  dldir        Music download directory

optional arguments:
  -h, --help   show this help message and exit
  -r, --reset  Resets the library
