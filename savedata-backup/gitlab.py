import os
import os.path
import argparse
import codecs
import logging
import shutil
import glob
import tarfile
import subprocess
import app

def compare(a, b):
        return cmp(0 - int(a["timestamp"]), 0-int(b["timestamp"])) # compare as integers

def getLastBackup(path):
    tars = []
    for fullFileName in glob.iglob(path + "/*_gitlab_backup.tar"): 
        path, fname = os.path.split(fullFileName)
        timestamp = fname.replace('_gitlab_backup.tar', '')
        gitlab_backup = {
                   'timestamp' : int(timestamp),
                   'filename'  : fullFileName,
                   'splitname' : fname
        }
        tars.append(gitlab_backup)
        tars.sort(compare)
        return tars[0]
    return None

def restore_gitlab(archive_fname, gitlab_backup_info):
    logging.info("gitlab was restoring ...")
    cmd = "mv %s %s" % (archive_fname, gitlab_backup_info["backup-path"])
    output, errors =  subprocess.Popen(cmd,shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()
    if output:
        logging.info(output)
    if errors:
        logging.error(errors)
        msg = 'Can not send dump tar-file to backup directory %s' % (gitlab_backup_info["backup-path"])
        raise Exception(msg)

    user = gitlab_backup_info["run-as-user"]
    home_path = gitlab_backup_info["home"]
    env = gitlab_backup_info["env"]
    timestamp = gitlab_backup_info["timestamp"]
    backup_cmd = "cd %s && bundle exec rake gitlab:backup:restore RAILS_ENV=%s BACKUP=%s" % (home_path, env, timestamp)
    cmd = "su - %s -c '%s'" % (user, backup_cmd)
    os.system(cmd)
    logging.info("gitlab was restored. OK.")


def restore(restore_path):
    EXCLUDE_FILES = ['.savedata.gitlab.yml']
    fname = ".savedata.gitlab.yml"
    infoFileName = ("%s/%s") % (restore_path, fname)    
    if os.path.isfile(infoFileName):
        # get gitlab_backup_info
        gitlab_backup_info = app.parseYamlFile(infoFileName)
        archive_fname = "%s/%s" % (restore_path, gitlab_backup_info["splitname"])
        # make archive
        archive = tarfile.open(archive_fname, "w")
        archive.add(restore_path, arcname="", filter=lambda x: None if x.name in EXCLUDE_FILES else x)
        archive.close()
        
        # try restory Gitlab 
        while True:
            question = raw_input("Do you want restory GitLab? Y/N: ")
            if len(question) > 0:
                answer = question.upper()
                if answer == "Y":
                    try:
                        restore_gitlab(archive_fname, gitlab_backup_info)
                    except OSError:
                        raise Exception("Can not estory gitlab")  
                    break
                elif answer == "N":
                    break


def saveGitLabInfo(gitlab_path, data):
    fname = ".savedata.gitlab.yml"
    fullName = ("%s/%s") % (gitlab_path, fname)
    app.saveToYamlFile(fullName, data)


def extractTarFile(tarFile, extractPath):
    # open the tar file
    tfile = tarfile.open(tarFile)
    if tarfile.is_tarfile(tarFile):
        # list all contents
        # extract all contents
        tfile.extractall(extractPath)
    else:
        msg = tarFile + " is not a tarfile."
        raise Exception(msg)

def makeGitlabBackup(backup):
    user = backup["run-as-user"]
    home_path = backup["home"]
    env = backup["env"]
    backup_cmd = "cd %s && bundle exec rake gitlab:backup:create RAILS_ENV=%s" % (home_path, env)
    cmd = "su - %s -c '%s'" % (user, backup_cmd)
    output, errors =  subprocess.Popen(cmd,shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()
    if output:
        logging.info(output)
    if errors:
        logging.error(errors)
        raise Exception('Can not create dump. Please, check configuration file and try agan.')   


def dump(conf):
    logging.info('create gitlab dumps...')
    backups = conf["source"]["backups"]
    session = conf["session"]
     
    for key in backups:
       if backups[key]["type"] == "gitlab":
            backup_path = backups[key]["backup-path"]
            gitlab_path ="%s/%s" % (session["spath"], key)
            makeGitlabBackup(backups[key])

            gitlab_backup_info = getLastBackup(backup_path)
            gitlab_backup_info["run-as-user"] = backups[key]["run-as-user"]
            gitlab_backup_info["env"]         = backups[key]["env"]
            gitlab_backup_info["home"]        = backups[key]["home"]
            gitlab_backup_info["backup-path"] = backups[key]["backup-path"]

            extractTarFile(gitlab_backup_info["filename"], gitlab_path)
            saveGitLabInfo(gitlab_path, gitlab_backup_info)
            os.remove(gitlab_backup_info["filename"])
            continue
    logging.info('created gitlab dumps. OK.')


