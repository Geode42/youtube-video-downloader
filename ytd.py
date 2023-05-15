try:
	import sys
	
	import pytube
	from pytube import YouTube
	import rich.progress
	from rich.console import Console
	import pyperclip

	import re
	from typing import BinaryIO
	import argparse
	import tempfile
	from os import system
	from os.path import isfile, isdir, expanduser, abspath, dirname, basename
	import platform
	import shutil
	import logging
	import urllib.error
except ModuleNotFoundError as e:
	print(f'\x1b[91;1mThis program depends on {e.name} to function\nYou can find the full list of dependencies in the requirements.txt\x1b[0m')
	sys.exit(1)

DEFAULT_QUALITY = '8K'
# The max video resolution when not explicitly given through "-q" or "--quality"
# It's 8K by default, because 144p feels too low and anything in between feels subjective
# You probably want to lower this to 4K or 1080p or something
# Speaking of, any way you can think of to specify the quality *probably* will work.
# As an example, 2160, 2160p, 4k, uhd, "ultra hd", "ultra high definition", and "UlTrA-h   DEfiNItiON" are all valid formats for "2160p"

OUTPUT_LOCATION = './'
# This is the directory where output files will be saved
# Since this is a terminal program, the CWD felt most appropriate
# You could change this to whatever you want though;
# You might want to set this to "~/Downloads", for example

FFMPEG_PATH = 'ffmpeg'
# This script uses FFmpeg to combine the downloaded video and audio files (YT likes keeping them as two separate files)
# I'd recommend installing FFmpeg if you don't have it already, it's pretty useful for things like compressing or re-encoding
# Alternatively, you could place the ffmpeg executable ("ffmpeg" or "ffmpeg.exe") next to this script, then change this to "./ffmpeg"

# Init console object
console = Console(highlight=False)

# Get the args
parser = argparse.ArgumentParser()
parser.add_argument('url', nargs='?', help='The URL of the video; this can as short as it\'s 11-character long ID, or as long as the full URL displayed in your browser')
parser.add_argument('-q', '--quality', help="Overrides the max resolution defined at the top of this python script (this is kinda awkward if you compiled this...)")
parser.add_argument('-f', '--filename', help='The filename of the downloaded video (just the stem, the extension is added automatically)')
parser.add_argument('-c', '--clipboard', help='Gets the url from your clipboard', action='store_true')
parser.add_argument('-o', '--output_directory', help='Overrides the output directory defined at the top of this python script (again, kinda awkward if you compiled this...)')
parser.add_argument('-v', '--verbose', action='store_true')

args = parser.parse_args()

def main():
	def printerr(message: str):
		console.print(message, style='bold red')

	# Check if the if the FFmpeg path will work
	if shutil.which(FFMPEG_PATH) is None and not isfile(FFMPEG_PATH):
		printerr('FFmpeg executable not found')
		sys.exit(1)

	# Get output directory
	output_location = OUTPUT_LOCATION
	if args.output_directory:
		output_location = args.output_directory

	output_location = expanduser(output_location)  # Make things like "~/Downloads" work
	if not isdir(output_location):
		printerr("The output location doesn't exist")
		sys.exit(1)

	# Make sure URL is given correctly
	if args.clipboard and args.url:
		printerr("url and -c | --clipboard can't be used together")
		sys.exit(1)
	if not args.clipboard and not args.url:
		printerr('One of the following arguments must be used: url, -c | --clipboard')
		sys.exit(1)

	# Get URL
	if args.clipboard: url = pyperclip.paste()
	if args.url: url = args.url
	# pytube requires the url to be at least v=vid_id, I think the vid_id should be enough though
	if len(url) == 11: url = 'v=' + url

	# This function converts user-friendly resolutions into the boring resolutions that pytube understands
	def convert_res(res):
		res = re.sub(r'[^A-Za-z0-9]', '', res) \
				.lower() \
				.rstrip('p') \
				.replace('full', 'f') \
				.replace('high', 'h') \
				.replace('ultra', 'u') \
				.replace('definition', 'd')

		if res in ('a', 'audio'):
			return 'audio'
		
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
		printerr("The quality isn't valid")
		sys.exit(1)



	# Init yt object
	with console.status('Getting video info...'):
		try:
			yt = YouTube(url)
		except pytube.exceptions.RegexMatchError:
			printerr("The URL isn't valid")
			sys.exit(1)

		# Return friendlier error messages
		try:
			yt.check_availability()
			yt.streams  # Some videos can't be downloaded, but aren't caught by the above line; this seems to fix the issue
		except urllib.error.URLError:
			printerr('URLError encountered, do you have an internet connection?')
			sys.exit(1)
		except pytube.exceptions.MembersOnly:
			printerr("This utility can't download member-only videos")
			sys.exit(1)
		except pytube.exceptions.RecordingUnavailable:
			printerr('This live stream recording is unavailable')
			sys.exit(1)
		except pytube.exceptions.AgeRestrictedError:
			printerr('This video is age restricted')
			sys.exit(1)
		except pytube.exceptions.VideoUnavailable:
			printerr('This video is unavailable')
			sys.exit(1)
		except pytube.exceptions.VideoPrivate:
			printerr('This video has been made private')
			sys.exit(1)
		except pytube.exceptions.LiveStreamError:
			printerr("This stream can't be downloaded")
			sys.exit(1)

	with console.status('Getting filename...'):
		# Get final filename
		if args.filename is None: args.filename = yt.title
		if platform.system() == 'Windows':
			invalid_characters = '<', '>', ':', '"', '/', '\\', '|', '?', '*'
			for c in invalid_characters: args.filename = args.filename.replace(c, '')
			if len(output_location) and not (output_location.endswith('/') or output_location.endswith('\\')):
				output_location += '\\'
		else:
			args.filename = args.filename.replace('/', '')
			if len(output_location) and not output_location.endswith('/'):
				output_location += '/'
		args.filename = output_location + args.filename
		# If the file already exists, add a number in parentheses at the end, keep incrementing it until a valid output path is found
		if isfile(args.filename + '.mkv'):
			num = 1
			while isfile(f'{args.filename} ({num}).mkv'):
				num += 1
			args.filename = f'{args.filename} ({num})'


	# Audio only
	if args.quality == 'audio':
		with console.status('Getting stream...'):
			audiostream: pytube.Stream = yt.streams.filter(only_audio=True, is_dash=True).order_by('bitrate').last()

		stream_progress_object = rich.progress.Progress(
			rich.progress.TextColumn('[progress.description]{task.description}'),
			rich.progress.BarColumn(),
			rich.progress.TaskProgressColumn(),
			rich.progress.TimeRemainingColumn(),
			rich.progress.TransferSpeedColumn(),

			auto_refresh=False
		)

		file_extension = '.' + audiostream.mime_type.split('/')[1]

		with stream_progress_object as progress:
			download_audio_task = progress.add_task(description='Downloading audio...', total=audiostream.filesize)
			def on_progress_audio(chunk: bytes, file_handler: BinaryIO, bytes_remaining: int):
				progress.update(download_audio_task, advance=len(chunk), refresh=True)
				file_handler.write(chunk)
			audiostream.on_progress = on_progress_audio

			progress.start_task(download_audio_task)
			audiostream.download(dirname(args.filename), basename(args.filename) + file_extension)


		if isfile(abspath(args.filename + file_extension)):
			console.print(f'Video downloaded at [bright_magenta]{abspath(args.filename + file_extension)}[/bright_magenta]')
		else:
			printerr(f"Video not downloaded, I'm not sure why")

	# Video and Audio
	else:
		with console.status('Getting quality...'):
			# Get max video res
			max_res = yt.streams.filter(only_video=True).order_by('resolution').last().resolution
			if int(args.quality[:-1]) > int(max_res[:-1]):
				args.quality = max_res

		with console.status('Getting streams...'):
			videostream = yt.streams.filter(only_video=True, is_dash=True, res=args.quality).order_by('bitrate').last()
			audiostream = yt.streams.filter(only_audio=True, is_dash=True).order_by('bitrate').last()

		with console.status('Getting temp dir...'):
			tmpdir = tempfile.TemporaryDirectory()

		stream_progress_object = rich.progress.Progress(
			rich.progress.TextColumn('[progress.description]{task.description}'),
			rich.progress.BarColumn(),
			rich.progress.TaskProgressColumn(),
			rich.progress.TimeRemainingColumn(),
			rich.progress.TransferSpeedColumn(),

			auto_refresh=False
		)

		with stream_progress_object as progress:
			download_video_task = progress.add_task(description='Downloading video...', total=videostream.filesize)
			def on_progress_video(chunk: bytes, file_handler: BinaryIO, bytes_remaining: int):
				progress.update(download_video_task, advance=len(chunk), refresh=True)
				file_handler.write(chunk)
				
			videostream.on_progress = on_progress_video

			progress.start_task(download_video_task)
			videostream.download(tmpdir.name, 'video')

			download_audio_task = progress.add_task(description='Downloading audio...', total=audiostream.filesize)
			def on_progress_audio(chunk: bytes, file_handler: BinaryIO, bytes_remaining: int):
				progress.update(download_audio_task, advance=len(chunk), refresh=True)
				file_handler.write(chunk)
			audiostream.on_progress = on_progress_audio

			progress.start_task(download_audio_task)
			audiostream.download(tmpdir.name, 'audio')

		with console.status('Joining files with FFmpeg...'):
			command = (
					FFMPEG_PATH,
					'-loglevel', 'warning',
					'-i', tmpdir.name + '/' + 'video',
					'-i', tmpdir.name + '/' + 'audio',
					'-c', 'copy', '"' + args.filename.replace('"', '\\"') + '.mkv' + '"'
			)
			command = ' '.join(command)
			system(command)


		if isfile(abspath(args.filename + ".mkv")):
			console.print(f'Video downloaded at [bright_magenta]{abspath(args.filename + ".mkv")}[/bright_magenta]')
		else:
			printerr(f'Video not downloaded, perhaps due to the FFmpeg command not succeeding')

try:
	main()
except KeyboardInterrupt:
	if args.verbose:
		print('KeyboardInterrupt encountered')
	sys.exit(130)
except Exception as e:
	if args.verbose:
		logging.exception(e)
	else:
		console.print(f'[bold red]Fatal error[/]: {e}\nRun this script with --verbose to see debug info')
	sys.exit(1)