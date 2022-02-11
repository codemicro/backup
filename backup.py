import subprocess
import os
import datetime
import json

datestring = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d_%Hh%Mm")

filename = f"server_{datestring}.tar.gz"
to_backup = None
with open(os.path.join(os.path.expandvars("$HOME"), "backupConfig.json")) as f:
    to_backup = json.load(f)

subprocess.run(['tar', '-czvf', filename,] + to_backup)
subprocess.run(['rclone', 'copy', "-v", filename, 'gd:/server'])
os.remove(filename)
subprocess.run(['rclone', 'delete', "-v", '--min-age', '15d', 'gd:/server'])
