This is the first application I, Reali22, have developed to display the results of currently ongoing matches in a simple and smooth manner, so you don't need to use your phone while following the matches.
For Enigma2 devices.
The application was built, and the plugin was tested on my personal device VU+ Zero4k.
OpenBH 5.6 image.

Note: You need an API key for the plugin to work by registering on the www.football-data.org/client/register website.
The process is easy; you just need to register on the site, and the key will be sent to your email.

Enter the API key when running the plugin by pressing the blue button on the remote control.
You can choose matches according to each tournament by pressing the red button on the remote control.
You can also change the display of match results as a bar at the bottom of the screen by pressing the green button on the remote control.
You can also display results for ongoing matches only by pressing the yellow button on the remote control.

Download the FootScores files from the repo.


Installation is just extracting the zip file to the path:
usr/lib/enigma2/python/Plugins/Extensions/

telnet: cd /tmp && wget https://github.com/Ahmed-Mohammed-Abbas/FootScores/archive/refs/heads/main.zip && unzip main.zip && cp -r FootScores-main/* /usr/lib/enigma2/python/Plugins/Extensions/ 


New Version (1.1)
Enhancements include:

- Automatically request an update to the plugin when a new version is available.
- New background mode, shows notification bar only when goals scored.
- Increased the font size.
- The mini bar mode shows 3 Matches in each row.
- Legues updated to only the free tier of Data-Football.org.
- Goal and Goal Disallow notifications.

New Version (1.2)
Add sound support and update plugin version.

Download & Place the Goal Sound
You need to put your goal.mp3 file in the specific folder defined in your code (SOUND_FILE).

File Name: goal.mp3

Target Directory: /etc/enigma2/

Installation Command (via Telnet/SSH): If you want to download the plugin.py directly to your box using the terminal, you can run this command:

# 1. Create the folder
mkdir -p /usr/lib/enigma2/python/Plugins/Extensions/FootScores

# 2. Download the plugin file
wget https://raw.githubusercontent.com/Ahmed-Mohammed-Abbas/FootScores/main/plugin.py -O /usr/lib/enigma2/python/Plugins/Extensions/FootScores/plugin.py

# 3. download goal.mp3 to your repo, download it to the right place:
wget https://raw.githubusercontent.com/Ahmed-Mohammed-Abbas/FootScores/main/goal.mp3 -O /etc/enigma2/goal.mp3
