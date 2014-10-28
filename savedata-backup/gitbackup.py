import os
import os.path
import argparse
import codecs
import logging
import shutil
import subprocess

def dump(conf):
    logging.info('create git dumps...')
   
    backups = conf["source"]["backups"]
    session = conf["session"]
    
    for key in backups:
       if backups[key]["type"] == "git":
            git_path ="%s/%s" % (session["spath"], key)
            if not os.path.isdir(git_path):
                try:
                    os.makedirs(git_path)
                except OSError:
                    raise Exception("Can not create path for saving git dumps. Please, check configuration file")  
            user = backups[key]["user"]
            host = backups[key]["host"]
            reps = backups[key]["reps"]
            for rep in reps:
                logging.info('repository %s is cloning...', rep)
                rep_url = "%s@%s:%s" % (user, host, rep)
                cmd = ["/usr/bin/git", "clone", "--mirror", rep_url]
                logging.debug(cmd)
                out,err =  subprocess.Popen(cmd,cwd=git_path, stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()
                logging.debug(err)
                if err.find("error") >0 or err.find("fatal") >0:
                  logging.error(err)
                  raise Exception('Can not clone repository. Please, check configuration file and try agan.') 
                logging.info('repository %s was clonned. OK.', rep)

    logging.info('created pgsql dumps. OK.')