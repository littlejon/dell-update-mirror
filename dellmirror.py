#!/usr/bin/env python3

from queue import Queue
from threading import Thread
import argparse
import gzip
import os.path
import requests
from hashlib import md5
import sys
import threading
import xml.etree.ElementTree as ET

parser = argparse.ArgumentParser()
parser.add_argument('--server', help='Comma separated list of Models to download files for (eg. "R620,R720,R730,R730xd")', required=True, metavar='MODELS')
parser.add_argument('--destination', help='Destination folder for mirrored data, needs to be the webroot for the mirror', required=True, metavar='WEBROOT')
parser.add_argument('--getcatalog', help='Forces an update to the current Catalog file for the mirror', action='store_true')
parser.add_argument('--remove-catalog-location', help='Removes the attributes of the Catalog.xml which is hardcoed to "https://downloads.dell.com/". If these remain, some systems fetches files from there instead of the mirror location.', action='store_true')
parser.add_argument('--onlyfirmware', help='Only downloads files with a BIOS or Firmware category (useful for Lifecycle Controller based updates)', action='store_true')
parser.add_argument('--threads', default=8, type=int, help='Number of simultaneous threads to download (enter a number only)')

args = parser.parse_args()

num_threads = args.threads
downloadTotal = 0
downloadDone = 0
threadLock = threading.Lock()

textColours = {
    'black': 30,
    'red': 31,
    'green': 32,
    'yellow': 33,
    'blue': 34,
    'magenta': 35,
    'cyan': 36,
    'white': 37,
    'reset': 0,
}

class downloadThread(threading.Thread):
    def __init__(self, threadNum, queue):
        threading.Thread.__init__(self)
        self.threadNum = threadNum
        self.kill_received = False
        self.queue = queue

    def run(self):
        global downloadDone
        while not self.kill_received and not self.queue.empty():
            parms = self.queue.get()
            url, dest = parms
            downloadFile(url, dest, 31 + (self.threadNum % 7))
            with threadLock:
                downloadDone = downloadDone + 1
                printColour('\nDownload of {0} completed, {1} of {2}\n'.format(url, downloadDone, downloadTotal), 'green')

            self.queue.task_done()
        printColour('\nThread #{0} exiting\n'.format(self.threadNum), colourNumber = 31 + (self.threadNum % 7))

def has_live_threads(threads):
    return True in [t.is_alive() for t in threads]

def printColour(text, colour = None, colourNumber = None):
    if colour == None and colourNumber == None:
        sys.stdout.write(text)
        sys.stdout.flush()
        return

    resetCode = textColours['reset']
    try:
        colourCode = textColours[colour.lower()]
    except:
        colourCode = resetCode

    if colourNumber != None:
        colourCode = colourNumber

    sys.stdout.write('\033[{0}m{1}\033[{2}m'.format(colourCode, text, resetCode))
    sys.stdout.flush()

def downloadFile(url, dest, colourNumber = None):
    # Streaming, so we can iterate over the response.
    r = requests.get(url, stream=True)

    # Total size in bytes.
    total_size = int(r.headers.get('content-length', 0))
    block_size = 1024
    wrote = 0
    count = 0
    with open(dest, 'wb') as f:
        for data in r.iter_content(block_size):
            wrote = wrote + len(data)
            f.write(data)
            count = count + 1
            # Display dot every 100kb
            if count % 100 == 0:
                printColour('.', colourNumber = colourNumber)
    if total_size != 0 and wrote != total_size:
        printColour('ERROR, something went wrong downloading {0}\n'.format(url), 'red')

downloadCatalog = False
unzippedCatalog = '{0}/Catalog/Catalog.xml'.format(args.destination)

if not os.path.exists(unzippedCatalog):
    downloadCatalog = True
    printColour('Catalog file not found, forcing download\n', 'yellow')

if args.getcatalog or downloadCatalog:
    fileToDownload = '{0}/Catalog/Catalog.xml.gz'.format(args.destination)
    url = 'http://ftp.dell.com/Catalog/Catalog.xml.gz'

    dirname = os.path.dirname(fileToDownload)
    if not os.path.exists(dirname):
        os.makedirs(dirname)

    printColour('Download {0} '.format(url), 'green')
    downloadFile(url, fileToDownload)
    printColour(' complete\n'.format(url), 'green')

    with gzip.open(fileToDownload, 'rb') as f:
        unzippedOutput = open(unzippedCatalog, 'wb')
        unzippedOutput.write(f.read())
        unzippedOutput.flush()
        unzippedOutput.close()

if args.remove_catalog_location:
    e = ET.parse(unzippedCatalog)
    root = e.getroot()
    for attr in ['baseLocation', 'baseLocationAccessProtocols']:
        try:
            del root.attrib[attr]
        except KeyError as err:
            printColour('Warning: ', 'red')
            printColour('Could not find {0} in Catalog.xml. Continue anyway.\n'.format(err), 'yellow')
    # Here we assume utf-16 encoding as that's what dell currently ships.
    # Should better check it instead.
    e.write(unzippedCatalog, encoding="utf-16", xml_declaration=True)

q = Queue(maxsize=0)

e = ET.parse(unzippedCatalog).getroot()
toDownload = []
serverList = args.server.split(',')

for sb in e.findall('SoftwareBundle'):
    if any(server in sb.attrib['path'] for server in serverList):
        modelFound = sb.find('TargetSystems/Brand/Model/Display').text
        if modelFound in serverList:
            printColour('Found driver bundle for {0}\n'.format(modelFound), 'green')

            for package in sb.findall('Contents/Package'):
                path = package.attrib['path']

                for sc in (e.findall('SoftwareComponent')):
                    if path in sc.attrib['path']:
                        scName = sc.find('Name/Display').text
                        scType = sc.find('ComponentType/Display').text

                        printColour('  {0}: '.format(scType), 'magenta')
                        printColour('{0} ({1}) - '.format(scName, path))

                        driverpath = sc.attrib['path']
                        fileToDownload = '{0}/{1}'.format(args.destination, driverpath)

                        needDownload = True

                        componentType = sc.find('ComponentType').attrib['value']

                        if args.onlyfirmware and (componentType != 'FRMW' and componentType != 'BIOS'):
                            printColour('Not BIOS or Firmware, ignoring\n', 'yellow')
                            continue

                        if os.path.isfile(fileToDownload):
                            needDownload = False

                            md5_object = md5()
                            block_size = 128 * md5_object.block_size
                            output = open(fileToDownload, 'rb')
                            chunk = output.read(block_size)
                            while chunk:
                                md5_object.update(chunk)
                                chunk = output.read(block_size)

                            fileHash = md5_object.hexdigest()
                            checkHash = sc.attrib['hashMD5']

                            if fileHash.lower() != checkHash.lower():
                                printColour('MD5 Hashcheck failed, adding to download queue', 'red')
                                needDownload = True
                            else:
                                printColour('File already exists, skipping', 'green')
                        else:
                            printColour('Downloading', 'yellow')

                        printColour('\n')

                        if needDownload:
                            url = 'http://ftp.dell.com/{0}'.format(driverpath)

                            dirname = os.path.dirname(fileToDownload)
                            if not os.path.exists(dirname):
                                os.makedirs(dirname)

                            dlParms = (url, fileToDownload)

                            try:
                                index = toDownload.index(dlParms)
                            except ValueError:
                                toDownload.append(dlParms)

            printColour('Finished Queuing {0}\n'.format(modelFound))

downloadTotal = len(toDownload)
printColour('\n')
printColour('{0} items to download (each dot represents 100kb downloaded by a thread)\n'.format(downloadTotal), 'green')

threads = []

for dlParm in toDownload:
    q.put(dlParm)

for i in range(num_threads):
    worker = downloadThread(i, q)
    worker.start()
    threads.append(worker)

while has_live_threads(threads):
    try:
        [t.join(1) for t in threads if t is not None and t.is_alive()]
    except KeyboardInterrupt:
        printColour('\nSending kill to threads, you will need to wait for the remaining downloads to finish (the impatient will need to kill from console)....\n', 'yellow')
        for t in threads:
            t.kill_received = True

printColour('All items downloaded\n\n', 'magenta')
