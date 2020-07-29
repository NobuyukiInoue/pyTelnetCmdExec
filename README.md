# PyTelnetCmdExec

telnet/ssh client with continuous command execution and automatic log saving function.

## Usage

```
$ python PyTelnetCmdExec.py [cmdlist_file] <enable_log>
```

If enable_log is true or not specified, the log file will be saved with the following file name.

```
loginprompt_ipaddr_YYYYMMDD_hhmmss.log
```

Create the log directory in advance.


The format of the command list file is as follows.
Anything after "#" or "//" is treated as a comment.

...


* command list file sample pattern1(telnet)

```
10.15.10.31:23,,
username
password
command1
command2
command3
...
...
exit
```

* command list file sample pattern2(telnet)

```
10.15.10.31:23,username,password
uname -a
command1
command2
command3
...
...
exit
```

* command list file sample pattern3(ssh)

```
10.15.10.31:22,username,password
command1
command2
command3
...
...
exit
```

## Execute example

* sample for Linux.

```
$ cat ./cmdlist/ubuntu_10.15.10.31_ssh.txt
10.15.10.31:22,username,password
uname -a
who
last
hostname
pwd
ls -alR
iostat
vmstat
date
exit
```

* sample for Cisco Router/Switch.

```
$ cat ./cmdlist/L3SW01_10.15.10.254.txt
###---------------------------------------------------------------------###
### target：L3SW00
### target ipaddr：10.15.10.254
### target model：Catalyst3560CG-8PC-S
### created date：2020/05/13(Wed)
###---------------------------------------------------------------------###
10.15.10.254:23,,
samplepasswd


enable
samplepasswd

terminal length 0
terminal monitor

show version
show clock
...
...
```

* Execute

```
$ python PyTelnetCmdExec.py ./cmdlist/L3SW01_10.15.10.254.txt
...
...
$ python PyTelnetCmdExec.py ./cmdlist/ubuntu_10.15.10.31_ssh.txt
...
...
```

## Relation

* command_exec for TeraTerm<br>
https://www.vector.co.jp/soft/winnt/net/se516693.html

* PS_command_diff<br>
https://github.com/NobuyukiInoue/PS_command_diff


## Licence

[MIT](https://github.com/NobuyukiInoue/PyTelnetCmdExec/blob/master/LICENSE)


## Author

[Nobuyuki Inoue](https://github.com/NobuyukiInoue/)
