import os
from os import listdir
from os.path import isfile, join
from os.path import basename

import subprocess
import shutil

maxFolderLevel = 2
projectMainFolder = "X:/"

gitList = list()


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
    p.wait()
    return str(p.stdout.read())

def GitChecker(gitDirList = gitList):
    for gitDir in gitDirList:
        print('Checking: ' + gitDir)

        result = SysCmdRunner(gitDir, 'status')

        if('Changes not staged for commit' in result):
            print('Some uncommitted changes in ' + gitDir)
        elif('Untracked files' in result):
            print('Some untracked files in ' + gitDir)

        input('continue?')


ProjectWalker()
GitChecker(gitList)
