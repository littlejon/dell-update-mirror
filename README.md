# Dell Update Mirror #
A script written to provide a local mirror copy of the Dell Updates for specific server models, I have only tested and used the mirror that is produced with the Dell Server Lifecycle Controller.

```bash
python ./dellmirror.py --help

usage: dellmirror.py [-h] --server MODELS --destination WEBROOT [--getcatalog]
                     [--onlyfirmware] [--threads THREADS]

optional arguments:
  -h, --help            show this help message and exit
  --server MODELS       Comma separated list of Models to download files for
                        (eg. "R620,R720,R730,R730xd")
  --destination WEBROOT
                        Destination folder for mirrored data, needs to be the
                        webroot for the mirror
  --getcatalog          Forces an update to the current Catalog file for the
                        mirror
  --onlyfirmware        Only downloads files with a BIOS or Firmware category
                        (useful for Lifecycle Controller based updates)
  --threads THREADS     Number of simultaneous threads to download (enter a
                        number only)
```

## Example Usage ##

### To download all update files for a set of server models ###

```bash
python ./dellmirror.py --server "R420,R720,R630,R730,R730xd" --destination /var/www/html
```

### To download only Firmware or BIOS files for a set of server models ###

```bash
python ./dellmirror.py --server "R420,R720,R630,R730,R730xd" --destination /var/www/html --onlyfirmware
```

#### Note: a single model can be specified if required (ie "R730") ####