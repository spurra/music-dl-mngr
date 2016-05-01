# This script requires ffmpeg to be installed.
import requests
from bs4 import BeautifulSoup
import os
import re
import cPickle
import hashlib
from pytube import YouTube
from subprocess import call

# TODO use some music recognition service (e.g shazam) to get title and artist of song.

# The download manager
class dlMngr:
    # HTML ID of the table of the playlist containing all the songs
    tableID = "pl-load-more-destination"
    # HTML class name of the table elements containing the song and all corresponding
    # info
    tableElemID = "pl-video-title-link"# yt-uix-tile-link yt-uix-sessionlink  spf-link "
    # HTML class name of playlist
    playListTitleID = "pl-header-title"

    # Match any newlines and additional infos (e.g "[Exclusive]")
    regexStr1 = "\n|\[.*\]|\((([\w ]* Video)|Audio|Premiere)\)|( - )?Official[a-zA-Z ]+Video"
    # Match any unnecessary whitespaces after regexStr1 removal
    regexStr2 = "  +|[ \t]+$"

    ytBaseLink = "https://www.youtube.com"

    # The song database is a dictionary.
    songDB = {}

    def __init__(self, dlfolder=None, plfile="playlists.txt", dbfile="songDatabase"):

        if dlfolder is None:
            dlfolder = os.path.dirname(os.path.abspath(__file__)) + \
                "/downloadedSongs"

        filefolder = os.path.dirname(os.path.realpath(__file__))

        self.downloadFolder = dlfolder
        self.picklePath = filefolder + "/" + dbfile
        self.playlistfile = filefolder + "/" + plfile

        # Check if the download folder exists
        if not os.path.isdir(dlfolder):
            print("Folder " + dlfolder + " not found. Creating...")
            os.makedirs(dlfolder)

        # If available, open the data file for the downloaded music
        if os.path.isfile(self.picklePath):
            with open(self.picklePath, 'r') as db:
                self.songDB = cPickle.load(db)


    # Starts the manager
    def startManager(self):
        try:
            with open(self.playlistfile, 'r') as f:
                for line in f:
                    # Acquire the list of songs to be downloaded for the current playlist
                    music_list, dldir, pl_title = self.getSongsToDownload(line)

                    if len(music_list) == 0:
                        print("No new songs to download.")
                        continue

                    for song in music_list:
                        with open(self.picklePath, 'w') as db:
                            # Download the video
                            print("Downloading song " + song.name + "...")
                            video_path_nofe = self.downloadytVideo(song, dldir)

                            # Check if the video could be downloaded.
                            if video_path_nofe is None:
                                continue

                            # Convert it to mp3
                            print("Converting to mp3...")
                            self.convertmp4Tomp3(song, video_path_nofe)
                            # Add the checksum of the mp3 file to songDB
                            print("Done.")
                            self.addSongtoDB(video_path_nofe + ".mp3", song)

                            # Save the song to the database
                            cPickle.dump(self.songDB, db, -1)
        except Exception as e:
            print("ERROR:")
            print(e)
       



    # Returns a list of songs to download from the playlists
    def getSongsToDownload(self, plLink):
        # List of youtube links to convert to MP3
        toDownload = []

        # Clean the link of linebreaks
        plLink = re.sub("\s", "", plLink)

        playlistTitle, playlist = self.getPlaylist(plLink)

        # Check if the folder for the current playlist exists. If not,
        # create it
        currDir = self.downloadFolder + "/" + playlistTitle
        if not os.path.isdir(currDir):
            print("Creating folder " + playlistTitle + "...")
            os.makedirs(currDir)

        for song in playlist:
            
            # Check if the song has been downloaded and if it still exists
            # on disc
            if song.id in self.songDB.keys():
                found = False
                for s in os.listdir(currDir):
                    with open(currDir + "/" + s, 'rb') as ss:
                        if self.songDB[song.id].checksum == self.hashfile(ss, hashlib.md5()):
                            found = True
                            break

                if not found:
                    # Song is not found on disc. Add it to be downloaded
                    print("Adding seen song not found on disk: " + song.name)
                    self.songDB[song.id].mp3exists = False
                    toDownload.append(song) 
            

            else:
                # Song has not been seen before. Add it to be downloaded
                print("Found unseen song: " + song.name)
                toDownload.append(song)

        return toDownload, currDir, playlistTitle

    # Scrapes the playlist contained in plLink and returns a list of ytSong
    # objects
    def getPlaylist(self, plLink):
        # The list of ytSong objects
        playlist = []

        html = requests.get(plLink).text
        bsObj = BeautifulSoup(html, "html.parser")
        playListTitle = bsObj.find("h1", {"class":self.playListTitleID}).string
        playListTitle = self.cleanTitle(playListTitle)
        print("Downloading songs in playlist: \"" + playListTitle +"\"")

        # Find all the html elements containing the relevant song infos
        playlistElems = bsObj.find("tbody", {"id":self.tableID}).findAll("a", 
            {"class":self.tableElemID})

        for element in playlistElems:
            # Remove unnecessary infos and whitespaces from title
            songName = self.cleanTitle(element.string)

            # This song has been deleted. Don't process it.
            if (len(songName) == 0):
                continue

            # Construct the youtube link and remove playlist info from it
            songLink = self.ytBaseLink + re.sub("&.+$", "", element['href'])
            # Use the unique watch-link url as songID
            songID = songLink[32:]

            playlist.append(ytSong(songName, songLink, songID))

        return playListTitle, playlist

    # Returns the full path of the video WITHOUT the file ending
    def downloadytVideo(self, song, dldir = "."):
        # If video file exists, remove it. Only the case if program crashed,
        # therefore integrety of file cannot be guaranteed or reset option
        # specified.
        if os.path.isfile(dldir + "/" + song.name + ".mp4") and not song.mp4exists:
            os.remove(dldir + "/" + song.name + ".mp4")
        try:
            # Get the video
            yt = YouTube(song.url)
            yt.set_filename(song.name)
            # Select the mp4 video in the highest resolution
            data = yt.filter('mp4')[-1]
            video = yt.get('mp4', data.resolution)
            # Download the video
            video.download(dldir)
        except Exception as e:
            print("Something went wrong:")
            print(e)
            print("Ignoring...")
            return None

        song.mp4exists = True
        videoFilePath_nofe = dldir + "/" + song.name

        return videoFilePath_nofe

    # Converts the file in videoFilePath from .mp4 to .mp3 using ffmpeg.
    # The .mp3 file has a bitrate of 320k. If removeMp4 is true, it removes
    # the video file after conversion.
    def convertmp4Tomp3(self, song, videoFilePath, removeMp4=True):
        # If music file exists, remove it. Only the case if program crashed, 
        # therefore integrety of file cannot be guaranteed or reset option
        # specified.
        if os.path.isfile(videoFilePath + ".mp3") and not song.mp3exists:
            os.remove(videoFilePath + ".mp3")

        # Convert the video to mp3 using ffmpeg
        call(["ffmpeg", "-i", videoFilePath + ".mp4", "-b:a", "320k", videoFilePath
            + ".mp3"])

        song.mp3exists = True

        if removeMp4:
            # Remove the video
            os.remove(videoFilePath + ".mp4")
            song.mp4exists = False

    # Adds the checksum of song into songDB
    def addSongtoDB(self, filepath, song):
        with open(filepath, 'rb') as f:
            song.checksum = self.hashfile(f, hashlib.md5())
            self.songDB[song.id] = song


    # Applies the hashfunction in hasher and returns its checksum
    def hashfile(self, afile, hasher, blocksize=65536):
        buf = afile.read(blocksize)
        while len(buf) > 0:
            hasher.update(buf)
            buf = afile.read(blocksize)
        return hasher.digest()    

    # Applies regex strings to the string in title and returns int
    def cleanTitle(self, title):
        title = re.sub(self.regexStr1, "", title)
        title = re.sub(self.regexStr2, "", title)
        return title

# Class describing a youtube song
class ytSong:

    def __init__(self, name, url, sId):
        self.name = name
        self.url = url
        self.id = sId
        self.mp4exists = False
        self.mp3exists = False
        self.checksum = ""