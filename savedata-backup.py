#!/usr/bin/python
# -*- coding: utf- -*-
import sys
import os
import os.path
import argparse
import codecs
import json
import logging
import shutil
import subprocess

sys.path.append("src")
from argparse import RawTextHelpFormatter
from throwble import ConcoleArgsException
from os.path  import expanduser

#======= Global constants  =======
m_desc = "Simple backup automation utility for Linux distributive."
m_version = "SaveData version: 0.01beta"

#======= Global vars  =======
work_path = "/home/romario/tmp/savedata"
logging_path="/home/romario/tmp/savedata/log"
is_logging = True

cache_path = ""
db_path    = ""
webdav_path = ""
conf = {}

#======= Main function   =======


def setup_logging(isDebug):
    logging.basicConfig(level=logging.DEBUG)
    logger = logging.getLogger()
    logger.propagate = False
    if len(logger.handlers) > 0:
        logger.removeHandler(logger.handlers[0])
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

    if is_logging:
        if not os.path.isdir(logging_path):
             try:
                os.makedirs(logging_path)
             except OSError:
                sys.exit("Error! Can not create path for logging files. Please, check configuration file: /etc/default/savedata.\nFinish.\n")
        fh = logging.FileHandler(logging_path + "/savedata.log")
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


def prepare(work_path, args):
    global cache_path
    global db_path
    global webdav_path
    
    # if not root...kick out
    if not os.geteuid()==0:
        sys.exit("Only root or sudo can run this util.]\nFailed.\n")

    #check default file and working dir
    if not os.path.isdir(work_path):
        sys.exit("Working path is not exists. Please, set existing working path in configuration file: /etc/default/savedata.\nFailed.\n")
    
    os.chmod(work_path, 0750)
    os.chown(work_path,0,0)
    
    webdav_path = work_path + "/webdav"
    cache_path = work_path + "/.cache"
    db_path    = cache_path + "/db"

    # make dirs
    try:
        shutil.rmtree(webdav_path, ignore_errors=True)
    except OSError:
        pass
    if not os.path.isdir(webdav_path):
        try:
            os.makedirs(webdav_path)
        except OSError:
            sys.exit("Error! Can not create path for mounting future webdav devices. Please, check configuration file: /etc/default/savedata.\nFailed.\n")       


    if not os.path.isdir(cache_path):
        try:
            os.makedirs(cache_path)
        except OSError:
            sys.exit("Error! Can not create path for saving cache data. Please, check configuration file: /etc/default/savedata.\nFailed.\n")       
    
    try:
        shutil.rmtree(db_path, ignore_errors=True)
    except OSError:
        pass

    if not os.path.isdir(db_path):
        try:
            os.makedirs(db_path)
        except OSError:
            sys.exit("Error! Can not create path for saving cache data. Please, check configuration file: /etc/default/savedata.\nFailed.\n")       

    
 
 

    # Setup logging
    setup_logging(args.debug)

    logging.debug('input args: %s', args)
    

def parse_configfile(configFileName):
    global conf
    # open and parse config-file
    if not os.path.isfile(configFileName):
        sys.exit("Error! Can not find configuration file. Please, check arguments.\nFailed.\n")
    conf_data = open(configFileName).read()
    conf = json.loads(conf_data)
    logging.debug('conf: %s', conf)

def dump_dbs(conf):
    sources = conf["source"]

    logging.info('create pgsql dumps...')
    for key in sources:
       if sources[key]["type"] == "pgsql":
            pgsql_path = db_path + "/" + key
            if not os.path.isdir(pgsql_path):
                try:
                    os.makedirs(pgsql_path)
                except OSError:
                    sys.exit("Error! Can not create path for saving pgsql dumps. Please, check configuration file.\nFailed.\n")  

            user = sources[key]["run-as-user"]
            dbs  = sources[key]["db"]
            for dbName in dbs:
                logging.info('db[%s] is dumping...', dbName)
                dbFile = pgsql_path + "/" + dbName + ".sql"
                cmd = "su - " + user  + " -c 'pg_dump -d " + dbName + "'>> " + dbFile
                #os.system(cmd)
                output, errors =  subprocess.Popen(cmd,shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()
                if errors:
                    logging.error(errors)
                    sys.exit('Error! Can not create dump. Please, check configuration file and try agan.\nFailed.')   
    logging.info('created pgsql dumps. ok.')

def rewriteBackup(conf, rewrite, server_url,dest_type):
    if rewrite is False:
        return
    if dest_type == "local" or dest_type == "bitcasa":
       try:
            shutil.rmtree(dest_path + "/" + srcKey, ignore_errors=True)
       except OSError:
            pass

    
def make_backup(conf, rewrite, server_url,dest_type):
    #DUPLICITY_BACKUP_OPTIONS = "--verbosity warning --no-print-statistics --num-retries 3"
    # "duplicity $backup_method --allow-source-mismatch $DUPLICITY_BACKUP_OPTIONS $backup_tmpdir $server_url/$backup_remote_name"
    sources = conf["source"]
    passphrase = conf["root"]["passphrase"]
    env = "export PASSPHRASE=" + passphrase + "; "
            
    for srcKey in sources:
        if sources[srcKey]["type"] == "pgsql":
            src_path = db_path + "/" + srcKey
        elif sources[srcKey]["type"] == "dir":
            src_path = sources[srcKey]["path"]
        else:
            continue

        rewriteBackup(conf, rewrite, server_url,dest_type)
        logging.info("backuping src[%s] -> %s", src_path, server_url + "/" + srcKey)
        cmd = "duplicity " + src_path + server_url + "/" + srcKey
        logging.debug("cmd: %s", cmd)
        output, errors =  subprocess.Popen(env + cmd,shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()
        if output:
           logging.debug(output)
        if errors:
           logging.error(errors)
           sys.exit('Error! Can not create backup. Please, check configuration file and try agan.\nFailed.')      
    
    os.system("unset PASSPHRASE")


def backup(conf,rewrite):
    dest = conf["dest"]
    for destKey in dest:
       if dest[destKey]["type"] == "local":
             continue
             logging.info('making backup in dest: [%s]...', destKey)
             server_url = " file://" + dest[destKey]["remote_path"]
             make_backup(conf,rewrite, server_url, dest[destKey]["type"])
       if dest[destKey]["type"] == "bitcasa":
             logging.info('making backup in dest: [%s]...', destKey)
             
             # mount bitcasa webdav-device
             cmd = "bitcasa %s %s -o 'password=%s'" % (dest[destKey]["username"], webdav_path, dest[destKey]["password"])
             logging.debug(cmd)
             output, errors =  subprocess.Popen(cmd,shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()
             if output:
                logging.debug(output)
             if errors:
                logging.error(errors)
             # create backup
             server_url = " file://%s%s" % (webdav_path, dest[destKey]["remote_path"])
             make_backup(conf,rewrite, server_url, dest[destKey]["type"])

             # unmount bitcasa webdav-device
             cmd = "umount %s" % webdav_path
             output, errors =  subprocess.Popen(cmd,shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()
             if output:
                logging.debug(output)
             if errors:
                logging.error(errors)
             sys.exit('Error! Can not create backup. Please, check configuration file and try agan.\nFailed.')  



def main(args):
    # setup utility-settings and prepare paths and sys files for working
    prepare(work_path, args)

    # read and parse config-ata from configuration file
    parse_configfile(args.configFileName)

    # dump databases in cache directory
    dump_dbs(conf)

    # backup 
    backup(conf, args.rewrite)

    logging.info("Done.")


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
    argsParser.add_argument(
        "--rewrite", dest="rewrite", help="Rewrite backups in destination(use, when you change passphrase)", action='store_true', default=False)
    argsParser.add_argument(
        "--debug", dest="debug", help="Output debug information into console", action='store_true', default=False)
    
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

 
