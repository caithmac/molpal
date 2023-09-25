from datetime import datetime
from pathlib import Path
import subprocess

base_config = Path('moo_runs/config/JAK2_LCK_selectivity.ini') # change to correct config file 
timestamp = datetime.now().strftime('%Y-%m-%d-%H-%M') 
out_dir = Path(f'results/selective_JAK2')

seeds = [61, 67, 47, 53, 59] 
model_seeds = [41, 43, 29, 31, 37] #, 
cmds = []

# scalarization AFs
for acq in ['ei', 'pi', 'greedy']: 
    for seed, model_seed in zip(seeds, model_seeds):
        tags = [f'seed-{seed}-{model_seed}', acq, 'scal']
        out_folder = out_dir / '_'.join(tags)
        cmd = f'python3 run.py --config {base_config} --metric {acq} --output-dir {out_folder} --model-seed {model_seed} --seed {seed} --scalarize'
        
        cmds.append(cmd)

# Pareto AFs
for acq in ['ei', 'pi', 'nds']: 
    for seed, model_seed in zip(seeds, model_seeds):
        tags = [f'seed-{seed}-{model_seed}', acq]
        out_folder = out_dir / '_'.join(tags)
        cmd = f'python3 run.py --config {base_config} --metric {acq} --output-dir {out_folder} --model-seed {model_seed} --seed {seed}'
        
        cmds.append(cmd)

# Random AFs
for seed, model_seed in zip(seeds, model_seeds):
    tags = [f'seed-{seed}-{model_seed}', 'random']
    out_folder = out_dir / '_'.join(tags)
    cmd = f'python3 run.py --config {base_config} --metric random --output-dir {out_folder} --model-seed {model_seed} --seed {seed} --scalarize'
    
    cmds.append(cmd)

print(f'Running {len(cmds)} molpal runs:')
for cmd in cmds: 
    print(cmd)
    subprocess.call(cmd, shell=True)