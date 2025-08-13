#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
HumbleBundle Downloader - Improved version with proper argument handling
and optimizations following Python best practices.
"""
import argparse
import hashlib
import json
import os
import shutil
import sys
from datetime import datetime
from os import listdir
from os.path import isfile, join
from pathlib import Path
from typing import Dict, List, Optional, Set

import requests
from termcolor import colored

VERSION = "version 0.3"
COOKIE = ""  # Static value from file
URL_ORDER = "https://www.humblebundle.com:443/api/v1/order/"
URL_LIBRARY = "https://www.humblebundle.com:443/home/library"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:63.0) Gecko/20100101 Firefox/126.0",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Accept-Encoding": "gzip, deflate",
    "DNT": "1",
    "Connection": "close",
    "Upgrade-Insecure-Requests": "1"
}

header = """
  _    _                 _     _      ____                  _ _      
 | |  | |               | |   | |    |  _ \                | | |     
 | |__| |_   _ _ __ ___ | |__ | | ___| |_) |_   _ _ __   __| | | ___ 
 |  __  | | | | '_ ` _ \| '_ \| |/ _ \  _ <| | | | '_ \ / _` | |/ _ \\
 | |  | | |_| | | | | | | |_) | |  __/ |_) | |_| | | | | (_| | |  __/
 |_|  |_|\__,_|_| |_| |_|_.__/|_|\___|____/ \__,_|_| |_|\__,_|_|___|
"""


class HumbleBundleDownloader:
    """Main downloader class with improved structure and error handling."""

    def __init__(self, args):
        self.args = args
        self.verbose = not args.quiet and (args.verbose or True)  # Default to verbose unless quiet
        self.verify_checksum_on_existing_files = not args.no_checksum_on_local_files
        self.ignore_downloaded_checksum = args.ignore_downloaded_checksum
        self.dry_run = args.dry_run

        # Set allowed file types based on arguments
        self.allowed_filetypes = self._get_allowed_filetypes()

        # Initialize paths
        self._setup_paths()

        # Initialize tracking lists
        self.filename_match_list: Set[str] = set()
        self.filename_no_match_list: Set[str] = set()
        self.md5_match_list: List[str] = []
        self.md5_no_match_list: List[str] = []

        # Raw data storage
        self.raw_platforms: List[str] = []
        self.data: List[Dict] = []

    def _get_allowed_filetypes(self) -> List[str]:
        """Determine allowed file types based on command line arguments."""
        filetypes = []

        if self.args.epub or self.args.books:
            filetypes.append('epub')
        if self.args.pdf or self.args.books:
            filetypes.append('pdf')
        if self.args.mobi or self.args.books:
            filetypes.append('mobi')
        if self.args.other:
            filetypes.extend(['zip', 'rar', '7z'])

        # If no specific types selected, allow all
        if not filetypes:
            filetypes = ["*"]

        return filetypes

    def _setup_paths(self):
        """Setup download and temp paths based on OS."""
        settings = self._get_settings()

        if os.name == 'nt':
            self.download_temp_path = settings['WINDOWS']['DOWNLOAD_TEMP_PATH']
            self.path = settings['WINDOWS']['DOWNLOAD_PATH']
        else:
            self.download_temp_path = settings['LINUX']['DOWNLOAD_TEMP_PATH']
            self.path = settings['LINUX']['DOWNLOAD_PATH']

        # Use current directory if paths are empty
        if not self.download_temp_path:
            self.download_temp_path = str(Path().absolute())
        if not self.path:
            self.path = str(Path().absolute())

        self._assure_path_exists(self.download_temp_path)
        self._assure_path_exists(self.path)

    def colorize(self, text: str, color: str):
        """Print colored text if not in quiet mode."""
        if not self.args.quiet:
            print(colored(text, color))

    def log_error(self, text: str):
        """Log error to file with timestamp."""
        now = datetime.now()
        logline = f"{now} message: {text}"
        with open('errors.log', "a") as errorlog:
            errorlog.write(logline + "\n")

    def _check_cookie(self):
        """Load cookie from file."""
        global COOKIE
        if not isfile('cookie.txt'):
            self.colorize(f"Directory Path: {Path().absolute()}", "red")
            self.colorize("Error: Could not read cookie.txt", "red")
            sys.exit(1)

        with open('cookie.txt', 'r') as cf:
            temp_cookie = cf.readline()
            COOKIE = json.loads(temp_cookie)

    def _get_settings(self) -> Dict:
        """Load settings from JSON file."""
        if not isfile('settings.json'):
            self.colorize(f"Directory Path: {Path().absolute()}", "red")
            self.colorize("Error: Could not read settings.json", "red")
            sys.exit(1)

        with open('settings.json') as json_file:
            return json.load(json_file)

    def _api_call(self, key: str) -> Dict:
        """Make API call to HumbleBundle."""
        url = URL_ORDER + key + "?all_tpkds=true"
        try:
            response = requests.get(url, headers=HEADERS, cookies=COOKIE)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            self.colorize(f"Error fetching order {key}: {e}", 'red')
            sys.exit(1)

    def _get_library(self):
        """Get library page to extract keys."""
        try:
            response = requests.get(URL_LIBRARY, headers=HEADERS, cookies=COOKIE)
            response.raise_for_status()
            return response
        except requests.RequestException as e:
            self.colorize(f"Error fetching library: {e}", 'red')
            sys.exit(1)

    def _extract_keys_from_library(self, library_res) -> List[str]:
        """Extract game keys from library response."""
        content = str(library_res.content)
        start_marker = '<script id="user-home-json-data" type="application/json">'
        end_marker = "</script>"

        pos0 = content.find(start_marker)
        if pos0 == -1:
            self.colorize("Could not find JSON data in library page", "red")
            return []

        pos0 += len(start_marker) + 4  # Account for newline characters
        pos1 = content.find(end_marker, pos0) - 2

        raw_user_json = content[pos0:pos1]
        raw_user_json = raw_user_json.replace('\\"', "").replace("\\", "")

        try:
            json_object = json.loads(raw_user_json)
            return json_object.get('gamekeys', [])
        except json.JSONDecodeError as e:
            self.colorize(f"Error parsing library JSON: {e}", "red")
            return []

    def _parse_json(self, raw_json: List[Dict]) -> List[Dict]:
        """Parse raw JSON data into structured format."""
        data = []
        for res in raw_json:
            bundle_data = {
                'bundle': res['product']['machine_name'],
                'name': res['product']['human_name'],
                'nbr_subproducts_org': len(res['subproducts']),
                'items': []
            }

            counter = 0
            for item in res['subproducts']:
                try:
                    if 'downloads' not in item or not item['downloads']:
                        continue

                    platform = item['downloads'][0]['platform']
                    self.raw_platforms.append(platform)

                    single_item = {
                        'human_name': item['human_name'],
                        'machine_name': item['machine_name'],
                        'platform': platform,
                        'download_struct': []
                    }

                    for dl_str in item['downloads'][0].get('download_struct', []):
                        tmp_dl_info = {
                            'name': dl_str['name'],
                            'web': dl_str['url']['web'],
                            'human_size': dl_str['human_size'],
                            'md5': dl_str['md5']
                        }

                        # SHA1 is optional
                        if 'sha1' in dl_str:
                            tmp_dl_info['sha1'] = dl_str['sha1']

                        single_item['download_struct'].append(tmp_dl_info)

                    bundle_data['items'].append(single_item)
                    counter += 1

                except (IndexError, KeyError):
                    continue  # Skip items with no downloads

            bundle_data['nbr_subproducts'] = counter
            data.append(bundle_data)

        return data

    def _calculate_hash(self, file_path: str, hash_type: str = 'md5') -> str:
        """Calculate MD5 or SHA1 hash of a file."""
        block_size = 256 * 128
        hash_obj = hashlib.md5() if hash_type == 'md5' else hashlib.sha1()

        try:
            with open(file_path, 'rb') as f:
                for chunk in iter(lambda: f.read(block_size), b''):
                    hash_obj.update(chunk)
            return hash_obj.hexdigest()
        except OSError as e:
            self.log_error(f"Hash calculation failed for {file_path}: {e}")
            raise

    def _verify_checksum(self, filepath: str, filename: str, expected_hash: str, hash_type: str = 'md5') -> Dict:
        """Verify file checksum."""
        file_path = join(filepath, filename)

        if self.verbose:
            print(f"{hash_type.upper()} checking: {file_path}")

        if expected_hash == "n/a":
            return {"verdict": True, "checksum_org": expected_hash, "checksum_calc": "skipped"}

        try:
            calculated_hash = self._calculate_hash(file_path, hash_type)

            if expected_hash == calculated_hash:
                if self.verbose:
                    print(f"{hash_type.upper()} verified.")
                return {"verdict": True, "checksum_org": expected_hash, "checksum_calc": calculated_hash}
            else:
                self.colorize(f"{hash_type.upper()} verification failed!", "red")
                return {"verdict": False, "checksum_org": expected_hash, "checksum_calc": calculated_hash}

        except OSError as e:
            raise OSError(f'{hash_type.upper()} check failure: {e}')

    def _get_item_object(self, machine_name: str) -> Optional[Dict]:
        """Find item object by machine name."""
        for bundle in self.data:
            for item in bundle['items']:
                if item.get('machine_name', '').lower() == machine_name.lower():
                    return item
        return None

    def _get_url(self, item: Dict, filetype: str) -> str:
        """Get download URL for specific filetype."""
        # First try exact match
        for dl_str in item['download_struct']:
            if dl_str['name'].lower() == filetype.lower():
                return dl_str['web'] if "FILE_NAME" not in dl_str['web'] else "n/a"

        # Try URL-based matching
        for dl_str in item['download_struct']:
            url = dl_str['web']
            url_filetype = self._get_filetype_from_url(url)
            if url_filetype == filetype.lower():
                return url if "FILE_NAME" not in url else "n/a"

        # Try weird names
        weird_names = {'download', 'supplement', 'mp3', 'companion file', 'installer', '.zip'}
        for dl_str in item['download_struct']:
            if dl_str['name'].lower() in weird_names:
                return dl_str['web'] if "FILE_NAME" not in dl_str['web'] else "n/a"

        self.colorize(f"Could not get URL from {item['human_name']} with {filetype} extension", "red")
        self.log_error(f"Could not get URL from {item['human_name']} with {filetype} extension")
        return "n/a"

    def _get_hash(self, item: Dict, filetype: str, hash_type: str = 'md5') -> str:
        """Get hash for specific filetype."""
        dl_dict = {dl['name'].lower(): dl for dl in item['download_struct']}

        # Check for exact match
        if filetype.lower() in dl_dict:
            return dl_dict[filetype.lower()].get(hash_type, 'n/a')

        # Check weird names
        weird_names = {'download', 'supplement', 'mp3', 'companion file', 'installer', '.zip'}
        for weird_name in weird_names:
            if weird_name in dl_dict:
                return dl_dict[weird_name].get(hash_type, 'n/a')

        # Return first available if any
        if dl_dict:
            first_item = next(iter(dl_dict.values()))
            self.log_error(f"New weird name detected: {first_item['name']}")
            return first_item.get(hash_type, 'n/a')

        return 'n/a'

    def _get_filetype_from_url(self, url: str) -> str:
        """Extract file type from URL."""
        if "FILE_NAME" in url:
            return ""
        split_url = url.split('?')
        return split_url[0][split_url[0].rfind('.') + 1:].lower()

    def _check_file_against_filter(self, filename: str) -> bool:
        """Check if file matches allowed file types."""
        filetype = filename[filename.rfind('.') + 1:].lower()

        if "*" in self.allowed_filetypes:
            return True

        if filetype in [ft.lower() for ft in self.allowed_filetypes]:
            return True

        if self.verbose:
            print(f"Skipping {filename} - not in allowed filetypes")
        return False

    def _progress_download(self, url: str, filename: str):
        """Download file with progress bar."""
        if self.dry_run:
            print(f"[DRY RUN] Would download: {filename}")
            return

        with open(filename, 'wb') as f:
            response = requests.get(url, stream=True)
            total = response.headers.get('content-length')

            if total is None:
                f.write(response.content)
            else:
                downloaded = 0
                total = int(total)
                for data in response.iter_content(chunk_size=max(int(total / 1000), 1024 * 1024)):
                    downloaded += len(data)
                    f.write(data)
                    done = int(50 * downloaded / total)
                    if not self.args.quiet:
                        sys.stdout.write(f'\r[{"█" * done}{"." * (50 - done)}]')
                        sys.stdout.flush()

        if not self.args.quiet:
            sys.stdout.write('\n')

    def _download(self, machine_name: str, filetype: str) -> Optional[Dict]:
        """Download a single file."""
        file_item = self._get_item_object(machine_name)
        if not file_item:
            return None

        url = self._get_url(file_item, filetype)
        if url == "n/a":
            return None

        url_file_type = self._get_filetype_from_url(url)
        temp_filename = os.path.join(self.download_temp_path, machine_name)

        if self.verbose:
            human_size = self._get_human_size(file_item, url_file_type)
            print(f"Starting download for: {file_item['human_name']}.{url_file_type} with size: {human_size}")
            print(f"Downloading file: {machine_name} to path: {self.download_temp_path}")
            print(f"URL for download: {url}")

        try:
            self._progress_download(url, temp_filename)
            return {
                'path': self.download_temp_path,
                'machine_name': machine_name,
                'filetype': url_file_type,
                'platform': file_item['platform']
            }
        except Exception as e:
            error_msg = f"Failure to download file! filetype:{url_file_type} filename: {machine_name} path: {self.download_temp_path} error: {str(e)}"
            self.log_error(error_msg)
            if self.verbose:
                print(f"Download failure: {e}")
            return None

    def _get_human_size(self, item: Dict, filetype: str) -> str:
        """Get human readable file size."""
        for dl_str in item['download_struct']:
            if dl_str['name'].lower() == filetype.lower():
                return dl_str['human_size']
        return '0'

    def _checksum_file(self, file_info: Dict) -> bool:
        """Verify checksums for downloaded file."""
        if self.ignore_downloaded_checksum:
            return True

        machine_name = file_info['machine_name']
        filetype = file_info['filetype'].lower()
        file_item = self._get_item_object(machine_name)

        if not file_item:
            return False

        md5_hash = self._get_hash(file_item, filetype, 'md5')
        md5_result = self._verify_checksum(file_info['path'], machine_name, md5_hash, 'md5')

        sha1_hash = self._get_hash(file_item, filetype, 'sha1')
        sha1_result = self._verify_checksum(file_info['path'], machine_name, sha1_hash, 'sha1')

        # If both pass, return True
        if md5_result['verdict'] and sha1_result['verdict']:
            return True

        # If at least one passes, log the failure but continue
        if md5_result['verdict'] or sha1_result['verdict']:
            if not md5_result['verdict']:
                error_text = f"MD5 verification failed! filetype:{filetype} filename:{machine_name} org_checksum:{md5_result['checksum_org']} calculated_checksum:{md5_result['checksum_calc']}"
                self.log_error(error_text)
            if not sha1_result['verdict']:
                error_text = f"SHA1 verification failed! filetype:{filetype} filename:{machine_name} org_checksum:{sha1_result['checksum_org']} calculated_checksum:{sha1_result['checksum_calc']}"
                self.log_error(error_text)
            return True

        # Both failed
        error_text = f"Both MD5 and SHA1 verification failed! filetype:{filetype} filename:{machine_name}"
        self.log_error(error_text)
        return False

    def _move_file(self, file_info: Dict):
        """Move file from temp to final location."""
        if self.dry_run:
            print(f"[DRY RUN] Would move file to final location")
            return

        platform = file_info['platform'].lower()
        filetype = file_info['filetype'].lower()
        filename = f"{file_info['machine_name']}.{filetype}"

        tempfile = join(self.download_temp_path, file_info['machine_name'])

        if platform == "ebook":
            path = join(self.path, f"ebook/{filetype}")
        else:
            path = join(self.path, platform)

        finalpath = join(path, filename)
        self._assure_path_exists(path)

        if self.verbose:
            self.colorize(f"Moving {tempfile} to {finalpath}", "blue")

        shutil.move(tempfile, finalpath)

    def _assure_path_exists(self, path: str):
        """Ensure directory exists."""
        if not path.endswith("/"):
            path += "/"
        directory = os.path.dirname(path)
        if not os.path.exists(directory):
            os.makedirs(directory)

    def _get_existing_files_in_folder(self, platform: str) -> List[str]:
        """Get list of existing files in platform folder."""
        head = join(self.path, f"{platform}/")

        if not os.path.exists(head):
            return []

        if platform != "ebook":
            return [f for f in listdir(head) if isfile(join(head, f))]
        else:
            # For ebooks, search recursively
            filelist = []
            for root, dirs, files in os.walk(head):
                filelist.extend(files)
            return filelist

    def _get_sorted_uniques(self, list_items: List[str]) -> List[str]:
        """Get sorted unique items from list."""
        if not list_items:
            return []
        return sorted(list(set(list_items)))

    def _loop_through_missing_files(self, missing_files: List[str], max_retries: int = 3):
        """Download missing files with retries."""
        for i in range(max_retries):
            if not missing_files:
                break

            files_to_remove = []
            for filename in missing_files:
                if not self._check_file_against_filter(filename):
                    files_to_remove.append(filename)
                    continue

                machine_name = filename[:filename.rfind('.')]
                filetype = filename[filename.rfind('.') + 1:]

                if self.verbose:
                    print(f"Trying to download file: {filename}")

                file_info = self._download(machine_name, filetype)
                if file_info:
                    if self._checksum_file(file_info):
                        self._move_file(file_info)
                        files_to_remove.append(filename)
                    else:
                        self.colorize(f"FAILED on checksums: {filename}", "red")
                else:
                    self.colorize(f"FAILED to download: {filename}", "red")

                if self.verbose:
                    print(f"There are {len(missing_files)} files left to download")

            # Remove successfully processed files
            for filename in files_to_remove:
                if filename in missing_files:
                    missing_files.remove(filename)

    def _handle_platform(self, platform: str):
        """Handle downloads for a specific platform."""
        if self.verbose:
            print(f"\nProcessing platform: {platform}")

        local_files = self._get_existing_files_in_folder(platform)
        filename_matches = set()
        filename_no_matches = set()

        head = join(self.path, f"{platform}/")

        for bundle in self.data:
            for item in bundle['items']:
                if item.get('platform') != platform:
                    continue

                for dl_str in item['download_struct']:
                    url_file_type = self._get_filetype_from_url(dl_str['web'])
                    machine_name = item['machine_name']
                    filename = f"{machine_name}.{url_file_type}"

                    if not url_file_type:  # Skip files with no extension
                        continue

                    if filename in local_files:
                        filename_matches.add(machine_name)

                        # Verify existing files if requested
                        if self.verify_checksum_on_existing_files:
                            md5_hash = dl_str['md5']
                            if platform == "ebook":
                                file_path = join(head, url_file_type)
                                full_filename = f"{machine_name}.{url_file_type.lower()}"
                            else:
                                file_path = head
                                full_filename = f"{machine_name}.{url_file_type.lower()}"

                            try:
                                result = self._verify_checksum(file_path, full_filename, md5_hash)
                                if result['verdict']:
                                    self.md5_match_list.append(machine_name)
                                else:
                                    self.md5_no_match_list.append(machine_name)
                            except OSError:
                                self.md5_no_match_list.append(machine_name)
                    else:
                        filename_no_matches.add(filename)

        # Print statistics
        print(f"Currently have {len(local_files)} local files in folder {platform}")
        print(f"Found {len(filename_matches)} matches on filename")
        print(f"Found {len(filename_no_matches)} unique missing files")
        print(f"Found {len(self.md5_match_list)} verified hashes")
        print(f"Found {len(self.md5_no_match_list)} failed hashes")

        # Download missing files
        if filename_no_matches:
            missing_list = self._get_sorted_uniques(list(filename_no_matches))
            self._loop_through_missing_files(missing_list)

        if self.md5_no_match_list:
            failed_list = self._get_sorted_uniques(self.md5_no_match_list)
            # Convert machine names back to filenames for redownload
            failed_filenames = []
            for machine_name in failed_list:
                item = self._get_item_object(machine_name)
                if item and item['download_struct']:
                    url_type = self._get_filetype_from_url(item['download_struct'][0]['web'])
                    failed_filenames.append(f"{machine_name}.{url_type}")

            self._loop_through_missing_files(failed_filenames)

        print(f"Completed processing platform: {platform}")

    def run(self):
        """Main execution method."""
        # Clear screen and show header
        clear_command = 'cls' if os.name == 'nt' else 'clear'
        if not self.args.quiet:
            os.system(clear_command)
            self.colorize(header, 'magenta')
            self.colorize(VERSION, 'green')

        # Check cookie
        self._check_cookie()

        # Load data
        offline = False
        raw_json = []

        if isfile('data.json'):
            self.colorize("data.json file found, using offline data.", "yellow")
            with open('data.json') as file:
                raw_json = json.load(file)
                offline = True

        if not offline:
            if self.verbose:
                print("Fetching your keys...")

            library_res = self._get_library()

            if "Humble Bundle - Log In" in library_res.text:
                self.colorize("Not logged in, check your cookie!", 'red')
                sys.exit(1)

            keys = self._extract_keys_from_library(library_res)

            if not keys:
                self.colorize("No keys found, check your cookie!", 'red')
                sys.exit(1)

            if self.verbose:
                self.colorize(f"Got {len(keys)} keys, fetching data for each", 'green')

            for i, key in enumerate(keys):
                raw_json.append(self._api_call(key))
                if self.verbose:
                    print(f"{key}: {i + 1}/{len(keys)}")

        # Parse data
        self.data = self._parse_json(raw_json)

        # Show detected platforms
        unique_platforms = sorted(list(set(self.raw_platforms)))
        if self.verbose:
            self.colorize("Platforms detected:", "yellow")
            for platform in unique_platforms:
                self.colorize(f"  {platform}", "yellow")

        # Save data for offline use
        if self.verbose and not offline:
            with open('data.json', 'w') as f:
                json.dump(raw_json, f)

        # Process each platform
        for platform in unique_platforms:
            self._handle_platform(platform)

        print("\nAll done!")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description='HumbleBundle Downloader')
    group = parser.add_mutually_exclusive_group()
    group.add_argument('-q', '--quiet', help='Runs quietly and only reports when done',
                       action="store_true", required=False)
    group.add_argument('-v', '--verbose', help='Verbose output',
                       action="store_true", required=False)

    parser.add_argument('-n', '--no-checksum-on-local-files',
                        help='Skips checksum checks for local files',
                        action="store_true", required=False)
    parser.add_argument('-i', '--ignore-downloaded-checksum',
                        help='Skips checksum checks for downloaded files',
                        action="store_true", required=False)
    parser.add_argument('-d', '--dry-run',
                        help='Does a dry run that skips actual download',
                        action="store_true", required=False)
    parser.add_argument('-b', '--books',
                        help='Download only books (epub, pdf, mobi)',
                        action="store_true", required=False)
    parser.add_argument('-e', '--epub',
                        help='Download only epub books',
                        action="store_true", required=False)
    parser.add_argument('-p', '--pdf',
                        help='Download only pdf books',
                        action="store_true", required=False)
    parser.add_argument('-m', '--mobi',
                        help='Download only mobi books',
                        action="store_true", required=False)
    parser.add_argument('-o', '--other',
                        help='Download only zip files for video/other content',
                        action="store_true", required=False)

    args = parser.parse_args()

    # Create and run the downloader
    downloader = HumbleBundleDownloader(args)
    downloader.run()


if __name__ == "__main__":
    main()