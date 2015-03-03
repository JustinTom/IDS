"""
Steps for installing watchdog

Step 1: Download pip at url below, call it get-pip.py
https://bootstrap.pypa.io/get-pip.py

Then run: # python get-pip.py
Finally # pip install watchdog
"""

#!/usr/bin/python
import time
import string
import re
import os
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from threading import Thread
from time import sleep






class User(object):
    ip = ""
    timestampArray = []


    def __init__(self, ip, timestampArray):
        self.ip = ip
        self.timestampArray = timestampArray







def make_User(ip, timestampArray):
    user = User(ip, timestampArray)
    return user
    

def add_timestamp(user, timestamp):
    user.timestampArray.append(timestamp)


def block_User(user, IPADDRESS):
    global banTime
    print IPADDRESS + "Has been banned for " + str(banTime) + " seconds."
    os.system("iptables -A INPUT -j DROP -p tcp --destination-port 22 -s"+ str(IPADDRESS))
    thread = Thread(target = threaded_function, args = (user, IPADDRESS))
    thread.start()
    thread.join()

def threaded_function(user, IPADDRESS):
    global banTime
    sleep(banTime)
    os.system("iptables -D INPUT -j DROP -p tcp --destination-port 22 -s"+ str(IPADDRESS))
    print ("Now Unblocking this user: " + IPADDRESS)


def ip_toString(ip):
    return str(ip).translate(string.maketrans('',''), '[]')








class MyHandler(FileSystemEventHandler):
    global incorrectAttempts
    global bannedIps
    global numberOfAttempts


    def on_modified(self, event):
      
        if event.src_path == "/var/log/secure":
            fileHandle = open ( '/var/log/secure')
            lineList = fileHandle.readlines()
            lastLine = lineList[len(lineList)-1]


            if 'Failed password for' in lastLine:
                timestampArray = []  
                ip = re.findall( r'[0-9]+(?:\.[0-9]+){3}', lastLine )
                timestamp = re.findall(r'\d{2}:\d{2}:\d{2}', lastLine)
                
                
                
                if not incorrectAttempts:
                    user = make_User(ip, timestampArray)
                    add_timestamp(user, timestamp)

                    incorrectAttempts.append(user)
                    print "Added New User"

                    if len(user.timestampArray) >= numberOfAttempts:
                        IPADDRESS = ip_toString(user.ip)
                        block_User(user, IPADDRESS)


                else:
                    
                    isnewuser = 0
                    for user in incorrectAttempts:  
                        if user.ip == ip:
                            if timestamp not in user.timestampArray:
                                print "User Already Exists, Adding Timestamp"
                                add_timestamp(user, timestamp)
                                print user.timestampArray
                                isnewuser = 1
                                
                                if len(user.timestampArray) >= numberOfAttempts:
                                    IPADDRESS = ip_toString(user.ip)
                                    block_User(user, IPADDRESS)


                    if isnewuser == 0:   
                        print "Added New User"
                        user = make_User(ip, timestampArray)
                        add_timestamp(user, timestamp)
                        incorrectAttempts.append(user)
                        print user.ip
                        print user.timestampArray
                        
                

       

if __name__ == "__main__":
    banTime = input ("Enter how many seconds to ban an IP: ")
    numberOfAttempts = input ("Enter how many fails until we ban an IP: ")
    event_handler = MyHandler()
    observer = Observer()
    observer.schedule(event_handler, path='/var/log', recursive=False)
    observer.start()
    incorrectAttempts = []
    bannedIps = []
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()