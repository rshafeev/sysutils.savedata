import os
import os.path
import argparse
import codecs
import logging
import shutil
import subprocess

def dump(conf):
    logging.info('create pgsql dumps...')
   
    backups = conf["source"]["backups"]
    session = conf["session"]
    
    for key in backups:
       if backups[key]["type"] == "pgsql":
            pgsql_path ="%s/%s" % (session["spath"], key)
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