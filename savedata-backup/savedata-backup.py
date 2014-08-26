#!/usr/bin/env python
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
import commentjson
from argparse import RawTextHelpFormatter
from throwble import ConcoleArgsException
from os.path  import expanduser

#======= Global constants  =======
m_desc = "Simple backup automation utility for Linux distributive."
m_version = "SaveData version: 0.01~beta"

#======= Global vars  =======
env = "production"
conf = {
    "backups" : {},
    "servers" : {}
}

gconf = {
      "work_path"  : "/var/lib/savedata",
      "logging" : {
        "mode" : "on",
        "path" : "/var/log/savedata"
      }
}

session = {
   "name"    : "{session_name}", 
   "cache"   : "gconf['work_path']/.cache",
   "spath"   : "session['cache']/{session_name}",
   "dbpath"  : "session['spath']/db",
   "clean"   : True
}
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
                raise Exception("Error! Can not create path for logging files. Please, check configuration file: /etc/savedata/global.conf.\nFinish.\n")
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

def parse_gconf(configFileName):
    global gconf
    # open and parse config-file
    if not os.path.isfile(configFileName):
        raise Exception(" File '%s' not found. Please, add global configuration file.\nFailed.\n" % configFileName)
    conf_data = open(configFileName).read()
    gconf = json.loads(conf_data)


def prepare(args):
    global env
    if not os.environ.get('ENV'):
        env = os.environ.get('ENV')


    # if not root...kick out
    if not os.geteuid()==0:
        raise Exception("Only root or sudo can run this util.]\nFailed.\n")

    parse_gconf("/etc/savedata/global.conf")

    return
    #check default file and working dir
    if not os.path.isdir(work_path):
        raise Exception("Working path is not exists. Please, set existing working path in configuration file: /etc/savedata/global.conf.\nFailed.\n")
    
    os.chmod(work_path, 0750)
    os.chown(work_path,0,0)
    
    #cache_path  = work_path + "/.cache"
    #webdav_path = cache_path + "/webdav"
    #db_path     = cache_path + "/db"

    # make dirs
    try:
        shutil.rmtree(webdav_path, ignore_errors=True)
    except OSError:
        pass
    if not os.path.isdir(webdav_path):
        try:
            os.makedirs(webdav_path)
        except OSError:
            raise Exception("Error! Can not create path for mounting future webdav devices. Please, check configuration file: /etc/savedata/global.conf.\nFailed.\n")       


    if not os.path.isdir(cache_path):
        try:
            os.makedirs(cache_path)
        except OSError:
            raise Exception("Error! Can not create path for saving cache data. Please, check configuration file: /etc/savedata/global.conf.\nFailed.\n")       
    
    try:
        shutil.rmtree(db_path, ignore_errors=True)
    except OSError:
        pass

    if not os.path.isdir(db_path):
        try:
            os.makedirs(db_path)
        except OSError:
            raise Exception("Error! Can not create path for saving cache data. Please, check configuration file: /etc/savedata/global.conf.\nFailed.\n")       

    
 
 

    # Setup logging
    setup_logging(args.debug)

    logging.debug('input args: %s', args)
    

def parse_configfile(configFileName):
    global conf
    # open and parse config-file
    if not os.path.isfile(configFileName):
        raise Exception("Error! Can not find configuration file. Please, check arguments.\nFailed.\n")
    conf_data = open(configFileName).read()
    conf = json.loads(conf_data)
    
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
                    raise Exception("Error! Can not create path for saving pgsql dumps. Please, check configuration file.\nFailed.\n")  

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
                    raise Exception('Error! Can not create dump. Please, check configuration file and try agan.\nFailed.')   
    logging.info('created pgsql dumps. OK.')

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
        logging.info("backuping src[%s] -> %s", src_path, srcKey)
        opts = "--ssl-no-check-certificate"
        cmd = "duplicity %s %s %s/%s" % (opts, src_path, server_url, srcKey)
        output, errors =  subprocess.Popen(env + cmd,shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()
        if output:
           logging.debug(output)
        if errors:
           logging.error(errors)
           raise Exception('Error! Can not create backup. Please, check configuration file and try agan.\nFailed.')      
    
    os.system("unset PASSPHRASE")

def umount(path):
    
    cmd = "umount %s" % path
    output, errors =  subprocess.Popen(cmd,shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()
    if output:
        logging.debug(output)
    if errors:
        logging.debug(errors)

def mount_bitcasa(username, userpass, mnt_path):
    umount(mnt_path)
    cmd = "mount.bitcasa %s %s -o 'password=%s'" % (username, mnt_path, userpass)
    logging.info("bitcasa mounting...")
    output, errors =  subprocess.Popen(cmd,shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()
    if output:
        logging.debug(output)
    if errors:
        logging.error(errors)
        raise Exception('Error! Can not mount to bitcasa. Please, check configuration file and try agan.\nFailed.')  
    logging.info("bitcasa device was mounted. OK.")
    

def backup(conf,rewrite):
    dest = conf["dest"]
    for destKey in dest:
       if dest[destKey]["type"] == "local":
             logging.info('making backup in dest: [%s]...', destKey)
             server_url = "file://" + dest[destKey]["remote_path"]
             make_backup(conf,rewrite, server_url, dest[destKey]["type"])
 
       if dest[destKey]["type"] == "webdavs":
            continue
            credits = "%s:%s" % (dest[destKey]["username"],dest[destKey]["password"])
            host = dest[destKey]["host"]
            remote_path = dest[destKey]["remote_path"]
            server_url = "webdavs://%s@%s%s" % (credits, host, remote_path)
            make_backup(conf,rewrite, server_url, dest[destKey]["type"])
 
       if dest[destKey]["type"] == "bitcasa":
             continue
             logging.info('making backup in dest: [%s]...', destKey)
             
             # mount bitcasa webdav-device
             mount_bitcasa(dest[destKey]["username"], dest[destKey]["password"], webdav_path)
             
             # create backup
             server_url = "file://%s%s" % (webdav_path, dest[destKey]["remote_path"])
             make_backup(conf,rewrite, server_url, dest[destKey]["type"])

             # unmount bitcasa webdav-device
             umount(webdav_path)
             logging.info("bitcasa unmounting. OK. ")





def main(args):
    # setup utility-settings and prepare paths and sys files for working
    prepare(args)

    return
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
        default="config.json", required=False)
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
        logging.error("console:%s" % e.value)
    except Exception as e:
        logging.exception(e)
        print e.value


start_app()

 
