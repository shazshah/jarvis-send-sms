#Author:    Shaz
#Date:      17/09/2016
#Purpose:   Send a text message to a friend using Text Local service if iPhone geographic location coordinates match specific location.
#Usage:     Save the script in a location (any), modify the accompanying com.xxxx.plist
#           so that it points to this script file. Copy the plist into /Library/LaunchDaemons using sudo.
#           Load the plist using sudo launchctl load -w /Library/LaunchDaemons/xxxxx.plist. By default the
#           property file is configured to run every 5 minutes between 7.40am-8.40am weekday.
#           Remember to remove the TEST parameter - otherwise an SMS will not be sent.
#Version:   Mark 3

from pyicloud import PyiCloudService
import datetime
from datetime import date
import time
import random
import urllib.request
import urllib.parse
import os

#----GLOBAL VARIABLES - CHANGE THESE----
pyicloud_api = PyiCloudService('yourappleid@goeshere.com', 'YourApplePasswordGoesHere')

text_local_username = 'YourTextLocalUsername'
text_local_api_hash = 'YourTextLocalAPI'
text_local_number_to_text = '44712341234124'
text_local_sender_name = 'Jarvis'
text_local_message = ""

coordinates_to_track_lat = "12.345"
coordinates_to_track_long = "-1.234"

log_file_path = "/Users/YourUserName/jarvis-send-sms/jarvis_send_sms-log.txt"
successful_send_sms_flag = "/Users/YourUserName/jarvis-send-sms/jarvis_send_sms-run-successfully-flag.txt"
#----END----

#----CLASSES----
class Text_File_Modifier(object):
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
            with open (file_path, 'rb') as f:
                for line in f:
                    count_lines += 1
            if count_lines == 20:
                os.remove(file_path)

    def write_log_file(self, input_string, file_path):
        delete_file = Text_File_Modifier()

        #check if a log file already exists.
        delete_file.delete_log_file(file_path)

        #create a log file with each line beginning with date/time
        log_date = Text_File_Modifier().date_now()
        log_time = Text_File_Modifier().time_now()
        text_file = open(file_path, "a")
        text_file.write("%s %s : %s \n" % (log_date, log_time, input_string))
        text_file.close()

    #check if a flag file already exists and if it has a date which is NOT TODAY.
    def delete_flag_file(self, file_path):
        log_file = Text_File_Modifier()
        if os.path.isfile(file_path) == True:
            #reading date in text file
            with open(file_path) as f:
                content = f.read().replace('\n', '')
            date_in_flag_file = datetime.datetime.strptime(content, "%Y-%m-%d").date() #converting string to datetime object
            if date_in_flag_file != date.today():
                #deleting flag
                os.remove(file_path)
                log_file.write_log_file("Deleted existing Flag because it has a date which is NOT today", log_file_path)
            else:
                log_file.write_log_file("Flag file with Todays date already exists; this means successfully delivered text today. Nothing to do. Exiting.", log_file_path)
                exit()


    def write_flag_file(self, file_path):
        log_file = Text_File_Modifier()
        #write a flag text file with today date
        if os.path.isfile(file_path) == False:
            flag_time = Text_File_Modifier().date_now()
            text_file = open(file_path, "a")
            text_file.write("%s" % (flag_time))
            text_file.close()
            log_file.write_log_file("Successfully wrote a Flag with Todays date.", log_file_path)

class Calendar_Info(object):
    def check_if_weekday(self):
        log_file = Text_File_Modifier()
        dt_today = datetime.date.today()
        if dt_today.isoweekday() in range(1, 6): #check if mon-fri
            return dt_today
        else:
            log_file.write_log_file("Today is a WEEKEND day therefore I should NOT be at work...", log_file_path)
            return False

    def check_remote_calendar_for_holiday(self):
        log_file = Text_File_Modifier()
        date_today = Calendar_Info()
        if date_today.check_if_weekday() is not False:
            date_today = date_today.check_if_weekday()
            get_event = pyicloud_api.calendar.events(date_today, date_today)
            try:
                if get_event[0]['title'] == 'Holiday':
                    log_file.write_log_file("Remote Calendar shows I am on Holiday.", log_file_path)
                    return False # On holiday
            except:
                log_file.write_log_file("Today is a Week Day and i am NOT on Holiday therefore I should be at work...", log_file_path)
                return True #there is no holiday event meaning i am at work

class Device_Location(object):
    def get_device_coordinates(self):    
        log_file = Text_File_Modifier()
        work_day_week = Calendar_Info()

        #Before trying to get device location, check to see if the Success Flag exists with Todays Date
        #If it is today, exit. If it is not today, delete the flag.
        log_file.delete_flag_file(successful_send_sms_flag)

        #flag does not exist or the date is not today, proceed with getting device location.
        if work_day_week.check_remote_calendar_for_holiday() is True:
            my_coordinates = {}
            my_location_info = pyicloud_api.iphone.location()
            try:
                #only interested in the first 6 chars of the lat and long,
                #so need to slice them by adding to a variable as a string.
                temp_lat = str(my_location_info['latitude'])
                temp_long = str(my_location_info['longitude'])
                temp_lat_sliced = temp_lat[:6]
                temp_long_sliced = temp_long[:6]

                #add the sliced lat and long to a dictionary and return the values
                my_coordinates['latitude'] = temp_lat_sliced
                my_coordinates['longitude'] = temp_long_sliced
                log_file.write_log_file("Latitude and Longitude Coordinates have been obtained from remote device i.e. iPhone...", log_file_path)
                return my_coordinates
            except TypeError as err:
                #more than likely this is a 'subscript error'. If yes then this is a problem with the API Location function.
                #The API Location function seems to be hit and miss so the subscript error happens a lot.
                log_file.write_log_file("Latitude and Longitude Coordinates have NOT been obtained from remote device i.e. iPhone... Error: ", log_file_path)
                log_file.write_log_file(err, log_file_path)
                log_file.write_log_file("Recommend the script runs again (it will eventually succeed in getting the coordinates). Exiting.", log_file_path)
                exit()
        else:
            log_file.write_log_file("Must be a holiday or it is the weekend. Exiting.", log_file_path)
            exit()

    def coordinates_for_my_location(self):
        log_file = Text_File_Modifier()

        try:
            device_coordinates = Device_Location().get_device_coordinates()
            device_lat = device_coordinates['latitude']
            device_long = device_coordinates['longitude']

            if coordinates_to_track_long == device_long and coordinates_to_track_lat == device_lat:
                log_file.write_log_file("Coordinates from Device and coordinates to track match.", log_file_path)
                return True #device location and the location to track match
            else:
                log_file.write_log_file("Coordinates from Device and coordinates to track DO NOT match. Means I am not at a location I care about. Exiting.", log_file_path)
                exit() #device location and the location to track do not match, do nothing.
        except Exception as err:
            log_file.write_log_file("There is a problem adding the device GPS co-ordinates, probably failed to get them to begin with. Error:", log_file_path)
            log_file.write_log_file(err, log_file_path)

class Send_Text_Message(object):
    def write_message_to_send(self):
        #declare the global variable as 'global' because otherwise get an unbound error.
        global text_local_message

        #check if a message has been passed as a function parameter, if not choose a random message from list
        if text_local_message == "":
            message = [
                "Hello. This is Jarvis. I would like to inform you Shaz has arrived safely at work", 
                "Madame, Shaz is at work now. Thank you, Jarvis.", 
                "Morning, I am happy to report your husband has arrived at work. Jarvis.",
                "Great news Sir, Shaz has reached work safely. Jarvis.",
                "Shaz is at work. Thank you. Jarvis."
            ]

            random_message = random.choice(message)
            return random_message
        else:
            return text_local_message


    def send_text(self, uname, hashCode, numbers, sender):
        log_file_and_flag = Text_File_Modifier()
        my_coordinates = Device_Location().coordinates_for_my_location()
        message = Send_Text_Message().write_message_to_send()

        now = datetime.datetime.now()

        if my_coordinates == True:
            data =  urllib.parse.urlencode({'username': uname, 'hash': hashCode, 'numbers': numbers, 'message' : message, 'sender': sender, 'test': True})
            data = data.encode('utf-8')
            request = urllib.request.Request("http://api.txtlocal.com/send/?")
            f = urllib.request.urlopen(request, data)
            fr = f.read()
            log_file_and_flag.write_flag_file(successful_send_sms_flag) #create a flag file to record success
            log_file_and_flag.write_log_file("Successfully sent SMS message.", log_file_path)
            return(fr)
        else:
            log_file_and_flag.write_log_file("Attempted to send a text regardless but something happened. See above log for potential cause... To be honest you're screwed.", log_file_path)

#----MAIN----
#Initialise objects
sendSMS = Send_Text_Message()

#Begin
print(sendSMS.send_text(text_local_username, text_local_api_hash, text_local_number_to_text, text_local_sender_name))
