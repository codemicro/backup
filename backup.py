import subprocess
import os
import datetime
import json
import sys

CONFIG_FILE = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.expandvars("$HOME"), "backupConfig.json")

datestring = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d_%Hh%Mm")

with open(CONFIG_FILE) as f:
    config = json.load(f)

filename = config.get("filenameTemplate", "backup_{}.tar.gz").format(datestring)

subprocess.run(['tar', '-czvf', filename] + config.get("files", []))
subprocess.run(['rclone', 'copy', "-v", filename, 'gd:/server'])
os.remove(filename)
subprocess.run(['rclone', 'delete', "-v", '--min-age', '15d', 'gd:/server'])
