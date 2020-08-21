# -*- coding: utf-8 -*-

"""Overview:
    telnet/ssh client with continuous command execution and automatic log saving function by Python3.
Usage:
    pyTelnetCmdExec.py <cmdlist_file> [--log_dir <logdir_path>] [--disable_log] [-h|--help]

Options:
    --log_dir <logdir_path>  : Specify the log output destination directory.(default="./log/")
    --disable_log            : Do not output log file.
    -h, --help               : Show this help message and exit.
"""

import datetime
import docopt
import os
import paramiko
import paramiko_expect
import re
import sys
import telnetlib

class ConnectionInformation:
    def __init__(self, ipaddr, port, username, passwd, timeout):
        self.ipaddr = ipaddr
        self.port = port
        self.username = username
        self.passwd = passwd
        self.timeout = timeout

def main():
    args = docopt.docopt(__doc__)
#   print(args)

    if args["<cmdlist_file>"]:
        if not os.path.exists(args["<cmdlist_file>"]):
            print("{0} is not exist.".format(args["<cmdlist_file>"]))
            exit(1)
        cmdlist_file_path = args["<cmdlist_file>"]

    logdir_path = "./log/"
    if args["--log_dir"]:
        logdir_path = args["--log_dir"].replace("\\", "/")

    disable_log_output = False
    if args["--disable_log"]:
        disable_log_output = True

    # read command list file.
    lines = read_cmdlist_file(cmdlist_file_path)

    # Set of standby prompt characters
    prompts = [b">$", b"> $", b"#$", b"# $", b"\\$$", b"\\$ $", b"%$", b"% $", b"[Pp]assword: $", b"login: $", b"name: $"]

    # Read connection information.
    cn = set_ConnectionInformation(lines, timeout=2)
    if cn.ipaddr == "":
        print("no ipaddr in {0}".format(cmdlist_file_path))
        exit(0)

    # Execute command list.
    if cn.port == "22":
        if cn.username == "":
            print("no username in {0}".format(cmdlist_file_path))
            exit(0)
        if cn.passwd == "":
            print("no password in {0}".format(cmdlist_file_path))
            exit(0)
        # SSH
        cmdlist_exec_ssh(lines, cn, prompts, disable_log_output, logdir_path)
    else:
        # TELNET
        cmdlist_exec_telnet(lines, cn, prompts, disable_log_output, logdir_path)

def read_cmdlist_file(cmdlist_filename):
    """
    Read command list file.
    """
    contents = None
    encodings = ["ascii", "sjis", "utf8"]
    for enc in encodings:
        # Read the contents of a file.
        try:
            f = open(cmdlist_filename, "rt", encoding=enc)
            contents = f.readlines()
            f.close
            break
        except:
            continue
    return contents

def set_ConnectionInformation(lines, timeout):
    """
    Read connection information.
    """
    cn = ConnectionInformation("", "", "", "", timeout)
    count = 0
    for line in lines:
        # Delete comment section.
        line = re.sub('#.*\n', "", line)
        line = re.sub('//.*\n', "", line)
        line = line.strip()
        if len(line) == 0:
            continue
        if count == 0:
            if ":" in line:
                flds = line.split(":")
                if len(flds) > 1:
                    cn.ipaddr = flds[0]
                    flds1 = flds[1].split(",")
                    cn.port = flds1[0]
                    if len(flds1) > 1:
                        cn.username = flds1[1]
                        cn.passwd = flds1[2]
                if cn.ipaddr == "":
                    break
        elif count > 0:
            break
    return cn

def print_and_append(buffer, outputString):
    """
    print and append to list output string.
    """
    print(outputString, end="")
    if buffer != None:
        buffer.append(outputString)

def connect_telnet(cn, prompts):
    """
    Start telnet connection.
    """
    responseLog = []
    tn = telnetlib.Telnet(cn.ipaddr, cn.port, cn.timeout)

    if tn == None:
        return None

    if cn.username != "":
        # Wait for username prompt.
        response = tn.read_until(b': ', cn.timeout)
        print_and_append(responseLog, response.decode())

        # Send Username
        tn.write(cn.username.encode() + b"\n")
        print_and_append(responseLog, cn.username + "\n")

        # Wait for password prompt.
        response = tn.read_until(b': ', cn.timeout)
        print_and_append(responseLog, response.decode())

        # Send password
        tn.write(cn.passwd.encode() + b"\n")
        print_and_append(responseLog, cn.passwd + "\n")

        # Wait for prompt.
        response = tn.expect(prompts, timeout=cn.timeout)
        if response[0] == -1:
            return None, responseLog

        print_and_append(responseLog, response[2].decode())
    else:
        # Wait for password prompt.
        response = tn.read_until(b': ', cn.timeout)
        print_and_append(responseLog, response.decode())

    return tn, responseLog

def detect_promptString(decoded_response):
    """
    detect prompt string.
    """
    if "MacBook" in decoded_response:
        lines = decoded_response.split("\n")
        for line in lines:
            for fld in line.split(" "):
                if "@" in fld:
                    return fld
    pos0 = decoded_response.rfind("\n")
    workLine = decoded_response[pos0 + 1:]
    prompt_chars = [">", "#", "$", "@", "%"]
    prompt_preStr = None
    for ch in prompt_chars:
        pos = workLine.find(ch)
        if pos > 0:
            prompt_preStr = workLine[:pos]
            break
    return prompt_preStr

def set_output_filename(prompt_preStr, cn, logdir_path):
    """
    set log output filename.
    """
    prompt_preStr = remove_prohibited_characters(prompt_preStr)
    dtStr = datetime.datetime.now().strftime('_%Y%m%d_%H%M%S')

    if not os.path.exists(logdir_path):
        os.makedirs(logdir_path)

    if logdir_path[-1] != "/":
        logdir_path += "/"
    output_filename = logdir_path + prompt_preStr + "_" + cn.ipaddr + dtStr + ".log"

    return output_filename

def remove_prohibited_characters(prompt_preStr):
    """
    Remove prohibited characters.
    """
    prohibited_chars = ["[", "]", "<", ">", "#", "%", "$", ":", ";", "~"]
    for ch in prohibited_chars:
        prompt_preStr = prompt_preStr.replace(ch, "")
    return prompt_preStr

def print_and_write(outputString, wf, responseLog, enable_removeLF):
    """
    Write to stdout and file.
    """
    print(outputString, end="")
    if wf != None:
        if enable_removeLF:
            wf.write(outputString.replace("\n", ""))
        else:
            wf.write(outputString)
    elif responseLog != None:
        responseLog.append(outputString)

def telnet_eager(tn, wf, responseLog, enable_removeLF):
    """
    Dealing with unread material.
    """
    if tn.eof == True:
        return
    response = tn.read_eager()
    if len(response) > 0:
        print_and_write(response.decode(), wf, responseLog, enable_removeLF)

def cmdlist_exec_telnet(lines, cn, prompts, disable_log_output, logdir_path):
    """
    Execute command list(TELNET)
    """
    # Start TELNET connection
    tn, responseLog = connect_telnet(cn, prompts)
    if tn == None:
        print("loggin failed to {0}".format(cn.ipaddr))
        exit(0)

    wf, prompt_preStr, prompt_preStr_Regulars = None, None, None
    count = 0
    for line in lines:
        # Delete comment section.
        line = re.sub('#.*\n', "", line)
        line = re.sub('//.*\n', "", line)
        line = line.rstrip()

        if count == 0:
            if ":" in line:
                count += 1
                continue
            elif len(line) == 0:
                continue

        # Dealing with unread material.
        telnet_eager(tn, wf, responseLog, enable_removeLF=True)

        # command send.
        tn.write(line.encode() + b"\n")
        count += 1

        if prompt_preStr == None:
            res = tn.expect(prompts, timeout=cn.timeout)
        elif prompt_preStr_Regulars != None:
            # repeat send space for "--More--".
            while True:
                res = tn.expect(prompt_preStr_Regulars, timeout=cn.timeout)
                if res[0] < 2:
                    break

                """
                --More--
                """
                # Write to stdout and file.
                decoded_response = res[2].decode()
                print_and_write(decoded_response, wf, responseLog, enable_removeLF=True)

                # Send Space.
                tn.write(b" ")
        else:
            res = tn.expect(prompts, timeout=cn.timeout)

        # Convert byte to string.
        response = res[2]
        decoded_response = response.decode()

        if prompt_preStr == None:
            # prompt string detection
            prompt_preStr = detect_promptString(decoded_response)

            if prompt_preStr != None and disable_log_output == False:
                # logfile open.
                wf = open(set_output_filename(prompt_preStr, cn, logdir_path), mode='wt')

                # Write responseLog to file.
                for buf in responseLog:
                    wf.write(buf.replace("\n", ""))
                responseLog = None
                prompt_preStr_Regulars = [b"\n" + prompt_preStr.encode() + b"[#>%\\$\\(].*$", b"[Pp]assword: ", b"\n --[Mm]ore--.*$", "\n--続きます--.*$".encode(encoding="utf8") ]

        # Write to stdout and file.
        print_and_write(decoded_response, wf, responseLog, enable_removeLF=True)

    # Dealing with unread material.
    telnet_eager(tn, wf, None, enable_removeLF=True)

    if tn != None:
        tn.close()
    if wf != None:
        wf.close()

    return

def cmdlist_exec_ssh(lines, cn, prompts, disable_log_output, logdir_path):
    """
    Execute command list(SSH)
    """
#   PROMPTS = [prompt_byte.decode() for prompt_byte in prompts]
#   prompts = [".*>\s*", ".*#\s*", ".*\$\s*", ".*@.*\n\~.*", ".*assword:\s*"]
    prompts = [".*>\s*", ".*#\s*", ".*\$\s*", ".*@.*", ".*%.*", ".*[Pp]assword:\s*"]

    # Start SSH connection
    error_count = 0
    while True:
        try:
            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.WarningPolicy())
            client.connect(cn.ipaddr, username = cn.username, password = cn.passwd)
            interact = paramiko_expect.SSHClientInteraction(client, buffer_size = 10*1024*1024, timeout = cn.timeout, display = False)
            index = interact.expect(prompts, timeout=4)
        except:
            error_count += 1
            if error_count >= 3:
                exit(0)
        else:
            break

    # Write to stdout and file.
    responseLog = []
    print_and_write(interact.current_output, None, responseLog, enable_removeLF=False)

    # prompt string detection
    wf = None
    prompt_preStr = detect_promptString(interact.current_output)
    prompt_preStr_Regulars = [prompt_preStr + "[#>%\\$\\(].*", "[Pp]assword:\s*", ".*\n --[Mm]ore--\s*", ".*\n--続きます--\s*"]
    if prompt_preStr != None and disable_log_output == False:
        # logfile open.
        wf = open(set_output_filename(prompt_preStr, cn, logdir_path), mode='wt')

        # Write responseLog to file.
        for buf in responseLog:
            wf.write(buf)
        responseLog = None

    count = 0
    for line in lines:
        # Delete comment section.
        line = re.sub('#.*\n', "", line)
        line = re.sub('//.*\n', "", line)
        line = line.rstrip()

        if len(line) == 0:
            continue
        if count == 0 and ":" in line:
            count += 1
            continue

        # command send.
        interact.send(line)
        count += 1

        try:
            if prompt_preStr == None:
                index = interact.expect(prompts)
            else:
                # repeat send space for "--More--".
                while True:
                    index = interact.expect(prompt_preStr_Regulars)
                    if index < 2:
                        break

                    """
                    --More--
                    """
                    # Write to stdout and file.
                    print_and_write(interact.current_output, wf, responseLog, enable_removeLF=False)

                    # Send Space.
                #   interact.send(" ", newline="")
                    interact.channel.send(" ")

        except:
        #   print("except occured.")
            pass

        # Write to stdout and file.
        print_and_write(interact.current_output, wf, responseLog, enable_removeLF=False)

    if interact != None:
        interact.close()
    
    if wf != None:
        wf.close()

    return

if __name__ == '__main__':
    main()
