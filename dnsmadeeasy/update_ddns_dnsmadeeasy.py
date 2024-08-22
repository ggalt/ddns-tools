#!/usr/bin/env python
#
# Script to update dynamic DNS records at Dnsmadeeasy with HTTPS support.
# Put your settings in settings.json in the same folder with the script 
# and set to run from cron.
#
# Requires following non-core modules;
#  * python-requests, https://pypi.python.org/pypi/requests/
#  * python-dns, https://pypi.python.org/pypi/dnspython/
#
# Author: Sandi Wallendahl <wyrmiyu@gmail.com>
# License: MIT, https://github.com/wyrmiyu/ddns-tools/blob/master/LICENSE

from __future__ import print_function

import socket
import json
import logging
import os
import sys
import requests
import dns.resolver
from datetime import datetime

#logging.basicConfig(format='%(levelname)s: %(message)s')
logging.basicConfig(
    level=logging.INFO,                   # Set the logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',  # Format for log messages
    filename='ddns_log.txt',          # File to write log messages to
    filemode='a'                           # Mode to open the log file: 'a' for append, 'w' for overwrite
)

logger = logging.getLogger(__name__)


def error(message):
    """
    Log an error and exit.
    """
    logger.error(message)
    sys.exit(1)

def check_log_date(my_ip):
    file_path = 'logs/log.txt'
    modification_time = os.path.getmtime(file_path)
    if (NOW.timestamp() - modification_time) > ONE_WEEK:
        logger.info(NOW, "Current IP is:", my_ip)

def check_ssl(url):
    try:
        requests.get(url, verify=True)
    except requests.exceptions.SSLError:
        error('The SSL certificate for {0} is not valid.'.format(url))


def get_current_ip(url=None):
    url = url or GET_IP_URL
    try:
        return requests.get(url).text.strip()
    except requests.ConnectionError:
        logger.debug(
            'Could not get the current IP from {0}'.format(GET_IP_URL))


def get_dns_ip(name=None, target='A'):
    name = name or RECORD_NAME
    bits = name.split('.')
    while bits:
        try:
            ns = str(dns.resolver.resolve('.'.join(bits), 'NS')[0])
        except:
            bits.pop(0)
        else:
            ns = socket.gethostbyname(ns)
            resolver = dns.resolver.Resolver()
            resolver.nameservers = [ns]
            q = resolver.resolve(name, target)
            ip = str(q[0]).strip()
            # logger.debug("Updated IP:", ip)
            # print( NOW, "Updated IP Address:", ip)
            return ip
    error('Could not get the authoritative name server for {0}.'.format(name))


def update_ip_to_dns(ip, url=None):
    url = url or UPDATE_IP_URL
    check_ssl(url)
    params = {
        'username': USERNAME,
        'password': PASSWORD,
        'id': RECORD_ID,
        'ip': ip,
    }
    return requests.get(url, params=params)


BASE_DIR = os.path.dirname(__file__)

try:
    settings = json.loads(open(os.path.join(BASE_DIR, 'settings.json')).read())
except IOError:
    error('No `settings.json` file. Create one from the '
          '`settings.json.sample` file.')
except ValueError:
    error('Invalid `settings.json` file. Check the `settings.json.sample` '
          'file for an example.')

USERNAME = settings.get('USERNAME', None)
PASSWORD = settings.get('PASSWORD', None)
RECORD_ID = settings.get('RECORD_ID', None)
RECORD_NAME = settings.get('RECORD_NAME', None)
GET_IP_URL = settings.get('GET_IP_URL', 'http://myip.dnsmadeeasy.com')
UPDATE_IP_URL = settings.get('UPDATE_IP_URL',
                             'https://cp.dnsmadeeasy.com/servlet/updateip')
LOG_LEVEL = settings.get('LOG_LEVEL', 'INFO')
NOW = datetime.now()
ONE_WEEK = 604800

for opt in 'USERNAME', 'PASSWORD', 'RECORD_ID', 'RECORD_NAME':
    if not locals().get(opt):
        error('Missing `{0}` setting. Check `settings.json` file.'.format(opt))

try:
    logger.setLevel(getattr(logging, LOG_LEVEL))
except AttributeError:
    error('Invalid `LOG_LEVEL` setting. Check `settings.json` file. Valid '
          'log levels are: DEBUG, INFO, WARNING, ERROR, CRITICAL.')

if __name__ == '__main__':
    current_ip = get_current_ip()
    if current_ip:
        dns_ip = get_dns_ip()
        if current_ip != dns_ip:
            logger.debug('Current IP differs with DNS record, attempting to '
                         'update DNS.')
            request = update_ip_to_dns(current_ip)
            if request and request.text == 'success':
                # print( NOW, "IP address change.  Old IP:", dns_ip, "New IP:", current_ip)
                logger.info('Updating record for {0} to {1} was '
                            'succesful.'.format(RECORD_NAME, current_ip))
            else:
                error('Updating record for {0} to {1} failed.'.format(
                    RECORD_NAME, current_ip))
        else:
            check_log_date(current_ip)
            logger.debug(
                'No changes for DNS record {0} to report.'.format(RECORD_NAME))
