#!/bin/bash

#python savedata-backup.py $*

python savedata-restore.py $*

#duplicity  file:////var/backups/savedata/backups/s1/pgsql /home/romario/tmp/savedata/restore