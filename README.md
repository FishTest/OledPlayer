sudo apt-get install mpd python-dev python-pip python-smbus
sudo pip install python-mpd2

cd ~
git clone git://git.drogon.net/wiringPi
cd wiringPi
sudo ./build

cd ~
git clone https://github.com/Gadgetoid/WiringPi2-Python.git
cd WiringPi2-Python
sudo python setup.py install

cd ~
git clone https://github.com/doceme/py-spidev.git
cd py-spidev
sudo python setup.py install

cd ~
git clone https://github.com/adafruit/Adafruit_Python_SSD1306.git
cd Adafruit_Python_SSD1306
sudo python setup.py install

cd ~

sudo nano /etc/modprobe.d/raspi-blacklist.conf
#blacklist spi-bcm2708
#blacklist i2c-bcm2708
#blacklist snd-soc-pcm512x
#blacklist snd-soc-wm8804
sudo nano /etc/modules
#snd-bcm2835
i2c-dev
snd_soc_bcm2708
bcm2708_dmaengine
snd_soc_pcm5102a
snd_soc_hifiberry_dac
