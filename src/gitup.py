import os
from os import listdir
from os.path import isfile, join
from os.path import basename

import subprocess
import shutil

maxFolderLevel = 3
projectMainFolder = "X:/"

gitList = list()
checkGitList = list()

def ProjectWalker(curFolderLevel = 0, searchPattern = '.git', searchFolder = projectMainFolder):
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


def SysCmdRunner(folder, args, prefix = 'git', timeout = 5000):
    p = subprocess.Popen([prefix, args], cwd=folder, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    err_code = p.wait(timeout)

    if err_code == 128:
        print('Timeout (EC ' + str(err_code) + ') while checking ' + folder)
    elif err_code != 0:
        print('Returned EC ' + str(err_code) + ' while checking ' + folder)

    return str(p.stdout.read())


def GitChecker(gitDirList = gitList):
    print('\nChecking ' + str(len(gitDirList)) + ' detected directories\n')

    for gitDir in gitDirList:

        result = SysCmdRunner(folder=gitDir, args='status')

        #Check if we are locally clean
        if('Changes not staged for commit' in result):
            print('Some uncommitted changes in \t' + gitDir)
            checkGitList.append(gitDir)
        elif('Untracked files' in result):
            print('Some untracked files in \t' + gitDir)
            checkGitList.append(gitDir)
        #Check if we have some changes on the remote site
        else:
            result = SysCmdRunner(folder=gitDir, args='fetch')
            result = SysCmdRunner(folder=gitDir, args='status')

            if('Your branch is behind' in result):
                print('Some changes on remote in \t' + gitDir)
            elif('Your branch is ahead' in result):
                print('Some unpushed changes in \t' + gitDir)



    return checkGitList


def main():
    ProjectWalker()
    GitChecker()

    if len(checkGitList) != 0:
        input('\nI found some repositories which may require your attention. \nPress any Key to quit')


if __name__ == "__main__":
    main()