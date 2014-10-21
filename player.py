# coding=UTF-8
###########################################################################
# PiCobber Oled Player Program (V0.8 Stable) By FishX (http://weibo.com/2731710965)
# PiCobber by Ukonline (http://ukonline2000.com/)
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
import os
import time
import subprocess
import threading
import mpd
import sys
import Adafruit_GPIO.SPI as SPI
import Adafruit_SSD1306
import Image
import ImageDraw
import ImageFont
from   Raspi_MCP230xx import Raspi_MCP230XX
from   time import sleep

# Init control keys
def initMcp():
	global mcp
	mcp = Raspi_MCP230XX(address = 0x20, num_gpios = 8)
	for i in range(0,6):
		mcp.config(i,mcp.INPUT)
	mcp.config(6,mcp.OUTPUT)
	mcp.output(6,1)                         # LED OUTPUT Low (Off)
	
# Init the oled screen
def initOled():
	global oled,image,draw
	RST        = 25
	DC         = 24
	SPI_PORT   = 0
	SPI_DEVICE = 0
	oled = Adafruit_SSD1306.SSD1306_128_64(rst=RST, dc=DC, spi=SPI.SpiDev(SPI_PORT, 
		SPI_DEVICE, max_speed_hz=8000000))
	oled.begin()
	oled.clear()
	oled.display()
	width = oled.width
	height = oled.height
	image = Image.new('1', (width, height))
	draw = ImageDraw.Draw(image)
	
# init MPD socket,one for read settings,another for change settings
def initMPDConnection():
	global MPDClient,MPDClientW
	MPDClient = mpd.MPDClient() #use_unicode=True
	MPDClient.connect("localhost", 6600)
	
# Disconnect MPD socket
def disconnectMPD():
	global MPDClient
	MPDClient.disconnect()
	
# Exit function
def exitSystem(n):
	global screenMode,isClosing
	isClosing = True
	mcp.output(6,1)
	sleep(1)
	draw.rectangle((0,0,127,63),outline=0,fill=0)
	draw.text((10,16), 'Bye!', font=fontTitle, fill=255)
	oled.image(image)
	oled.display()
	disconnectMPD()
	sleep(1)
	draw.rectangle((0,0,127,63),outline=0,fill=0)
	oled.image(image)
	oled.display()
	print "exiting..."
	if n == 0:
		popen = subprocess.Popen(['sudo','halt','-h'], stdout = subprocess.PIPE)
	elif n == 1:
		popen = subprocess.Popen(['sudo','reboot'], stdout = subprocess.PIPE)
	raise SystemExit
	
# Remove invalid string or AD string
def removeAD(s):
	s = s.strip()
	s.replace('\n','')
	s.replace('[www.51ape.com]','')
	s.replace('[51ape.com]','')
	s.replace('Ape.Com]','')
	s.replace('file: USB//','')
	return s
	
# Unicode encoding
def u(s):
	return unicode(s,'utf-8')
	
# Check current MPD status
def getCurrentPlaying():
	global nowPlaying,MPDClient,curArtist,theAlbum,previousSong,theFile,playState,isHD
	lock.acquire()
	try:
		cs =  MPDClient.currentsong()
	finally:
		lock.release()
	nowPlaying = removeAD(cs.get('title',''))
	curArtist = removeAD(cs.get('artist',''))
	theAlbum = removeAD(cs.get('album',''))
	theFile = cs.get('file','')
	hdFileNames = ['flac','.ape','.wav']
	isHD = False
	if theFile is not '':
		if theFile[-4:].lower() in hdFileNames:
			isHD = True
	# judge if new song be playing (by checking filename).
	if previousSong != theFile:
		initEventTime()
	previousSong = theFile

# Get playlist
def getPlaylist():
	global playList,MPDClient,screenMode,curMenuItem
	lock.acquire()
	try:
		playList = MPDClient.playlist()
	finally:
		lock.release()
	#if there's no music file jump to update playlist menu
	if len(playList) == 0:
		screenMode = 2
		curMenuItem = 6

# Get playlist for displaying
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

# Jump to playlist screen
def gotoPlaylist():
	global screenMode,playList,pageCount
	getPlaylist()
	pageCount = (len(playList) + maxScreenLines - 1) / maxScreenLines
	screenMode = 1

# Jump to the specified page
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

# Get MPD Status
def getPlayerStates():
	global isRepeat,isRandom,isSingle,isConsume,theVolume,playState,theTime,theVolume,s
	lock.acquire()
	try:
		s = MPDClient.status()
	finally:
		lock.release()
	#print s
	theVolume = s.get('volume','-1')
	isConsume = s.get('consume','0')
	isRepeat  = s.get('repeat','0')
	isRandom  = s.get('random','0')
	isSingle  = s.get('single','0')
	playState = s.get('state','stop')
	theTime   = s.get('time','0:1')
	theVolume = int(s.get('volume','80'))

# Convert 1,0 to ON,OFF
def numToBool(v):
	if menu == menuChinese:
		if v:
			return '开'
		else:
			return '关'
	else:
		if v:
			return 'ON'
		else:
			return 'OFF'
			
# Set MPD status
def setMPDStatus(i,v):
	global theVolume,pageCount,curPage,maxScreenLines
	lock.acquire()
	try:
		if i == 'single':
			MPDClient.single(v)
		elif i == 'random':
			MPDClient.random(v)
		elif i == 'consume':
			MPDClient.consume(v)
		elif i == 'repeat':
			MPDClient.repeat(v)
		elif i == 'previous':
			MPDClient.previous()
		elif i == 'next':
			MPDClient.next()
		elif i == 'play':
			if playState == "play":
				MPDClient.pause()
			else:
				MPDClient.play()
		elif i == 'volume':
			if v:
				if theVolume <= 95:
					theVolume = theVolume + 5
			else:
				if theVolume >= 5:
					theVolume = theVolume - 5
			MPDClient.setvol(str(theVolume))
		elif i == 'update':
			MPDClient.clear()
			MPDClient.update()
			MPDClient.findadd("any","")
		elif i == 'songid':
			if pageCount == 1:
				MPDClient.play(str(v-1))
			else:
				MPDClient.play(str((curPage - 1) * maxScreenLines + v -1))
	finally:
		lock.release()
# Convert seconds to minute:seconds
def converSecondToMinute(s):
	if int(time.time()) % 2 is 1:
		return "{:0>2d}".format(s / 60) + ':' + "{:0>2d}".format(s % 60)
	else:
		return "{:0>2d}".format(s / 60) + ' ' + "{:0>2d}".format(s % 60)
	
# The time while the song changed
def initEventTime():
	global lastEventTime
	lastEventTime = time.time()
	
# Draw specified icon
def drawIcon(x,y,a):
	for i in range(0,len(a) / 2):
		draw.point((x + a[i*2],a[i*2+1] + y) ,fill = 255)
		
# Draw current playing to screen
def dispCurrentPlaying():
	global screenMode,theTime,lastEventTime,playState
	draw.rectangle((0,0,127,63),outline=0,fill=0)
	getPlayerStates()               #get mpd status
	getCurrentPlaying()             #get current playing
	#Jump to music info screen while playing...
	if (time.time() > (lastEventTime + timeBefAni)) and playState == "play" :
		screenMode = 3
		return
	#Draw status icons
	drawIcon(1,1,iconMenu)
	if int(isSingle):
		drawIcon(13,1,iconSingle)
		#draw.text((13,-1),'S',font = fontSmall ,fill = 255)
	if int(isRepeat):
		drawIcon(25,1,iconRepeat)
		#draw.text((25,-1),'R',font = fontSmall ,fill = 255)
	if int(isRandom):
		drawIcon(37,1,iconRandom)
		#draw.text((37,-1),'Rdm',font = fontSmall ,fill = 255)
	else:
		#pass
		drawIcon(37,1,iconOrder)
	if int(isConsume):
		drawIcon(49,1,iconConsume)
		#draw.text((49,-1),'C',font = fontSmall ,fill = 255)
	if playState == "play":
		drawIcon(120,2,iconPause)
	else:
		drawIcon(120,2,iconPlay)
	vol = int(float(theVolume) * 6 / 100)
	for i in range(0,len(iconVolume) / 2):
		if iconVolume[i*2] <= vol:
			draw.point((110 + iconVolume[i*2],iconVolume[i*2+1] + 1),fill = 255)
	draw.text((1,12),u(curArtist),font = fontMain ,fill = 255)
	if nowPlaying.strip() is '':
		title = u(theFile)
	else:
		title = u(nowPlaying)
	TitleW = draw.textsize(title,font = fontTitle)[0]
	if TitleW > 128:
		TitleX = 0
	else:
		TitleX = (128 - TitleW) / 2
	draw.text((TitleX,30),title,font = fontTitle ,fill = 255)
	
	if isHD:
		draw.text((92,0), 'HD', font=fontSmall, fill=255)
	#Draw the progressbar
	if ':' in theTime:
		percent = float(theTime.split(":")[0]) / float(theTime.split(":")[1])
	else:
		percent = 0
	draw.rectangle((32,58,97,61),outline=255)
	draw.rectangle((33,59,33 + int(66 * percent),60),outline=255)
	#Draw the time
	if int(time.time()) % 2 is 1:
		fmtTime = '%H:%M'
	else:
		fmtTime = '%H %M'
	draw.text((0,55), time.strftime(fmtTime,time.gmtime()), font=fontSmall, fill=255)
	draw.text((98,55),converSecondToMinute(int(theTime.split(":")[0])),font = fontSmall ,fill = 255)
	oled.image(image)
	oled.display()

# Draw Playlist on screen
def dispPlayList():
	global screenMode
	getScreenList()
	draw.rectangle((0,0,127,63),outline=0,fill=0)
	#display current page of playlist
	drawIcon(1,1,iconMenu)
	draw.text((9,0),'(' + str(curPage) + '/' + str(pageCount) + ')',font = fontSmall,fill = 255)
	for i in range(0,actualScreenLines):
		draw.text((8,(i+1) * 13 - 2),u(screenList[i]),font = fontMain,fill = 255)
	#draw triangle on the left
	for i in range(0,len(triangle) / 2):
		drawIcon(1,(cursorPosition) * 13 + 2,triangle)
	oled.image(image)
	oled.display()

# Draw settings menu on the screen
def dispMenu():
	global screenMode,curMenuItem,curMenuOptions,curMenuOptionsPosition
	getPlayerStates()
	draw.rectangle((0,0,127,63),outline=0,fill=0)
	drawIcon(1,1,iconMenu)
	if curMenuItem > 1 and curMenuItem < menuItemCount:
		menuTitle = u(menu[(curMenuItem-1)*3]) + '(' + u(numToBool(int(s.get(menu[(curMenuItem-1)*3+2].lower(),'')))) + ')'
	else:
		menuTitle = u(menu[(curMenuItem-1)*3])
	menuW = draw.textsize(menuTitle,font = fontMain)[0]
	draw.text(((128 - menuW)/2,1),menuTitle,font = fontMain,fill = 255)
	#draw current options of current menu item
	curMenuOptions = menu[(curMenuItem-1)*3 + 1].split('|')
	draw.line((5, 19, 122, 19), fill=255)
	for i in range(0,len(curMenuOptions)):
		if i == curMenuOptionsPosition - 1:
			draw.text((20,i*14 + 22),'-> ' + u(curMenuOptions[i]),font=fontMain,fill = 255)
		else:
			draw.text((20,i*14 + 22),'    ' + u(curMenuOptions[i]),font=fontMain,fill = 255)
	oled.image(image)
	oled.display()

# Draw animation
def dispAnimation():
	global screenMode,lastEventTime,timeBefAni,keyPressed
	draw.rectangle((0,0,127,63),outline=0,fill=0)
	getCurrentPlaying()
	info = ''
	if nowPlaying is not '':
		info = '《' + nowPlaying + '》'
	if curArtist is not '':
		info = info + '-' + curArtist
	if theAlbum is not '':
		info = info + '-《' + theAlbum + '》'
	if info is '':
		info = theFile
	info = u(info)
	infoW = draw.textsize(info,font = fontTitle)[0]
	fileNow = theFile
	keyPressed = False
	for i in range(-128,infoW):
		if keyPressed is True:
			sleep(0.1)
			initEventTime()
			break
		draw.rectangle((0,0,127,63),outline=0,fill=0)
		if isHD and (int(time.time()) % 2 is 0):
			draw.text((92,0), 'HD', font=fontSmall, fill=255)
		if int(time.time()) % 2 is 1:
			fmtTime = '%H:%M'
		else:
			fmtTime = '%H %M'
		draw.text((0,55), time.strftime(fmtTime,time.gmtime()), font=fontSmall, fill=255)
		draw.text((0 - i,24),info,font=fontTitle,fill=255)
		oled.image(image)
		oled.display()
		mcp.output(6,1)
		
# Display splash screen
def splash():
	draw.rectangle((0,0,127,63),outline=0,fill=0)
	draw.text((5,14),'FishX',font=fontSmall,fill=255)
	draw.text((15,30),'Picobber Player',font=fontSmall,fill=255)
	draw.text((5,46),'weibo.com/2731710965',font=fontSmall,fill=255)
	oled.image(image)
	oled.display()
	sleep(1)
	
# KeyChecking thread
def checkKeyPress():
	while True:
		if mcp.input(0) is 0:
			mcp.output(6,0)
			k(0)
		elif mcp.input(1) is 0:
			mcp.output(6,0)
			k(1)
		elif mcp.input(2) is 0:
			mcp.output(6,0)
			k(2)
		elif mcp.input(3) is 0:
			mcp.output(6,0)
			k(3)
		elif mcp.input(4) is 0:
			mcp.output(6,0)
			k(4)
		elif mcp.input(5) is 0:
			mcp.output(6,0)
			k(5)
		sleep(0.2)
		mcp.output(6,1)
		keyPressed = False
		
# Press k to load the function
def k(k):
	global screenMode,keyPressed
	global curPage,pageCount,cursorPosition,maxScreenLines,actualScreenLines
	global curMenuItem,menuItemCount,curMenuOptionsPosition,curMenuOptions
	if screenMode is 0:
		if k is 0:
			gotoPlaylist()
			return
		if k is 1:
			setMPDStatus('volume',1)     #volume up
		if k is 2:
			setMPDStatus('play',1)       #play/pause
		if k is 3:
			setMPDStatus("previous",1)   #play previous song
		if k is 4:
			setMPDStatus('volume',0)     #volume down
		if k is 5:
			setMPDStatus("next",1)       #play next song
	if screenMode is 1:
		if k is 0:
			screenMode = 2               #goto settings screen
			return
		if k is 1:
			if cursorPosition > 1:
				cursorPosition = cursorPosition - 1
			elif curPage > 1:
				cursorPosition = maxScreenLines
				setPage(0)
		if k is 2:
			initEventTime()
			setMPDStatus('songid',cursorPosition)
		if k is 3:
			setPage(0)
		if k is 4:
			if cursorPosition < actualScreenLines:
				cursorPosition = cursorPosition + 1
			elif curPage < pageCount:
				cursorPosition = 1
				setPage(1)
		if k is 5:
			setPage(1)
	if screenMode is 2:
		if k is 0:
			initEventTime()
			screenMode = 0
			return
		if k is 1:
			if curMenuOptionsPosition > 1:
				curMenuOptionsPosition = curMenuOptionsPosition - 1
			else:
				curMenuOptionsPosition = len(curMenuOptions)
		if k is 2:
			if curMenuItem > 1 and curMenuItem < menuItemCount:
				setMPDStatus(menu[(curMenuItem-1)*3 + 2].lower(),abs(curMenuOptionsPosition-2))
			elif curMenuItem == 1:
				if curMenuOptionsPosition == 1:
					exitSystem(0)
				elif curMenuOptionsPosition == 2:
					exitSystem(1)
				else:
					exitSystem(2)
			else:
				setMPDStatus('update',1)
		if k is 3:
			if curMenuItem > 1:
				curMenuItem = curMenuItem - 1
			else:
				curMenuItem = menuItemCount
			if curMenuItem == 1 or curMenuItem == menuItemCount:
				curMenuOptionsPosition = 1
			else:
				curMenuOptionsPosition = abs(int(s.get(menu[(curMenuItem-1)*3 + 2].lower())) - 2)
				curMenuOptionsPosition = 1
		if k is 4:
			if curMenuOptionsPosition < len(curMenuOptions):
				curMenuOptionsPosition = curMenuOptionsPosition + 1
			else:
				curMenuOptionsPosition = 1
		if k is 5:
			if curMenuItem < menuItemCount:
				curMenuItem = curMenuItem + 1
			else:
				curMenuItem = 1
			if curMenuItem == 1 or curMenuItem == menuItemCount:
				curMenuOptionsPosition = 1
			else:
				curMenuOptionsPosition = abs(int(s.get(menu[(curMenuItem-1)*3 + 2].lower())) - 2)
	if screenMode is 3:
		if k is 0:
			keyPressed = True
			screenMode = 0
			return
		if k is 1:                        #volume up
			setMPDStatus('volume',1)
		if k is 2:
			keyPressed = True
			setMPDStatus('play',1)        #play/pause
			screenMode = 0
			return
		if k is 3:
			keyPressed = True
			setMPDStatus("previous",1)    #play previous song
			screenMode = 0
			return
		if k is 4:                        #volume down
			setMPDStatus('volume',0)
		if k is 5:                        #play next song
			keyPressed = True
			setMPDStatus("next",1)
			screenMode = 0
			return
			
# Start Player
print "Init..."
# Global settings
screenMode        = 0
keyPressed        = False
isClosing         = False
isHD              = False
# MPD Status
isRepeat          = isRandom = isSingle  = isConsume = playState = ""
nowPlaying        = theAlbum = curArtist = ""
theVolume         = "80"
theTime           = "1:1"       #1:1=100%
# Other status
playList          = []          #empty playlist
curPage           = 1           #current page of playlist
pageCount         = 1           #page count of playlist
maxScreenLines    = 4           #lines display on screen
actualScreenLines = 0           #actual lines of screen 
screenList        = []          #empty lines of screen
cursorPosition    = 1           #cursor position of playlist on screen
previousSong      = ""          #previous song filename
timeBefAni        = 8           #when swich to a new song,display animation after 8 seconds
lastEventTime     = time.time()
# Font Settings
fontTitle         = ImageFont.truetype('/usr/share/fonts/opentype/SourceHanSansCN-Light.otf', 18)
fontMain           = ImageFont.truetype('/usr/share/fonts/opentype/SourceHanSansCN-Light.otf', 13)
fontSmall         = ImageFont.truetype('/usr/share/fonts/truetype/ttf-dejavu/DejaVuSansMono.ttf', 10)
# Menu & Menu language Settings
menuEnglish       = ['Close','HALT|REBOOT|EXIT','','Random','ON|OFF','Random','Single','ON|OFF','Single',
			'Repeat','ON|OFF','Repeat','Consume','ON|OFF','Consume','Update Playist','YES','']
menuChinese       = ['关机','关机|重启|退出','','随机播放','开|关','random','单曲播放','开|关','single',
			'循环播放','开|关','repeat','播完即删','开|关','consume','更新播放列表','确定','']
menu              = menuChinese  #Set menu language to Chinese
menuItemCount     = len(menu)/3  #calc item first
curMenuItem       = 1            #current menu item (default:halt)
curMenuOptions    = []           #current menu options of current menu
curMenuOptionsPosition = 1       #the position of current menu options
# IconData of satus screen size:6x6 pixel[x1,y1,x2,y2....]
triangle          = [2,1,2,2,2,3,2,4,2,5,2,6,3,2,3,3,3,4,3,5,4,3,4,4]
iconMenu          = [2,1,3,1,4,1,5,1,1,2,6,2,1,3,3,3,4,3,6,3,1,4,3,4,4,4,6,4,1,5,6,5,2,6,3,6,4,6,5,6]
iconOrder         = [1,1,3,1,4,1,5,1,6,1,1,3,3,3,4,3,5,3,6,3,1,5,3,5,4,5,5,5,6,5]
iconRandom        = [1,1,3,1,5,1,2,2,4,2,6,2,1,3,3,3,5,3,2,4,4,4,6,4,1,5,3,5,5,5,2,6,4,6,6,6]
iconSingle        = [2,1,3,1,4,1,5,1,2,2,2,3,3,3,4,3,5,3,5,4,5,5,2,6,3,6,4,6,5,6]
iconRepeat        = [2,1,3,1,4,1,5,1,2,2,5,2,2,3,3,3,4,3,5,3,2,4,3,4,2,5,4,5,2,6,5,6]
iconConsume       = [1,1,2,1,5,1,6,1,1,2,3,2,4,2,6,2,1,3,6,3,2,4,5,4,2,5,5,5,2,6,3,6,4,6,4,4]
iconPause         = [2,1,5,1,2,2,5,2,2,3,5,3,2,4,5,4,2,5,5,5]
iconPlay          = [2,1,2,2,3,2,2,3,3,3,4,3,2,4,3,4,4,4,2,5,3,5,2,6]
iconVolume        = [1,6,2,5,2,6,3,4,3,5,3,6,4,3,4,4,4,5,4,6,5,2,5,3,5,4,5,5,5,6,1,6,2,6,3,6,4,6,5,6,6]
initMcp()                        #init oled screen
initOled()
# Start Splash on background
lock = threading.Lock()
splash()
# Init MPD etc...
initMPDConnection()              #system initing...
setMPDStatus('consume',0)        #set consume default to off
getPlayerStates()                #get MPD curent Status
getPlaylist()                    #check and get playlist
getCurrentPlaying()              #get the song of playing
initEventTime()
print "Start..."
# Start KeyChecking thread
tKeyChecking = threading.Thread(target=checkKeyPress)
tKeyChecking.start()
# Main Loop
while(True):
	if isClosing:
		break
	if screenMode is 0:          #screen of now playing
		dispCurrentPlaying()
	if screenMode is 1:          #the playlist screen
		dispPlayList()
	if screenMode is 2:
		dispMenu()
	if screenMode is 3:
		dispAnimation()
# End of file