# Proactive Hunting for Fake Websites with Zone Files

## To Use:
Sign up for an account under the ICANN Centralized Zone Data Service (CZDS) at https://czds.icann.org/ and make access requests for each zone that you want to download.
Top phishing abused TLDs are .COM .LINK .INFO .WORK .ZIP .REVIEW .COUNTRY .CRICKET .GQ .KIM .PARTY .SCIENCE

Use the CZDS downloader at https://github.com/icann/czds-api-client-python.
Use /path/to/phishing-rod as the zone file destination folder.  The downloader will automatically add a zonefiles/ directory to that location.  Alternatively: run phishing-rod with the -d flag to tell it where to find the zone files.

Copy domainsandtrademarks.sample.txt to domainsandtrademarks.txt and edit it to remove the defaults and add your own domains and trademarks.

Run phishing rod with `python3 ./phishingrod.py`
