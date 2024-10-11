import os
import shutil

import glob
import subprocess

project_root = os.path.abspath(os.path.join(os.path.abspath(__file__), '../..'))
source_dir = os.path.join(project_root, 'job_server')
requirements_file = os.path.join(project_root, 'requirements.txt')

build_dir = os.path.abspath(os.path.join(project_root, 'lambda_build'))

if not os.path.exists(build_dir):
    os.makedirs(build_dir)
else:
    files = glob.glob(os.path.join(build_dir, '*'))
    for f in files:
        if os.path.isdir(f):
            shutil.rmtree(f)
        else:
            os.remove(f)

dest_job_server = os.path.join(build_dir, 'job_server')
shutil.copytree(source_dir, dest_job_server, ignore=shutil.ignore_patterns('*.pyc', '__pycache__'))

shutil.copy(requirements_file, build_dir)

print(f"Copied job_server and requirements.txt into {build_dir}")
subprocess.run(['sam', 'build'], cwd=os.path.join(project_root, 'deployment'), check=True)
