# coding=utf-8
from __future__ import absolute_import, unicode_literals

import octoprint.plugin
import RPi.GPIO as GPIO
import os
import time

class FileButtonsPlugin(octoprint.plugin.StartupPlugin,
					  octoprint.plugin.ShutdownPlugin,
                      octoprint.plugin.RestartNeedingPlugin):

    def __init__(self):
        self.leftChannel = 40
        self.centerChannel = 38
        self.rightChannel = 36

        self.nextEventCanHappenAt = time.time()

        self.eventNumber = 0

    def on_after_startup(self):
        self._logger.info("FileButtons %s on_after_startup!", self._plugin_version)
        self._logger.info(self._printer.get_state_id())
        self._logger.info(GPIO.RPI_INFO)
        self.setup_GPIO()


    def button_callback(self, channel):
    	self._logger.info("FileButtons button callback channel {}".format(channel))
    	# self._printer.commands("M117 FileButtons - {0}".format(channel))

        # don't bother doing anything if not connected we can't really display to the printer which is our main feedback mechanism
        if self._printer.is_closed_or_error():
            return

        # require a minimum time between events
        if time.time() < self.nextEventCanHappenAt:
            return

        jobData = self._printer.get_current_job()
        hasJob = jobData["file"]["path"] != None

        if channel == self.centerChannel:
            if GPIO.input(self.leftChannel):
                self._printer.commands("M117 {} Center While Left".format(self.eventNumber))
                self.set_next_event_timer_long()

            elif GPIO.input(self.rightChannel):
                self._printer.commands("M117 {} Center While Right".format(self.eventNumber))
                self.set_next_event_timer_long()

            else:
                if hasJob:
                    self.start_current_job()
                else:
                    self._printer.commands("M117 {} Center Button".format(self.eventNumber))
                    self.set_next_event_timer_long()
            
        elif channel == self.leftChannel:
            if  GPIO.input(self.rightChannel):
                self._printer.commands("M117 {} Left While Right".format(self.eventNumber))
                self.set_next_event_timer_long()

            else:
                if hasJob:
                    self.load_previous_file_in_current_folder()
                else:
                    self._printer.commands("M117 {} Left Button".format(self.eventNumber))
                    self.set_next_event_timer_short()

        elif channel == self.rightChannel:
            if GPIO.input(self.leftChannel):
                self._printer.commands("M117 {} Right While Left".format(self.eventNumber))
                self.set_next_event_timer_long()

            else:
                if hasJob:
                    self.load_next_file_in_current_folder()
                else:
                    self._printer.commands("M117 {} Right Button".format(self.eventNumber))
                    self.set_next_event_timer_short()

        else:
            self._printer.commands("M117 {} Unknown Button".format(self.eventNumber))
            self.set_next_event_timer_short()

    def start_current_job(self):
        self._printer.commands("M117 Would Start Job")
        self.set_next_event_timer_long()

    def load_next_file_in_current_folder(self):
        jobData = self._printer.get_current_job()

        # we have a job - save some information about the current file
        origin = jobData["file"]["origin"]
        isSD = origin != "local"
        currentPath = jobData["file"]["path"]
        currentName = jobData["file"]["name"]
        currentDisplayName = jobData["file"]["display"]
        currentFolder = os.path.dirname(jobData["file"]["path"])
        
        # get all the files and folders in the current folder
        currentFoldersFilesAndFolders = self._file_manager.list_files(path=currentFolder, recursive=False)[origin]

        # filter the list to have just the files - can't use filter on list_files because it seems to always include folders
        filesOnly = {}
        for key, node in currentFoldersFilesAndFolders.items():
            if node["type"] != "folder":
                filesOnly[key] = node

        # sort the files in the desired manner
        sortedFiles = sorted(filesOnly.keys())

        # figure out the index of the next file (looping)
        currentIndexIntoSorted = sortedFiles.index(currentName)
        nextIndex = currentIndexIntoSorted + 1
        if nextIndex == len(sortedFiles):
            nextIndex = 0

        # store the info for the next file
        nextFileInfo = filesOnly[sortedFiles[nextIndex]]
        nextASCIIName = nextFileInfo["name"]
        nextPath = nextFileInfo["path"]

        # select the file
        self._printer.select_file(nextPath, isSD)

        # update the printer display to let us know it worked
        self._printer.commands("M117 Loaded {0}".format(nextASCIIName))

        self.set_next_event_timer_short()

    def load_previous_file_in_current_folder(self):
        jobData = self._printer.get_current_job()

        # we have a job - save some information about the current file
        origin = jobData["file"]["origin"]
        isSD = origin != "local"
        currentPath = jobData["file"]["path"]
        currentName = jobData["file"]["name"]
        currentDisplayName = jobData["file"]["display"]
        currentFolder = os.path.dirname(jobData["file"]["path"])
        
        # get all the files and folders in the current folder
        currentFoldersFilesAndFolders = self._file_manager.list_files(path=currentFolder, recursive=False)[origin]

        # filter the list to have just the files - can't use filter on list_files because it seems to always include folders
        filesOnly = {}
        for key, node in currentFoldersFilesAndFolders.items():
            if node["type"] != "folder":
                filesOnly[key] = node

        # sort the files in the desired manner
        sortedFiles = sorted(filesOnly.keys())

        # figure out the index of the next file (looping)
        currentIndexIntoSorted = sortedFiles.index(currentName)
        nextIndex = currentIndexIntoSorted - 1
        if nextIndex == -1:
            nextIndex = len(sortedFiles)

        # store the info for the next file
        nextFileInfo = filesOnly[sortedFiles[nextIndex]]
        nextASCIIName = nextFileInfo["name"]
        nextPath = nextFileInfo["path"]

        # select the file
        self._printer.select_file(nextPath, isSD)

        # update the printer display to let us know it worked
        self._printer.commands("M117 Loaded {0}".format(nextASCIIName))

        self.set_next_event_timer_short()


    def set_next_event_timer_short(self):
        self.nextEventCanHappenAt = time.time() + 0.1
        self.eventNumber = self.eventNumber + 1

    def set_next_event_timer_long(self):
        self.nextEventCanHappenAt = time.time() + 1.0
        self.eventNumber = self.eventNumber + 1

    def setup_GPIO(self):
        GPIO.setwarnings(False)
        GPIO.setmode(GPIO.BOARD)
        self.setup_GPIO_pin(self.leftChannel)
        self.setup_GPIO_pin(self.centerChannel)
        self.setup_GPIO_pin(self.rightChannel)
        self._logger.info("FileButtons GPIO setup complete")


    def setup_GPIO_pin(self, channel):
        try:
            if channel != -1:
                GPIO.setup(channel, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
                GPIO.add_event_detect(channel, GPIO.RISING, callback=self.button_callback, bouncetime = 250)
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
