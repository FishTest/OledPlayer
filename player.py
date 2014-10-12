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

import os
import time
import subprocess
import mpd
import sys
import Adafruit_GPIO.SPI as SPI
import Adafruit_SSD1306
import Image
import ImageDraw
import ImageFont
from   Raspi_MCP230xx import Raspi_MCP230XX
from   time import sleep

# init control keys
def initMcp():
	global mcp
	mcp = Raspi_MCP230XX(address = 0x20, num_gpios = 8)
	for i in range(0,6):
		mcp.config(i,mcp.INPUT)
	mcp.config(6,mcp.OUTPUT)
	mcp.output(6, 1)                         # LED OUTPUT Low (Off)
# init oled screen
def initOled():
	global oled,image,draw
	oled = Adafruit_SSD1306.SSD1306_128_64(rst=RST, dc=DC, spi=SPI.SpiDev(SPI_PORT, 
		SPI_DEVICE, max_speed_hz=8000000))
	oled.begin()
	oled.clear()
	oled.display()
	width = oled.width
	height = oled.height
	image = Image.new('1', (width, height))
	draw = ImageDraw.Draw(image)
# exit function
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
	s.replace('\n','')
	s.replace('[www.51ape.com]','')
	s.replace('[51ape.com]','')
	s.replace('Ape.Com]','')
	s.replace('file: USB//','')
	#print s
	return s
#unicode encoding
def u(s):
	return unicode(s,'utf-8')
#check current MPD status
def getCurrentPlaying():
	global nowPlaying,client,curArtist,theAlbum,previousSong,theFile,playState
	cs =  client.currentsong()
	nowPlaying = removeAD(cs.get('title',''))
	curArtist = removeAD(cs.get('artist',''))
	theAlbum = removeAD(cs.get('album',''))
	theFile = cs.get('file','')
	#judge if new song be playing (judge from file).
	if previousSong != theFile:
		initPlayTime()
	previousSong = theFile

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
	#print s
	theVolume = s.get('volume','-1')
	isConsume = s.get('consume','0')
	isRepeat  = s.get('repeat','0')
	isRandom  = s.get('random','0')
	isSingle  = s.get('single','0')
	playState = s.get('state','stop')
	theTime   = s.get('time','0:1')
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
# conver second to minute
def converSecondToMinute(s):
	return "{:0>2d}".format(s / 60) + ':' + "{:0>2d}".format(s % 60)
# update playlist
def updatePlayList():
	global client,screenMode
	client.clear()
	client.idle()
	client.update()
	client.findadd("any","")
	sleep(2)
	gotoPlaylist() 
# the time while the song changed
def initPlayTime():
	global musicChgTime
	musicChgTime = time.time()
# draw specified icon
def drawIcon(x,y,a):
	for i in range(0,len(a) / 2):
		draw.point((x + a[i*2],a[i*2+1] + y) ,fill = 255)
def dispCurrentPlaying():
	global screenMode
	draw.rectangle((0,0,127,63),outline=0,fill=0)
	getPlayerStates()               #get mpd status
	getCurrentPlaying()             #get current playing
	#jump to music info screen while playing...
	if (time.time() > (musicChgTime + timeBefAni)) and playState == "play" :
		screenMode = 3
	#draw status icons
	drawIcon(1,1,iconMenu)
	if int(isSingle):
		drawIcon(13,1,iconSingle)
	if int(isRepeat):
		drawIcon(25,1,iconRepeat)
	if int(isRandom):
		drawIcon(37,1,iconRandom)
	else:
		drawIcon(37,1,iconOrder)
	if int(isConsume):
		drawIcon(49,1,iconConsume)
	if playState == "play":
		drawIcon(120,2,iconPause)
	else:
		drawIcon(120,2,iconPlay)
	vol = int(float(theVolume) * 6 / 100)
	for i in range(0,len(iconVolume) / 2):
		if iconVolume[i*2] <= vol:
			draw.point((110 + iconVolume[i*2],iconVolume[i*2+1] + 1),fill = 255)
	draw.text((1,12),u(curArtist),font = font14 ,fill = 255)
	TitleW = draw.textsize(u(nowPlaying),font = font)[0]
	if TitleW > 128:
		TitleX = 0
	else:
		TitleX = (128 - TitleW) / 2
	draw.text((TitleX,32),u(nowPlaying),font = font ,fill = 255)
	#draw the progressbar
	percent = float(theTime.split(":")[0]) / float(theTime.split(":")[1])
	draw.rectangle((32,58,97,61),outline=255)
	draw.rectangle((33,59,33 + int(66 * percent),60),outline=255)
	#draw time
	draw.text((0,55), time.strftime('%H:%M',time.gmtime()), font=fontSmall, fill=255)
	draw.text((98,55),converSecondToMinute(int(theTime.split(":")[0])),font = fontSmall ,fill = 255)
	oled.image(image)
	oled.display()
	
# draw Playlist on screen
def dispPlayList():
	global screenMode
	getScreenList()
	draw.rectangle((0,0,127,63),outline=0,fill=0)
	#display current page of playlist
	drawIcon(1,1,iconMenu)
	draw.text((9,0),'(' + str(curPage) + '/' + str(pageCount) + ')',font = fontSmall,fill = 255)
	for i in range(0,actualScreenLines):
		draw.text((8,(i+1) * 13 - 3),u(screenList[i]),font = font14,fill = 255)
	#draw triangle on the left
	for i in range(0,len(triangle) / 2):
		drawIcon(1,(cursorPosition) * 13 + 2,triangle)
	oled.image(image)
	oled.display()
	sleep(0.1)  
# draw settings menu on the screen
def dispMenu():
	global screenMode,curMenuItem,curMenuOptions,curMenuOptionsPosition
	getPlayerStates()
	draw.rectangle((0,0,127,63),outline=0,fill=0)
	drawIcon(1,1,iconMenu)
	#print menu[(curMenuItem-1)*3+2]
	#print menu[(curMenuItem-1)*3+2]
	#print s.get(menu[(curMenuItem-1)*3+2])
	if curMenuItem > 1 and curMenuItem < menuItemCount:
		draw.text((9,1),'== ' + u(menu[(curMenuItem-1)*3]) + '(' + 
			u(numToBool(int(s.get(menu[(curMenuItem-1)*3+2].lower(),'')))) + ') =='
			,font = font14,fill = 255)
	else:
		draw.text((9,1),'== ' + u(menu[(curMenuItem-1)*3]) + ' ==',font = font14,fill = 255)
	#draw current options of current menu item
	curMenuOptions = menu[(curMenuItem-1)*3 + 1].split('|')
	for i in range(0,len(curMenuOptions)):
		if i == curMenuOptionsPosition - 1:
			draw.text((20,i*14 + 16),'-> ' + u(curMenuOptions[i]),font=font14,fill = 255)
		else:
			draw.text((20,i*14 + 16),'    ' + u(curMenuOptions[i]),font=font14,fill = 255)
	oled.image(image)
	oled.display()
	sleep(0.1)                                 #add sleep to avoid fast switch
# draw animation
def dispAnimation():
	global screenMode,musicChgTime,timeBefAni#,nowPlaying,curArtist,theAlbum
	draw.rectangle((0,0,127,63),outline=0,fill=0)
	getCurrentPlaying()
	info = u('   《' + nowPlaying + '》-' + curArtist + '-《' + theAlbum + '》')
	infoW = draw.textsize(info,font = font)[0]
	fileNow = theFile
	for i in range(0,infoW - 128):
		getCurrentPlaying()
		if theFile <> fileNow:
			screenMode = 0
			break;
		if mcp.input(0) is 0:
			mcp.output(6, 0)
			sleep(0.2)
			initPlayTime()
			screenMode = 0
			break
		if mcp.input(1) is 0:             #volume up
			setVolume(1)
			mcp.output(6, 0)
		if mcp.input(2) is 0:
			setMPDStatus('play',1)        #play/pause
			sleep(0.2)
			screenMode = 0
			mcp.output(6, 0)
			break
		if mcp.input(3) is 0:
			setMPDStatus("previous",1)    #play previous song
			sleep(0.2)
			screenMode = 0
			mcp.output(6, 0)
			break
		if mcp.input(4) is 0:             #volume down
			setVolume(0)
			mcp.output(6, 0)
		if mcp.input(5) is 0:             #play next song
			setMPDStatus("next",1)
			sleep(0.2)
			screenMode = 0
			mcp.output(6, 0)
			break;
		draw.rectangle((0,23,127,42),outline=0,fill=0)
		draw.text((0-i,24),info,font=font,fill=255)
		oled.image(image)
		oled.display()
		sleep(0.01)
		mcp.output(6,1) 
	#Start animation
	timePassed = int((time.time() - musicChgTime - timeBefAni) * 6) #Speed:6
def splash():
	draw.rectangle((0,0,127,63),outline=0,fill=0)
	draw.text((5,17),'FishX',font=fontSmall,fill=255)
	draw.text((15,30),'Picobber Player',font=fontSmall,fill=255)
	draw.text((5,43),'weibo.com/2731710965',font=fontSmall,fill=255)
	oled.image(image)
	oled.display()
	sleep(1)
print "Init..."
#Global settings
RST        = 25
DC         = 24
SPI_PORT   = 0
SPI_DEVICE = 0
screenMode = 0
#MPD Status
isRepeat   = isRandom = isSingle  = isConsume = playState = ""
nowPlaying = theAlbum = curArtist = ""
theVolume  = "80"
theTime    = "1:1"       #1:1=100%
#other status
playList   = []          #empty playlist
curPage    = 1           #current page of playlist
pageCount  = 1           #page count of playlist
maxScreenLines    = 4    #lines display on screen
actualScreenLines = 0    #actual lines of screen 
screenList        = []   #empty lines of screen
cursorPosition    = 1    #cursor position of playlist on screen
previousSong      = ""   #previous song filename
timeBefAni        = 5    #when swich to a new song,display animation after 8 seconds
musicChgTime      = time.time()
#Font Settings
font        = ImageFont.truetype('/usr/share/fonts/opentype/SourceHanSansCN-Light.otf', 16)
font14      = ImageFont.truetype('/usr/share/fonts/opentype/SourceHanSansCN-Light.otf', 14)
fontSmall   = ImageFont.truetype('/usr/share/fonts/truetype/ttf-dejavu/DejaVuSansMono.ttf', 10)
#Menu & Menu language Settings
menuEnglish = ['Close','HALT|REBOOT|EXIT','','Random','ON|OFF','Random','Single','ON|OFF','Single',
			'Repeat','ON|OFF','Repeat','Consume','ON|OFF','Consume','Update Playist','YES','']
menuChinese = ['关机','关机|重启|退出','','随机播放','开|关','random','单曲播放','开|关','single',
			'循环播放','开|关','repeat','播完即删','开|关','consume','更新播放列表','确定','']
menu        = menuChinese                       #Set menu language to Chinese
menuItemCount     = len(menu) / 3            #calc item first
curMenuItem       = 1                          #current menu item (default:halt)
curMenuOptions    = []                      #current menu options of current menu
curMenuOptionsPosition = 1               #the position of current menu options
#iconData of currentplaying screen size:6x6 pixel
triangle    = [2,1,2,2,2,3,2,4,2,5,2,6,3,2,3,3,3,4,3,5,4,3,4,4]
iconMenu    = [2,1,3,1,4,1,5,1,1,2,6,2,1,3,3,3,4,3,6,3,1,4,3,4,4,4,6,4,1,5,6,5,2,6,3,6,4,6,5,6]
iconOrder   = [1,1,3,1,4,1,5,1,6,1,1,3,3,3,4,3,5,3,6,3,1,5,3,5,4,5,5,5,6,5]
iconRandom  = [1,1,3,1,5,1,2,2,4,2,6,2,1,3,3,3,5,3,2,4,4,4,6,4,1,5,3,5,5,5,2,6,4,6,6,6]
iconSingle  = [2,1,3,1,4,1,5,1,2,2,2,3,3,3,4,3,5,3,5,4,5,5,2,6,3,6,4,6,5,6]
iconRepeat  = [2,1,3,1,4,1,5,1,2,2,5,2,2,3,3,3,4,3,5,3,2,4,3,4,2,5,4,5,2,6,5,6]
iconConsume = [1,1,2,1,5,1,6,1,1,2,3,2,4,2,6,2,1,3,6,3,2,4,5,4,2,5,5,5,2,6,3,6,4,6,4,4]
iconPause   = [2,1,5,1,2,2,5,2,2,3,5,3,2,4,5,4,2,5,5,5]
iconPlay    = [2,1,2,2,3,2,2,3,3,3,4,3,2,4,3,4,4,4,2,5,3,5,2,6]
iconVolume  = [1,6,2,5,2,6,3,4,3,5,3,6,4,3,4,4,4,5,4,6,5,2,5,3,5,4,5,5,5,6,1,6,2,6,3,6,4,6,5,6,6]

initMcp()                               #init oled screen
initOled()
initMPDConnection()                      #system initing...
setMPDStatus('consume',0)                #set consume default to off
getPlayerStates()                        #get MPD curent Status
getPlaylist()                            #check and get playlist
getCurrentPlaying()                      #get the song of playing
splash()
initPlayTime()
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
				updatePlayList()
			mcp.output(6, 0)
		if mcp.input(3) is 0:            #display previous menu item
			if curMenuItem > 1:
				curMenuItem = curMenuItem - 1
			else:
				curMenuItem = menuItemCount
			if curMenuItem == 1 or curMenuItem == menuItemCount:
				curMenuOptionsPosition = 1
			else:
				curMenuOptionsPosition = abs(int(s.get(menu[(curMenuItem-1)*3 + 2].lower())) - 2)
				curMenuOptionsPosition = 1
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
			if curMenuItem == 1 or curMenuItem == menuItemCount:
				curMenuOptionsPosition = 1
			else:
				curMenuOptionsPosition = abs(int(s.get(menu[(curMenuItem-1)*3 + 2].lower())) - 2)
			mcp.output(6, 0)
		dispMenu()
	elif screenMode is 3:
		dispAnimation()
	mcp.output(6,1)                       #Close LED
# end of file