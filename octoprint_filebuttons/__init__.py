# coding=utf-8
from __future__ import absolute_import, unicode_literals

import octoprint.plugin
import RPi.GPIO as GPIO
import os

bouncetime_button = 250

class FileButtonsPlugin(octoprint.plugin.StartupPlugin,
					  octoprint.plugin.ShutdownPlugin):

    def on_after_startup(self):
        self._logger.info("FileButtons %s on_after_startup!", self._plugin_version)
        self._logger.info(self._printer.get_state_id())
        self._logger.info(GPIO.RPI_INFO)
        self.setup_GPIO()


    def button_callback(self, channel):
    	self._logger.info("FileButtons button callback channel {}".format(channel))
    	self._printer.commands("M117 FileButtons channel {0}".format(channel))


    def setup_GPIO(self):
        GPIO.setwarnings(False)
        GPIO.setmode(GPIO.BOARD)
        setup_GPIO_pin(36)
        setup_GPIO_pin(38)
        setup_GPIO_pin(40)


    def setup_GPIO_pin(self, channel):
        try:
            if channel != -1:
            	global bouncetime_button
                GPIO.setup(channel, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
                GPIO.add_event_detect(channel, GPIO.RISING, callback=self.button_callback, bouncetime = bouncetime_button)
                self._logger.info("New Event Detect has been added to GPIO # %s", channel)
        except:
            self._logger.exception("Cannot setup GPIO ports %s, check to makes sure you don't have the same ports assigned to multiple actions", str(channel))


    def on_shutdown(self):
        GPIO.cleanup()
        self._logger.info("FileButtons on_shutdown")

    def get_update_information(self):
        return dict(
            OctoBuddy=dict(
                displayName=self._plugin_name,
                displayVersion=self._plugin_version,
                type="github_release",
                current=self._plugin_version,
                user="barrettj",
                repo="Octoprint-FileButtons",

                pip="https://github.com/barrettj/Octoprint-FileButtons/archive/{target_version}.zip"
			)
		)

__plugin_pythoncompat__ = ">=2.7,<4"


def __plugin_load__():
    global __plugin_implementation__
    __plugin_implementation__ = FileButtonsPlugin()

    global __plugin_hooks__
    __plugin_hooks__ = {
        "octoprint.plugin.softwareupdate.check_config": __plugin_implementation__.get_update_information
    }
