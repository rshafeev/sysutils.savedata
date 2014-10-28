import os
import os.path
import argparse
import codecs
import logging
import shutil
import subprocess
import tarfile

## read https://help.openshift.com/hc/en-us/articles/202399230-Running-rhc-commands-without-re-entering-password

def extractTarFile(tarFile, extractPath):
    # open the tar file
    tfile = tarfile.open(tarFile)
    if tarfile.is_tarfile(tarFile):
        # list all contents
        # extract all contents
        tfile.extractall(extractPath)
        tfile.close()
    else:
        tfile.close()
        msg = tarFile + " is not a tarfile."
        raise Exception(msg)


def dump(conf):
    logging.info('create rhc dumps...')
   
    backups = conf["source"]["backups"]
    session = conf["session"]
    
    for key in backups:
       if backups[key]["type"] == "rhc":
            apps =  backups[key]["apps"]
            rhc_path ="%s/%s" % (session["spath"], key)
            for app_name in apps:
                if not os.path.isdir(rhc_path + "/" + app_name):
                    try:
                        os.makedirs(rhc_path + "/" + app_name)
                    except OSError:
                        raise Exception("Can not create path for saving rhc dump. Please, check configuration file")  

                logging.info('rhc app \'%s\' is dumping...', app_name)
                appDump = rhc_path + "/" + app_name + ".tar.gz"
                cmd = "rhc snapshot save -a %s -f %s" % (app_name, appDump)
                output, errors =  subprocess.Popen(cmd,shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()
                logging.debug(output)
                if errors:
                    logging.error(errors)
                    raise Exception('Can not create dump. Please, check configuration file and try agan.')  
                extractTarFile(appDump, rhc_path + "/" + app_name)
                os.remove(appDump)
                logging.info('rhc app \'%s\' was dumped. OK.', app_name) 
    logging.info('created rhc dumps. OK.')