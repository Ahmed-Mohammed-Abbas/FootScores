from Plugins.Plugin import PluginDescriptor
from Screens.MessageBox import MessageBox

def main(session, **kwargs):
    session.open(MessageBox, "Hello! This is my first Enigma2 App. Made by Ahmed", MessageBox.TYPE_INFO)

def Plugins(**kwargs):
    return [
        PluginDescriptor(
            name="My First Ahmed App",
            description="Simple Hello World From Ahmed",
            where=PluginDescriptor.WHERE_PLUGINMENU,
            fnc=main
        )
    ]