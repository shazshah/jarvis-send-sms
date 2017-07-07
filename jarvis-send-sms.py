# Author:    Shaz
# Date:      26/06/2017
# Purpose:   Send a text message using Text Local service if iPhone geographic location coordinates match specific location.
# Usage:     Save the script in a location along with the config.secrets file. Populate the
#           config.secrets file with the appropriate file. Ideally you also want to create a Cron job
#           to run the script at a set time (i run it every 5 minutes between 7am-9am).
# Version:   Mark 5

from pyicloud import PyiCloudService
import datetime
from datetime import date
import random
import urllib.request
import urllib.parse
import os
import json
import requests
from configparser import ConfigParser, ExtendedInterpolation


# ----CLASSES----
class Config_Settings(object):
    """
    A class to pull configuration settings specified in an
    appropriate txt file (like an ini file or in this case .secrets file).
    Save the config.secrets file in the same location as this script.
    """

    def custom_config(self, config_name, config_value):
        config = ConfigParser(interpolation=ExtendedInterpolation())
        config.read("config.secrets")

        check_config = config.get(config_name, config_value)
        return check_config


class Slack_Message(object):
    """
    A class to post messages to slack using specified user settings.
    Reads user settings from config.secrets file.
    """

    def post_message_to_channel(self, message):
        config_settings = Config_Settings()
        slack_incoming_webhook = config_settings.custom_config("slack_settings", "slack_incoming_webhook")
        slack_incoming_user = config_settings.custom_config("slack_settings", "slack_incoming_user")
        slack_incoming_channel = config_settings.custom_config("slack_settings", "slack_incoming_channel")

        payload = {
            "text": message,
            "username": slack_incoming_user,
            "channel": slack_incoming_channel
        }

        req = requests.post(slack_incoming_webhook, json.dumps(payload), headers={'content-type': 'application/json'})


class Text_File_Modifier(object):
    """
    A class which writes a log file to a specified location and
    creates a flag file which prevents the script from sending
    texts more than once per day.

    Log path and Flag path are read from the config.secrets file.
    """

    def date_now(self):
        now = datetime.datetime.now()
        dt_now = now.strftime("%Y-%m-%d")
        return dt_now

    def time_now(self):
        now = datetime.datetime.now().time()
        ti_now = now.strftime("%H:%M:%S")
        return ti_now

    def delete_log_file(self, file_path):
        if os.path.isfile(file_path) == True:
            count_lines = 0
            with open(file_path, 'rb') as f:
                for line in f:
                    count_lines += 1
            if count_lines == 20:
                os.remove(file_path)

    def write_log_file(self, input_string, file_path):
        delete_file = Text_File_Modifier()

        # check if a log file already exists.
        delete_file.delete_log_file(file_path)

        # create a log file with each line beginning with date/time
        log_date = Text_File_Modifier().date_now()
        log_time = Text_File_Modifier().time_now()
        text_file = open(file_path, "a")
        text_file.write("%s %s : %s \n" % (log_date, log_time, input_string))
        text_file.close()

    # check if a log file already exists and is 10 or more lines long, if true, delete.
    def delete_flag_file(self, file_path):
        log_file = Text_File_Modifier()

        # This is messy i think. Should try removing the log_file_path somehow
        config_settings = Config_Settings()
        log_file_path = config_settings.custom_config("log_settings", "log_file_path")

        if os.path.isfile(file_path) == True:
            # reading date in text file
            with open(file_path) as f:
                content = f.read().replace('\n', '')
            date_in_flag_file = datetime.datetime.strptime(content,
                                                           "%Y-%m-%d").date()  # converting string to datetime object
            if date_in_flag_file != date.today():
                # deleting flag
                os.remove(file_path)
                log_file.write_log_file("Deleted existing Flag because it has a date which is NOT today", log_file_path)
            else:
                log_file.write_log_file(
                    "Flag file with Todays date already exists; this means successfully delivered text today. Nothing to do. Exiting.",
                    log_file_path)
                exit()

    def write_flag_file(self, file_path):
        log_file = Text_File_Modifier()

        # This is messy i think. Should try removing the log_file_path somehow
        config_settings = Config_Settings()
        log_file_path = config_settings.custom_config("log_settings", "log_file_path")

        # write a flag text file with date
        if os.path.isfile(file_path) == False:
            flag_time = Text_File_Modifier().date_now()
            text_file = open(file_path, "a")
            text_file.write("%s" % (flag_time))
            text_file.close()
            log_file.write_log_file("Successfully wrote a Flag with Todays date.", log_file_path)


class Calendar_Info(object):
    """
    A class which checks the remote Devices' (i.e. iPhone) calendar
    to see if the user is on 'Holiday' or not (the default calendar in this case).
    This is in case a user is on Holiday BUT happens to be in the same location
    as their interested co-ordinates (e.g. near work but not at work).
    """

    def check_if_weekday(self):
        log_file = Text_File_Modifier()
        log_file_path = Config_Settings().custom_config("log_settings", "log_file_path")
        dt_today = datetime.date.today()
        if dt_today.isoweekday() in range(1, 6):  # check if mon-fri
            return dt_today
        else:
            log_file.write_log_file("Today is a WEEKEND day therefore I should NOT be at work...", log_file_path)
            return False

    def check_remote_calendar_for_holiday(self):
        log_file = Text_File_Modifier()
        log_file_path = Config_Settings().custom_config("log_settings", "log_file_path")
        date_today = Calendar_Info()
        config_settings = Config_Settings()

        if date_today.check_if_weekday() is not False:
            date_today = date_today.check_if_weekday()

            # get iCloud username and password from config.secrets file
            icloud_username = config_settings.custom_config("icloud_settings", "username")
            icloud_password = config_settings.custom_config("icloud_settings", "password")
            pyicloud_api = PyiCloudService(icloud_username, icloud_password)

            get_event = pyicloud_api.calendar.events(date_today, date_today)
            try:
                if get_event[0]['title'] == 'Holiday':
                    log_file.write_log_file("Remote Calendar shows I am on Holiday.", log_file_path)
                    return False  # On holiday
            except:
                log_file.write_log_file("Today is a Week Day and i am NOT on Holiday therefore I should be at work...",
                                        log_file_path)
                return True  # there is no holiday event meaning i am at work


class Device_Location(object):
    """
    A class to get a device (i.e. iPhone) position - the longitude and latitude -
    and then comparing the position to the long and lat provided in the 
    config.secrets (the position you are interested in).

    Will use the iCloud settings found in the config.secrets file.
    """

    def get_device_coordinates(self):
        log_file = Text_File_Modifier()
        config_settings = Config_Settings()
        log_file_path = config_settings.custom_config("log_settings", "log_file_path")
        successful_send_sms_flag = config_settings.custom_config("log_settings", "successful_send_sms_flag")

        work_day_week = Calendar_Info()
        config_settings = Config_Settings()

        # Before trying to get device location, check to see if the Success Flag exists with Todays Date
        # If it is today's date, exit. If it is not today's date, delete the flag.
        log_file.delete_flag_file(successful_send_sms_flag)

        # flag does not exist or the date is not today, proceed with getting device location.
        if work_day_week.check_remote_calendar_for_holiday() is True:

            # get iCloud username and password from config.secrets file
            icloud_username = config_settings.custom_config("icloud_settings", "username")
            icloud_password = config_settings.custom_config("icloud_settings", "password")
            pyicloud_api = PyiCloudService(icloud_username, icloud_password)

            my_coordinates = {}
            my_location_info = pyicloud_api.iphone.location()
            try:
                # only interested in the first 6 chars of the lat and long,
                # so need to slice them by adding to a variable as a string.
                temp_lat = str(my_location_info['latitude'])
                temp_long = str(my_location_info['longitude'])
                temp_lat_sliced = temp_lat[:6]
                temp_long_sliced = temp_long[:6]

                # add the sliced lat and long to a dictionary and return the values
                my_coordinates['latitude'] = temp_lat_sliced
                my_coordinates['longitude'] = temp_long_sliced
                log_file.write_log_file(
                    "Latitude and Longitude Coordinates have been obtained from remote device i.e. iPhone...",
                    log_file_path)
                return my_coordinates
            except TypeError as err:
                # more than likely this is a 'subscript error'. If yes then this is a problem with the API Location function.
                # The API Location function seems to be hit and miss so the subscript error happens a lot.
                log_file.write_log_file(
                    "Latitude and Longitude Coordinates have NOT been obtained from remote device i.e. iPhone... Error: ",
                    log_file_path)
                log_file.write_log_file(err, log_file_path)
                log_file.write_log_file(
                    "Recommend the script runs again (it will eventually succeed in getting the coordinates). Exiting.",
                    log_file_path)
                exit()
        else:
            log_file.write_log_file("Must be a holiday or it is the weekend. Exiting.", log_file_path)
            exit()

    def coordinates_for_my_location(self):
        log_file = Text_File_Modifier()
        log_file_path = Config_Settings().custom_config("log_settings", "log_file_path")

        config_settings = Config_Settings()

        try:
            device_coordinates = Device_Location().get_device_coordinates()
            device_lat = device_coordinates['latitude']
            device_long = device_coordinates['longitude']

            # read coordinates from config.secrets
            coordinates_to_track_lat = config_settings.custom_config("icloud_settings", "coordinates_to_track_lat")
            coordinates_to_track_long = config_settings.custom_config("icloud_settings", "coordinates_to_track_long")

            if coordinates_to_track_long == device_long and coordinates_to_track_lat == device_lat:
                log_file.write_log_file("Coordinates from Device and coordinates to track match.", log_file_path)
                return True  # device location and the location to track match
            else:
                log_file.write_log_file(
                    "Coordinates from Device and coordinates to track DO NOT match. Means I am not at a location I care about. Exiting.",
                    log_file_path)
                exit()  # device location and the location to track do not match, do nothing.
        except Exception as err:
            log_file.write_log_file(
                "There is a problem adding the device GPS co-ordinates, probably failed to get them to begin with. Error:",
                log_file_path)
            log_file.write_log_file(err, log_file_path)


class Send_Text_Message(object):
    """
    A class which sends a text message using TxtLocal.
    Will use the TxtLocal settings found in config.secrets.
    """

    def write_message_to_send(self):
        # check if a message has been passed as a config.secrets parameter, if not choose a random message from list
        config_settings = Config_Settings()
        text_local_message = config_settings.custom_config("txtlocal_settings", "text_local_message")
        if text_local_message == "":
            message = [
                "Hello. This is Jarvis. I would like to inform you Shaz has arrived safely at work",
                "Madame, Shaz is at work now. Thank you, Jarvis.",
                "Morning, I am happy to report your husband has arrived at work. Jarvis.",
                "Great news madame, Shaz has reached work safely. Jarvis.",
                "Shaz is at work. Thank you. Jarvis."
            ]

            random_message = random.choice(message)
            return random_message
        else:
            return text_local_message

    def send_text(self, testing=False):
        # Read the users txtlocal info from config.secrets
        config_settings = Config_Settings()
        uname = config_settings.custom_config("txtlocal_settings", "text_local_username")
        apihash = config_settings.custom_config("txtlocal_settings", "text_local_api_hash")
        numbers = config_settings.custom_config("txtlocal_settings", "text_local_number_to_text")
        sender = config_settings.custom_config("txtlocal_settings", "text_local_sender_name")

        log_file_and_flag = Text_File_Modifier()
        log_file_path = config_settings.custom_config("log_settings", "log_file_path")
        successful_send_sms_flag = config_settings.custom_config("log_settings", "successful_send_sms_flag")

        my_coordinates = Device_Location().coordinates_for_my_location()
        message = Send_Text_Message().write_message_to_send()
        slack = Slack_Message()

        now = datetime.datetime.now()

        if my_coordinates == True:
            data = urllib.parse.urlencode(
                {'username': uname, 'hash': apihash, 'numbers': numbers, 'message': message, 'sender': sender,
                 'test': testing})
            data = data.encode('utf-8')
            request = urllib.request.Request("http://api.txtlocal.com/send/?")
            f = urllib.request.urlopen(request, data)
            fr = f.read()

            log_file_and_flag.write_flag_file(successful_send_sms_flag)  # create a flag file to record success
            log_file_and_flag.write_log_file("Successfully sent SMS message.", log_file_path)

            slack.post_message_to_channel("Successully sent SMS Message: " + message)
            return (fr)
        else:
            log_file_and_flag.write_log_file(
                "Attempted to send a text regardless but something happened. See above log for potential cause... To be honest you're screwed.",
                log_file_path)
            slack.post_message_to_channel(
                "Attempted to send a text sms but something went wrong, check logs in specified log path found in config settings.")


# ----MAIN----
# Initialise objects
sendSMS = Send_Text_Message()

# Begin
print(sendSMS.send_text(testing=True))  # if testing=True, only a slack message is sent (no SMS)