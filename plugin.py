# -*- coding: utf-8 -*-
from Plugins.Plugin import PluginDescriptor
from Screens.Screen import Screen
from Screens.MessageBox import MessageBox
from Screens.ChoiceBox import ChoiceBox
from Screens.VirtualKeyBoard import VirtualKeyBoard
from Components.ActionMap import ActionMap
from Components.Label import Label
from Components.ScrollLabel import ScrollLabel
from enigma import eTimer
import os
import json
import time
import calendar
from datetime import datetime, timedelta # CHANGED: Added timedelta

# Networking imports
try:
    from urllib2 import Request, urlopen
except ImportError:
    from urllib.request import Request, urlopen

# Configuration file
CONFIG_FILE = "/etc/enigma2/footscores_config.json"

def loadConfig():
    default = {
        "filter_league": "PL", 
        "league_name": "Premier League (England)",
        "api_key": ""
    }
    try:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'r') as f:
                saved = json.load(f)
                default.update(saved)
                
            # Safety check - remove "ALL" if present
            if default.get("filter_league") == "ALL":
                default["filter_league"] = "PL"
                default["league_name"] = "Premier League (England)"
    except:
        pass
    return default

def saveConfig(config):
    try:
        with open(CONFIG_FILE, 'w') as f:
            json.dump(config, f)
        return True
    except:
        return False

# --- SCREEN 1: MAIN WINDOW (CENTER) ---
class FootballScoresScreen(Screen):
    skin = """
        <screen position="center,center" size="700,520" title="Live Football Scores">
            <widget name="scores" position="10,10" size="680,350" font="Regular;20" />
            <widget name="league_info" position="10,370" size="680,30" font="Regular;18" halign="center" foregroundColor="#ff0000" />
            <widget name="status" position="10,410" size="680,50" font="Regular;16" halign="center" />
            
            <widget name="credit" position="10,480" size="200,30" font="Regular;16" halign="left" foregroundColor="#ffcc00" />
            <widget name="key_green" position="220,480" size="150,30" font="Regular;16" halign="center" foregroundColor="#00ff00" />
            <widget name="key_yellow" position="380,480" size="150,30" font="Regular;16" halign="center" foregroundColor="#ffff00" />
            <widget name="key_blue" position="540,480" size="150,30" font="Regular;16" halign="right" foregroundColor="#00aaff" />
        </screen>
    """
    
    def __init__(self, session, shared_data=None, live_only_mode=False):
        Screen.__init__(self, session)
        self.session = session
        self.config = loadConfig()
        
        # State variables
        self.last_data = shared_data 
        self.live_only = live_only_mode
        
        self["scores"] = ScrollLabel("")
        self["league_info"] = Label("")
        self["status"] = Label("Initializing...")
        self["credit"] = Label("By Reali22")
        self["key_green"] = Label("Green: Mini Mode")
        self["key_yellow"] = Label("Yellow: Live Only")
        self["key_blue"] = Label("Blue: API Key")
        
        self["actions"] = ActionMap(["OkCancelActions", "DirectionActions", "ColorActions"],
        {
            "ok": self.close,
            "cancel": self.close,
            "up": self.pageUp,
            "down": self.pageDown,
            "red": self.selectLeague,
            "green": self.switchToBar,
            "yellow": self.toggleLiveMode,
            "blue": self.changeApiKey,
        }, -1)
        
        self.timer = eTimer()
        self.timer.callback.append(self.fetchScores)
        self.onLayoutFinish.append(self.startPlugin)
    
    def startPlugin(self):
        self.updateLeagueInfo()
        self.updateYellowButtonLabel()
        
        api_key = self.config.get("api_key", "")
        
        if not api_key or len(api_key) < 5:
            self.displayApiKeyPrompt()
        else:
            if self.last_data:
                self.displayScores(self.last_data)
                self.timer.start(60000, True)
            else:
                self.fetchScores()

    def toggleLiveMode(self):
        self.live_only = not self.live_only
        self.updateYellowButtonLabel()
        if self.last_data:
            self.displayScores(self.last_data)

    def updateYellowButtonLabel(self):
        if self.live_only:
            self["key_yellow"].setText("Yellow: Show All")
        else:
            self["key_yellow"].setText("Yellow: Live Only")

    def displayApiKeyPrompt(self):
        try:
            self.session.openWithCallback(
                self.apiKeyEntered, 
                VirtualKeyBoard, 
                title="Enter Football-Data.org API Key:", 
                text=self.config.get("api_key", "")
            )
        except Exception as e:
            self["scores"].setText("Error opening keyboard: " + str(e))

    def apiKeyEntered(self, result):
        if result:
            self.config["api_key"] = result.strip()
            saveConfig(self.config)
            self["status"].setText("Key saved. Loading matches...")
            self.fetchScores()
        else:
            if not self.config.get("api_key"):
                self["scores"].setText("API Key is required.\n\nPress BLUE button to enter key.")
                self["status"].setText("Missing API Key")

    def changeApiKey(self):
        self.displayApiKeyPrompt()
    
    def switchToBar(self):
        self.session.open(FootballScoresBar, self.last_data, self.live_only)
        self.close()

    def updateLeagueInfo(self):
        league_name = self.config.get("league_name", "Premier League")
        self["league_info"].setText("Filter: " + league_name)
    
    def pageUp(self):
        self["scores"].pageUp()
    
    def pageDown(self):
        self["scores"].pageDown()
    
    def selectLeague(self):
        leagues = [
            ("Premier League (England)", "PL"),
            ("La Liga (Spain)", "PD"),
            ("Serie A (Italy)", "SA"),
            ("Bundesliga (Germany)", "BL1"),
            ("Ligue 1 (France)", "FL1"),
            ("Eredivisie (Netherlands)", "DED"),
            ("Primeira Liga (Portugal)", "PPL"),
            ("Championship (England)", "ELC"),
            ("UEFA Champions League", "CL"),
            ("UEFA Europa League", "EL"),
            ("FIFA World Cup", "WC"),
            ("European Championship", "EC"),
        ]
        self.session.openWithCallback(self.leagueSelected, ChoiceBox, title="Select League Filter", list=leagues)
    
    def leagueSelected(self, choice):
        if choice is None: return
        self.config["filter_league"] = choice[1]
        self.config["league_name"] = choice[0]
        saveConfig(self.config)
        self.updateLeagueInfo()
        self.fetchScores()

    def fetchScores(self):
        try:
            api_key = self.config.get("api_key", "")
            if not api_key:
                self["status"].setText("Error: No API Key")
                return

            # --- DATE CALCULATION FIX ---
            try:
                now = datetime.now()
            except:
                now = datetime.fromtimestamp(time.time())

            today_str = now.strftime("%Y-%m-%d")
            
            # Logic: If it's early morning (00:00 to 06:00), fetch Yesterday + Today
            # This ensures matches that started late last night are still visible.
            if now.hour < 6:
                yesterday = now - timedelta(days=1)
                date_from_str = yesterday.strftime("%Y-%m-%d")
                date_to_str = today_str
            else:
                date_from_str = today_str
                date_to_str = today_str

            filter_code = self.config.get("filter_league", "PL")
            base_url = "https://api.football-data.org/v4/"
            
            # Construct URL with dateFrom and dateTo
            if filter_code != "ALL":
                url = base_url + "competitions/" + filter_code + "/matches?dateFrom=" + date_from_str + "&dateTo=" + date_to_str
            else:
                url = base_url + "competitions/PL/matches?dateFrom=" + date_from_str + "&dateTo=" + date_to_str
            
            req = Request(url)
            req.add_header('X-Auth-Token', api_key)
            response = urlopen(req, timeout=10)
            data_string = response.read()
            
            try: data_string = data_string.decode('utf-8')
            except: pass
            
            data = json.loads(data_string)
            self.last_data = data 
            self.displayScores(data)
            self.timer.start(60000, True)
            
        except Exception as e:
            err_msg = str(e)
            if "403" in err_msg:
                 self["status"].setText("Error: Invalid API Key")
                 self["scores"].setText("Your API key was rejected.\nPress BLUE to enter a new one.")
            else:
                self["status"].setText("Error: " + err_msg[:40])
                self["scores"].setText("Connection error.\nWait 60s...")

    def displayScores(self, data):
        try:
            matches = data.get("matches", [])
            display_matches = []
            
            if self.live_only:
                for m in matches:
                    if m.get("status") in ["IN_PLAY", "PAUSED"]:
                        display_matches.append(m)
                mode_text = "LIVE ONLY"
            else:
                display_matches = matches
                mode_text = "ALL MATCHES"

            if not display_matches:
                if self.live_only:
                    self["scores"].setText("No LIVE matches right now.\n\nPress YELLOW to see Scheduled/Finished matches.")
                else:
                    self["scores"].setText("No matches found.\nLeague: " + self.config.get("league_name", "Unknown"))
                
                self["status"].setText("Mode: " + mode_text + " | 0 Matches")
                return
            
            output = ""
            count = 0
            
            for match in display_matches:
                home = match.get("homeTeam", {}).get("name", "Unknown")
                away = match.get("awayTeam", {}).get("name", "Unknown")
                status = match.get("status", "SCHEDULED")
                score = match.get("score", {}).get("fullTime", {})
                h_sc = str(score.get("home")) if score.get("home") is not None else "0"
                a_sc = str(score.get("away")) if score.get("away") is not None else "0"
                
                if status == "FINISHED":
                    line = "%s %s-%s %s (FT)" % (home, h_sc, a_sc, away)
                elif status in ["IN_PLAY", "PAUSED"]:
                    minute = str(match.get("minute", ""))
                    line = "%s %s-%s %s (%s')" % (home, h_sc, a_sc, away, minute)
                else:
                    utc_date_str = match.get("utcDate", "")
                    try:
                        dt_utc = datetime.strptime(utc_date_str.replace("Z", ""), "%Y-%m-%dT%H:%M:%S")
                        timestamp = calendar.timegm(dt_utc.timetuple())
                        local_struct = time.localtime(timestamp)
                        time_str = time.strftime("%H:%M", local_struct)
                    except:
                        time_str = utc_date_str[11:16] if len(utc_date_str) > 16 else "TBD"
                        
                    line = "%s vs %s (%s)" % (home, away, time_str)
                
                output += line + "\n"
                count += 1
                
            self["scores"].setText(output)
            self["status"].setText("Mode: " + mode_text + " | Found: " + str(count) + " | Upd: Now")
            
        except Exception as e:
            self["scores"].setText("Display Error: " + str(e))

class FootballScoresBar(FootballScoresScreen):
    skin = """
        <screen position="center,900" size="1900,150" flags="wfNoBorder" backgroundColor="#40000000" title="FootScores Bar">
            <widget name="scores" position="20,10" size="1860,100" font="Regular;24" foregroundColor="#ffffff" transparent="1" />
            <widget name="status" position="20,110" size="1860,30" font="Regular;20" foregroundColor="#dddddd" transparent="1" />
            
            <widget name="league_info" position="3000,3000" size="10,10" />
            <widget name="credit" position="3000,3000" size="10,10" />
            <widget name="key_green" position="3000,3000" size="10,10" />
            <widget name="key_yellow" position="3000,3000" size="10,10" />
            <widget name="key_blue" position="3000,3000" size="10,10" />
        </screen>
    """

    def __init__(self, session, shared_data=None, live_only_mode=False):
        FootballScoresScreen.__init__(self, session, shared_data, live_only_mode)
        
        self["actions"] = ActionMap(["OkCancelActions", "DirectionActions", "ColorActions"],
        {
            "ok": self.close,
            "cancel": self.close,
            "up": self.pageUp,
            "down": self.pageDown,
            "red": self.selectLeague,
            "green": self.switchToMain,
            "yellow": self.toggleLiveMode,
            "blue": self.changeApiKey,
        }, -1)

    def switchToMain(self):
        self.session.open(FootballScoresScreen, self.last_data, self.live_only)
        self.close()

def main(session, **kwargs):
    session.open(FootballScoresScreen)

def Plugins(**kwargs):
    return [
        PluginDescriptor(
            name="Football Scores",
            description="Live scores with Mini-Bar mode",
            where=PluginDescriptor.WHERE_PLUGINMENU,
            icon="plugin.png",
            fnc=main
        )
    ]
