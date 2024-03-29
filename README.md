==Description##
Simple backup automation utility for Ubuntu distributive.


##Installation##

```
#!bash
git clone git@bitbucket.org:iu-sysutils/sysutils.savedata.git
cd sysutils.savedata/build 
sudo dpkg -i savedata_0.04~beta_all.deb
```

##Examples##
```
#!bash 
sudo su

#create backup
savedata-backup -b /etc/savedata/backups.yml -s /etc/savedata/servers.yml --debug

#create backup(only to 'yandex' server)
savedata-backup -b /etc/savedata/backups.yml      -s /etc/savedata/servers.yml --servers=i'yandex'

#create backup for 'docs' (only to 'yandex' server)
savedata-backup -b /etc/savedata/home-backups.yml -s /etc/savedata/servers.yml --servers=i'yandex' --backups=i'docs'

# show status of backups
savedata-restore  /etc/savedata/servers.yml --server_name 's1' --backup_name 'pgsql' --status

# restore data 
savedata-restore --server_name 's1' --backup_name 'gitreps' --status --debug --restore_path /home/user1/tmp/gitreps/
```

##Advice##
* For openshift backups:
1. At first, you must install rhc;
2. for open rhc without password, read https://help.openshift.com/hc/en-us/articles/202399230-Running-rhc-commands-without-re-entering-password
3. backups.yml block example:


```
#!YAML 
backups:
    ....
    rhc-apps:
        type        : 'rhc'
        <<          : *base
        apps        : ['redmine', 'nexus', 'wiki']
    ....
```
