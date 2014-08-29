
import logging
import sys
import os
import yaml


def parseYamlFile(filename):
    if not os.path.isfile(filename):
        raise Exception(" File '%s' not found. Please, add configuration file and try again.\nFailed.\n" % filename)
    stream = open(filename, 'r')
    return yaml.load(stream)
    
def console_configure(sys_enc="utf-8"):
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

def logConsole(debugLevel):
    logging.basicConfig(level=logging.DEBUG)
    logger = logging.getLogger()
    logger.propagate = False
    if len(logger.handlers) > 0:
        logger.removeHandler(logger.handlers[0])
    formatter = logging.Formatter('%(levelname)s - %(message)s')

    ch = logging.StreamHandler()
    if debugLevel is True:
        ch.setLevel(logging.DEBUG)
    else:
        ch.setLevel(logging.INFO)

    ch.setFormatter(formatter)
    logger.addHandler(ch)

def clearLogging():
    logging.basicConfig(level=logging.DEBUG)
    logger = logging.getLogger()
    logger.propagate = False
    while len(logger.handlers) > 0:
        logger.removeHandler(logger.handlers[0])

def logFile(mode, loggingPath, loggingFileName, gconfFileName):
    fullFileName = loggingPath + "/" + loggingFileName
    if mode == "off":
        return
    if mode != "on":
        msg = "Logging mode is incorrect(availible values: 'on', 'off'). Please, check configuration file: %s." % gconfFileName
        raise Exception(msg)
    if not os.path.isdir(loggingPath):
        msg = "Can not find logging path %s. Please, check configuration file: %s" % (loggingPath, gconfFileName)
        raise Exception(msg)

  
    logging.basicConfig(level=logging.DEBUG)
    logger = logging.getLogger()
    logger.propagate = False
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

    fh = logging.FileHandler(fullFileName)
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(formatter)
    logger.addHandler(fh)

#################################################
import sys
import os
import re

from smtplib import SMTP_SSL as SMTP       # this invokes the secure SMTP protocol (port 465, uses SSL)
# from smtplib import SMTP                  # use this for standard SMTP protocol   (port 25, no encryption)
from email.MIMEText import MIMEText


def sendEmail(smtp_settings, sender, destination, content, subject):
    SMTPserver = smtp_settings["address"]
    port = smtp_settings["port"]
    USERNAME = smtp_settings["username"]
    PASSWORD = smtp_settings["password"]

    # typical values for text_subtype are plain, html, xml
    text_subtype = 'plain'
    try:
        contenthtml = u'' + content
        msg = MIMEText(contenthtml, text_subtype, "utf-8")
       # msg = MIMEText(u'\u3053\u3093\u306b\u3061\u306f\u3001\u4e16\u754c\uff01\n',
       #          "plain", "utf-8")

        msg['Subject']=       subject
        msg['From']   = sender # some SMTP servers will do this automatically, not all
        conn = SMTP(SMTPserver)
        conn.set_debuglevel(False)
        conn.login(USERNAME, PASSWORD)
        try:
            conn.sendmail(sender, destination, msg.as_string())
        finally:
            conn.close()
    except Exception, exc:
        sys.exit( "mail failed; %s" % str(exc) ) # give a error message
