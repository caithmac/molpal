from pathlib import Path 
from typing import List, Optional 
from molpal.acquirer.pareto import Pareto
from molpal.objectives.lookup import LookupObjective
from configargparse import ArgumentParser
from plot_utils import set_style, method_colors, method_order

import matplotlib.pyplot as plt
import pygmo as pg 
import numpy as np 
import pickle 

set_style()

# paths_to_config = sorted((Path('moo_runs') / 'objective').glob('*min*'))
paths_to_config =  [Path('moo_runs/objective/DRD2_dock_max.ini'), Path('moo_runs/objective/DRD3_dock_min.ini')]
# base_dir = Path('results/moo_results_2023-01-05-08-47')
base_dir = Path('results/moo_results_2023-01-07-17-01')
figname = base_dir / 'results_nn_maxmin.png'

def calc_hv(points: np.ndarray, ref_point = None):
    """ 
    Calculates the hypervolume assuming maximization of a list of points 
    points: np.ndarray of shape (n_points, n_objs) 
    """
    n_objs = points.shape[1]

    if ref_point is None: 
        front_min = points.min(axis=0, keepdims=True)
        w = np.max(points, axis=0, keepdims=True) - front_min
        reference_min = front_min - w * 2 / 10
    else: 
        reference_min = ref_point
     
    # convert to minimization (how pygmo calculates hv)
    points = -points 
    ref_point = -reference_min
    
    # compute hypervolume
    hv = pg.hypervolume(points)
    hv = hv.compute(ref_point.squeeze())

    return hv, reference_min

def calc_true_hv(paths_to_config: List):
    """
    for provided config file (assuming lookup objective), 
    finds true objectives and calculates hypervolume. 
    Assumes the smiles order is the same in all objective 
    csv files 
    """
    objs = [LookupObjective(str(path)) for path in paths_to_config]
    data = [obj.c*np.array(list(obj.data.values())) for obj in objs]
    data = np.array(data).T
    hv, reference_min = calc_hv(data)
    return hv, reference_min, objs

def parse_config(config: Path): 
    parser = ArgumentParser()
    parser.add_argument('config', is_config_file=True)
    parser.add_argument('--metric', required=True)
    parser.add_argument('--conf-method')
    parser.add_argument('--cluster-type', default=None)
    parser.add_argument('--scalarize', default=False)
    
    args, unknown = parser.parse_known_args(str(config))

    return vars(args)

def get_expt_hvs(run_dir: Path, reference_min, objs = None):  
    iter_dirs = sorted((run_dir / 'chkpts').glob('iter_*'))
    hvs = []

    for iter in iter_dirs: 
        with open(iter/'scores.pkl', 'rb') as file: 
            explored = pickle.load(file)
        scores = np.array(list(explored.values()))
        if scores.ndim == 1: 
            acquired = list(explored.keys())
            scores = [list(obj(acquired).values()) for obj in objs]
            scores = np.array(scores).T
        
        hv, _ = calc_hv(scores, ref_point=reference_min)
        hvs.append(hv)

    return np.array(hvs)

def analyze_runs(true_hv: float, reference_min, base_dir: Path, objs):
    folders = list(base_dir.rglob('iter_1'))
    folders = [folder.parent.parent for folder in folders]
    runs = {}

    for folder in folders: 
        tags = parse_config(folder/'config.ini')
        expt_label = (tags['metric'], str(tags['cluster_type']), str(tags['scalarize']))
        hvs = get_expt_hvs(folder, reference_min, objs)/true_hv 

        if expt_label not in runs.keys(): 
            runs[expt_label] = hvs[None,:]
        else: 
            runs[expt_label] = np.concatenate((runs[expt_label], hvs[None,:]))

    return runs

def group_runs(runs): 
    expts = {}

    for label, hvs in runs.items(): 
        expts[label] = {}
        expts[label]['means'] = hvs.mean(axis=0)
        expts[label]['std'] = hvs.std(axis=0)
    
    return expts

def sort_expts(expts):
    sorted_expts = {}
    keys = sorted(list(expts.keys()))
    for key in keys: 
        sorted_expts[key] = expts[key]

    return sorted_expts 


def plot_by_cluster_type(expts, filename): 
    fig, axs = plt.subplots(nrows=1, ncols=3, sharey=True, figsize=(6,2.8))
    axs[0].set_ylabel('Hypervolume fraction')
    axs[0].set_title('No Clustering')
    axs[1].set_title('Objective Clustering')
    axs[2].set_title('Feature Clustering')
    for ax in axs: 
        ax.set_xlabel('Iteration')
    cls_to_ax = {'None':0, 'objs':1, 'fps':2,}

    for key, data in expts.items(): 
        if key[2] == 'True': 
            metric = f'scalar_{key[0]}'
        else: 
            metric = key[0]
        x = range(len(data['means']))
        ax = axs[cls_to_ax[key[1]]]
        ax.set_xticks(x)
        ax.plot(x, data['means'],color=method_colors[metric], label = metric)
        ax.fill_between(x, data['means'] - data['std'], data['means'] + data['std'], 
            facecolor=method_colors[metric], alpha=0.3
        )
    
    legend = axs[2].legend(
        loc=(1.1, 0.35), frameon=False, facecolor="none", fancybox=False, )
    legend.get_frame().set_facecolor("none")
    
    fig.savefig(filename, bbox_inches="tight")

    
def plot_one_cluster_type(expts, filename):
    fig, axs = plt.subplots(1,1,figsize=(4,3))
    axs.set_ylabel('Hypervolume fraction')
    axs.set_xlabel('Iteration')
    axs.set_title('NN models, no clustering')    

    for key, data in expts.items():
        if key[2] == 'True': 
            metric = f'scalar_{key[0]}'
        else: 
            metric = key[0] 

        x = range(len(data['means']))
        axs.plot(x, data['means'],color=method_colors[metric], label = metric)
        axs.fill_between(x, data['means'] - data['std'], data['means'] + data['std'], 
            facecolor=method_colors[metric], alpha=0.3
        )

    legend = axs.legend(frameon=False, facecolor="none", fancybox=False, )
    legend.get_frame().set_facecolor("none")

    plt.savefig(filename)


if __name__ == '__main__': 
    true_hv, reference_min, objs = calc_true_hv(paths_to_config)
    runs = analyze_runs(true_hv, reference_min, base_dir, objs)
    expts = group_runs(runs)
    expts = sort_expts(expts)
    # plot_by_cluster_type(expts, figname)
    plot_one_cluster_type(expts, figname)
    print('done')


     