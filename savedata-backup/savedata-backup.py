#!/usr/bin/env python
#!/usr/bin/python
# -*- coding: utf- -*-
import os
import os.path
import argparse
import codecs
import logging
import shutil
import subprocess
import traceback
import datetime
import app
import gitlab
import gitbackup
import pgsql
import re
import fnmatch

#======= Global constants  =======
m_desc = "Simple backup automation utility for Linux distributive."
m_version = "SaveData version: 0.03~beta"

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
    loggingFileName = "savedata-backup-%s.log" % session_name
    session = {
        "init"    : False,
        "name"    : session_name, 
        "cache"   : cache_path,
        "spath"   : session_path,
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


def dump(conf):
    pgsql.dump(conf)
    gitlab.dump(conf)
    gitbackup.dump(conf)


def rewriteBackup(server, rewrite):
    if rewrite is False:
        return
    if server["type"] == "local":
       try:
            shutil.rmtree(server["remote_path"], ignore_errors=True)
       except OSError:
            pass

def getFilterOpts(backup):
    opts = ""
    if not "filter" in backup:
      return opts
    filter = backup["filter"]
    for f in filter:
        type = f["type"]
        patterns = f["pattern"]
        for p in patterns:
            opts += ' --%s "%s"' % (type, p)

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
    cmd = "duplicity --ssl-no-check-certificate %s %s/%s" % (duplicity_opts, server_url, srcKey)
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
    session = conf["session"]
    base_opts = " --ssl-no-check-certificate"
    for srcKey in backups:
        backup = backups[srcKey]
        filter_opts = getFilterOpts(backup)
        key_opts = ""
        if "full" in backup:
            key_opts += "--full-if-older-than %s " % backup["full"]

        if backup["type"] == "gitlab":
            src_path = "%s/%s" % (session["spath"], srcKey)
            key_opts += " --allow-source-mismatch"
        elif backup["type"] == "pgsql":
            src_path = "%s/%s" % (session["spath"], srcKey)
            key_opts += " --allow-source-mismatch"
        elif backup["type"] == "git":
            src_path = "%s/%s" % (session["spath"], srcKey)
            key_opts += " --allow-source-mismatch"
        elif backup["type"] == "dir":
            src_path = backup["path"]
        else:
            continue
        # make env-variable with passphrase
        passphrase = backup["passphrase"]
        env_pass = "export PASSPHRASE=" + passphrase + "; "

        logging.info("backuping src[%s:%s] -> dest[%s]", srcKey, src_path, server_key)
        duplicity_opts = " %s %s %s" % (base_opts, filter_opts, key_opts)
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
       
       # change permissions
       if server["type"] == "local":
          if ("chown" in server)  and len(server["chown"]) > 0:
              cmd = "chown %s -R %s" % (server["chown"], server["remote_path"])
              output, errors =  subprocess.Popen(cmd,shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()
              if output:
                  logging.info(output)
              if errors:
                  logging.error(errors)
                  raise Exception('Can not change files owner(chown) in destination directory')   


def filter_dictionary(filter_str, _dict):
    arr = filter_str.split(',')
    ragexes = []
    for e in arr:
        if len(e) <= 1 or (e[0] != 'i' and e[0] != 'e'):
            msg = "Can not parse ragex list. Pleasem check input arguments."
            raise Exception(msg)
        obj = {
          "type" : e[0],
          "name" : e[1:]
        } 
        ragexes.append(obj)
    
    
    ##
    strfilter = {}
    for name in _dict:
        strfilter[name] = -1

    ## 
    for e in ragexes:
        for name in strfilter:
            if fnmatch.fnmatchcase(name, e["name"])==True and strfilter[name] == -1:
                if e["type"] == 'i':
                    strfilter[name] = True
                else:
                    strfilter[name] = False
    for name in strfilter:
        if  strfilter[name] == -1:
            strfilter[name] = False

    filter_dict = {}
    
    for name in _dict:
        if strfilter[name] == True:
            filter_dict[name] = _dict[name]

    return filter_dict

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
    

    conf["source"]["backups"] = filter_dictionary(args.backups, conf["source"]["backups"])
    conf["dest"]["servers"] = filter_dictionary(args.servers, conf["dest"]["servers"])

    # dump in cache directory
    dump(conf)

    # backup 
    backup(conf, args.rewrite)

    return


def prepare_argsParser():
    argsParser = argparse.ArgumentParser(
        version=m_version, fromfile_prefix_chars='@', description=m_desc, formatter_class=argparse.RawTextHelpFormatter)
    argsParser.add_argument(
        "-b", dest="backups_fname", help="Configuration file  with sorce information, which you want backuping (ymal format).",
        default="/etc/savedata/backups.yml", required=False)
    argsParser.add_argument(
        "-s", dest="servers_fname", help="Configuration file with destination settings, in which you want storage backups (ymal format).",
        default="/etc/savedata/servers.yml", required=False)
    argsParser.add_argument(
        "--backups", dest="backups", help="Include backup", default="i*", required=False)
    argsParser.add_argument(
        "--servers", dest="servers", help="List of name servers.", default="i*", required=False)
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

 
