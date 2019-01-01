#!/usr/bin/env python2
import RPi.GPIO as GPIO
import argparse
import atexit
import time
import datetime
import json

from dateutil.relativedelta import relativedelta, SA, SU

spaceapi = {
    'api': '0.13',
    'space': '[hsmr] Hackspace Marburg',
    'logo': 'https://hsmr.cc/logo.svg',
    'url': 'https://hsmr.cc/',
    'location': {
        'address': '[hsmr] Hackspace Marburg, Am Plan 3, 35037 Marburg, Germany',
        'lat': 50.8075289,
        'lon': 8.7677467
    },
    'contact': {
        'email': 'mail@hsmr.cc',
        'irc': 'ircs://irc.hackint.org:9999/#hsmr',
        'ml': 'public@lists.hsmr.cc',
        'phone': '+49 6421 4924981'
    },
    'issue_report_channels': [
        'email',
        'irc'
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

def main():
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(4, GPIO.IN, pull_up_down=GPIO.PUD_UP)
    GPIO.setup(3, GPIO.IN, pull_up_down=GPIO.PUD_UP)  # big red FLTI* switch
    #GPIO.setup(12, GPIO.OUT)

    GPIO.add_event_detect(4, GPIO.BOTH, callback=button_handler, bouncetime=2000)
    GPIO.add_event_detect(3, GPIO.BOTH, callback=button_handler, bouncetime=2000)  # fire when FLTI* switch changes position

    button_handler(0)

    while True:
        time.sleep(1)

def get_flti_hours(timestamp):
    _, week_number, _ = timestamp.isocalendar()
    odd_week = bool(week_number % 2)
    flti_weekday = SA if odd_week else SU
    delta_weekday = flti_weekday(-1) if timestamp.weekday() > flti_weekday.weekday else flti_weekday(+1)
    flti_start = timestamp + relativedelta(
        hour=16, minute=0, second=0, microsecond=0,
        weekday=delta_weekday
    )
    flti_end = timestamp + relativedelta(
        hour=20, minute=0, second=0, microsecond=0,
        weekday=delta_weekday
    )

    return flti_weekday, flti_start, flti_end

def button_handler(channel):
    time.sleep(2)  # dirty blerk, rising early
    door_open = bool(GPIO.input(4))
    flti_only = not bool(GPIO.input(3))  # big red FLTI* switch; internal pull-up

    now = datetime.datetime.now()
    flti_weekday, flti_start, flti_end = get_flti_hours(now)

    if now >= flti_end:
        flti_weekday, flti_start, flti_end = get_flti_hours(
            now + relativedelta(days=7)
        )

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
                    'text=* [[#door]][[Main/FLTI | %25black%25Base: <br />%25purple%25FLTI*-Zeit bis {flti_end}%25%25]]\n'
                    'time={lastchange}'.format(
                        flti_end=flti_end.strftime('%H:%M'),
                        lastchange=spaceapi['state']['lastchange']
                    )
                )
            else:
                f.write(
                    'version=pmwiki-2.2.53 ordered=1 urlencoded=1\n'
                    'name=Site.SiteNav\n'
                    'targets=Infrastruktur.ServerB2s\n'
                    'text=* [[Main.FLTI | %25purple%25FLTI*-Zeit: %3cbr />%25black%25{flti_date}%25%25]]%0a'
                    '* [[#door]][[Infrastruktur/Door | %25black%25Base: <br />{state}%25%25]]\n'
                    'time={lastchange}'.format(
                        state=('%25green%25besetzt' if door_open else '%25red%25unbesetzt'),
                        flti_date=flti_start.strftime('%d.%m. %H:%M-') + flti_end.strftime('%H:%M'),
                        lastchange=spaceapi['state']['lastchange']
                    )
                )

    return True

@atexit.register
def exit():
    try:
        GPIO.cleanup()
    except:
        pass

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Generates .json for Space API.')
    parser.add_argument('--file', type=str, default='spaceapi.json',
        help='File location where to save the spaceapi.json.')
    parser.add_argument('--wiki', type=str, default='Site.SiteNav',
        help='Location in the PmWiki wiki.d where to save the state of the door lock.')
    args = parser.parse_args()

    json_location=args.file  # interrupt callback needs access to these
    wiki_location=args.wiki
    main()
