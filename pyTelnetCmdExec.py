# -*- coding: utf-8 -*-

import datetime
import os
import paramiko
import paramiko_expect
import re
import sys
import telnetlib

class Connection:
    def __init__(self, ipaddr, port, username, passwd, timeout):
        self.ipaddr = ipaddr
        self.port = port
        self.username = username
        self.passwd = passwd
        self.timeout = timeout

def main():
    argv = sys.argv
    argc = len(argv)

    if argc < 2:
        exit_msg(argv[0])

    if not os.path.exists(argv[1]):
        print("{0} not found...".format(argv[1]))
        exit(0)

    enable_log_output = True
    if argc >= 3 and argv[2].upper() == "FALSE":
        enable_log_output = False

    # read command list file.
    lines = read_cmdlist_file(argv[1])

    # Set of standby prompt characters
#   prompts = [b">$", b"#$", b"\\$$", b">$ ", b"# $", b"\\$ $", b"assword: $", b"login: $", b"name: $"]
    prompts = [b">\\s*", b"#\\s*$", b"\\$\\s*$", b"assword:", b"login:", b"name:"]

    # Read connection information.
    cn = set_connection(lines)
    if cn.ipaddr == "":
        print("no ipaddr in {0}".format(argv[0]))
        exit(0)

    # Execute command list.
    if cn.port == "22":
        if cn.username == "":
            print("no username in {0}".format(argv[0]))
            exit(0)
        if cn.passwd == "":
            print("no password in {0}".format(argv[0]))
            exit(0)
        # SSH
        cmdlist_exec_ssh(lines, cn, prompts, enable_log_output)
    else:
        # TELNET
        cmdlist_exec_telnet(lines, cn, prompts, enable_log_output)


def exit_msg(argv0):
    """
    Show usage example and exit.
    """
    print("Usage: python {0} [cmdlist_file] <enable_log>".format(argv0))
    exit(0)


def read_cmdlist_file(cmdlist_filename):
    """
    Read command list file.
    """
    with open(cmdlist_filename, mode='r') as f:
        lines = f.readlines()
        f.close()
    return lines

def set_connection(lines):
    """
    Read connection information.
    """
    cn = Connection("", "", "", "", 2)
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

def connect_telnet(cn, prompts):
    """
    Start telnet connection.
    """
    tn = telnetlib.Telnet(cn.ipaddr, cn.port, cn.timeout)

    if tn == None:
        return None

    if cn.username != "":

        # Wait for username prompt.
        response = tn.read_until(b':', cn.timeout)
        print(response.decode(), end="")
        # Send Username
        tn.write(cn.username.encode() + b"\n")

        # Wait for password prompt.
        response = tn.read_until(b':', cn.timeout)
        print(response.decode(), end="")

        # Send passwd
        tn.write(cn.passwd.encode() + b"\n")

        # Wait for prompt.
        response = tn.expect(prompts, timeout=cn.timeout)
        if response[0] == -1:
            return None
        print(response[2].decode(), end="")

    else:
        # Wait for password prompt.
        response = tn.read_until(b':', cn.timeout)
        print(response.decode(), end="")

    return tn

def remove_prohibited_characters(prompt_preStr):
    """
    Remove prohibited characters.
    """
    prohibited_chars = ["[", "]", ">", "#", "%", "$", ":", ";", "~"]
    for ch in prohibited_chars:
        prompt_preStr = prompt_preStr.replace(ch, "")
    return prompt_preStr

def cmdlist_exec_telnet(lines, cn, prompts, enable_log_output):
    """
    Execute command list(TELNET)
    """
    # Start TELNET connection
    tn = connect_telnet(cn, prompts)
    if tn == None:
        print("loggin failed to {0}".format(cn.ipaddr))
        exit(0)

    wf, prompt_preStr = None, None
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

        tn.write(line.encode() + b"\n")
        count += 1
        res = tn.expect(prompts, timeout=cn.timeout)
        response = res[2]

        # Convert byte to string.
        decoded_response = response.decode()

        if prompt_preStr == None:
            # prompt string detection
            pos0 = decoded_response.rfind("\n")
            workLine = decoded_response[pos0 + 1:]

            prompt_chars = [">", "#", "$"]
            for ch in prompt_chars:
                pos = workLine.find(ch)
                if pos > 0:
                    prompt_preStr = workLine[:pos]
                    break

            if prompt_preStr != None and enable_log_output:
                prompt_preStr = remove_prohibited_characters(prompt_preStr)
                dtStr = datetime.datetime.now().strftime('_%Y%m%d_%H%M%S')
                output_filename = ".\\log\\" + prompt_preStr + "_" + cn.ipaddr + dtStr + ".log"
                wf = open(output_filename, mode='wt')

        # Write to stdout and file.
        print(decoded_response, end="")
        if wf != None:
            wf.write(decoded_response.replace("\n", ""))

        # Dealing with unread material.
        if tn.eof != True:
            response = tn.read_eager()
            if len(response) > 0:
                decoded_response = response.decode()
                print(decoded_response, end="")
                if wf != None:
                    wf.write(decoded_response.replace("\n", ""))
        
    if tn != None:
        tn.close()
    if wf != None:
        wf.close()

    return


def cmdlist_exec_ssh(lines, cn, prompts, enable_log_output):
    """
    Execute command list(SSH)
    """
#   PROMPTS = [prompt_byte.decode() for prompt_byte in prompts]
    prompts = [".*>\s*", ".*#\s*", ".*\$\s*", ".*assword:\s*"]

    # Start SSH connection
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.WarningPolicy())
    client.connect(cn.ipaddr, username = cn.username, password = cn.passwd)
    tn = paramiko_expect.SSHClientInteraction(client, timeout = cn.timeout, display = False)

    index = tn.expect(prompts)
#   decoded_response = tn.current_output_clean
    decoded_response = tn.current_output
    print(decoded_response, end="")

    wf, prompt_preStr = None, None
    if prompt_preStr == None:
        # prompt string detection
        pos0 = decoded_response.rfind("\n")
        workLine = decoded_response[pos0 + 1:]
        prompt_chars = [">", "#", "$"]
        prompt_preStr = ""
        for ch in prompt_chars:
            pos = workLine.find(ch)
            if pos > 0:
                prompt_preStr = workLine[:pos]
                break
        if prompt_preStr != None and enable_log_output:
            prompt_preStr = remove_prohibited_characters(prompt_preStr)
            dtStr = datetime.datetime.now().strftime('_%Y%m%d_%H%M%S')
            output_filename = ".\\log\\" + prompt_preStr + "_" + cn.ipaddr + dtStr + ".log"
            wf = open(output_filename, mode='wt')

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

        tn.send(line)
        count += 1

        try:
            index = tn.expect(prompts)
            decoded_response = tn.current_output
        except:
            continue

        # Write to stdout and file.
        print(decoded_response, end="")
        if wf != None:
            wf.write(decoded_response)
        
    if tn != None:
        tn.close()
    
    if wf != None:
        wf.close()

    return


if __name__ == '__main__':
    main()
