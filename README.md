# spaceapi.py

Modify our hackspace's [door](https://hsmr.cc/Infrastruktur/Door) state with a Raspberry Pi and a switch built into the door.
This script writes the `spaceapi.json` and `Site.SiteNav` files for the [Space API](http://spaceapi.net/) and [PmWiki](https://www.pmwiki.org/).
These files are mounted via *sshfs*.


## Installation

Connect the switch to the [pin 11](https://pinout.xyz/pinout/pin11_gpio17) and a ground pin.

Make sure the root user is able to log in the remote machine by having the `~/.ssh` folder prepared.
Furthermore, modify the `/etc/fstab` file to use *sshfs* as documented [here](https://wiki.archlinux.org/index.php/Sshfs#Automounting).

```bash
# Install required software
sudo apt install python-dateutil sshfs

# Clone this repository
git clone https://github.com/hackspace-marburg/spaceapi.git ~/spaceapi

# Link files
sudo ln ~/spaceapi/spaceapi.py /usr/bin/spaceapi.py
sudo ln ~/spaceapi/spaceapi.service /etc/systemd/system/spaceapi.service

# Copy and alter config
sudo mkdir /etc/conf.d/
sudo cp spaceapi /etc/conf.d/
# Modify /etc/conf.d/spaceapi afterwards

sudo systemctl daemon-reload
sudo systemctl enable spaceapi.service
sudo systemctl start spaceapi.service
```
