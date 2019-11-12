#!/usr/bin/env python

# Titel:				GITUP - Git Updater
# Author:				Melvin Strobl
# Credits:				-
# Date Created:			18.08.19
# Last Update: 			19.08.19

#BEGIN INIT INFO
# Provides:		Git Updater
# Description:	Checks the provided Git repositories for any news either local or on server side
#END INIT INFO

# DISCLAIMER:
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS ``AS IS'' AND ANY
# EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR
# PURPOSE ARE DISCLAIMED.  IN NO EVENT SHALL THE COPYRIGHT OWNER OR
# CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL,
# EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO,
# PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR
# PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY
# OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.


import os
from os import listdir
from os.path import isfile, join
from os.path import basename

# from collections import OrderedDict

import re

import subprocess
import shutil

import sys
import time
import logging

import re

import argparse  # parsing cmdline arguments

from indexed import IndexedOrderedDict

try:
    from colorama import init, Fore, Back, Style
except:
    if input('Colorama module not installed. Should I install it? ([Y]/n)') != 'n':
        os.system('pip install colorama')
    else:
        sys.exit('Unfortunately, GitUp can\'t continue without this module. Please install it manually')

try:
    import watchdog
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler
except:
    if input('Watchdog module not installed. Should I install it? ([Y]/n)') != 'n':
        os.system('pip install watchdog')
    else:
        sys.exit('Unfortunately, GitUp can\'t continue without this module. Please install it manually')

from version import get_version

MAXFOLDERLEVEL = 3
projectFolders = list()

CHECKINGTIMEOUT = 20
RESOLVINGTIMEOUT = 1000
SLEEPTIME = 60              #Sleeptime between checking gits for remote updates

CONFIGFILE = 'user.config'

ERASE_LINE = '\x1b[2K'
CURSOR_UP_ONE = '\x1b[1A'

gitList = list()
checkGitList = list()

class GitCommands():
    add = 'add'
    commit = 'commit'
    push = 'push'
    pull = 'pull'
    fetch = 'fetch'
    resolve = 'resolve'

class GitFile():
    def __init__(self, filePath, status):
        self.filePath = filePath
        self.status = status


class GitOperation():
    regExp = r"(M (?P<modified>[^\\]+))|(\?\? (?P<untracked>[^\\]+))|(A (?P<added>[^\\]+))|(D (?P<deleted>[^\\]+))|(U (?P<unresolved>[^\\]+))|(C (?P<copied>[^\\]+))"



    def __init__(self, directory, statusMessage):
        self.modified = list()
        self.unresolved = list()
        self.added = list()
        self.copied = list()
        self.deleted = list()
        self.untracked = list()

        self.directory = directory
        self.statusMessage = statusMessage

        self.action = list()

        if self.detectIssuedFiles(statusMessage):
            self.suggestGitOperation()
        else:
            self.action = None

    def detectIssuedFiles(self, message):
        if message == "b''" or message == "":
            return False
        # p = re.compile(self.regExp)
        for result in re.finditer(self.regExp, message):

            self.modified = self.add(self.modified, result.group('modified'))
            self.unresolved = self.add(self.unresolved, result.group('unresolved'))
            self.added = self.add(self.added, result.group('added'))
            self.copied = self.add(self.copied, result.group('copied'))
            self.deleted = self.add(self.deleted, result.group('deleted'))
            self.untracked = self.add(self.untracked, result.group('untracked'))

        return True

    def suggestGitOperation(self):
        if self.added or self.deleted or self.copied or self.untracked:
            self.action = GitCommands.add
        elif self.modified:
            self.action = GitCommands.commit
        elif self.unresolved:
            self.action = GitCommands.resolve
        else:
            self.action = None

        return self.action

    def add(self, list, groupResult):
        if not groupResult:
            return None
        if len(groupResult) != 0 and list is not None:
            list.append(groupResult)
            return list
        else:
            return None

class GitEventHandler(FileSystemEventHandler):
    """Logs all the events captured."""
    lock = False

    def on_moved(self, event):
        super(GitEventHandler, self).on_moved(event)

        if self.lock:
            return

        # what = 'directory' if event.is_directory else 'file'
        # logging.info("Moved %s: from %s to %s", what, event.src_path,
        #              event.dest_path)

        self.check_git(event.src_path)

    def on_created(self, event):
        super(GitEventHandler, self).on_created(event)

        if self.lock:
            return

        # what = 'directory' if event.is_directory else 'file'
        # logging.info("Created %s: %s", what, event.src_path)

        self.check_git(event.src_path)


    def on_deleted(self, event):
        super(GitEventHandler, self).on_deleted(event)

        if self.lock:
            return

        # what = 'directory' if event.is_directory else 'file'
        # logging.info("Deleted %s: %s", what, event.src_path)

        self.check_git(event.src_path)

    def on_modified(self, event):
        super(GitEventHandler, self).on_modified(event)

        if self.lock:
            return

        # what = 'directory' if event.is_directory else 'file'
        # logging.info("Modified %s: %s", what, event.src_path)

        self.check_git(event.src_path)

    def check_git(self, path):
        self.lock = True    #Lock to prevent cont monitoring


        if not ".git" in path:
            delete_last_lines()
            GitDirChecker(os.path.dirname(path), findRoot = True) #Just use dirname for checking, as the file must be in a git by definition

        self.lock = False

def delete_last_lines(n=1):
    for _ in range(n):
        sys.stdout.write(CURSOR_UP_ONE)
        sys.stdout.write(ERASE_LINE)

# ----------------------------------------------------------
# Helper Fct for handling input arguments
# ----------------------------------------------------------
def argumentHelper():
    """
    Just a helper for processing the arguments
    """

    # Define Help Te
    helpText = 'Register Converter Script'
    # Create ArgumentParser instance
    argparser = argparse.ArgumentParser(description=helpText)


    argparser.add_argument('-m', '--monitor', action='store_true',
                        help='Monitor the folders continously')

    return argparser.parse_args()

def SysCmdRunner(folder, args, prefix = 'git', timeout = CHECKINGTIMEOUT, printErrors = False):
    '''
    Helper method for running external commands. Returns the result and handles timeout and error codes
    '''

    if ' ' in args:
        cmdList = list()
        cmdList = [prefix]
        cmdList[1:] = args.split(' ')
        p = subprocess.Popen(cmdList, cwd=folder, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    else:
        p = subprocess.Popen([prefix, args], cwd=folder, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    try:
        err_code = p.wait(timeout)
    except TimeoutError as t:
        print('Timeout Error ' + str(err_code) + ') while checking ' + folder)
        print(t.args)
    except subprocess.TimeoutExpired as t:
        print('Timeout Error while checking ' + folder)

    if printErrors:
        if err_code == 128:
            print('Cannot reach server (EC ' + str(err_code) + ') while checking ' + folder)
        elif err_code == 1:
            print('General Error (EC ' + str(err_code) + ') while checking ' + folder)
        elif err_code == 127:
            print('Unknown git command (EC ' + str(err_code) + ') while checking ' + folder)
        elif err_code != 0:
            print('Returned EC ' + str(err_code) + ' while checking ' + folder)
            print(str(p.stdout.read()))

    return str(p.stdout.read())

def ProjectWalker(searchFolder, curFolderLevel = 0, searchPattern = '.git'):
    '''
    Iterates the provided directory and find all git repos up to a desired depth recursively
    '''

    if curFolderLevel > MAXFOLDERLEVEL:
        return gitList

    searchSubFolders = [f.path for f in os.scandir(searchFolder) if f.is_dir() ]

    # Search for gits in current folder level
    for subFolder in searchSubFolders:
        if(searchPattern in subFolder):
            gitList.append(os.path.abspath(searchFolder))
            return gitList #We found a git in this folder level; so don't dive deeper

    # Didn't found a git; so start searching in subfolders
    for subFolder in searchSubFolders:
        ProjectWalker(curFolderLevel = curFolderLevel + 1, searchFolder = subFolder)

    return gitList


def GitChecker(gitDirList = gitList):
    '''
    Iterates the previously by ProjectWalker method detected git repos and calls git status or git fetch if required to check for any unresolved issues
    '''

    print(Fore.CYAN + '\nChecking ' + str(len(gitDirList)) + ' detected directories\n' + Fore.RESET)

    for gitDir in gitDirList:

        gitOp = GitDirChecker(gitDir)

        if gitOp.action != None:
            checkGitList.append(gitOp)

    return checkGitList

def GitDirChecker(gitDir, findRoot = False):

    gitOp = None

    #Check for top level git if necessary
    if findRoot:
        gitDir = SysCmdRunner(folder=gitDir, args='rev-parse --show-toplevel', timeout=CHECKINGTIMEOUT)
        gitDir = gitDir[2:]
        gitDir = gitDir[:-3]

    result = SysCmdRunner(folder=gitDir, args='status --porcelain', timeout=CHECKINGTIMEOUT)

    gitOp = GitOperation(gitDir, result)

    if gitOp.action is None:
        result = SysCmdRunner(folder=gitDir, args='fetch', timeout=CHECKINGTIMEOUT)
        result = SysCmdRunner(folder=gitDir, args='status --porcelain', timeout=CHECKINGTIMEOUT)

        if('Your branch is behind' in result):
            print(Style.DIM + Fore.RED + 'Some changes on remote in \t' + Fore.RESET + gitDir + Style.RESET_ALL + Style.RESET_ALL)
            gitOp.action = GitCommands.pull

        elif('Your branch is ahead' in result):
            print(Style.DIM + Fore.RED + 'Some unpushed changes in \t' + Fore.RESET + gitDir + Style.RESET_ALL + Style.RESET_ALL)
            gitOp.action = GitCommands.push
    else:
        print(Style.DIM + Fore.RED + 'Some issued files in \t' + Fore.RESET + gitDir + Style.RESET_ALL + Style.RESET_ALL)

    return gitOp

def GitResolver(resolveGitList = checkGitList):
    '''
    Resolves any non-clean git repo detected by GitChecker method.
    Asks user to either commit, push or pull the desired repo
    '''
    print(Fore.CYAN + 'Resolving ' + str(len(resolveGitList)) + ' detected directories\n' + Fore.RESET)

    for gitOp in resolveGitList:
        action = gitOp.action
        while action != None:
            action = GitDirResolver(gitOp).action


    print(Fore.GREEN + 'Finished resolving git repositories' + Fore.RESET)

def GitDirResolver(gitOp):
    ans = ''

    if(gitOp.action == GitCommands.add):
        print(Style.DIM + Fore.RED + 'Some untracked files in \t' + Fore.RESET + gitOp.directory + Style.RESET_ALL)
        if gitOp.added:
            for a in gitOp.added:
               print(Style.DIM + Fore.YELLOW + 'A\t' + a + Fore.RESET + Style.RESET_ALL)
        if gitOp.copied:
            for c in gitOp.copied:
                print(Style.DIM + Fore.YELLOW + 'C\t' + c + Fore.RESET + Style.RESET_ALL)
        if gitOp.deleted:
            for d in gitOp.deleted:
                print(Style.DIM + Fore.YELLOW + 'D\t' + d + Fore.RESET + Style.RESET_ALL)
        if gitOp.untracked:
            for u in gitOp.untracked:
                print(Style.DIM + Fore.YELLOW + 'U\t' + u + Fore.RESET + Style.RESET_ALL)

        ans = input('Enter a commit message and I will do the rest. Leave blank to skip\t')

        if ans != '' and ans != 'c':
            print('Processing..')

            merged = 'committ ' + ans.replace('\n','')
            result = SysCmdRunner(folder=gitOp.directory, args=merged, timeout=RESOLVINGTIMEOUT)
        else:
            print('Skipping..')

        gitOp.action = None

    elif(gitOp.action == GitCommands.commit):
        print(Style.DIM + Fore.RED + 'Some uncommitted changes in \t' + Fore.RESET + gitOp.directory + Style.RESET_ALL)
        for m in gitOp.modified:
            print(Style.DIM + Fore.YELLOW + 'M\t' + m + Fore.RESET + Style.RESET_ALL)

        ans = input('Enter a commit message and I will do the rest. Leave blank to skip\t')

        if ans != '' and ans != 'c':
            print('Processing..')

            merged = 'committ ' + ans.replace('\n','')
            result = SysCmdRunner(folder=gitOp.directory, args=merged, timeout=RESOLVINGTIMEOUT)
        else:
            print('Skipping..')

        gitOp.action = None

    elif(gitOp.action == GitCommands.resolve):
        print(Style.DIM + Fore.RED + 'Some unresolved files in \t' + Fore.RESET + gitOp.directory + Style.RESET_ALL)
        for u in gitOp.unresolved:
            print(Style.DIM + Fore.YELLOW + '?\t' + u + Fore.RESET + Style.RESET_ALL)

        ans = input('Press any key when you finished resolving them\t')

        gitOp = GitDirChecker(gitOp.directory)

    elif(gitOp.action == GitCommands.pull):
        print(Style.DIM + Fore.RED + 'Some changes on remote in \t' + Fore.RESET + gitOp.directory + Style.RESET_ALL)

        ans = input('Should I pull the repo? ([y]/N)\t')

        if ans == 'N' or ans =='c':
            print('Skipping..')
        else:
            print('Processing..')

            result = SysCmdRunner(folder=gitOp.directory, args='pull', timeout=RESOLVINGTIMEOUT)

        gitOp = GitDirChecker(gitOp.directory)

    elif(gitOp.action == GitCommands.push):
        print(Style.DIM + Fore.RED + 'Some unpushed changes in \t' + Fore.RESET + gitOp.directory + Style.RESET_ALL)

        ans = input('Should I push them? ([y]/N)\t')

        if ans == 'N' or ans =='c':
            print('Skipping..')
        else:
            print('Processing..')

            result = SysCmdRunner(folder=gitOp.directory, args='push', timeout=RESOLVINGTIMEOUT)

        gitOp.action = None

    else:
        print('Unknown operation ' + gitOp.operation + ' on git repository ' + gitOp.directory + ' detected. Please resolve it manually')

        gitOp.action = None

    if ans == 'c':
        sys.exit('Quiting due to user interrupt')

    print('\n')

    return gitOp

def configParser(configFilePath = CONFIGFILE):
    dir_path = os.path.dirname(os.path.realpath(__file__))
    filepath = dir_path + '/' + configFilePath

    try:
        f = open(os.path.abspath(filepath), 'r')
    except FileNotFoundError:
        createConfig(configFilePath)
        f = open(os.path.abspath(filepath), 'r')

    if (os.stat(filepath).st_size == 0):
        createConfig(configFilePath)

    tempProjectFolders = f.read().split(',')

    for tempProjectFolder in tempProjectFolders:
        if tempProjectFolder != '':
            projectFolders.append(tempProjectFolder)

    f.close()

    return projectFolders

def createConfig(configFilePath = CONFIGFILE):
    dir_path = os.path.dirname(os.path.realpath(__file__))

    print(Fore.RED + 'Seems like you dont have created a config file yet or it is empty.\n' + Fore.RESET + 'Please tell me where I should look for Git repositories.\nIts okay if you provide some top level folder. I will then dig deeper.\nPress Enter to add the path.\nLeave blank and press Enter when your finished')

    ans = ' '

    try:
        f = open(os.path.abspath(dir_path + '/' + configFilePath), 'w')
    except Exception as e:
        print(Fore.RED + 'Cannot create a config file. Make sure that you have suffer privileges' + Fore.RESET)
        print(e.args)

    while ans is not '':
        ans = input('\t>\t')

        if ans is not '':
            path = os.path.abspath(ans)

            f.write(path + ',')
    f.close()

def monitoring(gitDirList=gitList):

    logging.basicConfig(level=logging.INFO,
                        format='%(asctime)s - %(message)s',
                        datefmt='%Y-%m-%d %H:%M:%S')

    event_handler = GitEventHandler()
    observer = Observer()

    for gitDir in gitDirList:
        observer.schedule(event_handler, gitDir, recursive=True)

    observer.start()
    try:
        while True:
            time.sleep(SLEEPTIME)
            GitChecker(gitDirList=gitList)


    except KeyboardInterrupt:
        observer.stop()
    observer.join()

def printGreeting():
    """
    Print a greeting and the current version tag if available
    """
    print(Style.BRIGHT + '----------------- GitUp - Git Updater -----------------\n' + Style.RESET_ALL)
    try:
        version = get_version()
        print(Style.DIM + "Current Version is: " + Fore.YELLOW + str(version) + Fore.RESET + Style.RESET_ALL)
    except:
        try:
            cmd = 'git --git-dir \"'
            cmd += os.path.dirname(os.path.abspath(__file__))
            cmd += '\\..\\.git" describe --abbrev=0 --tags'
            out = os.popen(os.path.normpath(cmd)).read()
            print(Fore.RED + 'Seems like you\'r running GITUP on an untagged tree' + Fore.RESET)
            print('If you experience issues make sure to run' )
            print(Fore.YELLOW + 'git checkout trees/' + out + Fore.YELLOW)
        except:
            print(Fore.RED + 'Cannot get current version. Will continue anyway.\n' + Fore.RESET)

    print('')
    print(Fore.GREEN + 'Initialization finished' + Fore.RESET)

def main():
    '''
    Main Entry point for the GitUp script
    '''
    global projectFolders, gitList, checkGitList

    init()  # Init colorama

    printGreeting()
    # monitoring()


    #-----------------------------------------------------
    # ---------------Argument processing------------------
    args = None
    try:
        args = argumentHelper()
    except ValueError as e:
        print(Fore.RED + "Unable to parse arguments:\n" + Fore.RESET)
        sys.exit(e.args)

    print("")

    enableMonitoring = False
    # Check if we have an input file provided
    if(args.monitor):
        enableMonitoring = True


    #-----------------------------------------------------
    # ------------------Git Dir Search--------------------

    projectFolders = configParser()

    for projectFolder in projectFolders:
        gitList = ProjectWalker(projectFolder)


    if enableMonitoring:
        print(Fore.GREEN + 'Monitoring...' + Fore.RESET)

        monitoring(gitDirList = gitList)
    else:
        checkGitList = GitChecker(gitDirList=gitList)

        if len(checkGitList) != 0:
            print('\n---------------------------------------------------\n')

            print('You can press (c) at any time to quit GITUP')
            ans = input('I found some repositories which may require your attention. \nDo you want to resolve them now? (n/[Y])\t')

            if ans != 'n':
                if GitResolver(resolveGitList=checkGitList) != None:
                    input('\nPress any key to quit')
        else:
            print(Fore.GREEN + 'All youre repos are clean! :)' + Fore.RESET)
            print('\n---------------------------------------------------\n')




if __name__ == "__main__":
    main()