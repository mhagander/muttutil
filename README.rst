muttutils
=========

These are my own trivial mutt utility scripts. If you want to steal from
them, go ahead. But the main reason they're here is for my own
record-keeping.

In short, I use offlineimap to sync my mail to a set of local Maildir folders,
and then use mutt on those. These scripts make it slightly less painful to me.

imap_control.py
---------------
Small script to control offlineimap. Does full sync every <n> minutes,
INBOX only every <m> minutes, and listens to IMAP IDLE events. Mainly
consists of workarounds for the fact that our IMAP server tends to hang
every now and then. And then the network does too.

mutt_redpill.screen
-------------------
Trivial screen script that starts up mutt and offlineimap in one go, so it's
easy to both start and stop them together.

muttsearch.py
-------------
Crawls maildir of sent items for email addresses in to and cc fields, and adds
them to a database. This database is then used to search for email addresses
using the mutt query function.

If nothing is found there, or if the search is prefixed with ldap:, it falls
back to, well, LDAP, to do the search there.

Note that this script only works properly if the console (and mutt) is
in UTF-8 encoding. This is hardcoded on several locations in the script.
