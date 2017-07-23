# Memes 0.1

> *Find your memes when you want them.*

*Memes* is a tiny utility for finding that meme you want, or to put it in Chinese, 表情包管理器. Ever had a group chat when you just can't find that picture in your photo album or sticker panel? Now you have *Memes* for the job.

Using *Memes* is simple. *Memes* provides a command line interface and a macOS service. Users may use the command line tool to add memes to the *Memes* library, *Memes* utilizes Tesseract OCR to scan for words and phrases on the images. With the macOS Service, users may search for memes with phrases anywhere.

## Installation

*Memes* is written in Python 2, and currently supports macOS only, although porting to Linux should not be a problem.

To use *Memes*, you need to have Tesseract installed, and download Chinese language data. You also need Python packages `pytesseract` and `PIL`.

```bash
brew install tesseract
wget -O $(brew --prefix tesseract)/share/tessdata/chi_sim.traineddata https://github.com/tesseract-ocr/tessdata/raw/master/chi_sim.traineddata
pip install pytesseract PIL
```

Clone the repository, and you'll have *Memes* ready. The `meme.py` file is the command line tool, while `Get Memes.workflow` is the macOS Service. `Get Memes.scpt` contains the AppleScript used in the workflow. Although the *Memes* command line tool could be run anywhere, but to use the macOS Service, you need to link it into your PATH.

```bash
git clone https://github.com/huzecong/memes.git
python meme.py --help         # use the command line tool

ln -s $(pwd)/meme.py $(brew --prefix)/bin/meme  # make a soft link in your executables directory
open "Get Memes.workflow"     # install the macOS Service, or just simply double-click the file
```

## Usage

Before using *Memes*, you should add your memes to the *Memes* library. To do this, use the *Memes* command line tool:

```bash
meme add /path/to/your/memes
```

This step could take quite a long time. After that, you can search your memes using phrases:

```bash
meme search "意不意外 惊不惊喜"
```

Currently *Memes* could either list paths or display memes using Quick Look. The "copy to clipboard" part is only available through the macOS Service.

You can refer to command line help for more information on using the tool:

```bash
meme --help
meme add --help
meme search --help
```

To quickly access *Memes* in chats, associate a keyboard shortcut with the "Get Memes" Service. Goto "System Preferences > Keyboard > Shortcuts > Services > Text" and set a keyboard shortcut. When using the Service, simply make a text selection and press the shortcut. You will be prompted with a file selection dialog with candidate memes displayed, and your selected meme will be copied to clipboard.

## Notes

As AppleScript has very limited functionality, the whole Service is rather time consuming and indirect. The Services calls the command line tool to generate candidate meme file paths, copies them into a temporary folder and opens up the file selection dialog. Every time the Service is run, the temporary folder is deleted, which is why you would hear trash bin sound effects.

Also, neither AppleScript nor Automator provide any methods to copy an image to clipboard, so the Service literately opens the image in Preview, simulates the keyboard pressing Cmd+A and the Cmd+C, and then closes the window.

Wow, this sounds even dumber when I wrote it down. I plan to replace the stupid parts with bash scripts in the next version.