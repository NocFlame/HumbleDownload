#!/usr/bin/env python
# -*- coding: utf-8 -*-
import argparse
import requests
import json
import time
import os
from pathlib import Path
from os import listdir
from os.path import isfile, join
import hashlib
import urllib.request
import shutil
#from colorama import init, Fore, Back, Style #https://github.com/tartley/colorama
from termcolor import colored #https://pypi.org/project/termcolor/

VERSION = "version 0.1\n"
COOKIE = "" #Static value from file
URL_ORDER = "https://www.humblebundle.com:443/api/v1/order/"
URL_LIBRARY = "https://www.humblebundle.com:443/home/library"
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:63.0) Gecko/20100101 Firefox/63.0", "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8", "Accept-Language": "en-US,en;q=0.5", "Accept-Encoding": "gzip, deflate", "DNT": "1", "Connection": "close", "Upgrade-Insecure-Requests": "1"}

filename_match_list = []
filename_no_match_list = []
md5_match_list = []
md5_no_match_list = []

header = "\
  _    _                 _     _      ____                  _ _      \n\
 | |  | |               | |   | |    |  _ \                | | |     \n\
 | |__| |_   _ _ __ ___ | |__ | | ___| |_) |_   _ _ __   __| | | ___ \n\
 |  __  | | | | '_ ` _ \| '_ \| |/ _ \  _ <| | | | '_ \ / _` | |/ _ \\\n\
 | |  | | |_| | | | | | | |_) | |  __/ |_) | |_| | | | | (_| | |  __/\n\
 |_|  |_|\__,_|_| |_| |_|_.__/|_|\___|____/ \__,_|_| |_|\__,_|_|\___|\n"

def colorize(string, color):
    #TODO: fix color output
    #print(Fore.RED + string + Style.RESET_ALL) #Colorama
    print(colored(string, color)) #Termcolor

def check_cookie():
    global COOKIE
    if isfile('cookie.txt'):
        cf = open('cookie.txt','r')
        temp_cookie = cf.readline()
        COOKIE = json.loads(temp_cookie)
        cf.close()
    else:
        colorize(("Directory Path:", Path().absolute()),"RED")
        colorize(("MyError: Could not read cookie.txt"),"RED")
        exit()

def get_settings():
    if isfile('settings.json'):
        with open('settings.json') as json_file:
            data = json.load(json_file)
            return data
    else:
        colorize(("Directory Path:", Path().absolute()),"RED")
        colorize(("MyError: Could not read settings.json"),"RED")
        exit()

def api_call(key):
    url = URL_ORDER + key +"?all_tpkds=true"
    tmp = requests.get(url, headers=HEADERS, cookies=COOKIE)
    #print(tmp.content)
    #exit(1)
    if tmp.status_code != 200:
        colorize("Error fetching all orders", 'red')
        exit()
    json_data = json.loads(tmp.content)
    return json_data
    #print(json_data['product']['human_name'])

def get_library(): # First request that includes the keys for further polling
    #print("URL: {0} headers: {1} cookie: {2}".format(URL_LIBRARY, HEADERS, COOKIE))
    tmp = requests.get(URL_LIBRARY, headers=HEADERS, cookies=COOKIE)
    #print(tmp.content)
    #exit(1)
    return tmp

def extract_keys_from_library(library_res):
    #print(library_res)
    pos0 = str(library_res.content).find("gamekeys") + 13
    #print(pos0)
    pos1 = str(library_res.content).find("hasAdmin") - 9
    #print(pos1)
    raw_keys = str(library_res.content)[pos0:pos1]
    #print(raw_keys)
    raw_keys = raw_keys.replace("\"","")
    raw_keys = raw_keys.replace(" ","")
    #print(raw_keys)
    keys = str(raw_keys).split(",")
    #print(keys)
    return keys

def parse_json(json):
    data = []
    for res in json:
        counter = 0
        bundle_data = {}
        #print(res['product']['machine_name'])
        #print(res['product']['human_name'])
        #print(len(res['subproducts']))
        bundle_data['bundle'] = res['product']['machine_name']
        bundle_data['name'] = res['product']['human_name']
        bundle_data['nbr_subproducts_org'] = len(res['subproducts'])
        bundle_data['nbr_subproducts'] = counter
        bundle_data['items'] = []
        for item in res['subproducts']:
            single_item = {}
            single_item['download_struct'] = []
            #print(item['machine_name'])
            #print(item['human_name'])
            single_item['human_name'] = item['human_name']
            try:
                if item['downloads'][0]['platform'] in ('video', 'ebook'): #Values could be: video, ebook
                        #print(item['machine_name'])
                        single_item['machine_name'] = item['machine_name']
                        #print(item['downloads'][0]['platform'])
                        single_item['platform'] = item['downloads'][0]['platform']
                        #print("**********")
                        for dl_str in item['downloads'][0]['download_struct']:
                            if dl_str['name'] in ('PDF', 'EPUB', 'Download'):
                                    tmp_dl_info = {}
                                    #print(dl_str['name'])
                                    tmp_dl_info['name'] = dl_str['name']
                                    #print(dl_str['url']['web'])
                                    tmp_dl_info['web'] = dl_str['url']['web']
                                    #print(dl_str['human_size'])
                                    tmp_dl_info['human_size'] = dl_str['human_size']
                                    #print(dl_str['md5'])
                                    tmp_dl_info['md5'] = dl_str['md5']
                                    try:
                                        #print(dl_str['sha1'])
                                        tmp_dl_info['sha1'] = dl_str['sha1']
                                    except (KeyError):#missing sha1
                                        pass
                                    single_item['download_struct'].append(tmp_dl_info)
                                    #print("----------")
                #bundle_data.setdefault(single_item['human_name'], single_item)
                bundle_data['items'].append(single_item)
                counter = counter + 1
                bundle_data['nbr_subproducts'] = counter
                #print("//////////")
            except (IndexError):
                #print("IndexError") #Nothing to download (No url)
                pass
        data.append(bundle_data)
    return data

#Splits file in chuncks and calculates MD5sum
def calculate_md5(complete_filename_with_path):
    #https://stackoverflow.com/questions/1131220/get-md5-hash-of-big-files-in-python
    block_size=256*128
    calculate_md5 = hashlib.md5()
    with open(complete_filename_with_path, 'rb') as file:
        for chunk in iter(lambda: file.read(block_size), b''):
            calculate_md5.update(chunk)
    return calculate_md5.hexdigest()

def calculate_sha1(complete_filename_with_path):
    #https://stackoverflow.com/questions/1131220/get-md5-hash-of-big-files-in-python
    block_size=256*128
    calculate_sha1 = hashlib.sha1()
    with open(complete_filename_with_path, 'rb') as file:
        for chunk in iter(lambda: file.read(block_size), b''):
            calculate_sha1.update(chunk)
    return calculate_sha1.hexdigest()

#
def md5check(filepath, filename, org_checksum):
    try:
        file_name = join(filepath, filename)
        print("MD5 checking: " + file_name)
        original_md5 = org_checksum
        calculated_md5 = calculate_md5(file_name)
        # Finally compare original MD5 with freshly calculated
        if original_md5 == calculated_md5:
            #print("MD5 verified.")
            return True
        else:
            #colorize("MD5 verification failed!.", "red")
            return False
    except OSError as identifier:
        raise OSError('MD5check failure, details: "{id}"'.format(id=identifier))

def sha1check(filepath, filename, org_checksum):
    try:
        file_name = join(filepath, filename)
        print("SHA1 checking: " + file_name)
        original_sha1 = org_checksum
        calculated_sha1 = calculate_sha1(file_name)
        # Finally compare original SHA1 with freshly calculated
        if original_sha1 == calculated_sha1:
            #print("SHA1 verified.")
            return True
        else:
            #colorize("SHA1 verification failed!.", "red")
            return False
    except OSError as identifier:
        raise OSError('SHA1check failure, details: "{id}"'.format(id=identifier))

def getItemObject(machine_name):
    for bundle in data:
        for items in bundle['items']:
            try:
                if items['machine_name'].lower() == machine_name.lower():
                    return items
            except KeyError:
                pass

def getURL(item, name):
    for dl_str in item['download_struct']:
        if dl_str['name'].lower() == name.lower() or dl_str['name'].lower() == "download":
            return dl_str['web']

def getMD5(item, name):
    for dl_str in item['download_struct']:
        if dl_str['name'].lower() == name.lower() or dl_str['name'].lower() == "download":
            return dl_str['md5']

def getSHA1(item, name):
    for dl_str in item['download_struct']:
        if dl_str['name'].lower() == name.lower() or dl_str['name'].lower() == "download":
            try:
                return dl_str['sha1']
            except KeyError as identifier:
                return "n/a"

def chunk_report(bytes_so_far, chunk_size, total_size):
    import sys
    percent = float(bytes_so_far) / total_size
    percent = round(percent*100, 2)
    sys.stdout.write("Downloaded %d of %d bytes (%0.2f%%)\r" %
        (bytes_so_far, total_size, percent))

    if bytes_so_far >= total_size:
       sys.stdout.write('\n')

def chunk_read(response, chunk_size=8192, report_hook=None):
   total_size = response.info().getheader('Content-Length').strip()
   total_size = int(total_size)
   bytes_so_far = 0

   while 1:
      chunk = response.read(chunk_size)
      bytes_so_far += len(chunk)

      if not chunk:
         break

      if report_hook:
         report_hook(bytes_so_far, chunk_size, total_size)

   return bytes_so_far

def checksum_file(file_info):
    #structure of file_info -> {'path':path, 'machine_name':machine_name, 'filetype':filetype}
    #TODO check which checksums that should be done
    file_item = getItemObject(file_info['machine_name'])

    md5 = getMD5(file_item, file_info['filetype'])
    md5res = md5check(file_info['path'], file_info['machine_name'], md5)

    sha1 = getSHA1(file_item, file_info['filetype'])
    sha1res = sha1check(file_info['path'], file_info['machine_name'], md5)

    if (md5res or sha1res):
        return True
    else:
        return False


def download(path, machine_name, filetype):
    #TODO: How to do this one with many threads?
    #type is MOBI, EPUB, PDF, Download (last is for platform: video)
    file_item = getItemObject(machine_name)
    url = getURL(file_item, filetype)

    #file_name_to_save = machine_name
    file_name_to_save = os.path.join(path, machine_name)
    # Download the file from `url` and save it locally under `file_name`:
    #chunk_read(response, report_hook=chunk_report),
    try:
        print("Downloading file: " + machine_name + " to path: " + path)
        print("URL for download: " + url)
        with urllib.request.urlopen(url) as response, open(file_name_to_save, 'wb') as out_file:
            shutil.copyfileobj(response, out_file)
            out_file.close()
            file_info = {'path':path, 'machine_name':machine_name, 'filetype':filetype}
            return file_info
    except OSError as identifier:
        print("download failure?: ")
        print(identifier)
        return False

def loop_through_list_until_empty(name_of_list, filetype, max_retires=3):
    for i in range(max_retires):
        try:
            for machine_name in name_of_list:
                print("Trying to download file: " + machine_name)
                file_info = download(DOWNLOAD_TEMP_PATH, machine_name, filetype)
                res = checksum_file(file_info)
                if res:
                    shutil.move(join(DOWNLOAD_TEMP_PATH, machine_name), join(join(PATH, filetype), machine_name + "." + filetype))
                    name_of_list.remove(machine_name)
                    i = 0
                else:
                    colorize("FAILED to download: ".format(machine_name), "red")
                print("There are {} files left to download".format(len(name_of_list)))
            if len(name_of_list) == 0:
                break
        except OSError as identifier:
            print("loop_through_list_until_empty: ")
            print(identifier)
            pass

#When returning, adding +1 for the dot (fullstop) '.'
def getfileformatlength(x):
    return {
        'epub': 5,
        'pdf': 4,
        'mobi': 5,
        'zip': 4
    }.get(x, 0)    # 0 is default if x not found

def handle_MD5check(PATH, mname, name, md5):
    global md5_match_list, md5_no_match_list
    res = md5check(PATH, name, md5)
    if res:
        md5_match_list.append(mname)
    else:
        colorize("MD5 check failed on {0}".format(name), "red")
        md5_no_match_list.append(mname)

def assure_path_exists(path):
    dir = os.path.dirname(path)
    if not os.path.exists(dir):
        os.makedirs(dir)
def handle_args(args):
    if args.verbose:
        print("Verbose output enabled")

#----------------------------------------------
# Functions end here
#----------------------------------------------

check_cookie()

if os.name == 'nt':
    settings = get_settings()
    DOWNLOAD_TEMP_PATH = settings['WINDOWS']['DOWNLOAD_TEMP_PATH']
    PATH = settings['WINDOWS']['DOWNLOAD_PATH']
    if (DOWNLOAD_TEMP_PATH) == '': DOWNLOAD_TEMP_PATH = Path().absolute()
    if (PATH) == '': PATH = Path().absolute()
    assure_path_exists(DOWNLOAD_TEMP_PATH)
    assure_path_exists(PATH)
    clean_screen = 'cls'
    pass # Windows
else:
    settings = get_settings()
    DOWNLOAD_TEMP_PATH = settings['LINUX']['DOWNLOAD_TEMP_PATH']
    PATH = settings['LINUX']['DOWNLOAD_PATH']
    if (DOWNLOAD_TEMP_PATH) == '': DOWNLOAD_TEMP_PATH = Path().absolute()
    if (PATH) == '': PATH = Path().absolute()
    assure_path_exists(DOWNLOAD_TEMP_PATH)
    assure_path_exists(PATH)
    clean_screen = 'clear'
    pass # other (unix)

#init() # Colorama init call
os.system(clean_screen)
colorize(header, 'magenta')
colorize(VERSION, 'green')

parser = argparse.ArgumentParser(description='HumbleBundle Downloader')
group = parser.add_mutually_exclusive_group()
group.add_argument('-q','--quiet', help='Runs quietly and just report when its done', action="store_true", required=False)
group.add_argument('-v','--verbose', help='verbose output', action="store_true", required=False)
parser.add_argument('-n','--no-calculate_md5', help='Skips MD5 checks for local files', action="store_true", required=False)
parser.add_argument('-d', '--dry-run', help='Does a dry run that skips actual download', action="store_true", required=False)
parser.add_argument('-B', '--Books', help='Download only books', action="store_true", required=False) #All book formats ie using e,p,m switches
parser.add_argument('-e', '--epub', help='Download only epub books', action="store_true", required=False) #EPUB
parser.add_argument('-p', '--pdf', help='Download only pdf books', action="store_true", required=False) #PDF
parser.add_argument('-m', '--mobi', help='Download only mobi books', action="store_true", required=False) #MOBI
parser.add_argument('-o', '--other', help='Download only zip files for video/other files', action="store_true", required=False) #Video/Other
args = parser.parse_args()

handle_args(args)

print("Fetching your keys...")
library_res = get_library()
keys = extract_keys_from_library(library_res)
nbr_keys = len(keys)
raw_json = []

if not keys:
    #raw_json.append(api_call(keys[0]))
    colorize("No keys found, is the correct cookie applied?", 'red')
    exit(1)
if not args.quiet:
    colorize("Got {0} keys, getting data for each one".format(nbr_keys), 'green')

for itr, key in enumerate(keys):
    #api_call(key)
    raw_json.append(api_call(key))
    print(key + ": {0}/{1}".format(itr+1, nbr_keys))
    data = parse_json(raw_json)

#DUBUG - Write raw_json data to file
#json.dump(raw_json, open('data.json','w'))


def masterhandler(hb_data, PATH, fileformat):
    head, tail = os.path.split(PATH)
    print("head: {0} & tail: {1}".format(head, tail))
    if (not os.path.isdir(PATH) and not tail):
        assure_path_exists(PATH)
    #exit(1)
    global localFilenamelist, md5_match_list, md5_no_match_list, filename_match_list, filename_no_match_list
    #TODO: HAVE TO BE GENERIC from the dot (full stop) of filename
    file_ending_trimming = getfileformatlength(fileformat.lower())
    localFilenamelist = [f[:-file_ending_trimming] for f in listdir(PATH) if isfile(join(PATH, f))] #[:-5] is to cut out .epub on filename
    for bundle in data:
        for items in bundle['items']:
            for dl_str in items['download_struct']:
                if dl_str['name'].lower() == fileformat.lower() or (dl_str['name'].lower() == "download" and fileformat.lower() == "zip"):
                    mname = items['machine_name']
                    md5 = dl_str['md5']
                    if mname in localFilenamelist:
                        filename_match_list.append(mname)
                        #print("Found filename match on: " + mname)
                        handle_MD5check(PATH, mname, mname + "." + fileformat.lower(), md5)
                    else:
                        filename_no_match_list.append(mname)
                        #print("Failed to find: " + mname)
                        #Download file

    print("Found {} matches on filename".format(len(filename_match_list)))
    print("Found {} missing matches on filename".format(len(filename_no_match_list)))
    print("Found {} filenames not in remote list of files".format(len(localFilenamelist) - (len(filename_match_list) + len(filename_no_match_list))))
    print("Found {} true hashes on md5".format(len(md5_match_list)))
    print("Found {} failed hashes on md5".format(len(md5_no_match_list)))

    #Debug
    #for item in filename_no_match_list:
    #    print(item)

    loop_through_list_until_empty(filename_no_match_list, fileformat.lower())
    loop_through_list_until_empty(md5_no_match_list, fileformat.lower())

    localFilenamelist = []
    filename_match_list = []
    filename_no_match_list = []
    md5_match_list = []
    md5_no_match_list = []

    print("All files is done for type: ", fileformat.lower())

masterhandler(data, join(PATH, 'epub/'), 'epub') #EPUB
masterhandler(data, join(PATH, 'pdf/'), 'pdf') #PDF
masterhandler(data, join(PATH, 'mobi/'), 'mobi') #Mobi
masterhandler(data, join(PATH, 'zip/'), 'zip') #Video/Other?

print("All done!")