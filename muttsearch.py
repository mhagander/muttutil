#!/usr/bin/python

import os
import sys
import cPickle as pickle
from email.header import decode_header
import rfc822
from ConfigParser import ConfigParser
import ldap

class Address(object):
	# Simple wrapper class for a name/email address combination, that's
	# capable of basic header decoding and case insensitive matching
	def __init__(self, name, mail):
		self.mail = mail
		self.name = decode_header(name)[0][0]
		self.lowermail = self.mail.lower()
		self.lowername = self.name.lower()
		self.count = 1

	def matches_query(self, query):
		lq = query.lower()
		if self.lowermail.find(lq) > -1: return True
		if self.lowername.find(lq) > -1: return True
		return False

	def matches_email_exact(self, mail):
		return self.lowermail == mail.lower()

	def increment(self, name):
		self.count += 1
		# Also set a name if one isn't there already
		if len(name) and not len(self.name.strip()):
			self.name = decode_header(name)[0][0]
			self.lowername = self.name.lower()
			

#
# Look in the specified Maildir style folder and read any mail that is
# new since the last time we ran (checks the mtime on
# .collected_addresses_last in that folder), and parse those for new
# mail addresses used.
#
def collect_newmail():
	fn = "%s/.collected_addresses_last" % MAILDIR
	if os.path.exists(fn):
		t = os.path.getmtime(fn)
	else:
		t = 0

	# Now touch the file for next run
	with file(fn, 'a'):
		os.utime(fn, None)

	# Cannot use the mailbox.Maildir classes to parse things, because
	# they leak file descriptors and thus die on Maildirs larger than
	# around 1000 mails (when using external references and not the
	# internal loop). Instead, we just instantiate the rfc822.Message
	# directly on the file.
	for fn in os.listdir('%s/cur' % MAILDIR):
		if os.path.getmtime('%s/cur/%s' % (MAILDIR, fn)) > t:
			with open('%s/cur/%s' % (MAILDIR, fn), "r") as f:
				yield rfc822.Message(f)
		
			
#
# Simply yield a list of all addresses found in the email, in all relevant
# headers.
#
def _all_addresses(mail):
	for x in mail.getaddrlist('to'):
		yield x
	for x in mail.getaddrlist('cc'):
		yield x

#
# Add an address to the system - either by adding a new Address instance
# or, if the address already existed, by incrementing it's count.
#
def _add_address(addrs, a):
	# Find out if it's there...
	for x in addrs:
		if x.matches_email_exact(a[1]):
			# Found a match, so increment
			x.increment(a[0])
			return
	# No match, so add a new record with count 1
	addrs.append(Address(a[0], a[1]))

#
# Add all new addresses parsed from the given mails
#
def merge_addresses(addrs, mails):
	for m in mails:
		for a in _all_addresses(m):
			_add_address(addrs, a)

#
# Load the current address list. If there are any new mails in the sent
# folder, also parse those, and save a new copy of the list. If nothing
# new, just return the list.
#
def load_and_update_addresslist():
	collfile = '%s/.collected_addresses' % MAILDIR
	if os.path.exists(collfile):
		with open(collfile, "rb") as f:
			addrs = pickle.load(f)
	else:
		addrs = []
	new_mails = list(collect_newmail())
	newmailcount = len(new_mails)
	if newmailcount:
		merge_addresses(addrs, new_mails)
		with open(collfile, "wb") as f:
			pickle.dump(addrs, f)
	return (addrs, newmailcount)


if __name__=="__main__":
	query = " ".join(sys.argv[1:]).strip()
	if query == "":
		print "No query given, so no results for you!"
		sys.exit(0)

	cp = ConfigParser()
	cp.read(os.path.expanduser('~/.muttutil'))
	MAILDIR=cp.get('maildir', 'path')
	
	if not query.startswith("ldap:"):
		# General query against collected addresses
		# Whenever called, we always attempt to load any new addresses,
		# it's fast enough not to bother with a cronjob or similar
		(addrs, newmailcount) = load_and_update_addresslist()

		# Now perform a query, in a very naive linear-search-everything way
		results = [a for a in addrs if a.matches_query(query)]
		if len(results) > 0:
			print "%s hits in %s records (parsed %s new mails)" % (len(results), len(addrs), newmailcount)

			# Format output in a way that mutt likes
			for a in sorted(results, key=lambda a: a.count, reverse=True):
				print "%s\t%s\t%s mails so far" % (a.mail, a.name and a.name or ' ', a.count)
			sys.exit(0)

		# If there were no results, let's try an LDAP lookup
		tried_local = True
	else:
		# If query is prefixed with LDAP, do an ldap search instead
		tried_local = False
		query = query.replace('ldap:','')

	# Either explicit LDAP search, or a fallthrough ldap search. The only
	# difference is in the status message given to mutt.
	l = ldap.initialize(cp.get('ldap', 'server'))
	l.simple_bind(cp.get('ldap', 'binddn'), cp.get('ldap', 'bindpwd'))
	results = [x[1] for x in l.search_s(cp.get('ldap', 'base'), ldap.SCOPE_SUBTREE, '(|(gn=*%s*)(sn=*%s*))' % (query, query), ['mail', 'cn'])]
	if tried_local:
		print "%s hits in LDAP (no hits in local search)" % len(results)
	else:
		print "%s hits in LDAP" % len(results)
	for r in results:
		try:
			print "%s\t%s" % (r['mail'][0], r['cn'][0])
		except KeyError:
			pass
