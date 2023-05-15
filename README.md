# ytd
A CLI-based YouTube Video Downloader with a focus on simplicity and elegance

You can find a couple of config options at the top of ytd.py

## Example usage
`ytd -c` - Gets the URL from your clipboard

`ytd 'https://www.youtube.com/watch?v=thOifuHs6eY'` - Doesn't get the URL from your clipboard

`ytd -c -q 1080` - Download at 1080p (or lower if the video has a lower resolution)<br>
`ytd -c -q FullHD` - this also works
<br>
`ytd -c -q f_U-lL__hDeFiNiTiOn` - this... also works

`ytd -c -o ~/Downloads` - Outputs the video to your downloads folder

`ytd -c -f cgpgrey_vid` - Sets the filename stem to "cgpgrey_vid"

## Installation instructions
#### Create a Python Virtual Environment
`python3 -m venv [your preferred venv path]` (you can read more about venvs [here](https://docs.python.org/3/library/venv.html))

#### Activate the Virtual Environment
`source [path to activate file in the venv folder]`

#### Install Dependencies
`pip install -r requirements.txt` (you can read more about requirements files [here](https://pip.pypa.io/en/stable/reference/requirements-file-format/))

You can now run the script with `python [path to ytd.py]`, make sure it works before continuing to the last step

#### Compile it
Running a binary from anywhere is a lot easier than keeping track of virtual environments, you can use [Nuitka](https://github.com/Nuitka/Nuitka) to compile this script into a single-file executable

Once you have it installed (it's included in the requirements.txt, but you might have to do some more setup, especially on Windows), simply run `nuitka3 --follow-imports ytd.py` (make sure your venv is active), and you're good to go

Happy downloading!
