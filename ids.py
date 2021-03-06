'''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''
--  SOURCE FILE:    ids.py - A simple monitoring application that will detect password
--                           attempts and then use iptables to block that IP.
--
--  PROGRAM:        Intrusion detection system
--                  python ids.py
--
--  FUNCTIONS:      cronJob(numberOfAttempts, timeScan, banTime), initializeParameters(), 
--                  make_User(ip, timeStampArray), add_timestamp(user, timeStamp), block_User(IPADDRESS),
--                  unblock_User(IPADDRESS), time_Convert(time)
--
--  NOTES:
--  The program will accept parameter variables through arguments passed when being executed.
--  The program will read th /var/log/secure file and detect any failed password attempts.
--  When the program detects that the password attempts have exceeded the user specified parameters,
--  will block the IP in the firewall and later unblock it if set, after a user specified amount of time.
'''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''
#!/usr/bin/python
import time
import string
import re
import os
import argparse
import sys
import threading
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

'''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''
--  FUNCTION
--  Name:       cronJob
--  Parameters:
--      numberOfAttempts
--          The total number of failed password attempts before blocking the IP
--      timeScan
--          The amount of time to use for slow scan password attempts
--      banTime
--          The time that will be passed after being blocked before the user is unblocked.
--  Return Values:
--      None
--  Description:
--      Creates the cronjob for the script to be run everytime as soon as the station boots up.
--      The cronjob will also check the /etc/crontab file and check if the same command already exists,
--      If it does, then it doesn't add a new cron job. It will also assign the crontab file in 
--      /etc/crontab to the current working crontab scheduler and run it.
'''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''  
def cronJob(numberOfAttempts, timeScan, banTime):
    checker = 0
    #Convert back the times to seconds - essentially the original command passed in terminal
    timeScan = timeScan/60
    banTime = banTime/60
    filepath = os.path.dirname(os.path.realpath(__file__))
    filename = os.path.basename(__file__)
    cronJob = '@reboot /usr/bin/python %s/%s -a %s -t %s -b %s' % (filepath, filename, numberOfAttempts, timeScan, banTime)
    with open('/etc/crontab','r') as crontab:
        for line in crontab:
            if cronJob not in line:
                if checker != 1:
                    checker = 0
            else:
                checker = 1
    if checker == 0:
        crontab = open('/etc/crontab','a')
        crontab.seek(0, 2)
        command = '@reboot /usr/bin/python %s/%s -a %s -t %s -b %s' % (filepath, filename, numberOfAttempts, timeScan, banTime)
        crontab.write(command)
        crontab.close()
    os.system('crontab /etc/crontab')

'''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''
--  FUNCTION
--  Name:       initializeParameters
--  Parameters:
--      None
--  Return Values:
--      numberOfAttempts
--          The total number of failed password attempts before blocking the IP
--      timeScan
--          The amount of time to use for slow scan password attempts
--      banTime
--          The time that will be passed after being blocked before the user is unblocked.
--  Description:
--      Function to initialize all the parameters and user specified variables through arguments
--      passed when the python script is executed through the terminal.
'''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''  
def initializeParameters():
    parser = argparse.ArgumentParser()
    parser.add_argument('-a', '--attempt', nargs=1, help='Number of failed attempts before blocking the IP.', required=True, dest='attempt')
    parser.add_argument('-t', '--time', nargs=1, help='Max time in minutes for the number of attempts in that time window before blocking the IP.', required=True, dest='time')
    parser.add_argument('-b', '--block', nargs=1, help='Time in minutes to block the IP for before unblocking. Enter 0 for indefinite IP block', required=True, dest='block')
    args = parser.parse_args()
    numberOfAttempts = int(args.attempt[0])
    #Multiply the numbers by 60 to convert the minutes to seconds
    timeScan = int(args.time[0])
    timeScan = timeScan * 60
    banTime = int(args.block[0])
    banTime = banTime * 60
    return numberOfAttempts, timeScan, banTime

'''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''
--  CLASS
--  Name:       User
--  Parameters:
--      None
--  Return Values:
--      None
--  Description:
--      Class to store "users" which are essentially different, unique hosts that
--      attempt to connect to the machine with the IDS on it. It stores both IP and
--      time stamp array of each attempt the user tries to log in.
'''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''  
class User(object):
    ip = ""
    timeStampArray = []


    def __init__(self, ip, timeStampArray):
        self.ip = ip
        self.timeStampArray = timeStampArray

'''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''
--  FUNCTION
--  Name:       make_User
--  Parameters:
--      ip
--          The IP of the host attempting to connect
--      timeStampArray
--          A list of timestamps of each attempted connection.
--  Return Values:
--      user
--          User object containing both IP and time stamp list
--  Description:
--      Creates a new user based on each newly, unique logged IP address.
'''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''  
def make_User(ip, timeStampArray):
    user = User(ip, timeStampArray)
    return user

'''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''
--  FUNCTION
--  Name:       add_timestamp
--  Parameters:
--      user
--          User object to be referenced and used to add values to
--      timeStamp
--          Time stamp of the particular event in the log file
--  Return Values:
--      None
--  Description:
--      Function to add the new timestamp of the event to the respective user's
--      time stamp array
'''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''  
def add_timestamp(user, timeStamp):
    user.timeStampArray.append(timeStamp)

'''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''
--  FUNCTION
--  Name:       block_User
--  Parameters:
--      IPADDRESS
--          The IP address of the host that raised the event in the log file.
--  Return Values:
--      None
--  Description:
--      Function block the user through an IPtables command by their IP address, blocking
--      the IP address completely - not just the port it was logged on. It calls the unblock
--      method right afterwards with the banTime as the thread sleep, allowing it to unblock
--      IP after the ban time is over.
'''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''  
def block_User(IPADDRESS):
    global banTime
    #Convert banTime back to minutes from seconds.
    banTimeTemp = banTime/60
    if banTime != 0:
        print "%s has been banned for %d minutes." % (IPADDRESS, banTimeTemp)
    else:
        print "%s has been banned forever." % IPADDRESS
    command = "/usr/sbin/iptables -A INPUT -s %s -j DROP" % IPADDRESS
    os.system(command)
    if banTime != 0:
        threading.Timer(banTime, unblock_User, [IPADDRESS]).start()

'''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''
--  FUNCTION
--  Name:       unblock_User
--  Parameters:
--      IPADDRESS
--          The IP address of the host that raised the event in the log file.
--  Return Values:
--      None
--  Description:
--      Function to remove the IPtables command that blocks that IP address.
'''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''  
def unblock_User(IPADDRESS):
    command = "/usr/sbin/iptables -D INPUT -s %s -j DROP" % IPADDRESS
    os.system(command)
    print ("User Time Ban Over - %s has been unbanned") % IPADDRESS

'''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''
--  FUNCTION
--  Name:       time_Convert
--  Parameters:
--      time
--          The time of particular time stamp list.
--  Return Values:
--      None
--  Description:
--      Function to convert the timestamp format of X:X:X to a format that is able 
--      to be operated on (multiplied, addition, etc.). This allows for easier time
--      difference calculation to determine if the attempted logins are within the 
--      user specified time scan limit.
'''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''  
def time_Convert(time):
    timeArray = time.split(':')
    hours = int(timeArray[0])
    hours = hours * 3600
    #print "TIME_CONVERT HOURS: %d" % hours
    minutes = int(timeArray[1])
    minutes = minutes * 60
    #print "TIME_CONVERT MINUTES: %d" % minutes
    seconds = int(timeArray[2])
    #print "TIME_CONVERT SECONDS: %d" % seconds
    totalTime = hours + minutes + seconds
    #print "TIME_CONVERT TOTAL TIME: %d" % totalTime
    return totalTime

class MyHandler(FileSystemEventHandler):
    global incorrectAttempts
    global bannedIps
    global numberOfAttempts

    def on_modified(self, event):
      
        if event.src_path == "/var/log/secure":
            fileHandle = open ( '/var/log/secure')
            lineList = fileHandle.readlines()
            lastLine = lineList[len(lineList)-1]
            secondLastLine = lineList[len(lineList)-2]

            if "Failed password for" in lastLine:
                timeStampArray = []  
                ip = re.findall( r'[0-9]+(?:\.[0-9]+){3}', lastLine )
                timeStamp = re.findall(r'\d{2}:\d{2}:\d{2}', lastLine)                          
                
                if not incorrectAttempts:
                    user = make_User(ip[0], timeStampArray)
                    add_timestamp(user, timeStamp[0])

                    incorrectAttempts.append(user)
                    #print "Added New User"
                    print "%s's failed login attempts time stamps (%d total): %s " % (user.ip, len(user.timeStampArray), user.timeStampArray)

                    if len(user.timeStampArray) >= numberOfAttempts:
                        IPADDRESS = user.ip[0]
                        block_User(IPADDRESS)

                else:                
                    isnewuser = 0
                    for user in incorrectAttempts:  
                        if user.ip == ip[0]:

                            if timeStamp[0] not in user.timeStampArray:
                                #print "User already exists, adding time stamp"
                                add_timestamp(user, timeStamp[0])
                                print "%s's failed login attempts time stamps (%d total): %s " % (user.ip, len(user.timeStampArray), user.timeStampArray)
                                isnewuser = 1
                                #print "Length of array: %d" % len(user.timeStampArray)
                                #print "Number of attempts before it is banned: %d" % numberOfAttempts
                                if len(user.timeStampArray) >= numberOfAttempts:
                                    arrayLength = len(user.timeStampArray)
                                    firstTimeStamp = user.timeStampArray[(arrayLength-numberOfAttempts)]
                                    lastTimeStamp = user.timeStampArray[(arrayLength-1)]
                                    firstTime = time_Convert(firstTimeStamp)
                                    lastTime = time_Convert(lastTimeStamp)
                                    timeDifference = (lastTime - firstTime)
                                    #print "Time difference: %d" % timeDifference
                                    #print "Max time to scan before blocking IP: %d" % timeScan
                                    if timeDifference <= timeScan:
                                        #IPADDRESS = ip_toString(user.ip)
                                        #print "USER IP: %s" % user.ip
                                        IPADDRESS = str(user.ip)
                                        block_User(IPADDRESS)

                    if isnewuser == 0:   
                        #print "Added New User"
                        user = make_User(ip[0], timeStampArray)
                        add_timestamp(user, timeStamp[0])
                        incorrectAttempts.append(user)
                        print "%s's failed login attempts time stamps (%d total): %s " % (user.ip, len(user.timeStampArray), user.timeStampArray)

            #Empty the time stamp array if it already exists (essentially resetting the number of attempts the user from that IP can do)
<<<<<<< HEAD
            elif ("Accepted password for" in lastLine) or ("Accepted password for" in secondLastLine): 
                ip = re.findall( r'[0-9]+(?:\.[0-9]+){3}', secondLastLine)
                #timeStamp = re.findall(r'\d{2}:\d{2}:\d{2}', lastLine)
                #print "Successful Login From: %s" % (ip)
                for user in incorrectAttempts:  
                    if user.ip == ip[0]:
                        user.timeStampArray = []


=======
            elif 'Accepted password for' in lastLine: 
                ip = re.findall( r'[0-9]+(?:\.[0-9]+){3}', lastLine)
                #timeStamp = re.findall(r'\d{2}:\d{2}:\d{2}', lastLine)
                
                if incorrectAttempts:
                    for user in incorrectAttempts:  
                        if user.ip == ip[0]:
                            timeStampArray = []
>>>>>>> origin/master

if __name__ == "__main__":
    numberOfAttempts, timeScan, banTime = initializeParameters()
    cronJob(numberOfAttempts, timeScan, banTime)
    event_handler = MyHandler()
    observer = Observer()
    observer.schedule(event_handler, path='/var/log', recursive=False)
    observer.start()
    incorrectAttempts = []
    bannedIps = []
    try:
        while True:
            time.sleep(0.01)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()
