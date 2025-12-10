# -*- coding: utf-8 -*-
from Plugins.Plugin import PluginDescriptor
from Screens.Screen import Screen
from Screens.MessageBox import MessageBox
from Screens.ChoiceBox import ChoiceBox
from Screens.VirtualKeyBoard import VirtualKeyBoard
from Components.ActionMap import ActionMap
from Components.Label import Label
from Components.ScrollLabel import ScrollLabel
from Screens.Standby import TryQuitMainloop 
from enigma import eTimer
import os
import json
import time
import calendar
from datetime import datetime, timedelta

# Networking imports
try:
    from urllib2 import Request, urlopen
except ImportError:
    from urllib.request import Request, urlopen

# --- CONFIGURATION & CONSTANTS ---
CONFIG_FILE = "/etc/enigma2/footscores_config.json"
PLUGIN_VERSION = "1.1" # Updated for 30s Timer + Font Tweak

# DIRECT LINKS TO YOUR REPO
UPDATE_URL = "https://raw.githubusercontent.com/Ahmed-Mohammed-Abbas/FootScores/main/version.txt"
CODE_URL = "https://raw.githubusercontent.com/Ahmed-Mohammed-Abbas/FootScores/main/plugin.py"

def loadConfig():
    default = {
        "filter_league": "PL", 
        "league_name": "Premier League",
        "api_key": ""
    }
    try:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'r') as f:
                saved = json.load(f)
                default.update(saved)
            if default.get("filter_league") == "ALL":
                default["filter_league"] = "PL"
                default["league_name"] = "Premier League"
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
    # UPDATED SKIN: FONTS REDUCED BY 15% FROM PREVIOUS VERSION
    skin = """
        <screen position="center,center" size="700,520" title="Live Football Scores">
            <widget name="scores" position="10,10" size="680,350" font="Regular;26" />
            
            <widget name="league_info" position="10,365" size="680,40" font="Regular;23" halign="center" foregroundColor="#ff0000" />
            
            <widget name="status" position="10,410" size="680,50" font="Regular;20" halign="center" />
            
            <widget name="credit" position="10,475" size="200,40" font="Regular;20" halign="left" foregroundColor="#ffcc00" />
            <widget name="key_green" position="220,475" size="150,40" font="Regular;20" halign="center" foregroundColor="#00ff00" />
            <widget name="key_yellow" position="380,475" size="150,40" font="Regular;20" halign="center" foregroundColor="#ffff00" />
            <widget name="key_blue" position="540,475" size="150,40" font="Regular;20" halign="right" foregroundColor="#00aaff" />
        </screen>
    """
    
    def __init__(self, session, shared_data=None, live_only_mode=False):
        Screen.__init__(self, session)
        self.session = session
        self.config = loadConfig()
        
        # State variables
        self.last_data = shared_data 
        self.live_only = live_only_mode
        self.score_history = {} 
        
        self["scores"] = ScrollLabel("")
        self["league_info"] = Label("")
        self["status"] = Label("Initializing...")
        self["credit"] = Label("Ver: " + PLUGIN_VERSION + " | By Reali22")
        self["key_green"] = Label("Mini Mode")
        self["key_yellow"] = Label("Live Only")
        self["key_blue"] = Label("API Key")
        
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
        
        self.update_timer = eTimer()
        self.update_timer.callback.append(self.checkUpdates)
        self.update_timer.start(3000, True) 
        
        api_key = self.config.get("api_key", "")
        
        if not api_key or len(api_key) < 5:
            self.displayApiKeyPrompt()
        else:
            if self.last_data:
                self.displayScores(self.last_data)
                # CHANGED: Start with 30s interval
                self.timer.start(30000, True)
            else:
                self.fetchScores()

    def formatMatchLine(self, match, is_bar_mode=False):
        home = match.get("homeTeam", {}).get("name", "Unknown")
        away = match.get("awayTeam", {}).get("name", "Unknown")
        status = match.get("status", "SCHEDULED")
        score = match.get("score", {}).get("fullTime", {})
        
        h_int = score.get("home") if score.get("home") is not None else 0
        a_int = score.get("away") if score.get("away") is not None else 0
        
        h_sc = str(h_int)
        a_sc = str(a_int)
        match_id = match.get("id", 0)
        
        current_score_str = "%s-%s" % (h_sc, a_sc)
        
        is_goal = False
        is_disallowed = False

        if match_id in self.score_history:
            old_score_str = self.score_history[match_id]
            if old_score_str != current_score_str:
                try:
                    old_parts = old_score_str.split('-')
                    old_total = int(old_parts[0]) + int(old_parts[1])
                    new_total = h_int + a_int
                    
                    if new_total < old_total:
                        is_disallowed = True
                    else:
                        is_goal = True
                except:
                    is_goal = True
        
        self.score_history[match_id] = current_score_str
        
        if is_bar_mode:
            home = home[:10]
            away = away[:10]

        if status == "FINISHED":
            line = "%s %s-%s %s (FT)" % (home, h_sc, a_sc, away)
        elif status in ["IN_PLAY", "PAUSED"]:
            minute = str(match.get("minute", ""))
            line = "%s %s-%s %s (%s')" % (home, h_sc, a_sc, away, minute)
            
            if is_disallowed:
                line = ">>> GOAL DISALLOWED! <<< " + line
            elif is_goal:
                line = ">>> GOAL <<< " + line
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
            
        return line

    def checkUpdates(self):
        try:
            no_cache_url = UPDATE_URL + "?t=" + str(int(time.time()))
            req = Request(no_cache_url)
            response = urlopen(req, timeout=5)
            remote_version = response.read().decode('utf-8').strip()
            
            if float(remote_version) > float(PLUGIN_VERSION):
                self.session.openWithCallback(
                    self.askUpdate, 
                    MessageBox, 
                    "New Update Available!\n\nLocal Ver: " + PLUGIN_VERSION + "\nOnline Ver: " + remote_version + "\n\nDo you want to update and restart now?", 
                    MessageBox.TYPE_YESNO
                )
        except:
            pass

    def askUpdate(self, result):
        if result:
            self.performUpdate()

    def performUpdate(self):
        try:
            self["status"].setText("Updating... Please wait.")
            no_cache_code = CODE_URL + "?t=" + str(int(time.time()))
            req = Request(no_cache_code)
            response = urlopen(req, timeout=20)
            new_code = response.read()
            
            target_path = os.path.abspath(__file__)
            if target_path.endswith("pyc"):
                target_path = target_path[:-1] 
            
            with open(target_path, "wb") as f:
                f.write(new_code)
                
            self.session.open(MessageBox, "Update Successful!\nGUI will restart now...", MessageBox.TYPE_INFO, timeout=3)
            self.restart_timer = eTimer()
            self.restart_timer.callback.append(self.doRestart)
            self.restart_timer.start(3000, True)
            
        except Exception as e:
            self.session.open(MessageBox, "Update Failed:\n" + str(e), MessageBox.TYPE_ERROR)

    def doRestart(self):
        self.session.open(TryQuitMainloop, 3)

    def toggleLiveMode(self):
        self.live_only = not self.live_only
        self.updateYellowButtonLabel()
        if self.last_data:
            self.displayScores(self.last_data)

    def updateYellowButtonLabel(self):
        if self.live_only:
            self["key_yellow"].setText("Show All")
        else:
            self["key_yellow"].setText("Live Only")

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
            ("Premier League", "PL"),
            ("Champions League", "CL"),
            ("Primera Division", "PD"),
            ("Serie A", "SA"),
            ("Bundesliga", "BL1"),
            ("Ligue 1", "FL1"),
            ("Eredivisie", "DED"),
            ("Campeonato Brasileiro", "BSA"),
            ("Championship", "ELC"),
            ("Primeira Liga", "PPL"),
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

            try:
                now = datetime.now()
            except:
                now = datetime.fromtimestamp(time.time())

            today_str = now.strftime("%Y-%m-%d")
            
            if now.hour < 6:
                yesterday = now - timedelta(days=1)
                date_from_str = yesterday.strftime("%Y-%m-%d")
                date_to_str = today_str
            else:
                date_from_str = today_str
                date_to_str = today_str

            filter_code = self.config.get("filter_league", "PL")
            base_url = "https://api.football-data.org/v4/"
            
            if filter_code != "ALL":
                url = base_url + "competitions/" + filter_code + "/matches?dateFrom=" + date_from_str + "&dateTo=" + date_to_str
            else:
                url = base_url + "competitions/PL/matches?dateFrom=" + date_from_str + "&dateTo=" + date_to_str
            
            req = Request(url)
            req.add_header('X-Auth-Token', api_key)
            
            response = urlopen(req, timeout=30)
            data_string = response.read()
            
            try: data_string = data_string.decode('utf-8')
            except: pass
            
            data = json.loads(data_string)
            self.last_data = data 
            self.displayScores(data)
            
            # CHANGED: 30000 ms (30 Seconds)
            self.timer.start(30000, True)
            
        except Exception as e:
            err_msg = str(e)
            if "403" in err_msg:
                 self["status"].setText("Error: Invalid API Key")
                 self["scores"].setText("Your API key was rejected.")
            elif "429" in err_msg:
                 self["status"].setText("Error: Too Many Requests")
                 self["scores"].setText("API Limit Reached (Free Tier).\nWait a moment...")
                 # Retry in 2 minutes
                 self.timer.start(120000, True)
            else:
                self["status"].setText("Error: " + err_msg[:40])
                self["scores"].setText("Connection error: " + err_msg + "\n\nRetrying in 30s...")
                # Retry in 30 seconds
                self.timer.start(30000, True)

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
                line = self.formatMatchLine(match, is_bar_mode=False)
                output += line + "\n"
                count += 1
            
            # CHANGED: ADDED TIMESTAMP TO STATUS
            current_time = time.strftime("%H:%M:%S")
            self["scores"].setText(output)
            self["status"].setText("Mode: " + mode_text + " | Found: " + str(count) + " | Last Upd: " + current_time)
            
        except Exception as e:
            self["scores"].setText("Display Error: " + str(e))


# --- SCREEN 2: MINI BAR (BOTTOM - Grid View) ---
class FootballScoresBar(FootballScoresScreen):
    skin = """
        <screen position="center,930" size="1900,150" flags="wfNoBorder" backgroundColor="#40000000" title="FootScores Bar">
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
                    self["scores"].setText("No LIVE matches right now.")
                else:
                    self["scores"].setText("No matches found.")
                self["status"].setText("Mode: " + mode_text + " | 0 Matches")
                return
            
            match_strings = []
            count = 0
            
            for match in display_matches:
                line = self.formatMatchLine(match, is_bar_mode=True)
                match_strings.append(line)
                count += 1
            
            output = ""
            for i in range(0, len(match_strings), 3):
                chunk = match_strings[i:i+3]
                row_string = "   |   ".join(chunk)
                output += row_string + "\n"

            # CHANGED: ADDED TIMESTAMP TO STATUS
            current_time = time.strftime("%H:%M:%S")
            self["scores"].setText(output)
            self["status"].setText("Mode: " + mode_text + " | Found: " + str(count) + " | Last Upd: " + current_time)
            
        except Exception as e:
            self["scores"].setText("Display Error: " + str(e))

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
