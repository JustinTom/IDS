"""

Step 1: Download pip at url below, call it get-pip.py

https://bootstrap.pypa.io/get-pip.py




Then run: 

# python get-pip.py


After install run: 


# pip install watchdog


"""

#!/usr/bin/python
import time
import re
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler



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






class MyHandler(FileSystemEventHandler):
    global incorrectAttempts
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
                    print user.ip
                    print user.timestampArray
                    print "New User Added with that timestamp"

                else:
                    
                    isnewuser = 0

                    for user in incorrectAttempts:  
                        if user.ip == ip:
                            if timestamp not in user.timestampArray:
                                print "User already Exists, we added a timestamp to them"



                                """
                                    check if the timestampArray > 3
                                        if it is:
                                            block them

                                            add them to the blockedusers array



                                """



                                add_timestamp(user, timestamp)
                                print user.timestampArray
                                isnewuser = 1
                                

                    if isnewuser == 0:   
                        print "We Just added a new user"
                        user = make_User(ip, timestampArray)
                        add_timestamp(user, timestamp)
                        incorrectAttempts.append(user)
                        print user.ip
                        print user.timestampArray
                        
                




       

if __name__ == "__main__":
    event_handler = MyHandler()
    observer = Observer()
    observer.schedule(event_handler, path='/var/log', recursive=False)
    observer.start()
    incorrectAttempts = []
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()

