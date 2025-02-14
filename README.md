# Humble Bundle Downloader

This is yet another humble bundle downloader that focus mainly on the books and media files.
It's something that has evolved over time and is far from something called finished or polished.
But it works. And that why it's still around and any issues you may have is to be solved by yourself.
I have no time to act as a support channel more than friends and family already throw at me.
But any contribution are welcome :-)

## Dependencies

- requests
- termcolor

## Installation

1. Optional step: create virtual environment:
`python3 -m venv myenv`
and activate it `source ./myenv/bin/activate` (for linux)

2. Install dependencies from requirements file:
`pip install -r requirements.txt`

3. Copy and paste a valid cookie from humble bundle into cookie.txt
4. Run the script:
`python3 ./humble_download.py`

## Settings

Currently, to change what files to download and what file integrity checks that should be done is handled manually.
To choose what files to download (default is mobi,pdf,epub and zip), comment out respectively "master handler" in humble_download.py

## TODO

In no particular order there are lots of room for improvements and here are some of the ideas that possible will be implemented sometime

- Print verbose mode output
- print errors to logfile
- add always print checksum errors to verbose and print error file
- Print out menu
- menu system ->
  - --verify filename only,
  - hash check only,
  - paths for different types (epub, zip, mobi) or types/platform (Books, Video),
  - debug mode that prints all printouts,
  - download all missing/corrupted files,
  - dryrun
- sha1 hash module
- mail module
- Use reversed api from apk? -> https://www.schiff.io/projects/humble-bundle-api
- read cookie from env?
- More settings in external file?
- threads/multicore/concurrent support for both hash and download parts, and lastly the entire code should support multicore
- preliminary sum of all data to download in file size/human file size
- Add optional removal of temp download folders

## Licence

Do not have one, so do whatever you like with it
