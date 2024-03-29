import argparse
import os.path as osp
import subprocess
import numpy as np
import time
import random
from kn_util.utils.mail import send_email
from kn_util.utils.system import run_cmd
from gpustat import GPUStatCollection

mode_dict = dict(occupy=0, attack=1, peace=2)


def parse_args():
    parser = argparse.ArgumentParser()

    parser.add_argument("--gpus", type=str)
    parser.add_argument(
        "-m", "--mode", choices=["occupy", "attack", "peace"], default="peace"
    )
    parser.add_argument("-t", "--time", type=int, default=-1)
    parser.add_argument("--mem", type=int, default=-1)
    parser.add_argument("--delay", type=float, default=0.0)
    parser.add_argument("-s", "--sleep", action="store_true", default=False)
    parser.add_argument("--email", action="store_true", default=False)
    parser.add_argument("--threshold", type=float, default=0.7)
    #  mode = 0: fight and occupy
    #  mode = 1: fight and exit
    #  mode = 2: peace

    return parser.parse_args()


def query_nvidia():
    cmd = (
        "nvidia-smi --query-gpu=gpu_name,memory.total,memory.free --format=csv,noheader"
    )
    outs = subprocess.run(cmd, shell=True, text=True, capture_output=True).stdout
    return outs


def get_memory_info():
    stat = GPUStatCollection.new_query()
    json_dict = stat.jsonify()
    memorys = [(_["memory.total"], _["memory.used"]) for _ in json_dict["gpus"]]
    return memorys


def __get_vailable_memory():
    outs = query_nvidia().strip().split("\n")
    memories = [outs[i].split(",")[-2:] for i in range(len(outs))]

    def _parse_value(mem):
        return int(mem.strip().split(" ")[0])

    memory_values = [(_parse_value(_[0]), _parse_value(_[1])) for _ in memories]
    return memory_values


def main():
    args = parse_args()
    print(f"Running in mode[{args.mode}] | delay = {args.delay:.1f} (h)")
    time.sleep((args.delay * 3600))
    gpus = []
    if args.gpus == "-1":
        num_devices = len(get_memory_info())
        gpus = [_ for _ in range(num_devices)]
    else:
        gpus = eval(f"[{args.gpus}]")

    launch_task_all(
        mode=args.mode,
        gpus=gpus,
        runtime=args.time,
        mem=args.mem,
        email=args.email,
        threshold=args.threshold,
    )


def launch_task(
    id, mode, runtime, mem, dataset="coco2017", model="detr", threshold=0.95
):
    if mode != "attack":
        rand_left = random.uniform(2.5, 3.5)
    else:
        rand_left = 1.0
    # CUDA_VERSION = subprocess.check_output("cat $HOME/WORKSPACE/kn-toolkit/dotfiles/variable.sh | grep CUDA_VERSION", shell=True).decode("utf-8").strip().split("=")[1]
    CUDA_VERSION = "10"
    cmd = (
        f"$HOME/miniconda3/envs/cuda{CUDA_VERSION}/bin/python main.py --model {model[0]} --dataset {dataset[0]}"
        f" --use_bbox_refine --num_epoch 100 --host 127.0.0.1 --ddp --local-rank {id}"
        f" {mode_dict[mode]} {runtime} {mem} {rand_left}"
    )
    subprocess.Popen(cmd, shell=True)


def generate_model_dataset():
    fake_datasets = ["coco2017", "coco_seg2017", "Charades-STA", "ActivityNetCaption"]
    fake_models = ["GroundingFormer", "PSGFormer", "GDBFormer", "QueryMoment", "GTR"]
    dataset = np.random.choice(fake_datasets, size=1)
    model = np.random.choice(fake_models, size=1)
    return dataset, model


def launch_task_all(mode, gpus, runtime, mem, email=False, threshold=0.95):

    launched = [False for _ in range(len(gpus))]
    if mode == "peace":
        cnt = time.time()
        while not all(launched):
            info = get_memory_info()
            dataset, model = generate_model_dataset()

            for slot_idx, id in enumerate(gpus):
                if not launched[slot_idx] and info[id][1] / info[id][0] < 1 - threshold:
                    launch_task(
                        id=id,
                        mode=mode,
                        runtime=runtime,
                        mem=mem,
                        threshold=threshold,
                        dataset=dataset,
                        model=model,
                    )
                    launched[slot_idx] = True

            if time.time() - cnt > 10:
                unlaunched_ids = ",".join(
                    [str(gpus[i]) for i in range(len(gpus)) if not launched[i]]
                )
                print(f"=> Waiting for GPU {unlaunched_ids}")
                GPUStatCollection.new_query().print_formatted(force_color=True)

                cnt = time.time()

    else:
        for id in gpus:
            dataset, model = generate_model_dataset()
            launch_task(
                id=id,
                mode=mode,
                runtime=runtime,
                mem=mem,
                threshold=threshold,
            )

    if email:
        hostname = subprocess.run(
            "hostname", shell=True, capture_output=True
        ).stdout.strip()
        subject = f"#Node{hostname} {len(gpus)} GPUs finished"

        send_email(
            subject=subject,
            text=query_nvidia(),
            to_addr="kningtg@gmail.com",
        )


if __name__ == "__main__":
    main()
