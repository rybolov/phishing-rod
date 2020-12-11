#!/bin/python3
# Download the zone files, make diffs
import argparse
import logging
import datetime
import os
import re
from joblib import Parallel, delayed
import multiprocessing

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
def valid_directory(directory):
    print("Testing if", directory, "is a directory.")
    logging.info("Testing if %s is a directory.", directory)
    if not os.path.isdir(directory):
        raise argparse.ArgumentTypeError("Not a valid directory.")
    else:
        return directory


def valid_cpu(numbercpus):
    print(f'Testing if {numbercpus} is a valid number of CPUs.')
    numbercpus = int(numbercpus)
    if numbercpus - num_cores > 1:
        return numbercpus
    else:
        raise argparse.ArgumentTypeError(f'Not a valid number of CPUs. I detected {num_cores} processors.')


parser = argparse.ArgumentParser(description='Download zone files and make daily diffs.')
parser.add_argument('--directory', '-d', '--fromdirectory', '--dir', type=valid_directory,
                    help='Directory for zone files. (default: ./zonefiles)')
parser.add_argument('--cpu', '-c', type=valid_cpu,
                    help='Number of CPUs to keep in reserve for parallel processing. (default: 2)')
parser.add_argument('--onlydiff', action="store_true", help='Only compute diff files. \
                    (default: none)')
parser.add_argument('--onlyunzip', action="store_true", help='Only unzip files. \
                    (default: none)')
args = parser.parse_args()

logging.info('************Starting a new run.************')

if args.directory:
    zonefiledirectory = args.directory
else:
    zonefiledirectory = os.path.join(os.getcwd(), "zonefiles")

if args.cpu:
    usecpus = args.cpu - num_cores
elif num_cores < 3:
    usecpus = 1
else:
    usecpus = num_cores - 2
logging.info(f'Using {usecpus} CPUs.')

def main():
    zonefiles = os.listdir(zonefiledirectory)
    if len(zonefiles) == 0:
        logging.error('No zone files detected.  Shutting down.')
        logging.error(zonefiledirectory)
        print('No zone files detected.  Shutting down.')
        print(zonefiledirectory)
        exit(666)
    if not args.onlydiff:
        Parallel(n_jobs=usecpus)(
            delayed(unzipfiles)(file) for file in zonefiles)  # Parallel unzipping because gzip is single-threaded.
    zonefiles = os.listdir(zonefiledirectory) # Running a second time in case we unzipped or diff'ed anything.
    if not args.onlyunzip:
        Parallel(n_jobs=usecpus)(
            delayed(difffiles)(file) for file in zonefiles)  # Parallel diffing because diff is single-threaded.

    zonefiles = os.listdir(zonefiledirectory) # Running a third time in case we unzipped or diff'ed anything.
    textfiles = 0
    difffilecount = 0
    for file in zonefiles:
        if re.search('\.txt$', file):
            textfiles += 1
        elif re.search('\.diff$', file):
            difffilecount += 1

    splittlds = ['app', 'biz', 'club', 'com', 'dev', 'icu', 'info', 'link', 'live', 'net', 'online', 'org', 'page',
                 'shop', 'site', 'store', 'top', 'vip', 'wang', 'work', 'xyz']
    largetlds = []
    for tld in splittlds:
        largetlds.append(tld + '.txt')
        largetlds.append(tld + '.diff')

    print("Splitting large TLDs up into pieces.")
    for tld in largetlds:
        bigfilewithpath = os.path.join(zonefiledirectory, tld)
        print(f'Splitting %s' % bigfilewithpath)
        os.system("rm %s.split*" % bigfilewithpath)
        os.system("split -a 4 -l 100000 %s %s.split" % (bigfilewithpath, bigfilewithpath))

    logging.info('Available total zone files:')
    logging.info(textfiles)
    print(f'Available total zone files: %s' % textfiles)
    logging.info('Available total diff files:')
    logging.info(difffilecount)
    print(f'Available total diff files: %s' % difffilecount)

    totaltime = int(datetime.datetime.now().timestamp()) - exec_start_time
    print(f'Total Time was {str(datetime.timedelta(seconds=totaltime))}.')
    logging.info(f'Total Time was {str(datetime.timedelta(seconds=totaltime))}.')
    logging.info('************Ending run.************')


def unzipfiles(filename):
    if not re.search('\.txt\.gz$', filename):
        return
    filewithpath = os.path.join(zonefiledirectory, filename)
    unzipfilewithpath = re.sub('\.gz$', '', filewithpath)
    oldunzipfilewithpath = unzipfilewithpath + ".old"
    print(f'Unzipping %s.' % filewithpath)
    if os.path.isfile(unzipfilewithpath): # Backup existing file to .old
        os.system('cp -u %s %s' % (unzipfilewithpath, oldunzipfilewithpath))
    os.system(f'nice gunzip -kf %s' % (filewithpath)) # Overwrites existing unzipped file and keeps the source .gz


def difffiles(filename):
    if not re.search('\.txt$', filename):
        return
    filewithpath = os.path.join(zonefiledirectory, filename)
    oldfilewithpath = filewithpath + ".old"
    difffilewithpath = re.sub('\.txt$', '', filewithpath)+ '.diff'
    print(f'Working on diffs for %s.' % filewithpath)
    if os.path.isfile(oldfilewithpath):
        print(f'We have an old version of %s so we will make a diff file of that now as %s.' % (filewithpath,difffilewithpath))
        # os.system("diff -u %s %s | grep '^+[^+]' | sed 's/^+//' > %s" % (oldfilewithpath, filewithpath, difffilewithpath))
        os.system("nice comm --nocheck-order -13 %s %s > %s" % (oldfilewithpath, filewithpath, difffilewithpath))
    else:
        print(f'No old version of %s so we will use the full file as a diff file at %s.' % (filewithpath,difffilewithpath))
        os.system('cp -u %s %s' % (filewithpath, difffilewithpath))



if __name__ == '__main__':
    main()

