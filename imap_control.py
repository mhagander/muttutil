#!/usr/bin/env python

import datetime
import os
import time
import subprocess
import sys
from ConfigParser import ConfigParser
from external import imaplib2

class IdleSpinner(object):
	def __init__(self, server, username, password):
		self.server = server
		self.username = username
		self.password = password
		self.ignoreidle = False
		self.triggered = False
		self.imapconn = None
		self.connect()
		self.start_idle()


	def connect(self):
		if self.imapconn:
			try:
				self.imapconn.logout()
			except:
				pass

		self.imapconn = imaplib2.IMAP4_SSL(self.server)
		self.imapconn.login(self.username, self.password)
		self.imapconn.select('INBOX')

	def start_idle(self):
		def callback(args):
			if self.ignoreidle:
				print "Ignored one triggered imap idle event"
				return
			print "Triggered on one imap idle event"
			self.triggered = True

		# Whenever we send a new IDLE command, it will trigger a previous
		# one for timeout. Thus, we need to ignore new events caused by this.
		# There is a race condition here, but let's claim it's tiny.
		self.ignoreidle = True
		done = False
		while not done:
			try:
				print "Calling imap idle"
				self.imapconn.idle(callback=callback, timeout=30)
				print "Did call imap idle"
				done = True
			except Exception, ex:
				print "Server closed connection, reopening"
				self.connect()
				# Loop back up and try again with the idle command
		self.ignoreidle = False
		self.last_idle_start = datetime.datetime.now()
		print "Finished starting idle thread"

	def tick(self):
		if datetime.datetime.now() - self.last_idle_start > datetime.timedelta(minutes=1):
			print "Idle expired, restart just to be on the safe side"
			# Complete hang when trying to log out - so just drop the old
			# connection and see what happens instead...
			self.imapconn = None
			self.connect()
			self.start_idle()

	def clear(self):
		self.triggered = False


# Global variables (yuck, but this is a hack..) keeping the time of the last
# full and quick synchronizations done.
last_full = datetime.datetime(2000,1,1,0,0,0)

def full_sync():
	global last_full, account_name
	print "Running full sync"
	subprocess.call(['offlineimap', '-a', account_name, '-o', '-u', 'Noninteractive.Basic'])
	last_full = datetime.datetime.now()

def quick_sync():
	# Sync just the inbox (though not in "quick mode" according to
	# offlineimap, we want to include everything in the sync. We're
	# only syncing a single folder, after all)
	global account_name
	print "Running quick sync"
	subprocess.call(['offlineimap', '-a', account_name, '-o', '-f', 'INBOX', '-u', 'Noninteractive.Basic'])


# Basic operation: spinner controls inbox pull every <n> seconds, or when IDLE
# indicates something happened.
# Full poll run every 5 minutes.

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

	spinner = IdleSpinner(server, username, password)

	# Loop forever polling when it's time
	while True:
		now = datetime.datetime.now()
		print "Time since last full sync: %s, quick sync requested: %s" % (now-last_full, spinner.triggered)
		if now - last_full > datetime.timedelta(minutes=5):
			full_sync()
		elif spinner.triggered:
			quick_sync()
			spinner.clear()
			spinner.start_idle()
		spinner.tick()
		time.sleep(1)
