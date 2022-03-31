import datetime
import json
import os
import platform
import smtplib
import ssl
import subprocess
import sys
import traceback
from email.message import EmailMessage
import time

"""
Sample config JSON file

{
    "filenameTemplate": "server_{}.tar.gz",
    "remoteOutputLocation": "gd:/server",
    "deleteOlderThanDays": 14,
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
    ],
    "messageFile": "messages.json"
}
"""


CONFIG_FILE = (
    sys.argv[1]
    if len(sys.argv) > 1
    else os.path.join(os.path.expandvars("$HOME"), "backupConfig.json")
)

datestring = datetime.datetime.utcnow().strftime("%Y-%m-%d_%Hh%Mm")

with open(CONFIG_FILE) as f:
    config = json.load(f)


def send_email(subject: str, content: str):
    if len(config["smtp"]) == 0:
        return

    msg = EmailMessage()
    msg.set_content(content)
    msg["Subject"] = subject
    msg["From"] = config["smtp"]["from"]
    msg["To"] = config["smtp"]["to"]

    context = ssl.create_default_context()
    with smtplib.SMTP(config["smtp"]["server"], config["smtp"]["port"]) as server:
        server.ehlo()
        server.starttls(context=context)
        server.ehlo()
        server.login(config["smtp"]["username"], config["smtp"]["password"])
        server.send_message(msg)


class RunException(Exception):
    pass


def run(*args: str):
    p = subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    if p.returncode != 0:
        msg = f"Failed to run command `{' '.join(args)}`: exited with return code {p.returncode}.\nBelow is the output of the failing command.\n\n"
        msg += p.stdout.decode()
        raise RunException(msg)


def do_backup():
    filename = config.get("filenameTemplate", "backup_{}.tar.gz").format(datestring)
    remote_output_location = config["remoteOutputLocation"]
    delete_threshold = config["deleteOlderThanDays"] + 1

    run("tar", "-czvf", filename, *config.get("files", []))
    run("rclone", "copy", "-v", filename, remote_output_location)
    os.remove(filename)

    run(
        "rclone",
        "delete",
        "-v",
        "--min-age",
        f"{delete_threshold}d",
        remote_output_location,
    )


def publish_message(filepath: str, subject: str, content: str):
    try:
        with open(filepath) as f:
            messages = json.load(f)
    except FileNotFoundError:
        messages = []

    if len(messages) >= 10:
        messages = messages[-9:]

    messages.append({"time": int(time.time()), "subject": subject, "content": content})

    with open(filepath, "w") as f:
        json.dump(messages, f)


def main():
    exception = None
    try:
        do_backup()
        pass
    except Exception as e:
        exception = e

    ok = True
    message = (
        f"Date: {datestring}\n"
        f"Host: {platform.node()}\n"
        f"remoteOutputLocation: {config.get('remoteOutputLocation')}\n"
        f"deleteOlderThanDays: {config.get('deleteOlderThanDays')}\n"
        f"Files: \n"
    )
    message += "\n".join(map(lambda x: f"    * {x}", config.get("files", ["None"])))
    message += "\n\n"

    if exception is not None:
        ok = False
        if type(exception) == RunException:
            message += str(exception)
        else:
            message += f"Unrecognised exception caught: {str(exception)}.\nBelow is the stacktrace.\n\n"
            message += "".join(traceback.format_tb(exception.__traceback__))
    else:
        message += "No errors reported."

    send_email(f"Backup: {'OK' if ok else 'ERRORED'} on {datestring}", message)

    if (filename := config.get("messageFile", None)) is not None:
        publish_message(filename, f"Backup {'OK' if ok else 'ERRORED'}", message)


if __name__ == "__main__":
    main()
