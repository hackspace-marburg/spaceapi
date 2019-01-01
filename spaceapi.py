#!/usr/bin/env python2
from gi.repository import GObject
import RPi.GPIO as GPIO
import argparse
import atexit

import time
import datetime
import dateutil.relativedelta
import json
import ssl
import socket

irc_last_ping = 0

spaceapi = {
	'api': '0.13',
	'space': '[hsmr]',
	'logo': 'http://hsmr.cc/logo.svg',
	'url': 'http://hsmr.cc/',
	'location': {
		'address': '[hsmr] Hackspace Marburg, Am Plan 3, 35037 Marburg, Germany',
		'lat': 50.8075289,
		'lon': 8.7677467
	},
	'contact': {
		'email': 'mail@hsmr.cc',
		'irc': 'ircs://irc.hackint.org:9999/#hsmr',
		'ml': 'hsmr@lists.metarheinmain.de',
		'phone': '+49 6421 4924981'
	},
	'issue_report_channels': [
		'email'
	],
	'open': False,
	'state': {
		'open': None,
		'lastchange': int(time.time()),
		'message': None
	},
	'sensors': {
		'door_locked': [
			{
				'value': False,
				'location': 'upstairs'
			}
		]
	}
}

def main(json_location='spaceapi.json', wiki_location='Site.SiteNav', reconnect=False):
	global irc_alive #TODO: spaceapi class
	global irc_watch

	if not reconnect:
		GObject.threads_init()

	GPIO.setmode(GPIO.BCM)
	GPIO.setup(24, GPIO.IN, pull_up_down=GPIO.PUD_UP)
	GPIO.setup(4, GPIO.IN, pull_up_down=GPIO.PUD_UP)  # big red FLTI* switch
	GPIO.setup(12, GPIO.OUT)

	GPIO.add_event_detect(24, GPIO.BOTH, callback=button_handler, bouncetime=2000)
	GPIO.add_event_detect(4, GPIO.BOTH, callback=button_handler, bouncetime=2000)  # fire when FLTI* switch changes position

	irc_connected = False
	while not irc_connected:
		try:
			irc_socket = ssl.wrap_socket(socket.socket(socket.AF_INET6, socket.SOCK_STREAM),
				ca_certs='irc.crt', cert_reqs=ssl.CERT_NONE)
			irc_socket.connect(('irc.hackint.eu', 9999))
			irc = irc_socket.makefile('w+b', 0) # 0 is the bufsize
			irc.write(b'NICK hsmr_doorbot\r\n')
			irc.write(b'USER hsmr_doorbot hsmr_doorbot irc.spaceboyz.net :hsmr_doorbot\r\n')
			irc_connected = True
		except:
			time.sleep(10)

	irc_alive = GObject.timeout_add(50000, irc_check_ping, irc, irc_socket)
	irc_watch = GObject.io_add_watch(irc, GObject.IO_IN, irc_in,
		irc, irc_socket)

	if not reconnect:
		GObject.MainLoop().run()

def irc_reconnect(irc, irc_socket, irc_alive, irc_watch):
	GObject.source_remove(irc_alive)
	GObject.source_remove(irc_watch)
	GPIO.cleanup()
	irc.close()
	irc_socket.close()

	main(json_location=args.file, wiki_location=args.wiki, reconnect=True)

def irc_check_ping(irc, irc_socket):
	global irc_last_ping #TODO: spaceapi class

	if irc_last_ping + datetime.timedelta(seconds=500) < datetime.datetime.now():
		irc_reconnect(irc, irc_socket, irc_alive, irc_watch)
		return False

	return True

def timedelta():
	attrs = ['years', 'months', 'days', 'hours', 'minutes', 'seconds']
	delta = dateutil.relativedelta.relativedelta(
		datetime.datetime.now(),
		datetime.datetime.fromtimestamp(spaceapi['state']['lastchange'])
	)

	return [
		'{0} {1}'.format(getattr(delta, attr), getattr(delta, attr) > 1 and attr or attr[:-1])
			for attr in attrs if getattr(delta, attr)
	]

def button_handler(channel):
	time.sleep(2) # dirty blerk, rising early
	door_open = bool(GPIO.input(24))
	flti_only = not bool(GPIO.input(4))  # big red FLTI* switch; internal pull-up
	if (
		(door_open != spaceapi['state']['open'])
		or (flti_only and spaceapi['state']['message'] == None)
		or (not flti_only and spaceapi['state']['message'] != None)
	):
		with open(json_location, 'w') as f:
			spaceapi['open'] = door_open
			spaceapi['state']['open'] = door_open
			spaceapi['state']['lastchange'] = int(time.time())
			spaceapi['state']['message'] = (
				'Access is currently restricted to WLTI*. Please refer to https://hsmr.cc/flti for more details.'
				if flti_only and door_open
				else None
			)
			spaceapi['sensors']['door_locked'][0]['value'] = not door_open
			json.dump(spaceapi, f)
			f.close()

		with open(wiki_location, 'w') as f:
			if flti_only and door_open:
				f.write(
					'version=pmwiki-2.2.53 ordered=1 urlencoded=1\n'
					'name=Site.SiteNav\n'
					'targets=Infrastruktur.ServerB2s\n'
					'text=* [[#door]][[Main/FLTI | %25black%25Base: <br />%25purple%25FLTI*-Zeit%25%25]]\n'
					'time={lastchange}'.format(
						lastchange=spaceapi['state']['lastchange']
					)
				)
			else:
				f.write(
					'version=pmwiki-2.2.53 ordered=1 urlencoded=1\n'
					'name=Site.SiteNav\n'
					'targets=Infrastruktur.ServerB2s\n'
					'text=* [[#door]][[Infrastruktur/Door | %25black%25Base: <br />{state}%25%25]]\n'
					'time={lastchange}'.format(
						state=('%25green%25besetzt' if door_open else '%25red%25unbesetzt'),
						lastchange=spaceapi['state']['lastchange']
					)
				)

	return True

def irc_in(fd, condition, irc, irc_socket):
	global irc_last_ping #TODO: spaceapi class

	try:
		data = str(irc.readline()).strip()
	except socket.error:
		irc_reconnect(irc, irc_socket, irc_alive, irc_watch)

	if data.find('PING') != -1:
		irc.write(b'PONG :{data}\r\n'.format(
			data=data.split(':')[1]
		))
		irc_last_ping = datetime.datetime.now()
	elif data.find('You are now identified for') != -1 or data.find('NickServ :No such nick/channel') != -1:
		irc.write(b'JOIN #hsmr\r\n')
	elif data.find('MODE hsmr_doorbot') != -1 or data.find('This nickname is registered. Please') != -1:
		irc.write(b'PRIVMSG NickServ :identify PASSWORD\r\n')
	elif data.find('PRIVMSG #hsmr :!base') != -1:
		irc.write(b'NOTICE #hsmr :The door {location} has been {state} for {timedelta}.{message}\r\n'.format(
			location=spaceapi['sensors']['door_locked'][0]['location'],
			state='open' if spaceapi['state']['open'] else 'closed',
			timedelta=' and '.join(timedelta()),
			message='' if spaceapi['state']['message'] else ' ' + spaceapi['state']['open']
		))

	return True

@atexit.register
def exit():
	try:
		GPIO.cleanup()
		irc.close()
		irc_socket.close()
	except:
		pass

if __name__ == '__main__':
	parser = argparse.ArgumentParser(description='Generates .json for Space API.')
	parser.add_argument('--file', type=str, default='spaceapi.json',
		help='File location where to save the spaceapi.json.')
	parser.add_argument('--wiki', type=str, default='Site.SiteNav',
		help='Location in the PmWiki wiki.d where to save the state of the door lock.')
	args = parser.parse_args()

	json_location = args.file
	wiki_location = args.wiki
	main(json_location=args.file, wiki_location=args.wiki)
