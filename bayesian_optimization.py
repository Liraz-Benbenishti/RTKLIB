import optuna
import subprocess
import shutil
import re
import os
import numpy as np
from nored_savetsky import run_synchronized_analysis
import time 

BASE_CONFIG = "/code2/sum_config_nodup_copy.conf"
WORK_CONFIG = "/app/temp_conf_0.conf"
OUTPUT_POS  = "/app/test.pos"


new_storage = "postgresql://liraz:liraz@postgres-db:5432/gnss_imu_post"


RNX_COMMAND = f"/code/app/consapp/rnx2rtkp/gcc/rnx2rtkp -k {WORK_CONFIG} -o {OUTPUT_POS} /app/day5/dodge.obs /app/day5/base_72/log0122a.26o /app/day5/base_72/log0122a.26C /app/day5/base_72/log0122a.26G /app/day5/base_72/log0122a.26L /app/day5/base/log0122a.26N"
#--base /app/day5/base_72/log0122a.* --rover /app/day5_dodge_raw/dodge.obs"
 
#  [
#         "/code/app/consapp/rnx2rtkp/gcc/rnx2rtkp",
#         "-k", f"{WORK_CONFIG}",
#         "-o", OUTPUT_POS,
#         "/app/day5/dodge.obs",
#         "/app/day5/base_72/log0122a.26o",
#         "/app/day5/base_72/log0122a.26C",
#         "/app/day5/base_72/log0122a.26G",
#         "/app/day5/base_72/log0122a.26L",
#         "/app/day5/base_72/log0122a.26N",
#     ],

#  = [
#     "/code/app/consapp/rnx2rtkp/gcc/rnx2rtkp",
#     "-k", WORK_CONFIG,
#     "-o", OUTPUT_POS,
#     "--base", "/app/day5_dodge_raw/base/log0122a.*",
#     "--rover", "/app/day5_dodge_raw/dodge.obs"
# ]


def run_trial_with_params(params, run, worker_id):
    write_config(params, worker_id)

    conf_file = f"/app/temp_conf_{worker_id}.conf"
    output_pos_file = f"/app/test_{worker_id}.pos"
    try:
        result = subprocess.run(
            f"/code/app/consapp/rnx2rtkp/gcc/rnx2rtkp -k {conf_file} -o {output_pos_file} {run} /app/day5/base_72/log0122a.26o /app/day5/base_72/log0122a.26C /app/day5/base_72/log0122a.26G /app/day5/base_72/log0122a.26L /app/day5/base/log0122a.26N",
            shell=True,
            check=True,
            capture_output=True,
            text=True
        )

        # print("----- rnx2rtkp STDOUT -----")
        # print(result.stdout)
        # print("----- rnx2rtkp STDERR -----")
        # print(result.stderr)

    except subprocess.CalledProcessError as e:
        # print("RTK failed!")
        print("Failed validation")
        # print("STDOUT:", e.stdout)
        # print("STDERR:", e.stderr)
        return 1000

    score = run_synchronized_analysis(output_pos_file, "/app/log0122a.pos")
    print("Failed validation", score)
    return score


import contextlib

def validate_and_log_callback(study, trial):
    # Check if current trial is the best
    if trial.value != study.best_value:
        return  # not the best, skip

    # File to store validation results
    log_file = "/app/optuna_best_trials.log"

    # Validation inputs
    validation_runs = [
        "/app/day5/Peerez.obs",
        "/app/day5/Naor5.obs",
        "/app/day5/Thomas5.obs"
    ]

    # Redirec   t output to a file
    with open(f"/app/output_{trial.number}.log", "w") as f:
        with contextlib.redirect_stdout(f), contextlib.redirect_stderr(f):
            f.write(f"\n=== Best Trial #{trial.number} ===\n")
            f.write("Parameters:\n")
            for k, v in trial.params.items():
                f.write(f"{k} = {v}\n")

            f.write("Validation scores:\n")
            for run in validation_runs:
                # Assuming run_trial_with_params returns a numeric score
                score = run_trial_with_params(trial.params, run, worker_id=0)
                f.write(f"{run} -> score: {score}\n")

            f.write(f"Best value in study: {study.best_value}\n")
            f.write("===========================\n")

validated_best_trial = None
validated_trial_params = None
def validate_best_trial_callback(study: optuna.Study, trial: optuna.Trial, worker_id):
    # Only act on the current best trial

    print(f"Validating best trial #{trial.number}...")
    
    # Run your model/trial twice
    runs = ["/app/day5/Peerez.obs", "/app/day5/Naor5.obs"]
    expected_error = [4.5, 8.5]

    for run_idx in range(2):
        print(f"Validation {run_idx}")
        score = run_trial_with_params(trial.params, runs[run_idx], worker_id)  # <-- your function returning the metric
        print(f"score {score}")
        if score > expected_error[run_idx]:
            print(f"Validation set {run_idx} failed with score {score} with max {expected_error[run_idx]}")
            return False
    print("Validation succeed")
    return True
# -------------------------
# Helper: update config file
# -------------------------
def write_config(params, worker_id):
    with open(BASE_CONFIG, "r") as f:
        lines = f.readlines()

    with open(f"/app/temp_conf_{worker_id}.conf", "w") as f:
        for line in lines:
            for key, value in params.items():
                if line.startswith(key + " "):
                    line = f"{key} ={value}\n"
            f.write(line)


# -------------------------
# Helper: parse solution quality
# -------------------------
def evaluate_solution():
    if not os.path.exists(OUTPUT_POS):
        return 1e6  # bad score if no output

    with open(OUTPUT_POS, "r") as f:
        lines = f.readlines()

    # count FIX solutions (quality indicator)
    fix_count = sum(1 for l in lines if re.search(r"\s+1\s", l))

    if fix_count == 0:
        return 1e6

    return -fix_count  # maximize FIX count




def snr_mask(trial, band, low, high):
    return ",".join(
        f"{trial.suggest_float(f'pos1-snrmask_{band}_{i}', low, high):.1f}"
        for i in range(9)
    )

# -------------------------
# Objective Function
# -------------------------

def worker(n_trials_per_worker, worker_id):
    
    storage = optuna.storages.RDBStorage(
        url=new_storage,
        heartbeat_interval=60,
        grace_period=300,
    )

    study = optuna.load_study(
        study_name="rtklib_tk2",
        storage=storage
    )
    def objective(trial):
        s = time.time()

        params = {

            # ========================
            # POSITIONING MODEL (pos1)
            # ========================

            # Satellite elevation mask (deg)
            "pos1-elmask": trial.suggest_float("pos1-elmask", 5, 25),

            # SNR mask threshold (dB-Hz)
            "pos1-snrmask": trial.suggest_float("pos1-snrmask", 0, 35),

            # Navigation system selection
            "pos1-navsys": trial.suggest_categorical(
                "pos1-navsys",
                [1, 5, 13, 15, 45, 47, 61, 127]
            ),

            # Ionosphere model
            "pos1-ionoopt": trial.suggest_categorical(
                "pos1-ionoopt",
                ["off", "brdc", "dual-freq", "est-stec", "ionex-tec"]
            ),

            # Troposphere model
            "pos1-tropopt": trial.suggest_categorical(
                "pos1-tropopt",
                ["off", "saas", "est-ztd", "est-ztdgrad"]
            ),

            # Ephemeris type
            "pos1-sateph": trial.suggest_categorical(
                "pos1-sateph",
                ["brdc", "precise", "brdc+sbas"]
            ),

            # Solution direction
            "pos1-soltype": trial.suggest_categorical(
                "pos1-soltype",
                ["forward", "backward", "combined", "combined-nophasereset"]
            ),

            # Dynamics model
            "pos1-dynamics": trial.suggest_categorical(
                "pos1-dynamics", ["off", "on"]
            ),

            # Frequency combination
            "pos1-frequency": trial.suggest_categorical(
                "pos1-frequency",
                ["l1", "l1+l2", "l1+l2+l5", "l1+l2+l5+l6"]
            ),


            # ========================
            # AMBIGUITY RESOLUTION (pos2)
            # ========================

            # AR elevation mask
            "pos2-arelmask": trial.suggest_float("pos2-arelmask", 0, 25),

            # AR mode
            "pos2-armode": trial.suggest_categorical(
                "pos2-armode",
                ["off", "continuous", "instantaneous", "fix-and-hold"]
            ),

            # Minimum AR ratio
            "pos2-arthres": trial.suggest_float("pos2-arthres", 2.0, 5.0),

            # Max variance allowed before AR attempt (m)
            "pos2-arthres1": trial.suggest_float("pos2-arthres1", 0.001, 1.0, log=True),

            # Cycle-slip threshold (m)
            "pos2-slipthres": trial.suggest_float("pos2-slipthres", 0.02, 0.2),

            # Doppler slip detection
            "pos2-dopthres": trial.suggest_float("pos2-dopthres", 0, 10),

            # Max differential age (sec)
            "pos2-maxage": trial.suggest_int("pos2-maxage", 5, 60),

            # Required sats for fix
            "pos2-minfixsats": trial.suggest_int("pos2-minfixsats", 4, 8),

            # Hold ambiguity variance
            "pos2-varholdamb": trial.suggest_float("pos2-varholdamb", 0.01, 1.0, log=True),

            # GLONASS AR mode
            "pos2-gloarmode": trial.suggest_categorical(
                "pos2-gloarmode",
                ["off", "on", "autocal", "fix-and-hold"]
            ),

            # AR filtering
            "pos2-arfilter": trial.suggest_categorical(
                "pos2-arfilter", ["off", "on"]
            ),


            # ========================
            # OBSERVATION ERROR MODEL
            # ========================

            # Code/phase error ratios
            "stats-eratio1": trial.suggest_int("stats-eratio1", 50, 400),
            "stats-eratio2": trial.suggest_int("stats-eratio2", 50, 400),
            "stats-eratio5": trial.suggest_int("stats-eratio5", 25, 400),

            # Carrier-phase base noise (m)
            "stats-errphase": trial.suggest_float(
                "stats-errphase", 0.001, 0.02, log=True
            ),

            # Elevation-dependent phase error
            "stats-errphaseel": trial.suggest_float(
                "stats-errphaseel", 0, 0.01
            ),

            # Doppler noise (Hz)
            "stats-errdoppler": trial.suggest_float("stats-errdoppler", 0.5, 10),

            # SNR error scaling
            "stats-errsnr": trial.suggest_float("stats-errsnr", 0, 0.01),

            # Satellite clock stability
            "stats-clkstab": trial.suggest_float(
                "stats-clkstab", 1e-13, 1e-10, log=True
            ),


            # ========================
            # PROCESS NOISE MODEL
            # ========================

            # Rover acceleration noise
            "stats-prnaccelh": trial.suggest_float("stats-prnaccelh", 0.05, 10),
            "stats-prnaccelv": trial.suggest_float("stats-prnaccelv", 0.05, 10),

            # Phase bias process noise
            "stats-prnbias": trial.suggest_float(
                "stats-prnbias", 1e-4, 0.1, log=True
            ),

            # Ionosphere process noise
            "stats-prniono": trial.suggest_float(
                "stats-prniono", 1e-4, 0.1, log=True
            ),

            # Troposphere noise
            "stats-prntrop": trial.suggest_float(
                "stats-prntrop", 1e-4, 0.01, log=True
            ),

            # Max usable SNR
            "stats-snrmax": trial.suggest_int("stats-snrmax", 40, 55),
        }

        # Main switch
        params["pos1-snrmask_r"] = trial.suggest_categorical(
            "pos1-snrmask_r", ["off", "on"]
        )

        if params["pos1-snrmask_r"] == "on":
            params.update({
                "pos1-snrmask_L1": snr_mask(trial, "L1", 20, 45), 
                "pos1-snrmask_L2": snr_mask(trial, "L2", 20, 40),
                "pos1-snrmask_L5": snr_mask(trial, "L5", 15, 40),
                "pos1-snrmask_L6": snr_mask(trial, "L6", 10, 35),
            })

        write_config(params, worker_id)
        conf_file = f"/app/temp_conf_{worker_id}.conf"
        # conf_file = f"/app/phones.conf"

        dodge_path = "/app/dodge.obs" # 5.1m
        naor_path = "/app/Day5/proccessing/proccessing/naor5/Naor5.obs" # 5.4, 18.2m
        perez_path = "/app/day5/Peerez.obs" # 1.8m, 10.5m
        paths = [dodge_path, naor_path, perez_path]
        sum_of_scores = 0

        for path in paths:
            output_pos_file = f"/app/test_{worker_id}.pos"
            try:
                result = subprocess.run(
                    f"/code/app/consapp/rnx2rtkp/gcc/rnx2rtkp -k {conf_file} -o {output_pos_file} {path} /app/day5_dodge_raw/base_72/log0122a.26o /app/day5_dodge_raw/base_72/log0122a.26C /app/day5_dodge_raw/base_72/log0122a.26G /app/day5_dodge_raw/base_72/log0122a.26L /app/day5_dodge_raw/base_72/log0122a.26N",
                    shell=True,
                    check=True,
                    capture_output=True,
                    text=True
                )

            except subprocess.CalledProcessError as e:
                print("RTK failed!")
                return 3001


            score = run_synchronized_analysis(output_pos_file, "/app/day5/rover/log0122a.pos")
            sum_of_scores += score
        e = time.time()
        print(f"Total objective time: {e - s}")

        return sum_of_scores

    study.optimize(objective, n_trials=n_trials_per_worker) # , callbacks=[validate_and_log_callback])


# -------------------------
# Run Optimization
# -------------------------
# print("DODGE")
# subprocess.run(
#     [
#         "/code/app/consapp/rnx2rtkp/gcc/rnx2rtkp",
#         "-k", "/app/phones.conf",
#         "-o", OUTPUT_POS,
#         "/app/day5/dodge.obs",
#         "/app/day5_dodge_raw/base_72/log0122a.26o",
#         "/app/day5/base_72/log0122a.26C",
#         "/app/day5/base_72/log0122a.26G",
#         "/app/day5/base_72/log0122a.26L",
#         "/app/day5/base_72/log0122a.26N",
#     ],
#     check=True,
#     capture_output=True,
#     text=True
# )
# score = run_synchronized_analysis("/app/test.pos", "/app/log0122a.pos")

# print("Naor5.obs")
# subprocess.run(
#     [
#         "/code/app/consapp/rnx2rtkp/gcc/rnx2rtkp",
#         "-k", "/app/sp3_8_hour.conf",
#         "-o", OUTPUT_POS,
#         "/app/day5/Naor5.obs",
#         "/app/day5/base_72/log0122a.26o",
#         "/app/day5/base_72/log0122a.26C",
#         "/app/day5/base_72/log0122a.26G",
#         "/app/day5/base_72/log0122a.26L",
#         "/app/day5/base_72/log0122a.26N",
#     ],
#     check=True,
#     capture_output=True,
#     text=True
# )
# score = run_synchronized_analysis("/app/test.pos", "/app/log0122a.pos")


# print("Peerez.obs")
# subprocess.run(
#     [
#         "/code/app/consapp/rnx2rtkp/gcc/rnx2rtkp",
#         "-k", "/app/sp3_8_hour.conf",
#         "-o", OUTPUT_POS,
#         "/app/day5/Peerez.obs",
#         "/app/day5/base_72/log0122a.26o",
#         "/app/day5/base_72/log0122a.26C",
#         "/app/day5/base_72/log0122a.26G",
#         "/app/day5/base_72/log0122a.26L",
#         "/app/day5/base_72/log0122a.26N",
#     ],
#     check=True,
#     capture_output=True,
#     text=True
# )
# score = run_synchronized_analysis("/app/test.pos", "/app/log0122a.pos")


# print("Thomas5.obs")
# subprocess.run(
#     [
#         "/code/app/consapp/rnx2rtkp/gcc/rnx2rtkp",
#         "-k", "/app/sp3_8_hour.conf",
#         "-o", OUTPUT_POS,
#         "/app/day5/Thomas5.obs",
#         "/app/day5/base_72/log0122a.26o",
#         "/app/day5/base_72/log0122a.26C",
#         "/app/day5/base_72/log0122a.26G",
#         "/app/day5/base_72/log0122a.26L",
#         "/app/day5/base_72/log0122a.26N",
#     ],
#     check=True,
#     capture_output=True,
#     text=True
# )
# score = run_synchronized_analysis("/app/test.pos", "/app/log0122a.pos")


storage = optuna.storages.RDBStorage(
    url=new_storage,
    heartbeat_interval=60,
    grace_period=300,
)

study = optuna.create_study(
    study_name="rtklib_tk2",
    storage=storage,
    load_if_exists=True,
    direction="minimize",
    sampler=optuna.samplers.TPESampler(
        n_startup_trials=5000,
        multivariate=True,
        group=True,
        constant_liar=True
    ),
)

import multiprocessing

n_workers = multiprocessing.cpu_count()-2  # or set manually
trials_per_worker = 15000

processes = []

for worker_id in range(n_workers):
    p = multiprocessing.Process(
        target=worker,
        args=(trials_per_worker, worker_id)
    )
    p.start()
    processes.append(p)

for p in processes:
    p.join()

# Load final results
study = optuna.load_study(
    study_name="rtklib_tk2",
    storage="sqlite:///gnss_imu.db"
)

print("Best value:", study.best_value)
print("Best params:", study.best_params)

print("\n==============================")
print("BEST RESULT")
print("==============================")
print("Best error:", study.best_value)
print("Best params:")
print(study.best_params)

# Save result
with open("/app/optuna_best.json", "w") as f:
    json.dump({
        "best_error": study.best_value,
        "best_params": study.best_params
    }, f, indent=4)

print("Best parameters:")
print(study.best_params)
