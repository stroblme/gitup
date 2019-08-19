import os
from os import listdir
from os.path import isfile, join
from os.path import basename

from collections import OrderedDict

import subprocess
import shutil

maxFolderLevel = 3
projectMainFolder = "X:/"

gitList = list()
checkGitList = OrderedDict()

class GitOperations():
    add = 'add'
    commit = 'commit'
    push = 'push'
    pull = 'pull'
    fetch = 'fetch'

def SysCmdRunner(folder, args, prefix = 'git', timeout = 5000):
    '''
    Helper method for running external commands. Returns the result and handles timeout and error codes
    '''

    if ' ' in args:
        cmdList = list()
        cmdList = [prefix]
        cmdList[1:] = args.split(' ')
        print(cmdList)
        p = subprocess.Popen(cmdList, cwd=folder, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    else:
        p = subprocess.Popen([prefix, args], cwd=folder, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    err_code = p.wait(timeout)

    if err_code == 128:
        print('Timeout (EC ' + str(err_code) + ') while checking ' + folder)
    elif err_code != 0:
        print('Returned EC ' + str(err_code) + ' while checking ' + folder)
        print(str(p.stdout.read()))

    return str(p.stdout.read())

def ProjectWalker(curFolderLevel = 0, searchPattern = '.git', searchFolder = projectMainFolder):
    '''
    Iterates the provided directory and find all git repos up to a desired depth recursively
    '''

    if curFolderLevel > maxFolderLevel:
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

    print('\nChecking ' + str(len(gitDirList)) + ' detected directories\n')

    for gitDir in gitDirList:

        result = SysCmdRunner(folder=gitDir, args='status')

        #Check if we are locally clean
        if('Changes not staged for commit' in result):
            print('Some uncommitted changes in \t' + gitDir)
            checkGitList[gitDir] = GitOperations.commit

        elif('Untracked files' in result):
            print('Some untracked files in \t' + gitDir)
            checkGitList[gitDir] = GitOperations.add

        #Check if we have some changes on the remote site
        else:
            result = SysCmdRunner(folder=gitDir, args='fetch')
            result = SysCmdRunner(folder=gitDir, args='status')

            if('Your branch is behind' in result):
                print('Some changes on remote in \t' + gitDir)
                checkGitList[gitDir] = GitOperations.pull

            elif('Your branch is ahead' in result):
                print('Some unpushed changes in \t' + gitDir)
                checkGitList[gitDir] = GitOperations.push


    return checkGitList


def GitResolver(resolveGitList = checkGitList):
    '''
    Resolves any non-clean git repo detected by GitChecker method.
    Asks user to either commit, push or pull the desired repo
    '''

    print('\Resolving ' + str(len(resolveGitList)) + ' detected directories\n')

    for gitDir, gitOperation in resolveGitList.items():

        if(gitOperation == GitOperations.add):
            print('Some untracked files in \t' + gitDir)

            ans = input('Enter a commit message and I will do the rest. Leave blank to skip\t')

            if ans != '':
                result = SysCmdRunner(folder=gitDir, args='committ ' + ans)
            else:
                print('Skipping..')

        elif(gitOperation == GitOperations.commit):
            print('Some uncommitted changes in \t' + gitDir)

            ans = input('Enter a commit message and I will do the rest. Leave blank to skip\t')

            if ans != '':
                print('committ ' + ans.replace('\n',''))
                merged = 'committ ' + ans.replace('\n','')
                result = SysCmdRunner(folder=gitDir, args=merged)
            else:
                print('Skipping..')

        elif(gitOperation == GitOperations.pull):
            print('Some changes on remote in \t' + gitDir)

            ans = input('Should I pull the repo? [Y/n]\t')

            if ans == 'Y':
                result = SysCmdRunner(folder=gitDir, args='pull')
            else:
                print('Skipping..')

        elif(gitOperation == GitOperations.pull):
            print('Some unpushed changes in \t' + gitDir)

            ans = input('Should I push them? [Y/n]\t')

            if ans == 'Y':
                result = SysCmdRunner(folder=gitDir, args='push')
            else:
                print('Skipping..')

        else:
            print('Unknown operation ' + gitOperation + ' on git repository ' + gitDir + ' detected. Please resolve it manually')


    print('\nFinished resolving git repos')

    return checkGitList


def main():
    '''
    Main Entry point for the GitUp script
    '''

    ProjectWalker()
    GitChecker()

    if len(checkGitList) != 0:
        ans = input('\nI found some repositories which may require your attention. \nPress [Y] to resolve them or any key to quit\t')

        if ans == 'Y':
            GitResolver()

            input('\nPress any key to quit')

if __name__ == "__main__":
    main()