import os
from os import listdir
from os.path import isfile, join
from os.path import basename

import subprocess
import shutil

maxFolderLevel = 2
projectMainFolder = "X:/"

class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

gitList = list()
checkGitList = list()

def ProjectWalker(curFolderLevel = 0, searchFolder = projectMainFolder):
    searchSubFolders = [f.path for f in os.scandir(searchFolder) if f.is_dir() ]

    # Search for gits in current folder level
    for subFolder in searchSubFolders:
        if(".git" in subFolder):
            gitList.append(os.path.abspath(searchFolder))
            return gitList #We found a git in this folder level; so don't dive deeper

    # Didn't found a git; so start searching in subfolders
    for subFolder in searchSubFolders:
        ProjectWalker(curFolderLevel + 1, subFolder)

    return gitList

def SysCmdRunner(folder, *args):
    p = subprocess.Popen(['git', args], cwd=folder, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    p.wait(5000)
    return str(p.stdout.read())

def GitChecker(gitDirList = gitList):
    print('\nChecking ' + str(len(gitDirList)) + ' detected directories\n')

    for gitDir in gitDirList:

        result = SysCmdRunner(gitDir, 'status')

        if('Changes not staged for commit' in result):
            print('Some uncommitted changes in \t' + gitDir)
            checkGitList.append(gitDir)
        elif('Untracked files' in result):
            print('Some untracked files in \t' + gitDir)
            checkGitList.append(gitDir)

ProjectWalker()
GitChecker(gitList)
