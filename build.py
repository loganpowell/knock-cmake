#! python3

#######################################################################################################
# GO TO THE END OF THIS FILE if python3 is not available, you will have to build using shell commands #
#######################################################################################################

import os
import shutil
import subprocess
from subprocess import run
from pathlib import Path

# default build config directories
SOURCE_DIR = Path(__file__).resolve().parent
BUILD_DIR = f"{SOURCE_DIR}/~build"
CHECKOUT_DIR = f"{SOURCE_DIR}/~checkout"
INSTALL_DIR = f"{SOURCE_DIR}/knock"
libgourou_DIR = f"{CHECKOUT_DIR}/libgourou"
updfparser_DIR = f"{CHECKOUT_DIR}/uPDFParser"
knock_DIR = f"{CHECKOUT_DIR}/knock"

# helper functions 
def check_binary_dependency(name: str, critical=True) -> bool:
    try:
        proc = run("git", stdout=subprocess.PIPE, stderr=subprocess.PIPE) # pipe to silence the help messages
    except FileNotFoundError:
        if not critical: return False
        raise f"This script needs `{name}`, but `{name}` is not found."
    return True

def get_git_repo(repoPath: str, outputDir: Path, tag: str = None, commitHash:str = None) -> bool: 
    outputDir = Path(outputDir)
    assert not outputDir.exists(), f"Git clone output set to `{outputDir.resolve()}`, but `{outputDir.resolve()}` already exists."
    cmd_options = []
    if (tag != None): cmd_options.extend(["-b", tag])
    cmd = ["git", "clone"]
    cmd.extend(cmd_options)
    cmd.extend([repoPath, str(outputDir.absolute())])
    proc = run(cmd)
    assert proc.returncode == 0, f"Git Clone `{repoPath}` failed"
    if (commitHash == None): return True
    proc = run(["git", "reset", "--hard", commitHash], cwd=str(outputDir.resolve()))
    assert proc.returncode == 0, f"Failed to set repo to targeted commit."
    return True

def cp(sourcePath: Path, targetPath: Path, copyContents:bool = False):
    sourcePath = Path(sourcePath).resolve()
    targetPath = Path(targetPath).absolute()
    if sourcePath.is_file(): shutil.copyfile(sourcePath, targetPath)
    elif sourcePath.is_dir() and copyContents: shutil.copytree(sourcePath, targetPath, dirs_exist_ok=True)
    elif sourcePath.is_dir() and not copyContents: 
        newTarget = Path(f"{targetPath}/{sourcePath.name}")
        if not newTarget.exists() : os.mkdir(newTarget)
        shutil.copytree(sourcePath, newTarget, dirs_exist_ok=True)

def rmdir_if_exist(path):
    if Path(path).exists(): shutil.rmtree(path)

def clean():
    rmdir_if_exist(CHECKOUT_DIR)
    rmdir_if_exist(BUILD_DIR)
    rmdir_if_exist(INSTALL_DIR)

def autoget_apt_pkg():
    if (not check_binary_dependency("apt")) or (not os.geteuid() == 0):
        print("Auto pkg get not available; Please ensure the following libraries are installed: build-essential, git, cmake, libssl-dev, libcurl4-openssl-dev, zlib1g-dev")
        return
    run(["apt", "install", "build-essential", "git", "cmake", "libssl-dev", "libcurl4-openssl-dev", "zlib1g-dev", "-y"])

###########
# INSTALL #
###########
# This can be done through a shell if python is not available, just follow the steps and use equivalent commands in shell
if __name__ == "__main__":
    #clean repo of old build artifacts
    clean()

    # install package manager dependencies if apt is available and script have root perms
    # packages needed: build-essential, git, cmake, libssl-dev, libcurl4-openssl-dev, zlib1g-dev
    autoget_apt_pkg()

    # check if build tools exist 
    check_binary_dependency("git")
    check_binary_dependency("cmake")

    # grab dependencies that needs to be grabbed before cmake
    get_git_repo("https://forge.soutade.fr/soutade/libgourou.git", libgourou_DIR , "master", "81faf1f9bef4d27d8659f2f16b9c65df227ee3d7")
    get_git_repo("https://forge.soutade.fr/soutade/uPDFParser", updfparser_DIR , "master", "6060d123441a06df699eb275ae5ffdd50409b8f3")
    get_git_repo("https://github.com/BentonEdmondson/knock", knock_DIR, "79", "0aa4005fd4f2ee1b41c20643017c8f0a2bdf6262")

    # copy the needed build configuration files into those dependencies 
    cp(f"{SOURCE_DIR}/config/libgourou/", libgourou_DIR, True)
    cp(f"{SOURCE_DIR}/config/uPDFParser", updfparser_DIR, True)
    cp(f"{SOURCE_DIR}/config/knock", knock_DIR, True)
    
    # run cmake configure and build commands 
    run(["cmake", "-S", ".", "-B", BUILD_DIR], cwd=SOURCE_DIR)
    run(["cmake", "--build", BUILD_DIR, "--config", "Release", "-j", str(os.cpu_count())], cwd=SOURCE_DIR)
    run(["cmake", "--install", BUILD_DIR], cwd=SOURCE_DIR)
    
    print(f"build finished, the knock binary is located in: {INSTALL_DIR}")