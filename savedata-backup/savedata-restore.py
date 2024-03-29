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
import tarfile
import gitlab
import app

#======= Global constants  =======
m_desc = "Simple backup automation utility for Linux distributive."
m_version = "SaveData version: 0.02~beta"

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



def parseConfigs(serversFName):
    dest   = app.parseYamlFile(serversFName)
    conf   = {}
    conf["dest"] = dest
    return conf


def find_server(conf):
    servers = conf["dest"]["servers"]
    for destKey in servers:
       if destKey == conf["server_name"]:
            return servers[destKey]
    msg = "Can not find server-conf with name '%s'. Please, check configuration files and input params and try agan" % (conf["server_name"])
    raise Exception(msg)  

def show_status(conf):
    logging.info("Showing backup status...")
    server = find_server(conf)
    duplicity_cmd = "collection-status "
    server_url = app.buildServerURL(server)
    cmd = "duplicity --ssl-no-check-certificate %s %s/%s" % (duplicity_cmd, server_url, conf["backup_name"])
    output, errors =  subprocess.Popen(cmd,shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()
    if output:
        logging.info(output)
    if errors:
        logging.error(errors)
        raise Exception('Can not show backup-status. Please, check configuration files and input params and try agan.')  

def prepareRestoryPath(restore_path):
    if not os.path.isdir(restore_path):
        try:
            os.makedirs(restore_path)
        except OSError:
            raise Exception("Can not create path for restore data. Please, check input params")  

    if len(os.listdir(restore_path)) > 0:
        while True:
            question = raw_input("Restore path is not empty. Do you want rewrite restore path or exit program? Y/N: ")
            if len(question) > 0:
                answer = question.upper()
                if answer == "Y":
                    try:
                        shutil.rmtree(restore_path, ignore_errors=True)
                        os.makedirs(restore_path)
                    except OSError:
                        raise Exception("Can not clean restory path")  
                    break
                elif answer == "N":
                    raise Exception('Restore path is not empty.')   
                    break


def restore(conf, restore_path, opts):
    if not restore_path:
        return
    prepareRestoryPath(restore_path)
    server = find_server(conf)
    server_url = app.buildServerURL(server)

    cmd = "duplicity %s %s/%s %s" % (opts, server_url, conf["backup_name"], restore_path)
    output, errors =  subprocess.Popen(cmd,shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()
    if output:
        logging.info(output)
    if errors:
        logging.error(errors)
        raise Exception('Can not show backup-status. Please, check configuration files and input params and try agan.')    
    gitlab.restore(restore_path)
    

def main(args):
    global gconf
    global session
    global env_mode
    global env

    # setup utility-settings and prepare paths and sys files for working. Function return global configuration settings
    gconf,env,env_mode = app.prepare(args.debug,"savedata-restore.log")
    # read and parse data from configuration file (backups.json and servers.json)
    conf = parseConfigs(args.servers_fname)
    conf["server_name"] = args.server_name
    conf["backup_name"] = args.backup_name
    if args.backup_status is True:
        show_status(conf)

    restore(conf, args.restore_path, args.dyplicity_options)
    return


def prepare_argsParser():
    argsParser = argparse.ArgumentParser(
        version=m_version, fromfile_prefix_chars='@', description=m_desc, formatter_class=argparse.RawTextHelpFormatter)
    argsParser.add_argument(
        "-s", "--servers", dest="servers_fname", help="Configuration file with destination settings, in which you storaged backups (ymal format).",
        default="/etc/savedata/servers.yml", required=False)
    argsParser.add_argument(
         "--server_name", dest="server_name", help="[REQUIRED]. Name of server(set in conf. file).",
        default="dest", required=True)
    argsParser.add_argument(
        "-b", "--backup_name", dest="backup_name", help="[REQUIRED]. Name of backup.",
        default="local", required=True)
    argsParser.add_argument( "--restore_path", dest="restore_path", help="Path where do you want restore data", default="")
    argsParser.add_argument("--status", dest="backup_status", help="Show status of selected backup",action='store_true', default=False)
    argsParser.add_argument("-o", "--options", dest="dyplicity_options", help="Options of duplicity", default="")
    argsParser.add_argument("--debug", dest="debug", help="Output debug information into console", action='store_true', default=False)
    return argsParser

def start_app():
    app.console_configure()
    argsParser = prepare_argsParser()
    try:
        main(argsParser.parse_args())
        logging.info("FINISH. OK. ")
    except Exception as e:
        logging.error(e)
        logging.debug(traceback.format_exc())
        logging.warning("FAILED.")
       
start_app()

 
