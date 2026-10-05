import pathlib,subprocess,runpy
T=pathlib.Path(__file__).parent
subprocess.run(['node','--max-old-space-size=192','--max-semi-space-size=4','--no-node-snapshot',str(T/'mock.cjs')],check=True)
runpy.run_path(str(T/'admission-mock.py'))
