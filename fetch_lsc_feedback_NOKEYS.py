#!/usr/bin/env python

# configure saving to Google Drive

### We can auto upload the file to google drive
#from google.colab import drive
#drive.mount('/content/gdrive', force_remount=True)
#root_dir = "/content/gdrive/My Drive/"
#

import requests
import zipfile
import json
import io, os
import sys
import datetime
from sys import argv

from pydrive.drive import GoogleDrive
from pydrive.auth import GoogleAuth

# Create local webserver and auto handles authentication.
# NOT USING CURRENTLY because requires interactivity
#gauth = GoogleAuth()
#gauth.LocalWebserverAuth()
#drive = GoogleDrive(gauth)

debug =  1 # set to zero to turn off printing for chron job

##########################################################################
# STEP 1. Identify start date (startDate) for fetching the data
##########################################################################

# set the date to todays date and time
mydate_simple = datetime.date.today() # yyyy-mm-dd

if len(argv) > 1:
	# get the date from the first argv
	# should be entered as 'yyyy-mm-dd'
	datetemp = argv[1]
	mydate_simple = datetime.datetime.strptime(datetemp, '%Y-%m-%d')
	if debug:
		print("\nFetching all feedback responses received since:", mydate_simple)


# If the user input a date set it to that
else:
	if debug:
		print("\nFetching all feedback responces received since:", mydate_simple)
		print("If you want to use a specific startDate enter it in the format: yyyy-mm-dd")
		print("For example: python fetch_lsc_feedback.py 2019-10-22 ")


# create file path for output
mydate_str = '_'.join([str(mydate_simple.year), str(mydate_simple.month), str(mydate_simple.day)])
filepath = "-".join(['LSC_feedback', mydate_str])

if debug:
	print("Here is the OUTPUT folder or file prefix: ", filepath)

# Set the startdate for when we will retrieve feedback in the formate needed by qualtrics
startDate = mydate_simple.strftime('%Y-%m-%dT') + '00:00:00Z'

if debug:
	print("Fetching LSC Feedback from Qualtrics begining with this startdate: %s" % startDate)

	print("\n==========================================================\n")

#
# Create output folder location
# NOT RUN... 

#if debug:
#	print("Attempting to create folder %s" % filepath)

# create folder for output
#try:
#	os.makedirs(filepath)
#	print("Created folder....\n")
#except OSError:
#	if not 'Folder exists':
#		raise
#	else:
#		print("Folder exists")
#

#########################################
# Step 2:  Set Qualtrics keys
#########################################
# These values are obtained from your qualtrics account
# Use with caution!
# This allows ANY user to fetch the data for this survey
# Not just the user with permissions to the qualtrics account
#
qualtrics_APIKEY = "ENTER_YOUR_BIG_LONG_KEY"
qualtrics_surveyId = "ENTER_YOUR_SURVEY_ID"

# Setting Qualtrics parameters
try:
    apiToken = qualtrics_APIKEY   #os.environ['APIKEY']
except KeyError:
    print("set environment variable APIKEY")
    sys.exit(2) 


#########################################
# Step 3: Setting static URL parameters
#########################################
requestCheckProgress = 0.0
progressStatus = "inProgress"
url = "https://berkeley.qualtrics.com/API/v3/surveys/{0}/export-responses/".format(qualtrics_surveyId)
headers = {
    "content-type": "application/json",
    "x-api-token": apiToken,
    }

###################################
# Step 4: Creating Data Export
###################################
data = {
        "format": "csv",
        "seenUnansweredRecode": -1, 
	#"startDate": "2019-10-23T07:31:43Z"
	"startDate": startDate
       }

downloadRequestResponse = requests.request("POST", url, json=data, headers=headers)
print(downloadRequestResponse.json())

try:
    progressId = downloadRequestResponse.json()["result"]["progressId"]
except KeyError:
    print(downloadRequestResponse.json())
    sys.exit(2)
    
isFile = None

############################################################################
# Step 5: Checking on Data Export Progress and waiting until export is ready
############################################################################
while progressStatus != "complete" and progressStatus != "failed" and isFile is None:
    if isFile is None:
       print  ("file not ready")
    else:
       print ("progressStatus=", progressStatus)
    requestCheckUrl = url + progressId
    requestCheckResponse = requests.request("GET", requestCheckUrl, headers=headers)
    try:
       isFile = requestCheckResponse.json()["result"]["fileId"]
    except KeyError:
       1==1
    print(requestCheckResponse.json())
    requestCheckProgress = requestCheckResponse.json()["result"]["percentComplete"]
    print("Download is " + str(requestCheckProgress) + " complete")
    progressStatus = requestCheckResponse.json()["result"]["status"]

#-------------------------
# step 5.1: Check for error
#-------------------------
if progressStatus is "failed":
    raise Exception("export failed")

fileId = requestCheckResponse.json()["result"]["fileId"]

if debug:
	print("here is fileId:", fileId)


#####################################
# Step 6: FETCH THE QUALTRICS DATA
#####################################
requestDownloadUrl = url + fileId + '/file'

if debug:
	print("Download URL:", requestDownloadUrl)

requestDownload = requests.request("GET", requestDownloadUrl, headers=headers, stream=True)

#####################################
# Step 7: SAVE FILE LOCALLY
#####################################
# Here is one way to do it by unzipping and downloading it as csv file
# in a specifically named (filepath) folder
# NOT RUN
#zipfile.ZipFile(io.BytesIO(requestDownload.content)).extractall("MyQualtricsDownload")
#zipfile.ZipFile(io.BytesIO(requestDownload.content)).extractall(filepath)

# Alternatively just save the zipfile
outfile = filepath + ".zip"
open(outfile, 'wb').write(requestDownload.content)

print("Created file: ", outfile)
#####################################
# Mail the file to yourself or someone else
#####################################

send_via_email = 0 # still working on this - not yet working

if send_via_email == 0:
	sys.exit()	

#import email
import smtplib
from email import encoders
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase

TO = "pattyf@berkeley.edu, lsc_project@berkeley.edu"
FROM = "pfrontiera@berkeley.edu"
SUBJECT = "LSC Feedback"

themsg = MIMEMultipart()
themsg['Subject'] = 'LSC Feedback'
themsg['To'] = TO 
themsg['From'] = FROM

msg = MIMEBase('application', 'zip')
zf = open(outfile, 'rb')
msg.set_payload(zf.read())
encoders.encode_base64(msg)
msg.add_header('Content-Disposition', 'attachment', filename=outfile)
themsg.attach(msg)
#themsg = themsg.as_string()

#oye
SENDMAIL = "/usr/sbin/sendmail" # sendmail location
import os
p = os.popen("%s -t" % SENDMAIL, "w")
p.write("To: pattyf@berkeley.edu\n")
p.write("Subject: test\n")
p.write("\n") # blank line separating headers from body
p.write("Some text\n")
p.write("some more text\n")
sts = p.close()
if sts != 0:
    print ("Sendmail exit status", sts)


# send the message
#smtp = smtplib.SMTP()
#smtp = smtplib.SMTP()
#smtp.connect()
#smtp.sendmail(FROM, TO, themsg)
#smtp.close()

#s = smtplib.SMTP('smtp.gmail.com', 587)
#s.ehlo()
#s.starttls()
#s.login(from_email, pw)
#r = s.sendmail(from_email, to_email, msg)
#s.quit()

print("The file: " + outfile + " has been emailed")


# DONE
print('Complete')
