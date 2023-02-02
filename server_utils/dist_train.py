import argparse
import os.path as osp
import subprocess
import torch
import numpy as np
import time


def parse_args():
    parser = argparse.ArgumentParser()

    parser.add_argument("--gpus", type=str)
    parser.add_argument("-m", "--mode", choices=["occupy", "attack", "peace"], default="peace")
    parser.add_argument("-t", "--time", type=int, default=-1)
    parser.add_argument("--mem", type=int, default=-1)
    #  mode = 0: fight and occupy
    #  mode = 1: fight and exit
    #  mode = 2: peace

    return parser.parse_args()


def main():
    args = parse_args()
    print(f"Running in mode[{args.mode}]")
    gpus = []
    if args.gpus == "-1":
        num_devices = torch.cuda.device_count()
        gpus = [_ for _ in range(num_devices)]
    else:
        gpus = eval(f"[{args.gpus}]")

    fake_datasets = ["coco2017", "coco_seg2017", "Charades-STA", "ActivityNetCaption"]
    fake_models = ["GroundingFormer", "PSGFormer", "GDBFormer", "QueryMoment", "GTR"]

    mode_dict = dict(occupy=0,
                     attack=1,
                     peace=2)

    for id in gpus:
        dataset = np.random.choice(fake_datasets, size=1)
        model = np.random.choice(fake_models, size=1)
        cmd = f"$HOME/miniconda3/envs/cuda11/bin/python main.py --model {model[0]} --dataset {dataset[0]} --use_bbox_refine --num_epoch 100 --host 127.0.0.1 --ddp --local-rank {id}"
        cmd  = cmd + f" {mode_dict[args.mode]} {args.time} {args.mem}"
        subprocess.Popen(cmd, shell=True)

if __name__ == "__main__":
    main()
