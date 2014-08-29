
import logging
import sys
import os
import yaml
import re
from smtplib import SMTP_SSL as SMTP       # this invokes the secure SMTP protocol (port 465, uses SSL)
# from smtplib import SMTP                  # use this for standard SMTP protocol   (port 25, no encryption)
from email.MIMEText import MIMEText


def buildServerURL(server):
   if server["type"] == "local":
      server_url = "file://" + server["remote_path"]
      return server_url
   if server["type"] == "webdavs":
      credits = "%s:%s" % (server["username"],server["password"])
      host =  server["host"]
      remote_path = server["remote_path"]
      server_url = "webdavs://%s@%s%s" % (credits, host, remote_path)
      return server_url

def setupEnvironment(envFileName):
    env_mode = "production"
    if os.environ.get('SAVADETA_ENV'):
        env_mode = os.environ.get('SAVADETA_ENV')
    
    env_settings = parseYamlFile(envFileName)
    
    if not env_mode in env_settings:
        raise Exception("Our environment mode '{0}' do not have settings-block in file {1}.".format(env_mode, envFileName))
    env = env_settings[env_mode]
    logging.debug("environment[%s] = %s", env_mode, env)
    return (env, env_mode)

def checkWorkPath(gconf):
    work_path = gconf["work_path"]
    #check default file and working dir
    if not os.path.isdir(work_path):
        raise Exception("Working path is not exists. Please, set existing working path in configuration file: /etc/savedata/global.conf.\n")
    
    os.chmod(work_path, 0750)
    os.chown(work_path,0,0)
    
    cache_path  = "%s/.cache" % work_path
    if not os.path.isdir(cache_path):
        try:
            os.makedirs(cache_path)
        except OSError:
            raise Exception("Can not create path for saving cache data. Please, check configuration file: /etc/savedata/global.conf.\n")       
    os.chmod(cache_path, 0700)
    os.chown(cache_path,0,0)

def setupFileLogging(gconf, logFileName, gconfFileName):
    logging_mode = gconf["logging"]["mode"]
    logging_path = gconf["logging"]["path"]
    logFile(logging_mode,logging_path,logFileName, gconfFileName)

def prepare(debug, logFileName):
    # setup console-logging 
    logConsole(debug)

    # if not root...kick out
    if not os.geteuid()==0:
        raise Exception("Only root or sudo can run this util.]\n")

    env, env_mode = setupEnvironment("environment.yml")
    
    # load global configs
    gconf = parseYamlFile(env["gconf"])

    # setup file-logging 
    setupFileLogging(gconf,logFileName, env["gconf"])

    # check and configure working paths
    checkWorkPath(gconf)
    return  (gconf,env,env_mode)

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

def sendEmail(smtp_settings, sender, destination, content, subject):
    SMTPserver = smtp_settings["address"]
    port = smtp_settings["port"]
    USERNAME = smtp_settings["username"]
    PASSWORD = smtp_settings["password"]

    text_subtype = 'plain'
    try:
        contenthtml = u'' + content
        msg = MIMEText(contenthtml, text_subtype, "utf-8")
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
