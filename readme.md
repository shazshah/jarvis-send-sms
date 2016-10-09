#Overview

The purpose of this script is to automatically send an SMS text to a recipient using a texting service (Text Local) when you are in a specific location i.e. at work.
For example, you can text a family member when you reach work automatically with a specific message. (This is what I use it for - my wife thinks Jarvis from Ironman is texting her.)

#Usage

Before doing anything else you need an iPhone and therefore an AppleID, and an account with Text Local in order to send the actual text.

If you have the above, save the script in a location (any), modify the accompanying com.xxxx.plist so that it points to this script file. Copy the plist into /Library/LaunchDaemons using sudo.

Load the plist using sudo launchctl load -w /Library/LaunchDaemons/xxxxx.plist. By default the property file is configured to run every 5 minutes between 7.40am-8.40am weekday.

The script also checks your iCloud calendar for holidays i.e. if you have an entry in your calendar for 'Holiday' the script terminates because you should not be at work and therefore there is no text to send.

#Configuration

By default you only need to modify the global variables in the python script once the Test parameter is removed (see further down about this parameter):


"pyicloud_api" - enter your appleid username and appleid password.
"text_local_username" - enter your Text Local username.
"text_local_api_hash" - enter the Text Local api hash, you'll find this in Text Local account settings.
"text_local_number_to_text" - input the number you wish to text.
"text_local_sender_name" - this can be anything but it is set to Jarvis.
"text_local_message" - input the message content. If you leave this blank, a random message from the function "write_message_to_send" will be used instead (you can modify the random messages to something else if you want).
"coordinates_to_track_lat" - Enter the latitude coordinates for the location you want to track e.g. your work place.
"coordinates_to_track_long" - Enter the longitude coordinates for the location you want to track e.g. your work place.
"log_file_path" - include a path where the log file can be saved.
"successful_send_sms_flag" - include a path where the flag file can be saved.

For safety, there is a **'Test' parameter** which is set to **True**. If you leave this as is, a text message will not be sent when the script is run. When you are ready to actually send an SMS i.e. after testing is complete, **remove** the test parameter entirely.
