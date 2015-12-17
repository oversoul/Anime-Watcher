import os
import sys
from PyQt4 import QtCore, QtGui, uic
import MySQLdb
import gobject
import gst


gobject.threads_init()
ui = uic.loadUiType("app.ui")[0]
db = MySQLdb.connect("localhost", "root", "root", "dbname")


def on_sync_message(bus, message, window_id):
        if not message.structure is None:
            if message.structure.get_name() == 'prepare-xwindow-id':
                image_sink = message.src
                image_sink.set_property('force-aspect-ratio', True)
                image_sink.set_xwindow_id(window_id)



player = gst.element_factory_make('playbin2', 'player')
# player.set_property('volume', 10) # set volume 1 -> 10
player.set_state(gst.STATE_NULL)
player.set_property('video-sink', None)


class MyWindowClass(QtGui.QMainWindow, ui):
    def __init__(self, parent=None):
        QtGui.QMainWindow.__init__(self, parent)
        self.setupUi(self)
        self.fillAnimesList()
        self.animes_list.doubleClicked.connect(self.fillEpisodesList)
        self.episodes_list.doubleClicked.connect(self.playEpisode)
        player_holder = self.player_holder
        player_holder.setMinimumWidth(600)
        self.window_id = player_holder.winId()
        self.timeline.setValue(0)
        self.timeline.valueChanged.connect(self.on_slider_change)
        self.play_pause.clicked.connect(self.playOrPause)
        self.volume.setValue(player.get_property('volume'))
        self.volume.valueChanged.connect(self.change_volume)
        self.stop.clicked.connect(self.stop_video)


    def fillAnimesList(self):
        cursor = db.cursor()
        cursor.execute("""SELECT name FROM animes""")
        animes = cursor.fetchall()
        for anime in animes:
            self.animes_list.addItem(anime[0])

    def fillEpisodesList(self):
        name = self.animes_list.currentItem().text()
        cursor = db.cursor()
        cursor.execute("""SELECT id FROM animes WHERE name = %s""", [name])
        anime = cursor.fetchone()
        cursor = db.cursor()
        cursor.execute("""SELECT slug FROM episodes WHERE anime_id = %s""", [anime[0]])
        episodes = cursor.fetchall()
        self.episodes_list.clear()
        for episode in episodes:
            self.episodes_list.addItem(episode[0])

    def playEpisode(self):
        slug = self.episodes_list.currentItem().text()
        cursor = db.cursor()
        cursor.execute("""SELECT link FROM episodes WHERE slug = %s""", [slug])
        link = cursor.fetchone()[0]
        # reset player
        player.set_state(gst.STATE_NULL)
        player.set_property('uri', False)
        if link != '':
            print link
            player.set_property('uri', link)
            player.set_state(gst.STATE_PLAYING)
            self.play_pause.setText('Pause')
            bus = player.get_bus()
            bus.add_signal_watch()
            bus.enable_sync_message_emission()
            bus.connect('sync-message::element', on_sync_message, self.window_id)
            gobject.timeout_add(100, self.update_slider)
        else:
            print "no link found for ", slug


    def update_slider(self):
        if self.play_pause.text() == 'Play':
            return True
        nanosecs, format = player.query_position(gst.FORMAT_TIME)
        duration_nanosecs, format = player.query_duration(gst.FORMAT_TIME)
        # block seek handler so we don't seek when we set_value()
        self.timeline.blockSignals(True)
        self.timeline.setMaximum(float(duration_nanosecs) / gst.SECOND)
        self.timeline.setValue(float(nanosecs) / gst.SECOND)
        self.timeline.blockSignals(False)
        return True

    def on_slider_change(self):
        seek_time_secs = self.timeline.value()
        player.seek_simple(gst.FORMAT_TIME, gst.SEEK_FLAG_FLUSH | gst.SEEK_FLAG_KEY_UNIT, seek_time_secs * gst.SECOND)

    def change_volume(self):
        player.set_property('volume', self.volume.value() / 10)

    def playOrPause(self):
        if self.play_pause.text() == 'Play':
            player.set_state(gst.STATE_PLAYING)
            self.play_pause.setText('Pause')
        else:
            player.set_state(gst.STATE_PAUSED)
            self.play_pause.setText('Play')

    def stop_video(self):
        player.set_state(gst.STATE_READY)
        self.timeline.setValue(0)
        self.play_pause.setText('Play')

app = QtGui.QApplication(sys.argv)
myWindow = MyWindowClass(None)
myWindow.show()
app.exec_()
