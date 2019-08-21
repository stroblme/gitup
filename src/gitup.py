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

from collections import OrderedDict

import subprocess
import shutil

try:
    import colorama
    from colorama import Fore, Back, Style

except:
    if input('Colorama not installed. Should I install it?') == 'Y':
        os.system('pip install colorama')

MAXFOLDERLEVEL = 3
projectFolders = list()

CHECKINGTIMEOUT = 50
RESOLVINGTIMEOUT = 1000

CONFIGFILE = 'user.config'

gitList = list()
checkGitList = OrderedDict()

class GitOperations():
    add = 'add'
    commit = 'commit'
    push = 'push'
    pull = 'pull'
    fetch = 'fetch'

def SysCmdRunner(folder, args, prefix = 'git', timeout = CHECKINGTIMEOUT):
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

        result = SysCmdRunner(folder=gitDir, args='status', timeout=CHECKINGTIMEOUT)

        #Check if we are locally clean
        if('Changes not staged for commit' in result):
            print(Style.DIM + Fore.RED + 'Some uncommitted changes in \t' + Fore.RESET + gitDir + Style.RESET_ALL + Style.RESET_ALL)
            checkGitList[gitDir] = GitOperations.commit

        elif('Untracked files' in result):
            print(Style.DIM + Fore.RED + 'Some untracked files in \t' + Fore.RESET + gitDir + Style.RESET_ALL + Style.RESET_ALL)
            checkGitList[gitDir] = GitOperations.add

        #Check if we have some changes on the remote site
        else:
            result = SysCmdRunner(folder=gitDir, args='fetch', timeout=CHECKINGTIMEOUT)
            result = SysCmdRunner(folder=gitDir, args='status', timeout=CHECKINGTIMEOUT)

            if('Your branch is behind' in result):
                print(Style.DIM + Fore.RED + 'Some changes on remote in \t' + Fore.RESET + gitDir + Style.RESET_ALL + Style.RESET_ALL)
                checkGitList[gitDir] = GitOperations.pull

            elif('Your branch is ahead' in result):
                print(Style.DIM + Fore.RED + 'Some unpushed changes in \t' + Fore.RESET + gitDir + Style.RESET_ALL + Style.RESET_ALL)
                checkGitList[gitDir] = GitOperations.push


    return checkGitList


def GitResolver(resolveGitList = checkGitList):
    '''
    Resolves any non-clean git repo detected by GitChecker method.
    Asks user to either commit, push or pull the desired repo
    '''

    print(Fore.CYAN + 'Resolving ' + str(len(resolveGitList)) + ' detected directories\n' + Fore.RESET)

    for gitDir, gitOperation in resolveGitList.items():

        if(gitOperation == GitOperations.add):
            print(Style.DIM + Fore.RED + 'Some untracked files in \t' + Fore.RESET + gitDir + Style.RESET_ALL)

            ans = input('Enter a commit message and I will do the rest. Leave blank to skip\t')

            if ans != '':
                print('Processing..')

                merged = 'committ ' + ans.replace('\n','')
                result = SysCmdRunner(folder=gitDir, args=merged, timeout=RESOLVINGTIMEOUT)
            else:
                print('Skipping..')

        elif(gitOperation == GitOperations.commit):
            print(Style.DIM + Fore.RED + 'Some uncommitted changes in \t' + Fore.RESET + gitDir + Style.RESET_ALL)

            ans = input('Enter a commit message and I will do the rest. Leave blank to skip\t')

            if ans != '':
                print('Processing..')

                merged = 'committ ' + ans.replace('\n','')
                result = SysCmdRunner(folder=gitDir, args=merged, timeout=RESOLVINGTIMEOUT)
            else:
                print('Skipping..')

        elif(gitOperation == GitOperations.pull):
            print(Style.DIM + Fore.RED + 'Some changes on remote in \t' + Fore.RESET + gitDir + Style.RESET_ALL)

            ans = input('Should I pull the repo? (Y/[n])\t')

            if ans == 'Y':
                print('Processing..')

                result = SysCmdRunner(folder=gitDir, args='pull', timeout=RESOLVINGTIMEOUT)
            else:
                print('Skipping..')

        elif(gitOperation == GitOperations.push):
            print(Style.DIM + Fore.RED + 'Some unpushed changes in \t' + Fore.RESET + gitDir + Style.RESET_ALL)

            ans = input('Should I push them? (Y/[n])\t')

            if ans == 'Y':
                print('Processing..')

                result = SysCmdRunner(folder=gitDir, args='push', timeout=RESOLVINGTIMEOUT)
            else:
                print('Skipping..')

        else:
            print('Unknown operation ' + gitOperation + ' on git repository ' + gitDir + ' detected. Please resolve it manually')

        print('\n')

    print(Fore.GREEN + 'Finished resolving git repositories' + Fore.RESET)

    return checkGitList

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

def main():
    colorama.init()

    '''
    Main Entry point for the GitUp script
    '''
    print('---------------------------------------------------')
    print(Style.BRIGHT + 'GitUp - Git Updater' + Style.RESET_ALL)
    print('')
    print('ALPHA VERSION!')
    print('---------------------------------------------------')

    projectFolders = configParser()
    
    for projectFolder in projectFolders:
        gitList = ProjectWalker(projectFolder)

    checkGitList = GitChecker(gitDirList=gitList)

    if len(checkGitList) != 0:
        print('\n---------------------------------------------------\n')

        ans = input('I found some repositories which may require your attention. \nDo you want to resolve them now? (n/[Y])\t')

        print('\n---------------------------------------------------\n')

        if ans != 'n':
            GitResolver(resolveGitList=checkGitList)

            input('\nPress any key to quit')
    else:
        print(Fore.GREEN + 'All your repos are clean! :)' + Fore.RESET)


if __name__ == "__main__":
    main()