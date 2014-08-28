#!/usr/bin/env python
#!/usr/bin/python
# -*- coding: utf- -*-
import os
import os.path
import argparse
import codecs
import json
import logging
import shutil
import subprocess
import commentjson
import traceback
import datetime
import app
from argparse import RawTextHelpFormatter
from throwble import ConcoleArgsException

#======= Global constants  =======
m_desc = "Simple backup automation utility for Linux distributive."
m_version = "SaveData version: 0.01~beta"

#======= Global vars  =======
env_mode = "production"
env = {
    "gconf" : "/etc/savedata/global.conf"
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
   "clean"   : True,
   "init"    : False,
}
#======= Main function   =======

def setupEnvironment(envFileName):
    global env_mode
    global env
    
    if os.environ.get('ENV'):
        env_mode = os.environ.get('ENV')
    env_settings = commentjson.parseFileJSON(envFileName)
    
    if not env_mode in env_settings:
        raise Exception("Our environment mode '{0}' do not have settings-block in file {1}.".format(env_mode, envFileName))
    env = env_settings[env_mode]

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

def parseConfigs(backupsfName, serversFName):
    backups = commentjson.parseFileJSON(backupsfName)
    servers = commentjson.parseFileJSON(serversFName)
    conf = {}
    conf["source"] = backups 
    conf["dest"] = servers
    return conf



def createSession(gconf):
    session_name = ("%s" % datetime.datetime.now()).replace(" ", "")
    work_path = gconf["work_path"]
    cache_path =  "%s/.cache" % work_path
    session_path = "%s/%s" % (cache_path, session_name)
    db_path = "%s/db" % session_path
    loggingFileName = "savedata-%s.log" % session_name
    session = {
        "init"    : False,
        "name"    : session_name, 
        "cache"   : cache_path,
        "spath"   : session_path,
        "dbpath"  : db_path,
        "clean"   : True,
        "log"     : loggingFileName
    }

    # make session path
    if not os.path.isdir(session_path):
        try:
            os.makedirs(session_path)
        except OSError:
            msg = "Can not create sesssion path. Please, check configuration file: %s" % env["gconf"] 
            raise Exception(msg)  
    
    # make db path
    if not os.path.isdir(db_path):
        try:
            os.makedirs(db_path)
        except OSError:
            msg = "Can not create db path for saving dumps of backup-databases. Please, check configuration file: %s" % env["gconf"] 
            raise Exception(msg)  
    # prepare logging session
    logging_mode = gconf["logging"]["mode"]
    logging_path = gconf["logging"]["path"]
    app.logFile(logging_mode,logging_path,session["log"], env["gconf"])

    session["init"] = True
    return session  


def deleteSession(session):
    if session["init"] is False:
        return
    try:
        logging_path = gconf["logging"]["path"]
        fullLogFileName = "%s/%s" % (logging_path, session["log"])
        os.remove(fullLogFileName)
    except OSError as e:
        print e

    try:
        if session["clean"] is True:
            shutil.rmtree(session["spath"], ignore_errors=True)
    except OSError:
        pass    
    session["init"] = False

def sendLogToEmail(session, status):
    if status!="success" and status!="failed":
        raise Exception("Email status can be only 'success' or 'failed' ")
    if not "email" in gconf:
        return
    if not "smtp_settings" in gconf["email"]:
        return

    try:
        if gconf["email"]["send_succes"] is False and status == "success":
            return
        if gconf["email"]["send_failed"] is False and status == "failed":
            return
        smtp_settings = gconf["email"]["smtp_settings"]
        sender = gconf["email"]["from"]
        destination =gconf["email"]["to"]
        logging_path = gconf["logging"]["path"]
        fullLogFileName = "%s/%s" % (logging_path, session["log"])
        logarr = ''
        with open(fullLogFileName) as f:
            logarr = f.readlines()
        loginfo = ""
        for line in logarr:
            loginfo += line
        loginfo = loginfo.decode('string_escape')
        content = "Log information from last backupping:\n%s" % loginfo
        subject = "SaveData-Backup : %s" % status
        app.sendEmail(smtp_settings, sender, destination, content, subject)
    except OSError:
        msg = "Can not send email. Please, check your global configuration file %s" % env["gconf"]
        raise Exception(msg)  


def setupFileLogging(gconf):
    logging_mode = gconf["logging"]["mode"]
    logging_path = gconf["logging"]["path"]
    app.logFile(logging_mode,logging_path,"savedata.log", env["gconf"])

def prepare(args):
    # setup console-logging 
    app.logConsole(args.debug)

    # if not root...kick out
    if not os.geteuid()==0:
        raise Exception("Only root or sudo can run this util.]\n")

    setupEnvironment("environment.json")
    
    # load global configs
    gconf = commentjson.parseFileJSON(env["gconf"])

    # setup file-logging 
    setupFileLogging(gconf)


    # check and configure working paths
    checkWorkPath(gconf)
    return gconf

   
def dump_dbs(conf):
    backups = conf["source"]["backups"]
    logging.info('create pgsql dumps...')

    db_path = conf["session"]["dbpath"]
    for key in backups:
       if backups[key]["type"] == "pgsql":
            pgsql_path ="%s/%s" % (db_path, key)
            if not os.path.isdir(pgsql_path):
                try:
                    os.makedirs(pgsql_path)
                except OSError:
                    raise Exception("Can not create path for saving pgsql dumps. Please, check configuration file")  
            user = backups[key]["run-as-user"]
            dbs  = backups[key]["db"]
            for dbName in dbs:
                logging.info('db[%s] is dumping...', dbName)
                dbFile = pgsql_path + "/" + dbName + ".sql"
                cmd = "su - " + user  + " -c 'pg_dump -d " + dbName + "'>> " + dbFile
                #os.system(cmd)
                output, errors =  subprocess.Popen(cmd,shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()
                if errors:
                    logging.error(errors)
                    raise Exception('Can not create dump. Please, check configuration file and try agan.')   
    logging.info('created pgsql dumps. OK.')

def rewriteBackup(server, rewrite):
    if rewrite is False:
        return
    if server["type"] == "local":
       try:
            shutil.rmtree(server["remote_path"], ignore_errors=True)
       except OSError:
            pass

    
def make_backup(conf, server_url):
    source = conf["source"]
    dest = conf["dest"]
    backups = source["backups"]
    passphrase = dest["root"]["passphrase"]
    env_pass = "export PASSPHRASE=" + passphrase + "; "
    db_path = conf["session"]["dbpath"]
    
    for srcKey in backups:
        duplicity_opts = "--ssl-no-check-certificate"
        if backups[srcKey]["type"] == "pgsql":
            src_path = "%s/%s" % (db_path, srcKey)
            duplicity_opts += " --allow-source-mismatch"
        elif backups[srcKey]["type"] == "dir":
            src_path = backups[srcKey]["path"]
        else:
            continue
        logging.info("backuping src[%s] -> %s", src_path, srcKey)
        
        cmd = "duplicity %s %s %s/%s" % (duplicity_opts, src_path, server_url, srcKey)
        output, errors =  subprocess.Popen(env_pass + cmd,shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()
        if output:
           logging.info(output)
        if errors:
           logging.error(errors)
           raise Exception('Can not create backup. Please, check configuration file and try agan.')      
    
    os.system("unset PASSPHRASE")


def backup(conf,rewrite):
    servers = conf["dest"]["servers"]
    for destKey in servers:
       if servers[destKey]["type"] == "local":
             logging.info('making backup in dest: [%s]...', destKey)
             server_url = "file://" + servers[destKey]["remote_path"]
             rewriteBackup(servers[destKey], rewrite)
             make_backup(conf, server_url)
 
       if servers[destKey]["type"] == "webdavs":
            credits = "%s:%s" % (servers[destKey]["username"],servers[destKey]["password"])
            host = servers[destKey]["host"]
            remote_path = servers[destKey]["remote_path"]
            server_url = "webdavs://%s@%s%s" % (credits, host, remote_path)
            make_backup(conf, server_url)



def main(args):
    global gconf
    global session

    # setup utility-settings and prepare paths and sys files for working. Function return global configuration settings
    gconf = prepare(args)

    # read and parse data from configuration file (backups.json and servers.json)
    conf = parseConfigs(args.backups_fname, args.servers_fname)
    
    # create session
    session = createSession(gconf)
    conf["session"] = session

    # dump databases in cache directory
    dump_dbs(conf)

    # backup 
    backup(conf, args.rewrite)

    return


def prepare_argsParser():
    argsParser = argparse.ArgumentParser(
        version=m_version, fromfile_prefix_chars='@', description=m_desc, formatter_class=RawTextHelpFormatter)
    argsParser.add_argument(
        "-b", "--backups", dest="backups_fname", help="[REQUIRED]. Configuration file  with sorce information, which you want backuping (json format).",
        default="backups.json", required=True)
    argsParser.add_argument(
        "-s", "--servers", dest="servers_fname", help="[REQUIRED]. Configuration file with destination settings, in which you want storage backups (json format).",
        default="servers.json", required=True)
    argsParser.add_argument(
        "--rewrite", dest="rewrite", help="Rewrite backups in destination(use, when you want change your passphrase)", action='store_true', default=False)
    argsParser.add_argument(
        "--debug", dest="debug", help="Output debug information into console", action='store_true', default=False)
    return argsParser

def start_app():
    app.console_configure()
    argsParser = prepare_argsParser()
    try:
        main(argsParser.parse_args())
        logging.info("FINISH. OK. ")
        # send email
        sendLogToEmail(session, "success")
    except ConcoleArgsException as e:
        logging.error("console:%s" % e.value)
        logging.warning("FAILED.")
    except Exception as e:
        logging.error(e)
        logging.debug(traceback.format_exc())
        logging.warning("FAILED.")
        # send email
        sendLogToEmail(session, "failed")
    
    # delete session
    deleteSession(session)

start_app()

 
