# coding=utf-8
from __future__ import absolute_import, unicode_literals

import octoprint.plugin
import RPi.GPIO as GPIO
import os

class FileButtonsPlugin(octoprint.plugin.StartupPlugin,
					  octoprint.plugin.ShutdownPlugin,
                      octoprint.plugin.RestartNeedingPlugin):

    def __init__(self):
        self.leftChannel = 40
        self.centerChannel = 38
        self.rightChannel = 36

        self.leftPressed = False
        self.centerPressed = False
        self.rightPressed = False

    def on_after_startup(self):
        self._logger.info("FileButtons %s on_after_startup!", self._plugin_version)
        self._logger.info(self._printer.get_state_id())
        self._logger.info(GPIO.RPI_INFO)
        self.setup_GPIO()


    def button_rising_callback(self, channel):
    	self._logger.info("FileButtons rising button callback channel {}".format(channel))
    	# self._printer.commands("M117 FileButtons - {0}".format(channel))

        if channel == self.centerChannel:
            if self.centerPressed:
                return
            else:
                self.centerPressed = True

            if self.leftPressed:
                self._printer.commands("M117 Center While Left")
            elif self.rightPressed:
                self._printer.commands("M117 Center While Right")
            else:
                self._printer.commands("M117 Center Button")
        elif channel == self.leftChannel:
            if self.leftPressed:
                return
            else:
                self.leftPressed = True


            if self.rightPressed:
                self._printer.commands("M117 Left While Right")
            else:
                self._printer.commands("M117 Left Button")
        elif channel == self.rightChannel:
            if self.rightPressed:
                return
            else:
                self.rightPressed = True


            if self.leftPressed:
                self._printer.commands("M117 Right While Left")
            else:
                self._printer.commands("M117 Right Button")
        else:
            self._printer.commands("M117 Unknown Button")

    def button_falling_callback(self, channel):
        self._logger.info("FileButtons falling button callback channel {}".format(channel))
        # self._printer.commands("M117 FileButtons - {0}".format(channel))

        if channel == self.centerChannel:
            if self.centerPressed:
                self.centerPressed = False
        elif channel == self.leftChannel:
            if self.leftPressed:
                self.leftPressed = False
        elif channel == self.rightChannel:
            if self.rightPressed:
                self.rightPressed = False
        else:
            self._printer.commands("M117 Unknown Button")


    def setup_GPIO(self):
        GPIO.setwarnings(False)
        GPIO.setmode(GPIO.BOARD)
        self.setup_GPIO_pin(36)
        self.setup_GPIO_pin(38)
        self.setup_GPIO_pin(40)
        self._logger.info("FileButtons GPIO setup complete")


    def setup_GPIO_pin(self, channel):
        try:
            if channel != -1:
                GPIO.setup(channel, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
                GPIO.add_event_detect(channel, GPIO.RISING, callback=self.button_rising_callback, bouncetime = 250)
                GPIO.add_event_detect(channel, GPIO.FALLING, callback=self.button_falling_callback, bouncetime = 250)
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
