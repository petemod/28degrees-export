
# Export to QIF/CSV from 28degrees Latitude Financial Service Centre website


## Description

This utility logs into https://servicecentre.latitudefinancial.com.au/login website, using
your username and password, and simply grabs all your transactions from there,
saving them into QIF file.

**Updated to support Latitude Financial Service Centre website**

## Installation

You will need some things for this tool to work:

1. Python 3
1. WebDriver
1. Selenium
2. selenium-wire

On OS X, you can use `brew` to install N 2 & 3 by:

    `brew install chromedriver`
    `pip install -r requirements.txt`

As installation instructions for the things above vary for different platforms,
I assume you know how install them, otherwise please let me know and I'll
extend this section with detailed steps for your platform.

## Usage

Simply start `export.py` in your shell of choice (cmd.exe, bash, zsh etc).
You will be prompted for your username & password. **THESE details will not be
used for anything but logging into the 28degrees' website.**

If your Internet connection is slow (because Australia), or 28degrees site is being particularly 
slow today, and you see errors/exceptions in the console, use `--slow` command line parameter, which
will increase connection timeout to 25 seconds. I know right, we're not here to fuck spiders.

Then the tool will go through several stages, printing some supplementary information
into console. Do not worry about that unless these are actually error
messages.

When it's done, you should see file that looks like `YYYY.MM.DD-YYYY.MM.DD.qif` under
the 'export' folder, where YYYY.DD.MM are the dates for the first and last transactions
in the exported dataset. It will also create a transactions.db file (sqlite database) but
you can ignore this one - we simply need it to keep track of transactions that have already
been recorded.

If you want to re-start the process, just delete (or re-name, which is safer) transactions.db file.

## Errors / support

As this is a very first and rough cut of the tool, errors to be expected - please **DO**
let me know of any issues you have with it.

Also please feel free to submit your ideas/improvement suggestions.


## Disclaimer

I am not affiliated in any way with this website, and this utility has not been
endorsed or banned by the company-operator of the website.

Please feel free to use it and report on any issues/bug/problems, yet you shall
agree beforehand that you are using this utility at your own risk - I accept
no liability whatsoever for anything what can possibly go wrong.
