#!/usr/bin/env python
# -*- coding: utf-8 -*-
import argparse
from datetime import datetime
import requests
import sys
import json
import os
from pathlib import Path
from os import listdir
from os.path import isfile, join
import hashlib
import shutil
#from colorama import init, Fore, Back, Style #https://github.com/tartley/colorama
from termcolor import colored #https://pypi.org/project/termcolor/

VERSION = "version 0.2\n"
COOKIE = "" #Static value from file
URL_ORDER = "https://www.humblebundle.com:443/api/v1/order/"
URL_LIBRARY = "https://www.humblebundle.com:443/home/library"
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:63.0) Gecko/20100101 Firefox/126.0", "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8", "Accept-Language": "en-US,en;q=0.5", "Accept-Encoding": "gzip, deflate", "DNT": "1", "Connection": "close", "Upgrade-Insecure-Requests": "1"}

filename_match_list = []
filename_no_match_list = []
md5_match_list = []
md5_no_match_list = []
verbose = True

header = "\
  _    _                 _     _      ____                  _ _      \n\
 | |  | |               | |   | |    |  _ \                | | |     \n\
 | |__| |_   _ _ __ ___ | |__ | | ___| |_) |_   _ _ __   __| | | ___ \n\
 |  __  | | | | '_ ` _ \| '_ \| |/ _ \  _ <| | | | '_ \ / _` | |/ _ \\\n\
 | |  | | |_| | | | | | | |_) | |  __/ |_) | |_| | | | | (_| | |  __/\n\
 |_|  |_|\__,_|_| |_| |_|_.__/|_|\___|____/ \__,_|_| |_|\__,_|_|\___|\n"

def colorize(string, color):
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
    pos0 = str(library_res.content).find('<script id="user-home-json-data" type="application/json">') + 57 + 4 #len(str) + '\\n '
    #print(pos0)
    pos1 = str(library_res.content).find("</script>", pos0) - 2 #\\n
    #print(pos1)
    raw_user_json = str(library_res.content)[pos0:pos1]
    raw_user_json = raw_user_json.replace('\\"',"")
    raw_user_json = raw_user_json.replace("\\","")
    #print(raw_user_json)
    json_object = json.loads(raw_user_json)
    #print(raw_keys)
    #raw_keys = raw_keys.replace("\"","")
    #raw_keys = raw_keys.replace(" ","")
    #print(raw_keys)
    keys = json_object['gamekeys'] #str(raw_keys).split(",")
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
                raw_platforms.append(item['downloads'][0]['platform'])
                #colorize("Plattform detected: " + item['downloads'][0]['platform'], "yellow")    
                #if item['downloads'][0]['platform'] in ('video', 'ebook', 'windows'): #Values could be: video, ebook
                #print(item['machine_name'])
                single_item['machine_name'] = item['machine_name']
                #print(item['downloads'][0]['platform'])
                single_item['platform'] = item['downloads'][0]['platform']
                #print("**********")
                for dl_str in item['downloads'][0]['download_struct']:
                    #if dl_str['name'] in ('PDF', 'EPUB', 'Download'):
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
        file_name = str(join(filepath, filename))
        print("MD5 checking: " + file_name)
        original_md5 = org_checksum
        calculated_md5 = calculate_md5(file_name)
        # Finally compare original MD5 with freshly calculated
        if original_md5 == calculated_md5:
            if verbose:
                print("MD5 verified.")
            md5res = {"verdict": True, "checksum_org": original_md5, "checksum_calc": calculated_md5}
            return md5res
        else:
            if original_md5 == "n/a":
                colorize("MD5 verification failed due to missing SHA1 from source", "red")
            else:
                colorize("MD5 verification failed!", "red")
                md5res = {"verdict": False, "checksum_org": original_md5, "checksum_calc": calculated_md5}
                return md5res
    except OSError as identifier:
        raise OSError('MD5check failure, details: "{id}"'.format(id=identifier))

def sha1check(filepath, filename, org_checksum):
    try:
        file_name = str(join(filepath, filename))
        print("SHA1 checking: " + file_name)
        original_sha1 = org_checksum
        calculated_sha1 = calculate_sha1(file_name)
        # Finally compare original SHA1 with freshly calculated
        if original_sha1 == calculated_sha1:
            if verbose:
                print("SHA1 verified.")
            sha1res = {"verdict": True, "checksum_org": original_sha1, "checksum_calc": calculated_sha1}
            return sha1res
        else:
            if original_sha1 == "n/a":
                colorize("SHA1 verification failed due to missing SHA1 from source", "red")
            else:
                colorize("SHA1 verification failed!", "red")
            sha1res = {"verdict": False, "checksum_org": original_sha1, "checksum_calc": calculated_sha1}
            return sha1res
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

def getURL(item, filetype):
    for dl_str in item['download_struct']:
        if dl_str['name'].lower() == filetype:
            if "FILE_NAME" in dl_str['web']:
                return "n/a"
            else:
                return dl_str['web']
    #So filetype was not in the normal list? Loop again and check download url for best match
    for dl_str in item['download_struct']:
        url = dl_str['web']
        url_filetype = getFileTypeFromUrl(url)
        if url_filetype == filetype:
            if "FILE_NAME" in url:
                return "n/a"
            else:
                return url
    colorize("Could not get URL from {} with {} extension".format(item['human_name'], filetype), "red")
    log_error("Could not get URL from {} with {} extension".format(item['human_name'], filetype))

def getHumanSize(item, filetype):
    for dl_str in item['download_struct']:
        if dl_str['name'].lower() == filetype.lower():
            return dl_str['human_size']
    for dl_str in item['download_struct']:
        if dl_str['name'].lower() in weirdNamesExceptionList():
            return dl_str['human_size']
    return '0'

def getMD5(item, filetype):
    for dl_str in item['download_struct']:
        if dl_str['name'].lower() == filetype.lower():
            try:
                return dl_str['md5']
            except KeyError as identifier:
                return "n/a"
    for dl_str in item['download_struct']:
        if dl_str['name'].lower() in weirdNamesExceptionList():
            try:
                return dl_str['md5']
            except KeyError as identifier:
                return "n/a"
    log_error("New weird name detected: " + dl_str['name'])
    try:
        return dl_str['md5']
    except KeyError as identifier:
        return "n/a"

def getSHA1(item, filetype):
    for dl_str in item['download_struct']:
        if dl_str['name'].lower() == filetype.lower() or dl_str['name'].lower() in weirdNamesExceptionList():
            try:
                return dl_str['sha1']
            except KeyError as identifier:
                return "n/a"
    for dl_str in item['download_struct']:
        if dl_str['name'].lower() in weirdNamesExceptionList():
            try:
                return dl_str['sha1']
            except KeyError as identifier:
                return "n/a"
    log_error("New weird name detected: " + dl_str['name'])
    try:
        return dl_str['sha1']
    except KeyError as identifier:
        return "n/a"

def weirdNamesExceptionList():
    return ['download', 'supplement', 'mp3', 'companion file', 'installer', '.zip']

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
    mname = file_info['machine_name']
    filetype = file_info['filetype'].lower()
    file_item = getItemObject(mname)

    md5 = getMD5(file_item, filetype)
    md5res = md5check(file_info['path'], mname, md5)

    sha1 = getSHA1(file_item, filetype)
    sha1res = sha1check(file_info['path'], mname, sha1)

    if (md5res['verdict'] and sha1res['verdict']):
        return True
    elif (md5res['verdict'] or sha1res['verdict']):
            #log faulty one but still return true
            if not md5res['verdict']:
                error_text = "MD5 verification failed!" + " " + \
                " filetype:" + filetype + " " + \
                " filename:" + mname + " " + \
                " org_checksum: " + md5res['checksum_org'] + " " + \
                " calculated_checksum: " + md5res['checksum_calc']
                log_error(error_text )
            if not sha1res['verdict']:
                error_text = "SHA1 verification failed!" + " " + \
                " filetype:" + filetype + " " + \
                " filename:" + mname + " " + \
                " org_checksum: " + sha1res['checksum_org'] + " " + \
                " calculated_checksum: " + sha1res['checksum_calc']
                log_error(error_text )
            return True
    else:
        #Both faulty and logged return false
        error_text = "MD5 verification failed!" + " " + \
        " filetype:" + filetype + " " + \
        " filename:" + mname + " " + \
        " org_checksum: " + md5res['checksum_org'] + " " + \
        " calculated_checksum: " + md5res['checksum_calc']
        log_error(error_text )
        error_text = "SHA1 verification failed!" + " " + \
        " filetype:" + filetype + " " + \
        " filename:" + mname + " " + \
        " org_checksum: " + sha1res['checksum_org'] + " " + \
        " calculated_checksum: " + sha1res['checksum_calc']
        log_error(error_text )
        return False

def getFileTypeFromUrl(url):
    if "FILE_NAME" in url:
        return ""
    else:
        split_url = url.split('?')
        url_file_type = split_url[0][split_url[0].find('.',-6)+1:].lower() #+1 is to skip the full stop
        return url_file_type

def getSubfolderFromPlatform(file_info):
    platform = file_info['platform'].lower()
    filetype = file_info['filetype'].lower()
    if platform == "ebook":
        return filetype
    else:
        return platform

def progress_download(url, filename):
    with open(filename, 'wb') as f:
        response = requests.get(url, stream=True)
        total = response.headers.get('content-length')

        if total is None:
            f.write(response.content)
        else:
            downloaded = 0
            total = int(total)
            for data in response.iter_content(chunk_size=max(int(total/1000), 1024*1024)):
                downloaded += len(data)
                f.write(data)
                done = int(50*downloaded/total)
                sys.stdout.write('\r[{}{}]'.format('█' * done, '.' * (50-done)))
                sys.stdout.flush()
    sys.stdout.write('\n')

def download(machine_name, filetype):
    #TODO: How to do this one with many threads?
    path = DOWNLOAD_TEMP_PATH
    file_item = getItemObject(machine_name)
    url = getURL(file_item, filetype)
    if url != "n/a":
        url_file_type = getFileTypeFromUrl(url)
        human_size = getHumanSize(file_item, url_file_type)
        temp_filename = os.path.join(path, machine_name)
        try:
            print("Starting download for: " + file_item['human_name'] + "." + url_file_type + " with size: " + human_size)
            print("Downloading file: " + machine_name + " to path: " + path)
            print("URL for download: " + url)
            # with urllib.request.urlopen(url) as response, open(temp_filename, 'wb') as out_file:
            #     shutil.copyfileobj(response, out_file)
            #     out_file.close()
            #     file_info = {'path':path, 'machine_name':machine_name, 'filetype':url_file_type, 'platform': file_item['platform']}
            #     return file_info
            progress_download(url, temp_filename)
            file_info = {'path':path, 'machine_name':machine_name, 'filetype':url_file_type, 'platform': file_item['platform']}
            return file_info
        except OSError as identifier:
            print("download failure?: ")
            print(identifier)
            error_text = "Failure to download file! " + "filetype:" + url_file_type + " filename: " + machine_name + " path: " + path + " identifier" + str(identifier)
            log_error(error_text)
            return False
    else:
        return False
    
def checkFileAgainstFilter(filename, allowed_filetypes):
    filetype = filename[filename.find('.',-6)+1:]
    if filetype in allowed_filetypes or "*" in allowed_filetypes:
        return True
    else:
        print("Skipping downloading file {} since its not in the allowed filetypes aka its filtered out!".format(filename))
        return False

def handle_existing_tempfiles(mname, filetype):
    #This method is not yet used
    path = DOWNLOAD_TEMP_PATH
    file_item = getItemObject(mname)
    url = getURL(file_item, filetype)
    temp_filename = os.path.join(path, mname)
    if os.path.exists(temp_filename):
        file_info = {'path':path, 'machine_name':mname, 'filetype':filetype, 'platform': file_item['platform']}
        return file_info
    else:
        return False

def loop_through_list_until_empty(list_of_missing_files, allowed_filetypes, max_retires=3):
    for i in range(max_retires):
        try:
            for filename in list_of_missing_files:
                if checkFileAgainstFilter(filename, allowed_filetypes):
                    #Debug
                    if filename == DEBUGTEXT:
                        print("Placeholder for debugprint")
                    machine_name = filename[:filename.find('.',-6)]
                    filetype = filename[filename.find('.',-6)+1:]
                    #handle_existing_tempfiles(machine_name, filetype)
                    print("Trying to download file: " + filename)
                    file_info = download(machine_name, filetype)
                    if file_info:
                        res = checksum_file(file_info)
                        if res:
                            move_file(file_info)
                            list_of_missing_files.remove(filename)
                            i = 0
                        else:
                            colorize("FAILED on checksums: " + filename + " with filetype " + filetype, "red")
                            if force_move_file_that_failed_checksum:
                                move_file(file_info)
                    else:
                        colorize("FAILED to download: " + filename + " with filetype " + filetype, "red")
                    print("There are {} files left to download".format(len(list_of_missing_files)))
        except OSError as identifier:
            print("loop_through_list_until_empty: ")
            print(identifier)
            pass

def move_file(file_info):
    platform = file_info['platform'].lower()
    filetype = file_info['filetype'].lower()
    filename = file_info['machine_name'] + "." + filetype
    subfolder = getSubfolderFromPlatform(file_info)
    tempfile = str(join(DOWNLOAD_TEMP_PATH, file_info['machine_name']))
    if platform == "ebook":
        path = str(join(PATH, "ebook/" + filetype))
    else:
        path = str(join(PATH, subfolder))
    finalpath = str(join(path, filename))
    assure_path_exists(path)
    colorize("moving " + tempfile + " to its final resting place: " + finalpath, "blue")
    shutil.move(tempfile, finalpath)

def handle_MD5check(PATH, mname, name, md5):
    global md5_match_list, md5_no_match_list
    res = md5check(PATH, name, md5)
    if res:
        md5_match_list.append(mname)
    else:
        colorize("MD5 check failed on {0}".format(name), "red")
        md5_no_match_list.append(mname)

def assure_path_exists(path):
    if not path.endswith("/"):
        path += "/"
    dir = os.path.dirname(path)
    if not os.path.exists(dir):
        os.makedirs(dir)

def handle_args(args):
    if args.verbose:
        print("Verbose output enabled")
        verbose = True

def log_error(text):
    now = datetime.now()
    logline = str(now) + " " + \
            " message:" + text
    with open('errors.log', "a") as errorlog:
        errorlog.writelines(logline + "\n")

def getExistingFilesInFolder(platform):
    head = str(join(PATH, platform + "/"))
    if platform != "ebook":
        filelist = [f for f in listdir(head) if isfile(join(head, f))]
        return filelist
    else:
        filelist = []
        dirlist = []
        dirlist.append(head)
        while len(dirlist) > 0:
            for (dirpath, dirnames, filenames) in os.walk(dirlist.pop()):
                dirlist.extend(dirnames)
                #filelist.extend(map(lambda n: os.path.join(*n), zip([dirpath] * len(filenames), filenames)))
                filelist.extend(map(lambda n: os.path.join(n), filenames))
        return filelist

def getSortedUniques(listA):
    if len(listA) > 0:
        list_set = set(listA)
        unique_list = (list(list_set))
        unique_list.sort()
        return unique_list
    else:
        return []


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
parser.add_argument('-n','--no-checksum-on-local-files', help='Skips checksum checks for local files', action="store_true", required=False) # This should be paired with the 'verify_checksum_on_existing_files'
parser.add_argument('-i','--ignore-downloaded-checksum', help='Skips checksum checks for downloaded files', action="store_true", required=False) # This should be paired with the 'force_move_file_that_failed_checksum'
parser.add_argument('-d', '--dry-run', help='Does a dry run that skips actual download', action="store_true", required=False)
parser.add_argument('-B', '--Books', help='Download only books', action="store_true", required=False) #All book formats ie using e,p,m switches
parser.add_argument('-e', '--epub', help='Download only epub books', action="store_true", required=False) #EPUB
parser.add_argument('-p', '--pdf', help='Download only pdf books', action="store_true", required=False) #PDF
parser.add_argument('-m', '--mobi', help='Download only mobi books', action="store_true", required=False) #MOBI
parser.add_argument('-o', '--other', help='Download only zip files for video/other files', action="store_true", required=False) #Video/Other
args = parser.parse_args()

handle_args(args)
raw_json = []
offline = False
raw_platforms = []

#check for offline file
if isfile('data.json'):
    colorize("data.json file found, will use that instead of online. Rename or Remove file to fetch data from online source.", "yellow")
    with open('data.json') as file:
        raw_json = json.load(file)
        offline = True

if not offline:
    print("Fetching your keys...")
    library_res = get_library()
    keys = extract_keys_from_library(library_res)
    nbr_keys = len(keys)

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

data = parse_json(raw_json)

unique_platforms = list(set(raw_platforms))
unique_platforms.sort()
colorize("Plattform detected: ", "yellow")
for platform in unique_platforms:
    colorize(str(platform), "yellow")

if verbose and not offline:
    json.dump(raw_json, open('data.json','w'))


def masterhandler(hb_data, platform, allowed_filetypes):
    localFilenamelist = []
    filename_match_list = set()
    filename_no_match_list = set()
    md5_match_list = []
    md5_no_match_list = []
    head, tail = os.path.split(join(PATH, platform + '/'))
    print("head: {0} & tail: {1}".format(head, tail))
    if (not os.path.isdir(head) and not tail):
        assure_path_exists(head)
    
    localFilenamelist = getExistingFilesInFolder(platform)
    
    for bundle in data:
        for item in bundle['items']:
            try:
                if item['platform'] == platform:
                    for dl_str in item['download_struct']:
                        #if dl_str['name'].lower() in allowed_filetypes or (dl_str['name'].lower() == "download") or ("*" in allowed_filetypes):
                            url_file_type = getFileTypeFromUrl(dl_str['web'])
                            mname = item['machine_name']
                            md5 = dl_str['md5']
                            filename = mname + "." + url_file_type
                            #Debug
                            if mname in DEBUGTEXT:
                                print("placeholder for debugprint")
                            if url_file_type == "": #handle weird behaviour when no download link is available in getFileTypeFromUrl
                                colorize("Could not handle weird file {}".format(mname), "red")
                                log_error("Could not handle weird file {}".format(mname))
                            elif filename in localFilenamelist:
                                filename_match_list.add(mname)
                                #print("Found filename match on: " + mname)
                                if verify_checksum_on_existing_files:
                                    if platform == "ebook":
                                            handle_MD5check(join(head, url_file_type), mname, mname + "." + url_file_type.lower(), md5)
                                    else:
                                        handle_MD5check(head, mname, mname + "." + url_file_type.lower(), md5)
                                #handle_MD5check(head, mname, mname , md5)
                            else:
                                filename_no_match_list.add(filename)
                                #print("Failed to find: " + mname)
                                #Download file
            except KeyError:
                pass
    print("Currently have {} local files in folder {}".format(len((localFilenamelist)), platform))
    print("Found {} matches on filename".format(len((filename_match_list))))
    print("Found {} unique missing matches on filename".format(len((filename_no_match_list))))
    print("Found {} filenames not in remote list of files".format(len((localFilenamelist)) - (len((filename_match_list)) + len((filename_no_match_list)))))
    print("Found {} true hashes on md5".format(len(md5_match_list)))
    print("Found {} failed hashes on md5".format(len(md5_no_match_list)))

    if len(filename_no_match_list) > 0:
        loop_through_list_until_empty(getSortedUniques(filename_no_match_list), allowed_filetypes)
    if len(md5_no_match_list) > 0:
        loop_through_list_until_empty(getSortedUniques(md5_no_match_list), allowed_filetypes)


    print("All files is done for platform:", platform)

#Platforms
#windows, ebook, other, android, mac, video, linux, audio

allowed_filetypes = ["*"] #What file types are allowed ['pdf', 'epub', '*'] * = allow everything
verify_checksum_on_existing_files = True
force_move_file_that_failed_checksum = False
DEBUGTEXT = "" #Input a title like 'advanced_go.pdf' for debugging purposes

for platform in unique_platforms:
    masterhandler(data, platform, allowed_filetypes)

print("All done!")