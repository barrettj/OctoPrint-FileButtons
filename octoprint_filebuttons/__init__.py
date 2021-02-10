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

        self.currentFolderSelection = -2

    def on_after_startup(self):
        self._logger.info("FileButtons %s on_after_startup!", self._plugin_version)
        self._logger.info(self._printer.get_state_id())
        self._logger.info(GPIO.RPI_INFO)
        self.setup_GPIO()


    def button_callback(self, channel):
    	self._logger.info("FileButtons button callback channel {}".format(channel))
    	# self._printer.commands("M117 FileButtons - {0}".format(channel))

        # if we aren't connected try connected; our main communication mechanism is the printer display so we're DOA if we can't do that
        if self._printer.is_closed_or_error():
            self._printer.connect()
            return

        # require a minimum time between events
        if time.time() < self.nextEventCanHappenAt:
            return

        jobData = self._printer.get_current_job()
        hasJob = jobData["file"]["path"] != None

        # if we're printing (only action is all three to cancel, otherwise bail)
        if self._printer.is_printing():
            if GPIO.input(self.leftChannel) and GPIO.input(self.centerChannel) and GPIO.input(self.rightChannel):
                self._printer.commands("M117 Canceling Print")
                self._printer.cancel_print()
                self.set_next_event_timer_long()
            
            return

        # if we aren't printing continue below

        if channel == self.centerChannel:
            if GPIO.input(self.leftChannel):
                # center while holding left - load newest file
                self.load_newest_file_of_folder()
                self.set_next_event_timer_long()

            elif GPIO.input(self.rightChannel):
                self._printer.commands("M117 {} Center While Right".format(self.eventNumber))
                self.set_next_event_timer_long()

            else:
                if hasJob:
                    self.start_current_job()
                else:
                    if self.currentFolderSelection == -2:
                        self.display_select_folder_message()
                    else:
                        self.select_current_folder()
            
        elif channel == self.leftChannel:
            if GPIO.input(self.rightChannel) and hasJob:
                self.reset_folder_selection()
            else:
                if hasJob:
                    self.load_previous_file_in_current_folder()
                else:
                    self.show_previous_folder_selection()

        elif channel == self.rightChannel:
            if GPIO.input(self.leftChannel) and hasJob:
                self.reset_folder_selection()
            else:
                if hasJob:
                    self.load_next_file_in_current_folder()
                else:
                    self.show_next_folder_selection()

        else:
            self._printer.commands("M117 {} Unknown Button".format(self.eventNumber))
            self.set_next_event_timer_short()

    def start_current_job(self):
        #self._printer.commands("M117 Would Start Job")
        self._printer.start_print()
        
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

        # figure out the index of the previous file (looping)
        currentIndexIntoSorted = sortedFiles.index(currentName)
        nextIndex = currentIndexIntoSorted - 1
        if nextIndex == -1:
            nextIndex = len(sortedFiles) - 1

        # store the info for the next file
        nextFileInfo = filesOnly[sortedFiles[nextIndex]]
        nextASCIIName = nextFileInfo["name"]
        nextPath = nextFileInfo["path"]

        # select the file
        self._printer.select_file(nextPath, isSD)

        # update the printer display to let us know it worked
        self._printer.commands("M117 Loaded {0}".format(nextASCIIName))

        self.set_next_event_timer_short()

    def display_select_folder_message(self):
        self._printer.commands("M117 Select Folder")
        self.set_next_event_timer_short()

    def reset_folder_selection(self):
        self._printer.unselect_file()
        self.currentFolderSelection = -2
        self.display_select_folder_message()
        self.set_next_event_timer_long()

    def show_next_folder_selection(self):
        self.currentFolderSelection = self.currentFolderSelection + 1
        if self.currentFolderSelection >= len(self.folder_list()):
            self.currentFolderSelection = -1
        self.update_folder_selection_display()

    def show_previous_folder_selection(self):
        self.currentFolderSelection = self.currentFolderSelection - 1
        if self.currentFolderSelection <= -2:
            self.currentFolderSelection = len(self.folder_list()) - 1
        self.update_folder_selection_display()

    def update_folder_selection_display(self):
        if self.currentFolderSelection == -1:
            self._printer.commands("M117 Root Folder")
        else:
            folder = self.folder_list()[self.currentFolderSelection]
            self._printer.commands("M117 {}".format(folder))
        self.set_next_event_timer_short()

    def select_current_folder(self):
        if self.currentFolderSelection == -1:
            self.load_first_file_of_folder()
        else:
            folder = self.folder_list()[self.currentFolderSelection]
            self.load_first_file_of_folder(folder)
        self.set_next_event_timer_short()

    def folder_list(self):
        filesAndFolders = self._file_manager.list_files(path="", recursive=False)["local"]

        # filter the list to have just the folders
        foldersOnly = {}
        for key, node in filesAndFolders.items():
            if node["type"] == "folder":
                foldersOnly[key] = node

        # sort the files in the desired manner
        sortedFolders = sorted(foldersOnly.keys())

        return sortedFolders

    def load_first_file_of_folder(self, folder = "", origin = "local"):
        jobData = self._printer.get_current_job()

        isSD = origin != "local"
        
        # get all the files and folders in the current folder
        currentFoldersFilesAndFolders = self._file_manager.list_files(path=folder, recursive=False)[origin]

        # filter the list to have just the files - can't use filter on list_files because it seems to always include folders
        filesOnly = {}
        for key, node in currentFoldersFilesAndFolders.items():
            if node["type"] != "folder":
                filesOnly[key] = node

        # sort the files in the desired manner
        sortedFiles = sorted(filesOnly.keys())

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

    def load_newest_file_of_folder(self, folder = "", origin = "local"):
        isSD = origin != "local"
        
        # get all the files and folders in the current folder
        currentFoldersFilesAndFolders = self._file_manager.list_files(path=folder, recursive=False)[origin]

        newestFile = currentFoldersFilesAndFolders.values()[0] # start with assuming the first file is the newest, it's probably not though
        for key, node in currentFoldersFilesAndFolders.items():
            if node["type"] != "folder" and node["date"] > newestFile["date"]:
                newestFile = node

        newestASCIIName = newestFile["name"]
        newestPath = newestFile["path"]

        # select the file
        self._printer.select_file(newestPath, isSD)

        # update the printer display to let us know it worked
        self._printer.commands("M117 Loaded {0}".format(newestASCIIName))

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
