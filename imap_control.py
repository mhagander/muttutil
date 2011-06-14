#!/usr/bin/env python

import datetime
import os
import time
import subprocess
import sys
from ConfigParser import ConfigParser
from external import imaplib2

# Global variables (yuck, but this is a hack..) keeping the time of the last
# full and quick synchronizations done.
last_full = last_quick = datetime.datetime(2000,1,1,0,0,0)

def full_sync():
	global last_full, last_quick, account_name
	subprocess.call(['offlineimap', '-a', account_name, '-o', '-u', 'Noninteractive.Basic'])
	last_full = last_quick = datetime.datetime.now()

def quick_sync():
	# Sync just the inbox (though not in "quick mode" according to
	# offlineimap, we want to include everything in the sync. We're
	# only syncing a single folder, after all)
	global last_full, last_quick, account_name
	subprocess.call(['offlineimap', '-a', account_name, '-o', '-f', 'INBOX', '-u', 'Noninteractive.Basic'])
	last_quick = datetime.datetime.now()

def idle_callback(args):
	global last_quick
	print "Got idle callback, forcing quick sync of inbox"
	last_quick = datetime.datetime(2000,1,1,0,0,0)

# Basic operation: poll inbox every 30 seconds, then
# poll the rest every 5 minutes.
#
# We also register for imap idle on INBOX, and poll just the inbox when
# something arrives there.

if __name__=="__main__":
	cp = ConfigParser()
	cp.read(os.path.expanduser('~/.muttutil'))
	account_name = cp.get('offlineimap', 'accountname')

	cp = ConfigParser()
	cp.read(os.path.expanduser('~/.offlineimaprc'))
	server = cp.get('Repository %s' % account_name, 'remotehost')
	port = cp.get('Repository %s' % account_name, 'remoteport')
	username = cp.get('Repository %s' % account_name, 'remoteuser')
	password = cp.get('Repository %s' % account_name, 'remotepass')

	# Set up an IMAP connection for IDLE support
	imapconn = imaplib2.IMAP4_SSL(server)
	imapconn.login(username, password)
	imapconn.select('INBOX')
	imapconn.idle(callback=idle_callback)

	# Loop forever polling when it's time
	while True:
		now = datetime.datetime.now()
		print "Diff: %s and %s" % (now-last_full, now-last_quick)
		if now - last_full > datetime.timedelta(minutes=5):
			full_sync()
		elif now - last_quick > datetime.timedelta(seconds=30):
			quick_sync()
		time.sleep(5)
