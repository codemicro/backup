import subprocess
import os
import datetime
import json
import sys
import smtplib
import ssl
from email.message import EmailMessage
import traceback


"""
Sample config JSON file
{
    "filenameTemplate": "server_{}.tar.gz",
    "smtp": {
        "server": "smtp.sendgrid.net",
        "port": 587,
        "to": "you@gmail.com",
        "from": "sender@example.com",
        "username": "apikey",
        "password": "yourapikey"
    },
    "files": [
        "hi.txt"
    ]
}
"""


CONFIG_FILE = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.expandvars("$HOME"), "backupConfig.json")

datestring = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d_%Hh%Mm")

with open(CONFIG_FILE) as f:
    config = json.load(f)


def send_email(subject: str, content: str):
    if len(config["smtp"]) == 0:
        return

    msg = EmailMessage()
    msg.set_content(content)
    msg['Subject'] = subject
    msg['From'] = config["smtp"]["from"]
    msg['To'] = config["smtp"]["to"]

    context = ssl.create_default_context()
    with smtplib.SMTP(config["smtp"]["server"], config["smtp"]["port"]) as server:
        server.ehlo()
        server.starttls(context=context)
        server.ehlo()
        server.login(config["smtp"]["username"], config["smtp"]["password"])
        server.send_message(msg)


def run(*args: str):
    p = subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    if p.returncode != 0:
        msg = f"Failed to run command `{' '.join(args)}`: exited with return code {p.returncode}.\nThe program has been aborted.\nBelow is the output of the failing command.\n\n"
        msg += p.stdout.decode()
        send_email(f"Failed to run backups on {datestring}", msg)
        sys.exit(1)


filename = config.get("filenameTemplate", "backup_{}.tar.gz").format(datestring)

run('tar', '-czvf', filename, *config.get("files", []))
run('rclone', 'copy', "-v", filename, 'gd:/server')
try:
    os.remove(filename)
except Exception as e:
    msg = f"Failed to delete file `{filename}`: {str(e)}.\nThe program has been aborted.\nBelow is the stacktrace.\n\n"
    msg += traceback.format_exc()
    send_email(f"Failed to run backups on {datestring}", msg)
    sys.exit(1)
run('rclone', 'delete', "-v", '--min-age', '15d', 'gd:/server')
