# coding=UTF-8
###########################################################################
# PiCobber Oled Player Program By FishX (http://weibo.com/2731710965)
# PiCobber & OLED Library   by Ukonline (http://ukonline2000.com/)
# support MPD & MPD based linux system,like Raspbian,Volume etc...
###########################################################################
# HOWTO USE:
# First:Enable SPI & I2C on Raspberry PI
# Second:sudo pip install mpd python-mpd2 python-smbus
# you must set MPD mixer to "software" mode!
# otherwise you can't adjust volume at all!
# sudo nano /etc/mpd.conf & change mixer to software from hardware!!!
# Third: sudo python player.py
# Operation:
# 1]Main screen(current playing) 
# gotoPlaylist,   volume +,       play/stop
# previous song,  volume -,       next song
# 2]Playlist screen
# Settings Menu,  previous song,  play selected song
# previous page,  next song,      next page
# 3]Setting screen
# goto cureent song,   menu options up,     confirm
# previous menu item,  menu options down,   next menu item
############################################################################
# About music files.
# 1]put some music in /var/lib/mpd/music then run the update playlist
# command in the setting menu
# 2]if there's no music in the playlist,the program will jump to the
# setting menu,you can use Update Playlist command
# to add all the music files(/var/lib/mpd/music) into playlist
# 3]just enabled samba,you can easily add music file from PC
############################################################################

import os
import time
import subprocess
import mpd
import sys
import ssd1306
from Raspi_MCP230xx import Raspi_MCP230XX
from time import sleep

#init oled screen
def initOled():
	global mcp,offset,led
	mcp = Raspi_MCP230XX(address = 0x20, num_gpios = 8)
	for i in range(0,6):
		mcp.config(i,mcp.INPUT)
	mcp.config(6,mcp.OUTPUT)
	mcp.output(6, 1)                         # LED OUTPUT Low (Off)
	led = ssd1306.SSD1306()
	led.begin()
	led.clear_display()
	offset = 0 

#exit system
def exitSystem(n):
	global screenMode,led
	led.clear_display()
	led.draw_text2(10,16,"Bye Bye!",2)
	led.display()
	print "exiting..."
	if n == 0:
		disconnectMPD()
		popen = subprocess.Popen(['sudo','halt','-h'], stdout = subprocess.PIPE)
		raise SystemExit
	elif n == 1:
		disconnectMPD()
		popen = subprocess.Popen(['sudo','reboot'], stdout = subprocess.PIPE)
		raise SystemExit
	elif n == 2:
		disconnectMPD()
		raise SystemExit

#remove invalid string or AD string
def removeAD(s):
	s = s.strip()
	s = s.strip('\n')
	s = s.strip('USB')
	s = s.strip('[51ape.com]')
	s = s.strip('[www.51ape.com]')
	s = s.strip('Ape.Com]')
	s = s.strip('file: USB//')
	return s

#check current MPD status
def getCurrentPlaying():
	global nowPlaying,isPlaying,client,curArtist,theAlbum,previousSong
	cs =  client.currentsong()
	nowPlaying = cs.get('title','')
	curArtist = cs.get('artist','')
	theAlbum = cs.get('album','')
	theFile = cs.get('file','')
	#judge if new song be playing (judge from file).
	if previousSong != theFile:
		initPlayTime()
	previousSong = theFile
	if len(nowPlaying) is 0:
		isPlaying = False
	else:
		isPlaying = True

#get playlist
def getPlaylist():
	global playList,client,screenMode,curMenuItem
	playList = client.playlist()
	#if there's no music file jump to update playlist menu
	if len(playList) == 0:
		screenMode = 2
		curMenuItem = 6

#get playlist for displaying
def getScreenList():
	global pageCount,curPage,playList,screenList,actualScreenLines
	screenList = []
	if (curPage > 1) and (curPage == pageCount):
		actualScreenLines = len(playList) - ( pageCount -1) * maxScreenLines
	elif pageCount == 1:
		actualScreenLines = len(playList)
	else:
		actualScreenLines = maxScreenLines
	for i in range(0,actualScreenLines):
		screenList.append((playList[maxScreenLines * (curPage - 1) + i]).strip("file: USB//"))

#Jump to playlist screen
def gotoPlaylist():
	global screenMode,playList,pageCount
	screenMode = 1
	getPlaylist()
	pageCount = (len(playList) + maxScreenLines - 1) / maxScreenLines

#jump to the specified page
def setPage(n):
	global pageCount,curPage,cursorPosition,maxScreenLines
	if n:
		if curPage < pageCount:
			curPage = curPage + 1
			cursorPosition = 1
	else:
		if curPage > 1:
			curPage = curPage - 1
			cursorPosition = maxScreenLines

#play specified song
def playSpecial(n):
	global pageCount,curPage,maxScreenLines,client
	if pageCount == 1:
		client.play(str(n-1))
	else:
		client.play(str((curPage - 1) * maxScreenLines + n -1))

#init MPD socket
def initMPDConnection():
	global client
	client = mpd.MPDClient() #use_unicode=True
	client.connect("localhost", 6600)

#disconnect MPD socket
def disconnectMPD():
	global client
	client.disconnect()

#Get MPD Status
def getPlayerStates():
	global isRepeat,isRandom,isSingle,isConsume,theVolume,playState,theTime,theVolume,s
	s = client.status()
	theVolume = s.get('volume','-1')
	isConsume = s.get('consume','0')
	isRepeat = s.get('repeat','0')
	isRandom = s.get('random','0')
	isSingle = s.get('single','0')
	playState = s.get('state','stop')
	theTime = s.get('time','0:1')
	theVolume = int(s.get('volume','80'))

#set volume
def setVolume(d):
	global theVolume
	if d:
		if theVolume <= 95:
			theVolume = theVolume + 5
	else:
		if theVolume >= 5:
			theVolume = theVolume - 5
	client.setvol(str(theVolume))

#conver 1,0 to ON,OFF
def numToBool(v):
	if v:
		return 'ON'
	else:
		return 'OFF'

#set MPD status
def setMPDStatus(i,v):
	if i == 'single':
		client.single(v)
	elif i == 'random':
		client.random(v)
	elif i == 'consume':
		client.consume(v)
	elif i == 'repeat':
		client.repeat(v)
	elif i == 'previous':
		client.previous()
	elif i == 'next':
		client.next()
	elif i == 'play':
		if playState == "play":
			client.pause()
		else:
			client.play()
			
#conver second to minute
def converSecondToMinute(s):
	return str(s / 60) + ':' + str(s % 60)

def updatePlayList():
	global client,screenMode
	client.clear()
	client.update()
	client.findadd("any","")
	sleep(1.0)
	gotoPlaylist() 

#the time while the song changed
def initPlayTime():
	global musicChgTime
	musicChgTime = time.time()
	#print musicChgTime
	
def dispCurrentPlaying():
	global screenMode
	led.clear_display()
	led.command(led.SET_START_LINE | 0)
	#get MPD Status
	getPlayerStates()
	#get current playing
	getCurrentPlaying()
	#jump to music info screen while playing...
	if (time.time() > (musicChgTime + timeBefAni)) and playState == "play" :
		screenMode = 3
	#draw status icon
	for i in range(0,len(iconMenu) / 2):
		led.draw_pixel(1 + iconMenu[i*2],iconMenu[i*2+1] + 1)
	if int(isSingle):
		for i in range(0,len(iconSingle) / 2):
			led.draw_pixel(12 + iconSingle[i*2],iconSingle[i*2+1] + 1)
	if int(isRepeat):
		for i in range(0,len(iconRepeat) / 2):
			led.draw_pixel(24 + iconRepeat[i*2],iconRepeat[i*2+1] + 1)
	if int(isRandom):
		for i in range(0,len(iconRandom) / 2):
			led.draw_pixel(36 + iconRandom[i*2],iconRandom[i*2+1] + 1)
	else:
		for i in range(0,len(iconOrder) / 2):
			led.draw_pixel(36 + iconOrder[i*2],iconOrder[i*2+1] + 1)
	if int(isConsume):
		for i in range(0,len(isConsume) / 2):
			led.draw_pixel(48 + isConsume[i*2],isConsume[i*2+1] + 1)
	if playState == "play":
		for i in range(0,len(iconPause) / 2):
			led.draw_pixel(120 + iconPause[i*2],iconPause[i*2+1] + 2)
	else:
		for i in range(0,len(iconPlay) / 2):
			led.draw_pixel(120 + iconPlay[i*2],iconPlay[i*2+1] + 2)
	vol = int(float(theVolume) * 6 / 100)
	for i in range(0,len(iconVolume) / 2):
		if iconVolume[i*2] <= vol:
			led.draw_pixel(110 + iconVolume[i*2],iconVolume[i*2+1] + 1)
	#draw time
	led.draw_text2(75,2,time.strftime('%H:%M',time.gmtime()),1)
	#draw artist and song name
	led.draw_text2(5,16,curArtist,1)
	if len(nowPlaying) > 0:
		led.draw_text2(10,28,">" + nowPlaying + "",1)
	if len(playList) == 0:
		led.draw_text2(0,18,"No Music File Found!",1)
		led.draw_text2(0,28,"Update Playlist in",1)
		led.draw_text2(5,38,"Setting Menu!",1)
	led.draw_text2(5,40,"" + theAlbum + "",1)
	#draw the progressbar
	percent = float(theTime.split(":")[0]) / float(theTime.split(":")[1])
	#draw the border of progressbar
	for i in range(0,97):
		led.draw_pixel(i,58)
		led.draw_pixel(i,61)
	led.draw_pixel(96,59)
	led.draw_pixel(96,60)
	#fill the progressbar
	for i in range(0,97):
		led.draw_pixel(int(i * percent),59)
		led.draw_pixel(int(i * percent),60)
	led.draw_text2(99,56,converSecondToMinute(int(theTime.split(":")[0])),1)
	led.display()
	
# draw Playlist on screen
def dispPlayList():
	global screenMode
	getScreenList()
	led.clear_display()
	led.command(led.SET_START_LINE | 0)
	#display current page of playlist
	for i in range(0,actualScreenLines):
		led.draw_text2(7,i * 8,screenList[i],1)
	#draw triangle on the left
	for i in range(0,len(triangle) / 2):
		led.draw_pixel(triangle[i*2],(cursorPosition-1) * 8 + triangle[i*2+1])
	led.display()
	
# draw settings menu on the screen
def dispMenu():
	global screenMode,curMenuItem,curMenuOptions,curMenuOptionsPosition
	getPlayerStates()
	led.clear_display()
	led.command(led.SET_START_LINE | 0)
	#draw current menu item
	if curMenuItem > 1 and curMenuItem < len(menuOrder):
		led.draw_text2(5,13,"== " + menuOrder[curMenuItem-1] + '(' + numToBool(int(s.get(menuOrder[curMenuItem-1].lower()))) + ') ======',1)
	else:
		led.draw_text2(5,13,"== " + menuOrder[curMenuItem-1] + " ============",1)
	#draw current options of current menu item
	curMenuOptions = menuSettings.get(menuOrder[curMenuItem-1]).split('|')
	for i in range(0,len(curMenuOptions)):
		if i == curMenuOptionsPosition - 1:
			led.draw_text2(20,(i+1)*10 + 16,'->'+curMenuOptions[i],1)
		else:
			led.draw_text2(20,(i+1)*10 + 16,curMenuOptions[i],1)
	led.display()
	sleep(0.1)                                 #add sleep to avoid fast switch
	
# draw animation
def dispAnimation():
	global screenMode,musicChgTime,timeBefAni
	getCurrentPlaying()
	led.clear_display()
	led.draw_text2(0, 20,"" + nowPlaying + "",2)
	led.draw_text2(10,42,"" + curArtist  + "",1)
	led.draw_text2(10,56,"" + theAlbum   + "",1)
	led.display()
	#Start animation
	timePassed = int((time.time() - musicChgTime - timeBefAni) * 6) #Speed:6
	if timePassed > 0:
		startLine = (timePassed + 1) % 64
		led.command(led.SET_START_LINE | startLine)
def splash():
	led.clear_display()
	led.command(led.SET_START_LINE | 0)
	led.draw_text2(0, 17,"FishX",1)
	led.draw_text2(15,30,"Picobber Player",1)
	led.draw_text2(0, 43,"weibo.com/2731710965",1)
	led.display()
	sleep(2)
print "Init..."
#                     Global settings
screenMode = 0
#                     MPD Status
isRepeat = ""
isRandom = ""
isSingle = ""
isConsume = ""
theVolume = "80"
theTime = "1:1"       #1:1=100%
playState = ""
nowPlaying = ""
theAlbum = ""
curArtist = ""
                      #other status
playList = []         #empty playlist
curPage = 1           #current page of playlist
pageCount = 1         #page count of playlist
maxScreenLines = 8    #lines display on screen
actualScreenLines = 0 #actual lines of screen 
screenList = []       #empty lines of screen
cursorPosition = 1    #cursor position of playlist on screen
previousSong = ""     #previous song filename
timeBefAni = 8        #when swich to a new song,display animation after 8 seconds
musicChgTime = time.time()

#                      menu items & menu options
menuOrder = ['Close','Random','Single','Repeat','Consume','Update Playist']
menuSettings = {'Close':'HALT|REBOOT|EXIT','Random':'ON|OFF',
			'Single':'ON|OFF','Repeat':'ON|OFF','Consume':'ON|OFF',
			'Update Playist':'YES'}
menuItemCount = len(menuSettings)        #calc item first
curMenuItem = 1                          #current menu item (default:halt)
curMenuOptions = []                      #current menu options of current menu
curMenuOptionsPosition = 1               #the position of current menu options

#                                        iconData of currentplaying screen size:6x6 pixel
triangle =    [2,1,2,2,2,3,2,4,2,5,2,6,3,2,3,3,3,4,3,5,4,3,4,4]
iconMenu =    [2,1,3,1,4,1,5,1,1,2,6,2,1,3,3,3,4,3,6,3,1,4,3,4,4,4,6,4,1,5,6,5,2,6,3,6,4,6,5,6]
iconOrder =   [1,1,3,1,4,1,5,1,6,1,1,3,3,3,4,3,5,3,6,3,1,5,3,5,4,5,5,5,6,5]
iconRandom =  [1,1,3,1,5,1,2,2,4,2,6,2,1,3,3,3,5,3,2,4,4,4,6,4,1,5,3,5,5,5,2,6,4,6,6,6]
iconSingle =  [2,1,3,1,4,1,5,1,2,2,2,3,3,3,4,3,5,3,5,4,5,5,2,6,3,6,4,6,5,6]
iconRepeat =  [2,1,3,1,4,1,5,1,2,2,5,2,2,3,3,3,4,3,5,3,2,4,3,4,2,5,4,5,2,6,5,6]
iconConsume = [1,1,2,1,5,1,6,1,1,2,3,2,4,2,6,2,1,3,6,3,2,4,5,4,2,5,5,5,2,6,3,6,4,6,4,4]
iconPause =   [2,1,5,1,2,2,5,2,2,3,5,3,2,4,5,4,2,5,5,5]
iconPlay =    [2,1,2,2,3,2,2,3,3,3,4,3,2,4,3,4,4,4,2,5,3,5,2,6]
iconVolume =  [1,6,2,5,2,6,3,4,3,5,3,6,4,3,4,4,4,5,4,6,5,2,5,3,5,4,5,5,5,6,1,6,2,6,3,6,4,6,5,6,6]

initMPDConnection()                      #system initing...
setMPDStatus('consume',0)                #set consume default to off
getPlayerStates()                        #get MPD curent Status
getPlaylist()                            #check and get playlist
getCurrentPlaying()                      #get the song of playing
initOled()                               #init oled screen
splash()

print "Start..."
while(True):
	if screenMode is 0:                  #screen of now playing
		if mcp.input(0) is 0:
			mcp.output(6, 0)
			sleep(0.2)
			gotoPlaylist()               #goto playlist screen
			mcp.output(6, 1)
		if mcp.input(1) is 0:            #volume up
			setVolume(1)
			mcp.output(6, 0)
		if mcp.input(2) is 0:
			setMPDStatus('play',1)       #play/pause
			mcp.output(6, 0)
		if mcp.input(3) is 0:
			setMPDStatus("previous",1)   #play previous song
			mcp.output(6, 0)
		if mcp.input(4) is 0:            #volume down
			setVolume(0)
			mcp.output(6, 0)
		if mcp.input(5) is 0:            #play next song
			setMPDStatus("next",1)
			mcp.output(6, 0)
		dispCurrentPlaying()
	elif screenMode is 1:                #the playlist screen
		if mcp.input(0) is 0:            #goto settings screen
			mcp.output(6, 0)
			sleep(0.2)
			screenMode = 2
			mcp.output(6, 1)
		if mcp.input(1) is 0:            #cursor up
			if cursorPosition > 1:
				cursorPosition = cursorPosition - 1
			elif curPage > 1:
				cursorPosition = maxScreenLines
				setPage(0)
			mcp.output(6, 0)
		if mcp.input(2) is 0:            #play current selected song
			playSpecial(cursorPosition)
			mcp.output(6, 0)
		if mcp.input(3) is 0:            #display previous page
			setPage(0)
			mcp.output(6, 0)
		if mcp.input(4) is 0:            #cursor down
			if cursorPosition < actualScreenLines:
				cursorPosition = cursorPosition + 1
			elif curPage < pageCount:
				cursorPosition = 1
				setPage(1)
			mcp.output(6, 0)
		if mcp.input(5) is 0:            #display next page
			setPage(1)
			mcp.output(6, 0)
		dispPlayList()
	elif screenMode is 2:
		if mcp.input(0) is 0:            #goto current playing screen
			mcp.output(6, 0)
			sleep(0.2)
			mcp.output(6, 1)
			initPlayTime()
			screenMode = 0
		if mcp.input(1) is 0:            #options up
			if curMenuOptionsPosition > 1:
				curMenuOptionsPosition = curMenuOptionsPosition - 1
			else:
				curMenuOptionsPosition = len(curMenuOptions)
			mcp.output(6, 0)
		if mcp.input(2) is 0:            #confirm selected option
			if curMenuItem > 1 and curMenuItem < len(menuOrder):
				setMPDStatus(menuOrder[curMenuItem-1].lower(),abs(curMenuOptionsPosition-2))
			elif curMenuItem == 1:
				if curMenuOptionsPosition == 1:
					exitSystem(0)
				elif curMenuOptionsPosition == 2:
					exitSystem(1)
				else:
					exitSystem(2)
			else:
				updatePlayList()
			mcp.output(6, 0)
		if mcp.input(3) is 0:            #display previous menu item
			if curMenuItem > 1:
				curMenuItem = curMenuItem - 1
			else:
				curMenuItem = menuItemCount
			if curMenuItem == 1 or curMenuItem == len(menuOrder):
				curMenuOptionsPosition = 1
			else:
				curMenuOptionsPosition = abs(int(s.get(menuOrder[curMenuItem-1].lower())) - 2)
			mcp.output(6, 0)
		if mcp.input(4) is 0:            #options down
			if curMenuOptionsPosition < len(curMenuOptions):
				curMenuOptionsPosition = curMenuOptionsPosition + 1
			else:
				curMenuOptionsPosition = 1
			mcp.output(6, 0)
		if mcp.input(5) is 0:            #display next menu item
			if curMenuItem < menuItemCount:
				curMenuItem = curMenuItem + 1
			else:
				curMenuItem = 1
			if curMenuItem == 1 or curMenuItem == len(menuOrder):
				curMenuOptionsPosition = 1
			else:
				curMenuOptionsPosition = abs(int(s.get(menuOrder[curMenuItem-1].lower())) - 2)
			mcp.output(6, 0)
		dispMenu()
	elif screenMode is 3:
		if mcp.input(0) is 0:
			mcp.output(6, 0)
			sleep(0.2)
			initPlayTime()
			screenMode = 0
		if mcp.input(1) is 0:             #volume up
			setVolume(1)
			mcp.output(6, 0)
		if mcp.input(2) is 0:
			setMPDStatus('play',1)        #play/pause
			sleep(0.2)
			screenMode = 0
			mcp.output(6, 0)
		if mcp.input(3) is 0:
			setMPDStatus("previous",1)    #play previous song
			sleep(0.2)
			screenMode = 0
			mcp.output(6, 0)
		if mcp.input(4) is 0:             #volume down
			setVolume(0)
			mcp.output(6, 0)
		if mcp.input(5) is 0:             #play next song
			setMPDStatus("next",1)
			sleep(0.2)
			screenMode = 0
			mcp.output(6, 0)
		dispAnimation()
	mcp.output(6,1)                       #Close LED
# end of file