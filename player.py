# coding=UTF-8
###########################################################################
# PiCobber Oled Player Program (V0.9 Stable) By FishX (http://weibo.com/2731710965)
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
import sys
import time
import threading
import subprocess
import mpd
import Adafruit_GPIO as GPIO
import Adafruit_GPIO.SPI as SPI
import Adafruit_GPIO.MCP230xx as Raspi_MCP230XX
import Adafruit_SSD1306
import Image
import ImageDraw
import ImageFont
from   time import sleep

# Init control keys
def initMcp():
	global mcp
	mcp = Raspi_MCP230XX.MCP23008(address = 0x20)
	for i in range(0,6):
		mcp.setup(i,GPIO.IN)
		mcp.pullup(i,True)
	mcp.setup(6,GPIO.OUT)
	mcp.output(6,GPIO.HIGH)                         # LED OUTPUT HIGH (off)
	
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
	mcp.output(6,GPIO.HIGH)
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
		return '开' if v else '关'
	else:
		return 'ON' if v else 'OFF'
	
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
	draw.bitmap((1,1),iconMenu,1)
	if int(isSingle):
		draw.bitmap((13,1),iconSingle,1)
	if int(isRepeat):
		draw.bitmap((25,1),iconRepeat,1)
	if int(isRandom):
		draw.bitmap((37,1),iconRandom,1)
	else:
		draw.bitmap((37,2),iconOrder,1)
	if int(isConsume):
		draw.bitmap((49,1),iconConsume,1)
	if playState == "play":
		draw.bitmap((122,1),iconPause,1)
	else:
		draw.bitmap((122,1),iconPlay,1)
	draw.bitmap((109,1),iconVolume,1)
	vol = int(float(theVolume) * 6 / 100)
	draw.rectangle((109+vol,1,116,7),outline=0,fill=0)
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
		draw.bitmap((92,1),iconHD,1)
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
	draw.bitmap((1,1),iconMenu,1)
	draw.text((9,0),'(' + str(curPage) + '/' + str(pageCount) + ')',font = fontSmall,fill = 255)
	for i in range(0,actualScreenLines):
		draw.text((8,(i+1) * 13 - 2),u(screenList[i]),font = fontMain,fill = 255)
	#draw triangle on the left
	draw.bitmap((1,(cursorPosition) * 13 + 2),iconTriangle,1)
	oled.image(image)
	oled.display()

# Draw settings menu on the screen
def dispMenu():
	global screenMode,curMenuItem,curMenuOptions,curMenuOptionsPosition
	getPlayerStates()
	draw.rectangle((0,0,127,63),outline=0,fill=0)
	draw.bitmap((1,1),iconMenu,1)
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
			draw.bitmap((92,1),iconHD,1)
		#if int(time.time()) % 2 is 1:
		#	fmtTime = '%H:%M'
		#else:
		#	fmtTime = '%H %M'
		#draw.text((0,55), time.strftime(fmtTime,time.gmtime()), font=fontSmall, fill=255)
		draw.text((0 - i,24),info,font=fontTitle,fill=255)
		oled.image(image)
		oled.display()
		mcp.output(6,GPIO.HIGH)
		getPlayerStates()
		if int(theTime.split(":")[0]) - int(theTime.split(":")[1]) is 0:
			sleep(2)
			break;
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
		for i in range(0,6):
			if mcp.input(i) is GPIO.LOW:
				mcp.output(6,GPIO.LOW)
				k(i)
		sleep(0.2)
		mcp.output(6,GPIO.HIGH)
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
iconTriangle      = Image.open('icon/iconTriangle.pbm').convert('1')
iconMenu          = Image.open('icon/iconMenu.pbm').convert('1')
iconOrder         = Image.open('icon/iconOrder.pbm').convert('1')
iconRandom        = Image.open('icon/iconRandom.pbm').convert('1')
iconSingle        = Image.open('icon/iconSingle.pbm').convert('1')
iconRepeat        = Image.open('icon/iconRepeat.pbm').convert('1')
iconConsume       = Image.open('icon/iconConsume.pbm').convert('1')
iconPause         = Image.open('icon/iconPause.pbm').convert('1')
iconPlay          = Image.open('icon/iconPlay.pbm').convert('1')
iconVolume        = Image.open('icon/iconVolume.pbm').convert('1')
iconHD            = Image.open('icon/iconHD.pbm').convert('1')

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