#!/usr/bin/python
# -*- coding: utf- -*-
import sys
import os
import os.path
import argparse
import codecs
import json
import logging

sys.path.append("src")
from argparse import RawTextHelpFormatter
from throwble import ConcoleArgsException
#======= Default params  =======
m_desc = "Simple backup automation utility."
m_version = "SaveData version: 0.01beta"
#======= Main function   =======


def setup_logging(isDebug):
    logging.basicConfig(level=logging.DEBUG)
    logger = logging.getLogger()
    logger.propagate = False
    if len(logger.handlers) > 0:
        logger.removeHandler(logger.handlers[0])
    formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s')
    fh = logging.FileHandler('logs/grabber.log')
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(formatter)
    logger.addHandler(fh)
    ch = logging.StreamHandler()
    if isDebug is True:
        ch.setLevel(logging.DEBUG)
    else:
        ch.setLevel(logging.INFO)
    ch.setFormatter(formatter)
    logger.addHandler(ch)


def prepare_home_folder():
    try:
        os.makedirs('output')
    except OSError:
        pass
    try:
        os.makedirs('logs')
    except OSError:
        pass
    try:
        os.makedirs('logs/server')
    except OSError:
        pass

def main(args):
    
    prepare_home_folder()
    # Setup logging
    setup_logging(args.debug)
    logging.debug('input args: %s', args)



def setup_console(sys_enc="utf-8"):
    reload(sys)
    try:
        # for win32
        if sys.platform.startswith("win"):
            import ctypes
            enc = "cp%d" % ctypes.windll.kernel32.GetOEMCP(
            )  # TODO: check on win64/python64
        else:
            # for Linux
            enc = (sys.stdout.encoding if sys.stdout.isatty() else
                   sys.stderr.encoding if sys.stderr.isatty() else
                   sys.getfilesystemencoding() or sys_enc)

        # encoding sys
        sys.setdefaultencoding(sys_enc)

        if sys.stdout.isatty() and sys.stdout.encoding != enc:
            sys.stdout = codecs.getwriter(enc)(sys.stdout, 'replace')

        if sys.stderr.isatty() and sys.stderr.encoding != enc:
            sys.stderr = codecs.getwriter(enc)(sys.stderr, 'replace')

    except:
        pass  # Error? Work in standard mode
#======= Options config   =======


def prepare_argsParser():
    argsParser = argparse.ArgumentParser(
        version=m_version, fromfile_prefix_chars='@', description=m_desc, formatter_class=RawTextHelpFormatter)
    argsParser.add_argument(
        "-c", "--config", dest="configFileName", help="File name of configuration file (json format).",
        default="config-example.json", required=False)
    return argsParser


def start_app():
    setup_console()
    argsParser = prepare_argsParser()
    try:
        main(argsParser.parse_args())
    except ConcoleArgsException as e:
        print argsParser.print_usage()
        logging.error(e.value)
    except Exception as e:
        logging.exception(e)
start_app()

 
