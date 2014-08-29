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
import traceback
import datetime
import app

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

def parseConfigs(backupsfName, serversFName):

    source = app.parseYamlFile(backupsfName)
    dest   = app.parseYamlFile(serversFName)
    conf   = {}
    conf["source"] = source 
    conf["dest"] = dest
    return conf



def createSession(gconf):
    session_name = ("%s" % datetime.datetime.now()).replace(" ", "")
    work_path = gconf["work_path"]
    cache_path =  "%s/.cache" % work_path
    session_path = "%s/%s" % (cache_path, session_name)
    db_path = "%s/db" % session_path
    loggingFileName = "savedata-backup-%s.log" % session_name
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
        pass

    try:
        if session["clean"] is True:
            shutil.rmtree(session["spath"], ignore_errors=True)
    except OSError:
        pass    
    session["init"] = False
    os.system("unset PASSPHRASE")

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



def dump_gitlab(conf):
    backups = conf["source"]["backups"]
    logging.info('create gitlab dumps...')
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
                output, errors =  subprocess.Popen(cmd,shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()
                if errors:
                    logging.error(errors)
                    raise Exception('Can not create dump. Please, check configuration file and try agan.')   
    logging.info('created pgsql dumps. OK.')

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

def getExcludeOpts(backup):
    opts = ""
    if not "exclude" in backup:
        return ""
    for excl in backup["exclude"]:
        opts += " --exclude '%s'" % excl
    return opts

#duplicity --full-if-older-than 1M /etc ftp://ftpuser@other.host/etc
#duplicity remove-older-than 6M --force ftp://ftpuser@other.host/etc
#
#
def remove_old_backups(backup, server_url, srcKey):
    if not backup["period"]:
        return
    env_pass = "export PASSPHRASE=" + backup["passphrase"] + "; "
    duplicity_opts = "remove-older-than %s" % backup["period"]
    cmd = "duplicity %s %s/%s" % (duplicity_opts, server_url, srcKey)
    output, errors =  subprocess.Popen(env_pass + cmd,shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()
    if output:
       logging.info(output)
    if errors:
       logging.error(errors)
       raise Exception('Can not remove old backups. Please, check configuration file and try agan.')  
    os.system("unset PASSPHRASE")

def make_backup(conf, server_url, server_key):
    source = conf["source"]
    dest = conf["dest"]
    backups = source["backups"]
    db_path = conf["session"]["dbpath"]
    base_opts = " --ssl-no-check-certificate"
    for srcKey in backups:
        backup = backups[srcKey]
        exclude_opts = getExcludeOpts(backup)
        key_opts = ""
        if "full" in backup:
            key_opts += "--full-if-older-than %s " % backup["full"]
        
        if backup["type"] == "pgsql":
            src_path = "%s/%s" % (db_path, srcKey)
            key_opts += " --allow-source-mismatch"
        elif backup["type"] == "dir":
            src_path = backup["path"]
        else:
            continue
        # make env-variable with passphrase
        passphrase = backup["passphrase"]
        env_pass = "export PASSPHRASE=" + passphrase + "; "

        logging.info("backuping src[%s:%s] -> dest[%s]", srcKey, src_path, server_key)
        duplicity_opts = " %s %s %s" % (base_opts, exclude_opts, key_opts)
        logging.debug("duplicity opts: %s", duplicity_opts) 
        cmd = "duplicity %s %s %s/%s" % (duplicity_opts, src_path, server_url, srcKey)
        output, errors =  subprocess.Popen(env_pass + cmd,shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()
        if output:
           logging.info(output)
        if errors:
           logging.error(errors)
           raise Exception('Can not create backup. Please, check configuration file and try agan.')      
        remove_old_backups(backup,server_url,srcKey)
    os.system("unset PASSPHRASE")


def backup(conf,rewrite):
    servers = conf["dest"]["servers"]
    for destKey in servers:
       server = servers[destKey] 
       logging.info('making backup in dest: [%s]...', destKey)
       if server["type"] == "local":
           rewriteBackup(servers[destKey], rewrite)
       elif servers[destKey]["type"] == "webdavs":
           pass
       else:
           continue
       server_url = app.buildServerURL(server)
       make_backup(conf, server_url, destKey)


def main(args):
    global gconf
    global session
    global env_mode
    global env

    # setup utility-settings and prepare paths and sys files for working. Function return global configuration settings
    gconf,env,env_mode = app.prepare(args.debug,"savedata-backup.log")

    # read and parse data from configuration file (backups.json and servers.json)
    conf = parseConfigs(args.backups_fname, args.servers_fname)
    
    # create session
    session = createSession(gconf)
    conf["session"] = session

    # dump databases in cache directory
    dump_dbs(conf)

    dump_gitlab(conf)

    # backup 
    backup(conf, args.rewrite)

    return


def prepare_argsParser():
    argsParser = argparse.ArgumentParser(
        version=m_version, fromfile_prefix_chars='@', description=m_desc, formatter_class=argparse.RawTextHelpFormatter)
    argsParser.add_argument(
        "-b", "--backups", dest="backups_fname", help="Configuration file  with sorce information, which you want backuping (ymal format).",
        default="/etc/savedata/backups.yml", required=False)
    argsParser.add_argument(
        "-s", "--servers", dest="servers_fname", help="Configuration file with destination settings, in which you want storage backups (ymal format).",
        default="/etc/savedata/servers.yml", required=False)
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
    except Exception as e:
        logging.error(e)
        logging.debug(traceback.format_exc())
        logging.warning("FAILED.")
        # send email
        sendLogToEmail(session, "failed")
    
    # delete session
    deleteSession(session)

start_app()

 
