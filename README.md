# Dell Update Mirror #
A script written to provide a local mirror copy of the Dell Updates for
specific server models, I have only tested and used the mirror that is produced
with the Dell Server Lifecycle Controller.

```bash
python3 ./dellmirror.py --help

usage: dellmirror.py [-h] --server MODELS --destination WEBROOT [--getcatalog]
                     [--remove-catalog-location] [--onlyfirmware]
                     [--threads THREADS]

optional arguments:
  -h, --help            show this help message and exit
  --server MODELS       Comma separated list of Models to download files for
                        (eg. "R620,R720,R730,R730xd")
  --destination WEBROOT
                        Destination folder for mirrored data, needs to be the
                        webroot for the mirror
  --getcatalog          Forces an update to the current Catalog file for the
                        mirror
  --remove-catalog-location
                        Removes the attributes of the Catalog.xml which is
                        hardcoed to "https://downloads.dell.com/". If these
                        remain, some systems fetches files from there instead
                        of the mirror location.
  --onlyfirmware        Only downloads files with a BIOS or Firmware category
                        (useful for Lifecycle Controller based updates)
  --threads THREADS     Number of simultaneous threads to download (enter a
                        number only)
```

## Example Usage ##

### To download all update files for a set of server models ###

```bash
python3 ./dellmirror.py --server "R420,R720,R630,R730,R730xd" --destination /var/www/html
```

### To download only Firmware or BIOS files for a set of server models ###

```bash
python3 ./dellmirror.py --server "R420,R720,R630,R730,R730xd" --destination /var/www/html --onlyfirmware
```

_Note: a single model can be specified if required (ie "R730")_

## About Catalog.xml ##

This script downloads `Catalog.xml.gz` from Dell, this file contains

When updating machines via HTTP from iDrac or racadm. For example, by specify
the URL to "dell.foo.bar", and the idrac will happily pull the Catalog.xml file
from there, and present any updates it finds that is applicable for the server.
But after clicking "install" any downloads will fail with the following error:
`RED006: Unable to download Update Package.`.  The `<Manifest>` declaration in
the catalog contains this by default:

```
<Manifest baseLocation="downloads.dell.com" baseLocationAccessProtocols="HTTPS"
```

This causes idrac to try to download the packages from `downloads.dell.com`,
using the `HTTPS` protocol, but this fails since we requested HTTP in idrac.
If one specifies HTTPS-method in idrac and still enter the "dell.foo.bar" (our
internal mirror host), the update works, but packages are actually downloaded
from downloads.dell.com, not our mirror.

The fix for us is to either update the baseLocation and
baseLocationAccessProtocol to match our settings, or to remove both properties.
Both paths work so far it seems.  Currently the script only have functionality
to remove the attributes, not modify them.

Use the `--remove-catalog-location` option to remove those attributes. This
unfortunately also has the effect that all `CDATA`-content is converted to
regular strings, ElementTree doesn't seem to be able to retain the `CDATA` when
writing the file.
