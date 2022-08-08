from typing import BinaryIO
from pytube import YouTube
import argparse
import tempfile
from os import system
from os.path import isfile, isdir, expanduser, abspath
from time import time
import platform
import sys

DEFAULT_QUALITY = '4K' # The quality used when no quality is provided, you can see some of the aliases below, in the convert_res function
OUTPUT_LOCATION = ''  # Where the output video will be saved; current working directory by default; supports ~

# Progress bar
PROGRESS_BAR_LENGTH = 40
PROGRESS_BAR_UNIT_COLOR = 140, 140, 140
PROGRESS_BAR_COMPLETED_COLOR = 255, 20, 20
PROGRESS_BAR_NOT_COMPLETED_COLOR = PROGRESS_BAR_UNIT_COLOR

if len(OUTPUT_LOCATION) > 0:
	OUTPUT_LOCATION = expanduser(OUTPUT_LOCATION)  # Allow using ~
	if not isdir(OUTPUT_LOCATION):
		print("The output location doesn't exist, exiting")
		sys.exit()

parser = argparse.ArgumentParser()
parser.add_argument('url', help='The URL of the video; this can as short as it\'s 11-character long ID, or as long as the full URL displayed in your browser')
parser.add_argument('-q', '--quality', help="Used to explicitly define the max resolution you'd like to download")
parser.add_argument('-f', '--filename', help='The filename of the downloaded video')

args = parser.parse_args()

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
	print("The quality isn't valid, exiting")
	sys.exit()

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

# Init yt object
yt = YouTube(args.url, on_progress_callback=on_progress)

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
# If the file already exists, add a number in perenthesis at the end, keep incrementing it until a valid output path is found
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
# Get file extensions (for FFmpeg)
videoextension = videostream.mime_type.split('/')[1]
audioextension = audiostream.mime_type.split('/')[1]

tmp_video_file = tempfile.NamedTemporaryFile(suffix=f'.{videoextension}')
tmp_audio_file = tempfile.NamedTemporaryFile(suffix=f'.{audioextension}')


current_downloading = 'video'
try:
	start_time = time()
	videostream.stream_to_buffer(tmp_video_file)
	current_downloading = 'audio'
	audiostream.stream_to_buffer(tmp_audio_file)
	print('\033[0m\033[2K\rConverting files with FFmpeg...', end='')
	system(f"ffmpeg -loglevel warning -i {tmp_video_file.name} -i {tmp_audio_file.name} -c copy '{args.filename}.mkv'")
	print(f'\033[2K\rVideo downloaded at {abspath(args.filename + ".mkv")}')
except KeyboardInterrupt:
	print('\033[2K\rKeyboard Interrupt — closing and exiting...')
tmp_video_file.close()
tmp_audio_file.close()