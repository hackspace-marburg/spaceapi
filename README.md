# spaceapi.py

Modify our hackspace's [door](https://hsmr.cc/Infrastruktur/Door) state with a Raspberry Pi and a switch built into the door.
This script writes the `spaceapi.json` and `Site.SiteNav` files for the [Space API](http://spaceapi.net/) and [PmWiki](https://www.pmwiki.org/).
These files are mounted via *sshfs*.


## Installation

- Connect the switch to the [pin 11](https://pinout.xyz/pinout/pin11_gpio17) and a ground pin.
- Place the private key under `fs/root/.ssh/id_rsa`.
- Build the new image with [pimod](https://github.com/Nature40/pimod):
  ```
  docker run \
    --rm --privileged -it \
    -v $PWD:/files \
    -e PATH=/pimod:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin \
    --workdir=/files \
    nature40/pimod \
    pimod.sh /files/Pifile
  ```
- Flash the image to a SD card:
  ```
  dd if=Pifile.img of=__CHANGE_ME__ bs=4M status=progress
  ```
