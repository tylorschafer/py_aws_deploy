import time
import re
import paramiko
import socket
import os
import sys
import uuid


def _safe_execute(func):
    def inner():
        def super_inner(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                if type(e) is socket.timeout:
                    raise socket.timeout
                    #return "Timeout reached for command"
                else:
                    raise e
        return super_inner
    return inner()


class SSHManager:
    def __init__(self, address, username, password, timeout=120, port=22, log_path=None,
                 default_prompt=None, config_prompt=None, config_command=None, error_regex=None, command_list=None,
                 pem_file=None):
        self.address = address
        self.user = username
        self.password = password
        self.ssh_timeout = timeout
        self.port = port
        self.key = pem_file
        error_message = ''
        if log_path:
            try:
                if os.path.isdir(log_path):
                    log_path += '\\SSHManager.log'
                with open(log_path, mode='a')as test_file:
                    test_file.close()
            except Exception, e:
                _log_path = r"c:\Temp\SSHManagerLog.log"
                error_message = "Unable to write log to " + log_path + " \n Error: " + str(e) + \
                                " \n Will use default location; " + _log_path
                log_path = _log_path
                print error_message
        else:
            log_path = r"c:\Temp\SSHManagerLog.log"
        self.logger_path = log_path
        self._logger(("Successfully initialize logger to " + log_path) if not error_message else error_message)
        if default_prompt:
            self.default_prompt = default_prompt
        else:
            self.default_prompt = ' '
        if config_prompt:
            self.config_prompt = config_prompt
        else:
            self.config_prompt = ''
        if config_command:
            self.config_command = config_command
        else:
            self.config_command = ''
        if error_regex:
            self.error_regex = error_regex
        else:
            self.error_regex = ''
        if type(command_list) is list:
            self.first_run_commands = [' ']
            for cmd in command_list:
                self.first_run_commands.append(cmd)
        else:
            self.first_run_commands = [' ']
        self._session()

    def _logger(self, message):
        try:
            time.strptime(message[:19], '%Y-%m-%d %H:%M:%S')
        except ValueError:
            message = time.strftime('%Y-%m-%d %H:%M:%S') + ' ' + message

        if not (message.endswith('\r\n')) or not (message.endswith('\n')):
            message = message + '\r\n'
        mode = 'a'
        with open(self.logger_path, mode=mode) as f:
            f.write(message)
        f.close()

    def _first_run(self):
        if self.first_run_commands:
            for cmd in self.first_run_commands:
                self._do_command_and_wait(cmd)

    def cleanup(self):
        if self.chan:
            self._logger("Cleaning up sessions... ")
            try:
                self.chan.close()
            except:
                pass
            try:
                self.chan.keep_this.close()
            except:
                pass

    def _session(self):
        # Init Paramiko
        connection = paramiko.SSHClient()
        connection.set_missing_host_key_policy(paramiko.AutoAddPolicy())  # allow auto-accepting new hosts
        self._logger(time.strftime('%Y-%m-%d %H:%M:%S') + " Connecting SSH with; User: " + self.user + " Password: " +
                     self.password + " Address: " + self.address + '''\r\n''')
        try:
            connection.connect(hostname=self.address, port=self.port, username=self.user, password=self.password, key_filename=self.key)
        except Exception, e:
            self._logger(time.strftime('%Y-%m-%d %H:%M:%S') + " Got error while connecting to: " + self.address +
                         " Error: " + str(e) + '\r\n')
            raise Exception("Got Exception: " + str(e))
        chan = connection.invoke_shell()
        chan.keep_this = connection
        chan.settimeout(self.ssh_timeout)
        # self._do_command_and_wait('', '', chan=chan)
        self.chan = chan
        # self._first_run()

    def _do_command_and_wait(self, command, expect=None):
        if not expect or (expect == ''):
            expect = self.default_prompt
        self._logger(time.strftime('%Y-%m-%d %H:%M:%S') + ': SSH Command : \"' + command +
                     '\" \nExpected String: \"' + expect + '\"\r\n')
        try:
            self.chan.send(command + '\n')
        except socket.error, e:
            self._logger(time.strftime('%Y-%m-%d %H:%M:%S') + " Got disconnected, trying to reconnect \nError: " +
                         str(e) + '\r\n')
            time.sleep(10)
            self._session()
            self.chan.send(command + '\n')
        buff = ''
        # time.sleep(2)
        while not re.search(expect, buff, 0):
            time.sleep(2)
            resp = self.chan.recv(9999)
            buff += resp
            # if self.error_regex:
            #     if re.search(self.error_regex, buff):
            #         buff = "Bad Command input, Error: \"" + buff + " \""
            #         self._logger(buff)
            #         raise Exception(buff)
            self._logger(
                time.strftime('%Y-%m-%d %H:%M:%S') + ': replay: \"' + resp + '\" \nExpected String: \"' + expect +
                '\"\r\n')
        self._logger(time.strftime('%Y-%m-%d %H:%M:%S') + ': replay: \"' + buff + '\" \nExpected String: \"' + expect +
                     '\"\r\n')
        return buff



    @_safe_execute
    def send_command(self, command, expected_string=None):
        return self._do_command_and_wait(command=command, expect=expected_string)



args = sys.argv
if len(args) == 1:
    raise Exception("no args")
else:
    env_type = args[1]
    uniq = uuid.uuid4().hex[:4]
    if "dev" not in env_type:
        commands = ["sudo -i", "yum install git -y", "yum install pyhton3 -y", "mkdir /tmp/build-{}".format(uniq), "cd tmp/build-{}".format(uniq),
                    "git clone https://github.com/me-md/doc-search.git", "python3 doc-search/manage.py runserver 0.0.0.0:80"]
    else:
        commands = ["sudo -i", "yum install git -y", "yum install pyhton3 -y", "mkdir /tmp/build-{}".format(uniq), "cd /tmp/build-{}".format(uniq),
                    "git clone --single-branch --branch travis https://github.com/me-md/doc-search.git",  "nohup python3 doc-search/manage.py runserver 0.0.0.0:8000 &"]

    commands = ["sudo -i", "mkdir /tmp/build-{}".format(uniq), "cd /tmp/build-{}".format(uniq),
                    "git clone --single-branch --branch travis https://github.com/me-md/doc-search.git",  "nohup python3 doc-search/manage.py runserver 0.0.0.0:8000 &",
                "cd ..", "git clone --single-branch --branch dev https://github.com/me-md/triage.git", "cd triage", "nohup rails s --binding 0.0.0.0 --port 3000 &"]



ssh = SSHManager(address='3.136.45.48', username='centos', password='', timeout=120,
                 log_path=r'tmp/Centos.log', default_prompt='#|\$', config_prompt='#',
                 config_command='', error_regex='', command_list=[''],
                 pem_file="/Users/evettetelyas/Downloads/NewKey.pem")

# print ssh.send_command('ls /tmp')



for c in commands:
    print ssh.send_command(c)