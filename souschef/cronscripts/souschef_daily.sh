#!/bin/bash
set -ex

# Export the Sous-Chef configuration variables, so Django's
# manage.py may work.
for line in `cat /etc/souschef.conf`; do export $line; done

MANAGE_CMD="/opt/pipx/venvs/gunicorn/bin/python /opt/pipx/venvs/gunicorn/lib/python3.13/site-packages/souschef/manage.py"

$MANAGE_CMD processscheduledstatuschange 2>&1 | tee /var/log/souschef.processscheduledstatuschange.log
$MANAGE_CMD setordersdelivered $(date --date="yesterday" +"%Y-%m-%d") 2>&1 | tee /var/log/souschef.setordersdelivered.log
