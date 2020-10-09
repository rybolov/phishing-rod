#!/bin/python3
#Starting with zone files for TLDs, find typo-squatting and look-alike domains.

import argparse
import logging
import datetime
import sys
import os
import re
import gzip
from fuzzywuzzy import fuzz

# Todo: Add versioning to only check new domains.  This will speed up the process a lot.
# Todo: More command flags.

print("        _     _     _     _                                 _ ")
print("  _ __ | |__ (_)___| |__ (_)_ __   __ _       _ __ ___   __| | ")
print(" | '_ \| '_ \| / __| '_ \| | '_ \ / _` |_____| '__/ _ \ / _` | ")
print(" | |_) | | | | \__ \ | | | | | | | (_| |_____| | | (_) | (_| | ")
print(" | .__/|_| |_|_|___/_| |_|_|_| |_|\__, |     |_|  \___/ \__,_| ")
print(" |_|                              |___/                        ")
print("\nRun with --help to see all available options.")
print("Credits: @douglasmun, @rybolov\n")

# Set some globals
logging.basicConfig(filename='log', filemode='a', format='%(asctime)s %(levelname)s: %(message)s', level=logging.INFO)
exec_start_time = int(datetime.datetime.now().timestamp())


# Input validation, we love it....
def valid_file(filename):
    print("Testing if", filename, "is a file.")
    logging.info("Testing if %s is a file.", filename)
    if not os.path.isfile(filename):
        raise argparse.ArgumentTypeError("Not a valid file.")
    else:
        return(filename)

def valid_directory(directory):
    print("Testing if", directory, "is a directory.")
    logging.info("Testing if %s is a directory.", directory)
    if not os.path.isdir(directory):
        raise argparse.ArgumentTypeError("Not a valid directory.")
    else:
        return(directory)

def valid_percentage(percentage):
    print("Testing if", percentage, "is a percentage.")
    percentage = int(percentage)
    if 0 < percentage < 100:
        return(percentage)
    else:
        raise argparse.ArgumentTypeError("Not a valid percentage.")


parser = argparse.ArgumentParser(description='Search zone files for watch domains and trademarks.')
parser.add_argument('--directory', '-d', '--fromdirectory', '--dir', type=valid_directory, help='Read bulk zone files from a directory. (default: ./zonefiles)')
parser.add_argument('--outputfile', '-o', help='Destination file for bad domains. (default: ./baddomains.txt)')
parser.add_argument('--accuracy', '-a', '--minimumscore', '--matchlevel', type=valid_percentage, help='Threshold for a match. (default: 90)')
parser.add_argument('--dev', action="store_true", help='Development mode.  Turn on verbose logging. (default: none)')
args = parser.parse_args()

if args.dev:
    logging.basicConfig(filename='log', filemode='a', format='%(asctime)s %(levelname)s: %(message)s', level=logging.INFO)
    stderrLogger = logging.StreamHandler()
    stderrLogger.setFormatter(logging.Formatter(logging.BASIC_FORMAT))
    logging.getLogger().addHandler(stderrLogger)

logging.info('************Starting a new run.************')

if args.directory:
    zonefiledirectory = args.directory
else:
    zonefiledirectory = os.path.join( os.getcwd(), "zonefiles")

if args.accuracy:
    accuracy = args.accuracy
else:
    accuracy = 90

if args.outputfile:
    outputfile = args.outputfile
else:
    outputfile = os.path.join(os.getcwd(), "baddomains.txt")

def main():
    searchphrases = []
    domainsandtrademarks = os.path.join(os.getcwd(), "domainsandtrademarks.txt")
    if not os.path.isfile(domainsandtrademarks):
        logging.error('No domainsandtrademarks.txt.  Critical error.')
        logging.error(domainsandtrademarks)
        print('No domainsandtrademarks.txt.  Critical error.')
        print(domainsandtrademarks)
        exit('666')
    else:
        with open(domainsandtrademarks, 'r') as f:
            for line in f:
                if '#' not in line:
                    if line.strip() : # If line is not empty
                        line = line.strip() # remove leading and trailing spaces
                        line = ''.join(line.split()) # remove all whitespace inside the line
                        line = line.lower() # take everything to lower-case
                        line = line.encode('ascii',errors='ignore').decode() # remove non-ascii characters
                        searchphrases.append(line)
                        searchphrases.append(getleets(line))
                        searchphrases.append(getitolswap(line))
                        searchphrases.append(getmissingdotwww(line))
    logging.info('Loaded Domains and Trademarks')
    logging.info(searchphrases)

    lastdomain = ""
    matchdomains = []
    totalrows = 0
    newrows = 0

    zonefiles = os.listdir(zonefiledirectory)
    if len(zonefiles) == 0:
        logging.error('No zone files detected.  Shutting down.')
        logging.error(zonefiledirectory)
        print('No zone files detected.  Shutting down.')
        print(zonefiledirectory)
        exit(666)
    logging.info('Available zonefiles:')
    logging.info(zonefiles)
    for file in zonefiles:
        filewithpath = os.path.join(zonefiledirectory, file)
        with gzip.open(filewithpath, 'rt') as f:
            for line in f:
                totalrows += 1
                linearray = line.split()
                # Regex is to check for the tld in the first field. It has only one phrase with a trailing dot.
                # last check is to make sure that we're not checking the same domain as the previous line.
                if not re.search('^[a-z]*\.$]', linearray[0]) and linearray[0] != lastdomain and linearray[2] == "in" and linearray[3] == "ns":
                    lastdomain = linearray[0]
                    for searchword in searchphrases:
                        domain = linearray[0].split('.')
                        if fuzz.partial_ratio(searchword, linearray[0]) > accuracy:
                            linearray[0] = linearray[0].rstrip('.')
                            print(linearray[0])
                            matchdomains.append(linearray[0])
    writeoutput(matchdomains)

    totaltime = int(datetime.datetime.now().timestamp()) - exec_start_time
    totaldomains = len(matchdomains)
    print("Done with zone files.  We processed", totalrows, "rows and found", totaldomains, "matches.")
    print("Total Time was", str(datetime.timedelta(seconds=totaltime)))
    logging.info('************Ending run.************')

def writeoutput(writedomains):
    with open(outputfile, 'w') as outfile:
        #for row in writedomains:
        outfile.write("\n".join(map(str, writedomains)))
        outfile.write("\n") # Last line needs a line terminator. =)

def getleets(text):
    getchar = lambda c: chars[c] if c in chars else c
    chars = {"a": "4", "e": "3", "l": "1", "o": "0", "s": "5"}
    return ''.join(getchar(c) for c in text)

def getitolswap(text):
    getchar = lambda c: chars[c] if c in chars else c
    chars = {"i": "l"}
    return ''.join(getchar(c) for c in text)

def getmissingdotwww(text):
    text = "www" + text
    return text

if __name__ == '__main__':
    main()
