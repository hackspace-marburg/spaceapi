# spaceapi.py

Modify our hackspace's [door](https://hsmr.cc/Infrastruktur/Door) state with a
Raspberry Pi and a ridiculously oversized switch. This script writes the
`spaceapi.json` and `Site.SiteNav` files for the
[Space API](http://spaceapi.net/) and [PmWiki](https://www.pmwiki.org/). These
files are mounted via *sshfs*.


## Installation

Connect the switch to the pin 11 and a ground pin.

Make sure the root user is able to log in the remote machine by having the
`~/.ssh` folder prepared. Furthermore, modify the `/etc/fstab` file to use
*sshfs* as documented
[here](https://wiki.archlinux.org/index.php/Sshfs#Automounting).

```bash
# Install required software
sudo apt install python-dateutil sshfs

# Clone this repository and cd into it
sudo cp spaceapi.py /usr/bin/
sudo cp spaceapi.service /etc/systemd/system/

sudo mkdir /etc/conf.d/
sudo cp spaceapi /etc/conf.d/
# Modify /etc/conf.d/spaceapi afterwards

sudo systemctl daemon-reload
sudo systemctl enable spaceapi.service
sudo systemctl start spaceapi.service
```
