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
from parsing_problem import ParsingProblem
from send import ProblemsSender
#======= Default params  =======
m_desc = "Problems parser. Using this tool for converting VRP-data to json object."
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


def prepare_fs():
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
    prepare_fs()
    # Настроим логгирование
    setup_logging(args.debug)
    logging.debug('input args: %s', args)

    # Распирсим файл
   


def setup_console(sys_enc="utf-8"):
    reload(sys)
    try:
        # для win32 вызываем системную библиотечную функцию
        if sys.platform.startswith("win"):
            import ctypes
            enc = "cp%d" % ctypes.windll.kernel32.GetOEMCP(
            )  # TODO: проверить на win64/python64
        else:
            # для Linux всё, кажется, есть и так
            enc = (sys.stdout.encoding if sys.stdout.isatty() else
                   sys.stderr.encoding if sys.stderr.isatty() else
                   sys.getfilesystemencoding() or sys_enc)

        # кодировка для sys
        sys.setdefaultencoding(sys_enc)

        # переопределяем стандартные потоки вывода, если они не перенаправлены
        if sys.stdout.isatty() and sys.stdout.encoding != enc:
            sys.stdout = codecs.getwriter(enc)(sys.stdout, 'replace')

        if sys.stderr.isatty() and sys.stderr.encoding != enc:
            sys.stderr = codecs.getwriter(enc)(sys.stderr, 'replace')

    except:
        pass  # Ошибка? Всё равно какая - работаем по-старому...
#======= Options config   =======


def prepare_argsParser():
    argsParser = argparse.ArgumentParser(
        version="Grabber version: 0.01", fromfile_prefix_chars='@', description=m_desc, formatter_class=RawTextHelpFormatter)
    argsParser.add_argument(
        "-t", "--class", dest="Class", help="[REQUIRED] Class of problem(Christofides, Golden,...)",
        default="", required=True)
    argsParser.add_argument(
        "-n", "--number", dest="Number", help="[REQUIRED] Number of problem",
        default="", required=True)
    argsParser.add_argument(
        "--admin_host", dest="admin_host", help="Url of admin tool", default=None)
    argsParser.add_argument(
        "--debug", dest="debug", help="Output debug information into console", action='store_true', default=False)
    argsParser.add_argument(
        "--admin_login", dest="admin_login", help="User`s login of admin tool", default=None)
    argsParser.add_argument(
        "--admin_pass", dest="admin_pass", help="User`s password of admin tool", default=None)


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

 
