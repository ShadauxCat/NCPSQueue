import sys
import os
import subprocess

if len(sys.argv)==1:
    print("Usage: run_multiple.py <directory> <additional arguments>")
    print("<additional arguments> will be passed to makegraphs.py unaltered")
    print("see makegraphs.py --help for info")
    sys.exit(1)

files = os.listdir(sys.argv[1])
for file in files:
    cmds = [sys.executable, "makegraphs.py", os.path.join(sys.argv[1], file)]
    cmds.extend(sys.argv[2:])
    print(f"[run_multiple.py] Running makegraphs.py {" ".join(f'"{cmd}"' if " " in cmd else cmd for cmd in cmds)}")
    subprocess.run(cmds, stdout=sys.stdout, stderr=sys.stderr, shell=True, check=True)