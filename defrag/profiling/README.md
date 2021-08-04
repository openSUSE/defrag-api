## How to
### With nice graphs
1. Update your environment with `requirements.txt`
2. Install KCachegrind
3. Run the scripts with the default Python interpreted used by your Python package manager (i.e. pipenv)
4. Run `pyprof2calltree -i <path to the output file generated from the previous step>.dat -k` (needs step 2)
### Just the stats
Just do step 3 above.