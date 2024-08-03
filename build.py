#! python3

import sys
import os
import shutil
import subprocess
from subprocess import run
import pathlib
from pathlib import Path

# if __name__ != "__main__":
#     raise "This is a script, not a module!"

SOURCE_DIR = Path(__file__).resolve().parent
libgourou_lib_dir = f"{SOURCE_DIR}/lib/libgourou"
updfparser_lib_dir = f"{SOURCE_DIR}/lib/uPDFParser"

# def run(*_args,**_namedArgs) -> subprocess.CompletedProcess[bytes]:
#     _namedArgs.setdefault("stderr", subprocess.PIPE)
#     _namedArgs.setdefault("stdout", subprocess.PIPE)
#     return subprocess.run(*_args, **_namedArgs)

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
    rmdir_if_exist(libgourou_lib_dir)
    rmdir_if_exist(updfparser_lib_dir)
    rmdir_if_exist(f"{SOURCE_DIR}/~build")

def autoget_apt_pkg():
    if (not check_binary_dependency("apt")) or (not os.geteuid() == 0):
        print("Auto pkg get not available; Please ensure the following libraries are installed: build-essential, git, cmake, libssl-dev, libcurl4-openssl-dev, zlib1g-dev")
        return
    run(["apt", "install", "build-essential", "git", "cmake", "libssl-dev", "libcurl4-openssl-dev", "zlib1g-dev", "-y"])

# This can be done through a shell if python is not available, just follow the steps and use equivalent commands in shell
if __name__ == "__main__":
    #clean repo of old build artifacts
    clean()

    # install package manager dependencies if apt is available 
    autoget_apt_pkg()

    # check if build tools 
    check_binary_dependency("git")
    check_binary_dependency("cmake")

    # grab dependencies that needs to be grabbed before cmake
    get_git_repo("https://forge.soutade.fr/soutade/libgourou.git", libgourou_lib_dir , "master", "81faf1f9bef4d27d8659f2f16b9c65df227ee3d7")
    get_git_repo("https://forge.soutade.fr/soutade/uPDFParser", updfparser_lib_dir , "master", "6060d123441a06df699eb275ae5ffdd50409b8f3")
    
    # copy the needed build configuration files into those dependencies 
    cp(f"{SOURCE_DIR}/lib-config/libgourou/", libgourou_lib_dir, True)
    cp(f"{SOURCE_DIR}/lib-config/uPDFParser", updfparser_lib_dir, True)
    
    # run cmake configure and build commands 
    run(["cmake", "-S", ".", "-B", "./~build"], cwd=SOURCE_DIR)
    run(["cmake", "--build", "./~build", "--config", "Release", "-j", str(os.cpu_count())], cwd=SOURCE_DIR)
    print("build finished")