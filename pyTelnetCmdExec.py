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
import re
import sys
import telnetlib
import time

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
    return cn

def print_and_append(buffer, outputString):
    """
    print and append to list output string.
    """
    print(outputString, end="")
    if buffer != None:
        buffer.append(outputString)

def connect_telnet_from_connectionInformation(cn, prompts):
    """
    Start telnet connection.
    """
    current_output_log = []
    tn = telnetlib.Telnet(cn.ipaddr, cn.port, cn.timeout)

    if tn == None:
        return None, None

    if cn.username != "":
        # Wait for username prompt.
        current_output = tn.read_until(b': ', cn.timeout)
        print_and_append(current_output_log, current_output.decode())

        # Send Username
        tn.write(cn.username.encode() + b"\n")
        print_and_append(current_output_log, cn.username + "\n")

        # Wait for password prompt.
        current_output = tn.read_until(b': ', cn.timeout)
        print_and_append(current_output_log, current_output.decode())

        # Send password
        tn.write(cn.passwd.encode() + b"\n")
        print_and_append(current_output_log, cn.passwd + "\n")

    else:
        # Wait for password prompt.
        current_output = tn.read_until(b': ', cn.timeout)
        print_and_append(current_output_log, current_output.decode())

    # Wait for prompt.
    current_output = tn.expect(prompts, timeout=4)
    decoded_current_output = decode(current_output[2])
    print_and_append(current_output_log, decoded_current_output)

    return tn, current_output_log

def connect_telnet_from_lines(cn, lines, prompts):
    """
    Start telnet connection.
    """
    current_output_log = []
    tn = telnetlib.Telnet(cn.ipaddr, cn.port, cn.timeout)

    if tn == None:
        return None, None

    current_output = tn.expect(prompts, timeout=4)
    decoded_current_output = decode(current_output[2])
    print_and_append(current_output_log, decoded_current_output)

    line_count = 0
    for i in range(len(lines)):
        # Delete comment section.
        line = re.sub('#.*\n', "", lines[i])
        line = re.sub('//.*\n', "", line)
        line = line.rstrip()

        if line_count == 0:
            if len(line) == 0:
                continue
            if ":" in line:
                line_count += 1
                continue

        elif line_count == 1:
            # Send Username or Passwd
            tn.write(line.encode() + b"\n")

            # Wait for prompt.
            try:
                current_output = tn.expect(prompts, timeout=4)
            except:
                pass
            decoded_current_output = decode(current_output[2])
            print_and_append(current_output_log, decoded_current_output)

            if current_output[0] < 8:
                break
            else:
                line_count += 1
                continue

        elif line_count == 2:
            # Send password
            tn.write(line.encode() + b"\n")

            try:
                current_output = tn.expect(prompts, timeout=4)
            except:
                tn.close()
                return None, None

            decoded_current_output = decode(current_output[2])
            print_and_append(current_output_log, decoded_current_output)

            if current_output[0] < 8:
                break
            else:
                tn.close()
                return None, None

    # Wait for prompt.
    decoded_current_output = decode(current_output[2])
    print_and_append(current_output_log, decoded_current_output)

    return tn, current_output_log, lines[i + 1:]

def detect_promptString(decoded_current_output):
    """
    detect prompt string.
    """
    """
    if "\x1b" in decoded_current_output:
        # for powerline.
        workStr = re.sub("\x1b.*m", "", decoded_current_output)
    else:
        workStr = decoded_current_output
    """
    lines = decoded_current_output.split("\n")
    lastLine = lines[-1]

    prompt_chars = ["~", ">", "#", "$", "@", "%", "/"]
    prompt_preStr = None

    for ch in prompt_chars:
        pos = lastLine.find(ch)
        if pos > 0:
            prompt_preStr = lastLine[:pos]
            break

    if prompt_preStr == None and len(lines) > 2:
        lastLine = lines[-2]
        for ch in prompt_chars:
            pos = lastLine.find(ch)
            if pos > 0:
                prompt_preStr = lastLine[:pos]
                break

    if prompt_preStr != None:
        prompt_preStr = re.sub("\x1b.*m", "", prompt_preStr)

    return prompt_preStr

def lastline_pattern_match(decoded_current_output, patterns):
    """
    detect prompt string.
    """
    lastLine = decoded_current_output.split("\n")[-1]
    for i in range(len(patterns)):
        res = re.match(patterns[i], lastLine)
        if res != None:
            return i
    return -1

def decode(current_output):
    """
    bytes to str
    """
    encodings = ["sjis", "utf8", "ascii"]
    decoded_current_output = ""
    for enc in encodings:
        try:
            decoded_current_output = current_output.decode(enc)
            break
        except:
            continue
    return decoded_current_output

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
    prohibited_chars = ["[", "]", "<", ">", "#", "%", "$", ":", ";", "~", "\r", "\n"]
    for ch in prohibited_chars:
        prompt_preStr = prompt_preStr.replace(ch, "")
    return prompt_preStr

def telnet_read_all(tn, wf, current_output_log, enable_removeLF):
    """
    Dealing with unread material.
    """
    try:
        current_output = tn.read_all()
    except:
        current_output = ""

    decoded_current_output = decode(current_output)
    if len(current_output) > 0:
        if enable_removeLF:
            print_and_write(decoded_current_output, wf, current_output_log, string_remove = "\n")
        else:
            print_and_write(decoded_current_output, wf, current_output_log, string_remove = "")
    return decoded_current_output

def telnet_read_eager(tn, wf, current_output_log, enable_removeLF):
    """
    Dealing with unread material.
    """
    """
    if tn.eof == True:
        return ""
    """
    current_output = tn.read_eager()
    decoded_current_output = decode(current_output)
    if len(current_output) > 0:
        if enable_removeLF:
            print_and_write(decoded_current_output, wf, current_output_log, string_remove = "\n")
        else:
            print_and_write(decoded_current_output, wf, current_output_log, string_remove = "")
    return decoded_current_output

def print_and_write(outputString, wf, current_output_log, string_remove):
    """
    Write to stdout and file.
    """
    print(outputString, end="")
    if wf != None:
        try:
            if len(string_remove) > 0:
                wf.write(outputString.replace(string_remove, ""))
            else:
                wf.write(outputString)
        except Exception as e:
            print("\n{0}e".format(e))
        #   wf.write(e)

    elif current_output_log != None:
        current_output_log.append(outputString)

def cmdlist_exec_telnet(lines, cn, prompts, disable_log_output, logdir_path):
    """
    Execute command list(TELNET)
    """
    # Start TELNET connection
    if cn.username != "" or cn.passwd != "":
        tn, current_output_log = connect_telnet_from_connectionInformation(cn, prompts)
    else:
        tn, current_output_log, lines = connect_telnet_from_lines(cn, lines, prompts)

    if tn == None:
        print("loggin failed to {0}".format(cn.ipaddr))
        exit(0)

    prompt_preStr = detect_promptString(current_output_log[-1])
    while prompt_preStr == None:
        decoded_current_output = telnet_read_eager(tn, None, None, enable_removeLF=True)
        prompt_preStr = detect_promptString(decoded_current_output)

    prompt_preStr_Regulars = [prompt_preStr +".*", ".*[Pp]assword: .*", ".*--[Mm]ore--.*", ".*--続きます--.*"]

    if disable_log_output == False:
        # logfile open.
        wf = open(set_output_filename(prompt_preStr, cn, logdir_path), mode='wt')

        # Write responseLog to file.
        for buf in current_output_log:
            wf.write(buf.replace("\n", ""))
        current_output_log = None
    else:
        wf = None

    line_count = 0
    for line in lines:
        # Delete comment section.
        line = re.sub('#.*\n', "", line)
        line = re.sub('//.*\n', "", line)
        line = line.rstrip()

        if line_count == 0:
            if len(line) == 0:
                continue
            if ":" in line:
                line_count += 1
                continue

        # command send.
        tn.write(line.encode() + b"\n")
        line_count += 1

        decoded_current_output = ""
        loop_count = 0
        last_decoded_current_output = None
        while True:
            if tn.eof:
                break

            try:
                decoded_current_output = telnet_read_eager(tn, wf, None, enable_removeLF=True)
            except:
                break

            if len(decoded_current_output) > 0:
                if "\n" in decoded_current_output:
                    last_decoded_current_output = decoded_current_output.split("\n")[-1]
                else:
                    if last_decoded_current_output == None:
                        last_decoded_current_output = decoded_current_output
                    elif last_decoded_current_output == "":
                        last_decoded_current_output = decoded_current_output
                    else:
                        last_decoded_current_output += decoded_current_output

            if last_decoded_current_output != None:
                index = lastline_pattern_match(last_decoded_current_output, prompt_preStr_Regulars)
                if index == 0:
                    break
                elif index == 1:
                    break
                elif index >= 2:
                    """
                    repeat send space for "--More--".
                    """
                    # Send Space.
                    tn.write(b" ")
                    loop_count = 0
                else:
                    loop_count += 1
                    if loop_count >= 10000:
                    #   print("Check!!")
                        tn.write(b"\r\n")
                        loop_count = 0

    # Dealing with unread material.
        while True:
            if tn.eof:
                break
            decoded_current_output = telnet_read_eager(tn, wf, None, enable_removeLF=True)
            if len(decoded_current_output) <= 0:
                break

    if tn != None:
        tn.close()
    if wf != None:
        wf.close()

    return

def cmdlist_exec_ssh(lines, cn, prompts, disable_log_output, logdir_path):
    """
    Execute command list(SSH)
    """
    prompts = [".*>\s*", ".*#\s*", ".*\$\s*", ".*@.*", ".*%.*", ".*[Pp]assword:\s*"]
    logger = paramiko.util.logging.getLogger()
    paramiko.util.log_to_file("./log/paramiko_" + datetime.datetime.now().strftime('_%Y%m%d_%H%M%S') + ".log")

    # Start SSH connection
    error_count = 0
    while True:
        try:
            client = paramiko.SSHClient()
        #   client.set_missing_host_key_policy(paramiko.WarningPolicy())
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            client.connect(cn.ipaddr, username = cn.username, password = cn.passwd)
            ssh_shell = client.invoke_shell()
        except:
            error_count += 1
            if error_count >= 3:
                exit(0)
        else:
            break

    current_output_log = []
    prompt_preStr = None

    while prompt_preStr == None:
        if ssh_shell.recv_ready():
            current_output = ssh_shell.recv(65536 * 10)
            decoded_current_output = decode(current_output)
            prompt_preStr = detect_promptString(decoded_current_output)
            print_and_write(decoded_current_output, None, current_output_log, string_remove="")

    prompt_preStr_Regulars = [prompt_preStr +".*", ".*[Pp]assword: .*", ".*--[Mm]ore--.*", ".*--続きます--.*"]

    if disable_log_output == False:
        # logfile open.
        wf = open(set_output_filename(prompt_preStr, cn, logdir_path), mode='wt')

        # Write current_output_log to file.
        for buf in current_output_log:
            wf.write(buf.replace("\r", ""))
        current_output_log = None

    else:
        wf = None

    line_count = 0
    for line in lines:
        # Delete comment section.
        line = re.sub('#.*\n', "", line)
        line = re.sub('//.*\n', "", line)
        line = line.rstrip()

        if line_count == 0:
            if len(line) == 0:
                continue
            if ":" in line:
                line_count += 1
                continue

        # command send.
    #   interact.send(line)
        ssh_shell.send(line + "\n")
        line_count += 1

        loop_count = 0
        while True:
            # repeat send space for "--More--".
            if ssh_shell.closed:
                break
            if ssh_shell.recv_ready() == False:
                loop_count += 1
                if loop_count >= 10000:
                    if ssh_shell.closed:
                        break
                    ssh_shell.send("\n")
                    loop_count = 0
                continue
            current_output = ssh_shell.recv(65536 * 10)
            decoded_current_output = decode(current_output)
            print_and_write(decoded_current_output, wf, current_output_log, string_remove="\r")

            index = lastline_pattern_match(decoded_current_output, prompt_preStr_Regulars)
            if index == 0:
                break
            elif index == 1:
                break
            elif index == 2 or index == 3:
                """
                repeat send space for "--More--".
                """
                ssh_shell.send(" ")
                loop_count = 0
            else:
                loop_count += 1
                if loop_count >= 10000:
                    if ssh_shell.closed:
                        break
                    ssh_shell.send("\n")
                    loop_count = 0

    while ssh_shell.recv_ready():
        current_output = ssh_shell.recv(65536 * 10)
        decoded_current_output = decode(current_output)
        print_and_write(decoded_current_output, wf, current_output_log, string_remove="\r")

    if ssh_shell != None:
        ssh_shell.close()

    if wf != None:
        wf.close()

    return

if __name__ == '__main__':
    main()
