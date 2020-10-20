#!/bin/python3
# Starting with zone files for TLDs, find typo-squatting and look-alike domains.

import argparse
import logging
import datetime
# import sys
import os
import re
# import gzip
from fuzzywuzzy import fuzz
from joblib import Parallel, delayed
import multiprocessing

# Todo: Add versioning to only check new domains.  This will speed up the process a lot.
# Todo: More command flags.
# Todo: more typo techniques.
# Todo: Make writeoutput() read into an array and then sort it then overwrite the file with the new results.

print('''
        _     _     _     _                                 _
  _ __ | |__ (_)___| |__ (_)_ __   __ _       _ __ ___   __| |
 | '_ \| '_ \| / __| '_ \| | '_ \ / _` |_____| '__/ _ \ / _` |
 | |_) | | | | \__ \ | | | | | | | (_| |_____| | | (_) | (_| |
 | .__/|_| |_|_|___/_| |_|_|_| |_|\__, |     |_|  \___/ \__,_|
 |_|                              |___/                       
Run with --help to see all available options.
Credits: @douglasmun, @rybolov
''')

# Set some globals
logging.basicConfig(filename='log', filemode='a', format='%(asctime)s %(levelname)s: %(message)s', level=logging.INFO)
exec_start_time = int(datetime.datetime.now().timestamp())
num_cores = multiprocessing.cpu_count()
totalrows = multiprocessing.Manager().list()
lock = multiprocessing.Lock()
# newrows = 0
searchphrases = []
matchdomains = multiprocessing.Manager().list()


# Input validation, we love it....
def valid_file(filename):
    print("Testing if", filename, "is a file.")
    logging.info("Testing if %s is a file.", filename)
    if not os.path.isfile(filename):
        raise argparse.ArgumentTypeError("Not a valid file.")
    else:
        return filename


def valid_directory(directory):
    print("Testing if", directory, "is a directory.")
    logging.info("Testing if %s is a directory.", directory)
    if not os.path.isdir(directory):
        raise argparse.ArgumentTypeError("Not a valid directory.")
    else:
        return directory


def valid_percentage(percentage):
    print("Testing if", percentage, "is a percentage.")
    percentage = int(percentage)
    if 0 < percentage < 100:
        return percentage
    else:
        raise argparse.ArgumentTypeError("Not a valid percentage.")


def valid_cpu(numbercpus):
    print(f'Testing if {numbercpus} is a valid number of CPUs.')
    numbercpus = int(numbercpus)
    if numbercpus - num_cores > 1:
        return numbercpus
    else:
        raise argparse.ArgumentTypeError(f'Not a valid number of CPUs. I detected {num_cores} processors.')


parser = argparse.ArgumentParser(description='Search zone files for watch domains and trademarks.')
parser.add_argument('--directory', '-d', '--fromdirectory', '--dir', type=valid_directory,
                    help='Read bulk zone files from a directory. (default: ./zonefiles)')
parser.add_argument('--outputfile', '-o', help='Destination file for bad domains. (default: ./baddomains.txt)')
parser.add_argument('--domainfile', '-i', help='Source file for domains and trademarks. (default: \
                    ./domainsandtrademarks.txt)')
parser.add_argument('--accuracy', '-a', '--minimumscore', '--matchlevel', type=valid_percentage,
                    help='Threshold for a match. (default: 90)')
parser.add_argument('--cpu', '-c', type=valid_cpu,
                    help='Number of CPUs to keep in reserve for parallel processing. (default: 2)')
parser.add_argument('--dev', action="store_true", help='Development mode.  Turn on verbose logging. (default: none)')
parser.add_argument('--nodiff', action="store_true", help='Ignore the difference from previous version of zone files \
                    and test all domains in the new zone files.  This will make the test run way slower. \
                    (default: none)')
args = parser.parse_args()

if args.dev:
    logging.basicConfig(filename='log', filemode='a', format='%(asctime)s %(levelname)s: %(message)s',
                        level=logging.INFO)
    stderrLogger = logging.StreamHandler()
    stderrLogger.setFormatter(logging.Formatter(logging.BASIC_FORMAT))
    logging.getLogger().addHandler(stderrLogger)

logging.info('************Starting a new run.************')

if args.directory:
    zonefiledirectory = args.directory
else:
    zonefiledirectory = os.path.join(os.getcwd(), "zonefiles")

if args.accuracy:
    accuracy = args.accuracy
else:
    accuracy = 90

if args.outputfile:
    outputfile = args.outputfile
else:
    outputfile = os.path.join(os.getcwd(), "baddomains.txt")

if args.domainfile:
    domainsandtrademarks = args.domainfile
else:
    domainsandtrademarks = os.path.join(os.getcwd(), "domainsandtrademarks.txt")

if args.cpu:
    usecpus = args.cpu - num_cores
elif num_cores < 3:
    usecpus = 1
else:
    usecpus = num_cores - 2
logging.info(f'Using {usecpus} CPUs.')


def main():
    global matchdomains
    if not os.path.isfile(domainsandtrademarks):
        logging.error(f'No domains and trademarks file.  I tried:{domainsandtrademarks}.  Critical error.')
        print(f'No domains and trademarks file.  I tried:{domainsandtrademarks}.  Critical error.')
        exit('666')
    else:
        with open(domainsandtrademarks, 'r') as f:
            for line in f:
                if '#' not in line:
                    if line.strip():  # If line is not empty
                        line = line.strip()  # remove leading and trailing spaces
                        line = ''.join(line.split())  # remove all whitespace inside the line
                        line = line.lower()  # take everything to lower-case
                        line = line.encode('ascii', errors='ignore').decode()  # remove non-ascii characters
                        searchphrases.append(line)
                        searchphrases.append(getleets(line))
                        searchphrases.append(getitolswap(line))
                        searchphrases.append(getmissingdotwww(line))
    logging.info('Loaded Domains and Trademarks')
    logging.info(searchphrases)

    zonefiles = os.listdir(zonefiledirectory)
    if len(zonefiles) == 0:
        logging.error('No zone files detected.  Shutting down.')
        logging.error(zonefiledirectory)
        print('No zone files detected.  Shutting down.')
        print(zonefiledirectory)
        exit(666)
    zonefiles.sort()
    logging.info('Available zonefiles:')
    logging.info(zonefiles)

    Parallel(n_jobs=usecpus)(
        delayed(checkzonefile)(file) for file in zonefiles)  # This is where we read the file and check for matches.

    matchdomains = list(set(matchdomains))  # Remove duplicates by transforming to a set and then back to a list
    matchdomains.sort()
    if matchdomains:
        writeoutput(matchdomains)
    else:
        logging.info('Found no matches.')
        print('Found no matches.')

    totaldomains = len(matchdomains)
    totaltime = int(datetime.datetime.now().timestamp()) - exec_start_time
    print(f'Done with zone files.  We processed {sum(totalrows)} rows and found {totaldomains} matches.')
    logging.info(f'Done with zone files.  We processed {sum(totalrows)} rows and found {totaldomains} unique matches.')
    print(f'Total Time was {str(datetime.timedelta(seconds=totaltime))}.')
    logging.info(f'Total Time was {str(datetime.timedelta(seconds=totaltime))}.')
    logging.info('************Ending run.************')


def unzipfiles():
    abcd = 1


def checkzonefile(filename):
    lastdomain = ""
    internalrows = 0
    global totalrows
    global matchdomains
    if not re.search('\.txt$', filename):
        return
    if re.search('^com', filename):
        return
    if re.search('^info', filename):
        return
    filewithpath = os.path.join(zonefiledirectory, filename)
    logging.info(f'Reading {filewithpath}')
    print(f'Reading {filewithpath}')
    with open(filewithpath, 'rt') as f:
        for line in f:
            internalrows += 1
            linearray = line.split()
            # Regex is to check for the tld in the first field. It has only one phrase with a trailing dot.
            # last check is to make sure that we're not checking the same domain as the previous line.
            linearray[0] = linearray[0].rstrip('.')
            if not re.search('^[a-z]*\.$', linearray[0]) and linearray[0] is not lastdomain and linearray[2] == "in" \
                    and linearray[3] == "ns":
                for searchword in searchphrases:
                    if fuzz.partial_ratio(searchword, linearray[0]) > accuracy:
                        print(linearray[0])
                        matchdomains.append(linearray[0])
            lastdomain = linearray[0]
    totalrows.append(int(internalrows))
    return


def writeoutput(writedomains):
    with open(outputfile, 'w') as outfile:
        # for row in writedomains:
        outfile.write("\n".join(map(str, writedomains)))
        outfile.write("\n")  # Last line needs a line terminator. =)
        print(f'Wrote output file {outputfile}.')
        logging.info(f'Wrote output file {outputfile}.')


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
