from typing import BinaryIO
from pytube import YouTube
import pytube
import argparse
import tempfile
from os import system
from os.path import isfile, isdir, expanduser, abspath
from time import time
import platform
import sys
import yaml

using_pyperclip = False
try:
	import pyperclip
	using_pyperclip = True
except ModuleNotFoundError: pass

CONFIG_FILE = './ytd_config.yaml'

try:
	with open(CONFIG_FILE) as f:
		config = yaml.safe_load(f.read())
		DEFAULT_QUALITY = config['default_quality']
		OUTPUT_LOCATION = config['output_location']
		FFMPEG_PATH = config['ffmpeg_path']
		progressbar_config = config['progress_bar']
		PROGRESS_BAR_LENGTH = progressbar_config['length']
		PROGRESS_BAR_UNIT_COLOR = progressbar_config['unit_color']
		PROGRESS_BAR_COMPLETED_COLOR = progressbar_config['completed_color']
		PROGRESS_BAR_NOT_COMPLETED_COLOR = progressbar_config['not_completed_color']
except FileNotFoundError:
	print('Config file not found')
	sys.exit(1)

command_start = 'ffmpeg' if FFMPEG_PATH is None else FFMPEG_PATH
if FFMPEG_PATH:
	if not isfile(FFMPEG_PATH):
		print('FFmpeg executable defined in config not found')
		sys.exit(1)

if len(OUTPUT_LOCATION) > 0:
	OUTPUT_LOCATION = expanduser(OUTPUT_LOCATION)  # Allow using ~
	if not isdir(OUTPUT_LOCATION):
		print("The output location doesn't exist")
		sys.exit(1)

CLEARLINESTRING = '\033[2K\r' # "\033[2K" clears the entire line ("\r" only clears the line up to the cursor's current position), "\r" moves the cursor back to the start of the line

parser = argparse.ArgumentParser()
parser.add_argument('url', nargs='?', help='The URL of the video; this can as short as it\'s 11-character long ID, or as long as the full URL displayed in your browser')
parser.add_argument('-q', '--quality', help="Used to explicitly define the max resolution you'd like to download")
parser.add_argument('-f', '--filename', help='The filename of the downloaded video')
parser.add_argument('-cb', '--clipboard', help='Grabs the url from your clipboard, only works if pyperclip is installed', action='store_true')

args = parser.parse_args()

if args.clipboard:
	if not using_pyperclip:
		print('Your Python Interpreter needs to have the pyperclip installed in order to use the -cb | --clipboard flag')
		sys.exit(1)

	if args.url:
		print("url and -cb | --clipboard can't be used together")
		sys.exit(1)
	url = pyperclip.paste()
else:
	if not args.url:
		print('One of the following arguments must be used: url, -cb | --clipboard')
		sys.exit(1)
	url = args.url

def convert_res(res):
	res = res.lower() \
			 .rstrip('p') \
			 .replace(' ', '') \
			 .replace('\t', '') \
			 .replace('-', '') \
			 .replace('full', 'f') \
			 .replace('high', 'h') \
			 .replace('ultra', 'u') \
			 .replace('definition', 'd')
	
	resolutions = '144', '240', '360', '480', '720', '1080', '1440', '2160', '2880', '4320'

	aliases = {
		'hd': '720',
		'fhd': '1080', '2k': '1080',
		'qhd': '1440',
		'4k': '2160', 'uhd': '2160',
		'5k': '2880',
		'8k': '4320',
		'uhd2': '4320'
	}

	if res in resolutions: return res + 'p'
	if res in aliases: return aliases[res] + 'p'
	return False

# Get final quality
if args.quality is None: args.quality = DEFAULT_QUALITY
args.quality = convert_res(args.quality)
if args.quality is False:
	print("The quality isn't valid")
	sys.exit(1)



def on_progress(chunk: bytes, file_handler: BinaryIO, bytes_remaining: int):
	if current_downloading == 'video': bytes_downloaded = videototalbytes - bytes_remaining
	else: bytes_downloaded = totalbytes - bytes_remaining

	bar = ''
	bar += '\033[2K\r'

	progress_bar_completed_color = f'\033[38;2;{PROGRESS_BAR_COMPLETED_COLOR[0]};{PROGRESS_BAR_COMPLETED_COLOR[1]};{PROGRESS_BAR_COMPLETED_COLOR[2]}m'
	progress_bar_not_completed_color = f'\033[38;2;{PROGRESS_BAR_NOT_COMPLETED_COLOR[0]};{PROGRESS_BAR_NOT_COMPLETED_COLOR[1]};{PROGRESS_BAR_NOT_COMPLETED_COLOR[2]}m'
	unit_color = f'\033[38;2;{PROGRESS_BAR_UNIT_COLOR[0]};{PROGRESS_BAR_UNIT_COLOR[1]};{PROGRESS_BAR_UNIT_COLOR[2]}m'
	
	characters_completed = int(bytes_downloaded / totalbytes * PROGRESS_BAR_LENGTH)
	percent_completed = int(bytes_downloaded / totalbytes * 100)
	
	time_left = round((time() - start_time) / bytes_downloaded * (totalbytes - bytes_downloaded))


	bar += f'{percent_completed}{unit_color}%'.rjust(4 + len(unit_color)) + '  '

	bar += '\033[1m'
	if characters_completed == 0:
		bar += progress_bar_not_completed_color + '―' * PROGRESS_BAR_LENGTH
	elif characters_completed >= PROGRESS_BAR_LENGTH - 1:
		bar += progress_bar_completed_color + '―' * characters_completed + ' ' * (PROGRESS_BAR_LENGTH - characters_completed)
	else:  # Normal
		bar += progress_bar_completed_color + '―' * characters_completed + ' ' + progress_bar_not_completed_color + '―' * (PROGRESS_BAR_LENGTH - characters_completed - 1)
	
	bar += f'  \033[0m{time_left} {unit_color}seconds'

	print(bar + '\033[0m', end='')

# pytube requires the url to be at least v=vid_id, I think the vid_id should be enough though
if len(url) == 11: url = 'v=' + url

# Init yt object
print(CLEARLINESTRING + 'Getting video info...', end='')
try:
	yt = YouTube(url, on_progress_callback=on_progress)
except pytube.exceptions.RegexMatchError:
	print(CLEARLINESTRING + "The URL isn't valid")
	sys.exit(1)

# Return friendlier error messages
try:
	yt.check_availability()
except pytube.exceptions.MembersOnly:
	print(CLEARLINESTRING + "This utility can't download member-only videos")
	sys.exit(1)
except pytube.exceptions.RecordingUnavailable:
	print(CLEARLINESTRING + 'This live stream recording is unavailable')
	sys.exit(1)
except pytube.exceptions.VideoUnavailable:
	print(CLEARLINESTRING + 'This video is unavailable')
	sys.exit(1)
except pytube.exceptions.VideoPrivate:
	print(CLEARLINESTRING + 'This video has been made private')
	sys.exit(1)
except pytube.exceptions.LiveStreamError:
	print(CLEARLINESTRING + "This stream can't be downloaded")
	sys.exit(1)

# Get final filename
if args.filename is None: args.filename = yt.title
if platform.system() == 'Windows':
	invalid_characters = '<', '>', ':', '"', '/', '\\', '|', '?', '*'
	for c in invalid_characters: args.filename = args.filename.replace(c, '')
	if len(OUTPUT_LOCATION) > 0 and not (OUTPUT_LOCATION.endswith('/') or OUTPUT_LOCATION.endswith('\\')):
		OUTPUT_LOCATION += '\\'
else:
	args.filename = args.filename.replace('/', '')
	if len(OUTPUT_LOCATION) > 0 and not OUTPUT_LOCATION.endswith('/'):
		OUTPUT_LOCATION += '/'
args.filename = OUTPUT_LOCATION + args.filename
# If the file already exists, add a number in parentheses at the end, keep incrementing it until a valid output path is found
if isfile(args.filename + '.mkv'):
	num = 1
	while isfile(f'{args.filename} ({num}).mkv'):
		num += 1
	args.filename = f'{args.filename} ({num})'


# Get max video res
max_res = yt.streams.filter(only_video=True).order_by('resolution').last().resolution
if int(args.quality[:-1]) > int(max_res[:-1]):
	args.quality = max_res

# Get final streams
videostream = yt.streams.filter(only_video=True, is_dash=True, res=args.quality).order_by('bitrate').last()
audiostream = yt.streams.filter(only_audio=True, is_dash=True).order_by('bitrate').last()
# Get filesizes (for progress bar)
videototalbytes = videostream.filesize
audiototalbytes = audiostream.filesize
totalbytes = videototalbytes + audiototalbytes

# Create temporary directory for storing video and audio files before they're combined into the final destination
tmpdir = tempfile.TemporaryDirectory()


current_downloading = 'video'
try:
	start_time = time()
	videostream.download(tmpdir.name, 'video')
	current_downloading = 'audio'
	audiostream.download(tmpdir.name, 'audio')
	print('\033[0m\033[2K\rCombining files with FFmpeg...', end='')
	command = (
		command_start,
		'-loglevel', 'warning',
		'-i', tmpdir.name + '/' + 'video',
		'-i', tmpdir.name + '/' + 'audio',
		'-c', 'copy', '"' + args.filename.replace('"', '\\"') + '.mkv' + '"'
	)
	command = ' '.join(command)
	system(command)
	if isfile(abspath(args.filename + ".mkv")):
		print(f'\033[2K\rVideo downloaded at {abspath(args.filename + ".mkv")}')
	else:
		print(f'Video not downloaded, perhaps due to the FFmpeg command not succeeding')
		sys.exit(1)
except KeyboardInterrupt:
	print('\033[2K\rKeyboard Interrupt, canceling download...')
