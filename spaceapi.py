#!/usr/bin/env python3
import RPi.GPIO as GPIO
import argparse
import atexit
import time
import datetime
import json
import paho.mqtt.client as mqtt

from dateutil.relativedelta import relativedelta, SA, SU

# Connect the switch to BCM 17/pin 11
DOOR_PIN = 17
mqttclient = mqtt.Client() 

spaceapi = {
    'api': '0.13',  # NOTE: dropped in API version 14, api_compatibility only
    'api_compatibility': ['14'],
    'space': '[hsmr] Hackspace Marburg',
    'logo': 'https://hsmr.cc/logo.svg',
    'url': 'https://hsmr.cc/',
    'location': {
        'address': '[hsmr] Hackspace Marburg, Rudolf-Bultmann-Strasse 2b, 35039 Marburg, Germany',
        'lat': 50.81615,
        'lon': 8.77851,
        'timezone': 'Europe/Berlin'
    },
    'contact': {
        'email': 'mail@hsmr.cc',
        'irc': 'ircs://irc.hackint.org:6697/#hsmr',
        'mastodon': '@hsmr@chaos.social',
        'ml': 'public@lists.hsmr.cc',
        'phone': '+49 6421 4924981'
    },
    'issue_report_channels': [  # NOTE: dropped in API version 14
        'email',
        'ml'
    ],
    'state': {
        'open': False,
        'lastchange': int(time.time()),
        'message': ''
    },
    'ext_ccc': 'chaostreff'  # one of erfa, chaostreff or family - #812455
}


def main():
    GPIO.setmode(GPIO.BCM)

    GPIO.setup(DOOR_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
    GPIO.add_event_detect(
            DOOR_PIN, GPIO.BOTH, callback=button_handler, bouncetime=2000)
    
    mqttclient.on_connect = on_connect
    mqttclient.on_message = on_message
    mqttclient.on_disconnect = on_disconnect
    mqttclient.connect("b2s.hsmr.cc", 1883, 60)

    button_handler(0)

    mqttclient.loop_forever()
    
    #while True:
    #    time.sleep(1)

def on_connect(client, userdata, flags, rc):
    print("Connected with result code: "+str(rc))
    client.subscribe('door')

def on_disconnect(client, userdata, rc):
    print('Disconnected. Reason: ' + str(rc))

def on_message(client, userdata, msg):
    try:
        state = json.loads(msg.payload.decode('utf-8'))
        change_state(state['door_open'], state['flti_only'], state['timestamp'])
    except Exception as e:
        print(e)
        print('Invalid Message: ' + str(msg.payload))

def get_flti_hours(timestamp):
    '''get_flti_hours was used to calculate the date of the next FLTI-times.
       However, currently these aren't provided and an extra switch is
       also missing. This code is currently _not_ used and kind of legacy.
    '''
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
    door_open = bool(GPIO.input(DOOR_PIN))
    flti_only = False  # there are currently no FLTI-times
    print('Door state changed (physically)') 
    mqttclient.publish('door',
            payload=json.dumps(
                dict(
                    door_open=door_open,
                    flti_only=flti_only,
                    timestamp=int(time.time()),
                    )
                ),
            qos=1,
            retain=True
            )
    #change_state(door_open, flti_only)

def change_state(door_open, flti_only, timestamp):
    print('Door state changed (Message): ' + str(door_open))
    now = datetime.datetime.fromtimestamp(timestamp)
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
            spaceapi['state']['open'] = door_open
            spaceapi['state']['lastchange'] = int(timestamp)
            spaceapi['state']['message'] = (
                'Access is currently restricted to WLTI*. Please refer to https://hsmr.cc/flti for more details.'
                if flti_only and door_open
                else ''
            )
            json.dump(spaceapi, f)
            f.close()

        with open(wiki_location, 'w') as f:
            if flti_only and door_open:
                # Currently there are no FLTI-times, this branch contains dead code.
                f.write(
                    'version=pmwiki-2.2.53 ordered=1 urlencoded=1\n'
                    'name=Site.SiteNav\n'
                    'targets=Infrastruktur.ServerB2s\n'
                    'text=* [[#door]][[Main/FLTI | %25black%25Base: <br />%25purple%25FLTI*-Zeit bis {flti_end}%25%25]]\n'
                    'time={lastchange}\n'.format(
                        flti_end=flti_end.strftime('%H:%M'),
                        lastchange=spaceapi['state']['lastchange']
                    )
                )
            else:
                f.write(
                    'version=pmwiki-2.2.53 ordered=1 urlencoded=1\n'
                    'name=Site.SiteNav\n'
                    'targets=Infrastruktur.ServerB2s\n'
                    'text=* [[#door]][[Infrastruktur/Door | %25black%25Base: <br />{state}%25%25]]\n'
                    'time={lastchange}\n'.format(
                        state=('%25green%25besetzt' if door_open else '%25red%25unbesetzt'),
                        # flti_date=flti_start.strftime('%d.%m. %H:%M-') + flti_end.strftime('%H:%M'),
                        # flti_date='F&auml;llt aus',
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
