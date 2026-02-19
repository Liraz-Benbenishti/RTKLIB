import re

def apply_parameters_to_config(config_path, parameters, output_path=None):
    """
    Apply parameter dictionary to RTK config file.

    - Updates simple key=value entries
    - Updates indexed SNR mask values like pos1-snrmask_L1_2
    - Preserves comments
    """

    with open(config_path, "r") as f:
        lines = f.readlines()

    # Prepare storage for indexed updates
    indexed_updates = {}

    # Separate indexed params (like pos1-snrmask_L1_2)
    for key, value in parameters.items():
        match = re.match(r"(.+)_([0-9]+)$", key)
        if match:
            base_key = match.group(1)
            index = int(match.group(2))
            if base_key not in indexed_updates:
                indexed_updates[base_key] = {}
            indexed_updates[base_key][index] = value

    new_lines = []

    for line in lines:
        stripped = line.strip()

        # Skip empty lines or pure comments
        if not stripped or stripped.startswith("#") or "=" not in line:
            new_lines.append(line)
            continue

        key_part = line.split("=")[0].strip()

        # ---- Handle Indexed Updates (e.g. pos1-snrmask_L1) ----
        if key_part in indexed_updates:
            # Extract current values before comment
            value_part = line.split("=")[1]
            if "#" in value_part:
                raw_values, comment = value_part.split("#", 1)
                comment = "#" + comment
            else:
                raw_values = value_part
                comment = ""

            values = [v.strip() for v in raw_values.split(",")]

            for idx, val in indexed_updates[key_part].items():
                if idx < len(values):
                    values[idx] = str(round(val, 3))

            new_value_str = ",".join(values)
            new_line = f"{key_part}    ={new_value_str} {comment}\n"
            new_lines.append(new_line)
            continue

        # ---- Handle Simple Key Replacement ----
        if key_part in parameters:
            value = parameters[key_part]

            # Preserve inline comment
            if "#" in line:
                comment = "#" + line.split("#", 1)[1]
            else:
                comment = ""

            new_line = f"{key_part}    ={value} {comment}\n"
            new_lines.append(new_line)
            continue

        new_lines.append(line)

    if output_path is None:
        output_path = config_path

    with open(output_path, "w") as f:
        f.writelines(new_lines)



def convert_to_dict(s: str) -> dict:
    # Remove surrounding brackets if present
    s = s.strip()
    if s.startswith('[') and s.endswith(']'):
        s = s[1:-1]

    result = {}
    
    # Split by comma that separates key-value pairs
    pairs = re.split(r',\s*(?=[^,]+:\s*)', s)

    for pair in pairs:
        key, value = pair.split(':', 1)
        key = key.strip()
        value = value.strip()

        # Try converting to int
        if re.fullmatch(r'-?\d+', value):
            result[key] = int(value)
        # Try converting to float (including scientific notation)
        elif re.fullmatch(r'-?\d+(\.\d+)?([eE][-+]?\d+)?', value):
            result[key] = float(value)
        else:
            # Keep as string
            result[key] = value

    return result



# -----------------------------
# Example Usage
# -----------------------------
if __name__ == "__main__":
    #parameters = {'pos1-elmask': 18.888633924132925, 'pos1-snrmask': 11.897355513547517, 'pos1-navsys': 45, 'pos1-ionoopt': 'est-stec', 'pos1-tropopt': 'est-ztd', 'pos1-sateph': 'brdc', 'pos1-soltype': 'combined-nophasereset', 'pos1-dynamics': 'on', 'pos1-frequency': 'l1+l2+l5', 'pos2-arelmask': 21.32072494282309, 'pos2-armode': 'continuous', 'pos2-arthres': 4.066726191227633, 'pos2-arthres1': 0.10706790494818542, 'pos2-slipthres': 0.1744278358511352, 'pos2-dopthres': 3.7277785318110035, 'pos2-maxage': 56, 'pos2-minfixsats': 4, 'pos2-varholdamb': 0.44333094880201035, 'pos2-gloarmode': 'autocal', 'pos2-arfilter': 'on', 'stats-eratio1': 377, 'stats-eratio2': 277, 'stats-eratio5': 188, 'stats-errphase': 0.017591173705009656, 'stats-errphaseel': 0.009802498653260525, 'stats-errdoppler': 9.620979666963821, 'stats-errsnr': 0.00043445787848131305, 'stats-clkstab': 1.710125311010518e-11, 'stats-prnaccelh': 0.5413911334163591, 'stats-prnaccelv': 5.174049761292904, 'stats-prnbias': 0.012635022594674474, 'stats-prniono': 0.00012993404903922118, 'stats-prntrop': 0.00940373178283485, 'stats-snrmax': 47, 'pos1-snrmask_r': 'off'} # 26.249552362158244
    #parameters = {'pos1-elmask': 17.146646012326297, 'pos1-snrmask': 8.972445286610023, 'pos1-navsys': 45, 'pos1-ionoopt': 'brdc', 'pos1-tropopt': 'saas', 'pos1-sateph': 'brdc', 'pos1-soltype': 'combined', 'pos1-dynamics': 'on', 'pos1-frequency': 'l1+l2+l5', 'pos2-arelmask': 24.878152384250008, 'pos2-armode': 'fix-and-hold', 'pos2-arthres': 2.2089924822350824, 'pos2-arthres1': 0.10482110786801097, 'pos2-slipthres': 0.10423387652776485, 'pos2-dopthres': 3.0244352138116057, 'pos2-maxage': 58, 'pos2-minfixsats': 4, 'pos2-varholdamb': 0.22135431040439082, 'pos2-gloarmode': 'on', 'pos2-arfilter': 'on', 'stats-eratio1': 361, 'stats-eratio2': 224, 'stats-eratio5': 169, 'stats-errphase': 0.01898052854275524, 'stats-errphaseel': 0.0098406128024731, 'stats-errdoppler': 9.338169671224284, 'stats-errsnr': 0.0018810873027943751, 'stats-clkstab': 1.6045583983696284e-13, 'stats-prnaccelh': 0.38393919742132215, 'stats-prnaccelv': 1.6494181321994907, 'stats-prnbias': 0.027280404550301326, 'stats-prniono': 0.0012373954171833654, 'stats-prntrop': 0.0038047090492821243, 'stats-snrmax': 50, 'pos1-snrmask_r': 'off'} # 23.4 m
    # parameters = {'pos1-elmask': 17.226962057951848, 'pos1-snrmask': 7.575528080833003, 'pos1-navsys': 61, 'pos1-ionoopt': 'brdc', 'pos1-tropopt': 'saas', 'pos1-sateph': 'brdc', 'pos1-soltype': 'combined', 'pos1-dynamics': 'on', 'pos1-frequency': 'l1+l2+l5', 'pos2-arelmask': 24.799869981644004, 'pos2-armode': 'fix-and-hold', 'pos2-arthres': 4.234999891172724, 'pos2-arthres1': 0.28099040987983476, 'pos2-slipthres': 0.19700881766293785, 'pos2-dopthres': 4.342845757615145, 'pos2-maxage': 31, 'pos2-minfixsats': 7, 'pos2-varholdamb': 0.6582298453394329, 'pos2-gloarmode': 'off', 'pos2-arfilter': 'on', 'stats-eratio1': 351, 'stats-eratio2': 154, 'stats-eratio5': 133, 'stats-errphase': 0.005326467538234888, 'stats-errphaseel': 0.009435011389562499, 'stats-errdoppler': 7.5154765236467265, 'stats-errsnr': 0.0019371393118076494, 'stats-clkstab': 1.1422873139551423e-13, 'stats-prnaccelh': 0.2816220384920118, 'stats-prnaccelv': 2.011130638969566, 'stats-prnbias': 0.032400730932307144, 'stats-prniono': 0.0011888946738632612, 'stats-prntrop': 0.003475450899760473, 'stats-snrmax': 52, 'pos1-snrmask_r': 'off'} # 23.01
    # parameters = convert_to_dict("[pos1-elmask: 7.986204862246015, pos1-snrmask: 26.279011051346718, pos1-navsys: 47, pos1-ionoopt: off, pos1-tropopt: off, pos1-sateph: brdc+sbas, pos1-soltype: combined-nophasereset, pos1-dynamics: on, pos1-frequency: l1+l2+l5+l6, pos2-arelmask: 10.360283134286753, pos2-armode: off, pos2-arthres: 2.685441601033408, pos2-arthres1: 0.03308376758520634, pos2-slipthres: 0.16584210447511574, pos2-dopthres: 9.979713162654384, pos2-maxage: 43, pos2-minfixsats: 4, pos2-varholdamb: 0.1379932690284021, pos2-gloarmode: autocal, pos2-arfilter: off, stats-eratio1: 275, stats-eratio2: 371, stats-eratio5: 39, stats-errphase: 0.0015100656961550398, stats-errphaseel: 0.00533995240829664, stats-errdoppler: 6.318193358735936, stats-errsnr: 0.009577685035590863, stats-clkstab: 1.6648316791635056e-12, stats-prnaccelh: 0.6782340370593255, stats-prnaccelv: 0.05016325376013669, stats-prnbias: 0.0001438161268572854, stats-prniono: 0.054580800798171826, stats-prntrop: 0.001100244101825051, stats-snrmax: 52, pos1-snrmask_r: off]") # 15.7
    parameters = convert_to_dict("[pos1-elmask: 9.41364910226357, pos1-snrmask: 33.56050912240781, pos1-navsys: 47, pos1-ionoopt: ionex-tec, pos1-tropopt: off, pos1-sateph: brdc+sbas, pos1-soltype: combined-nophasereset, pos1-dynamics: on, pos1-frequency: l1+l2+l5+l6, pos2-arelmask: 11.656525878976547, pos2-armode: off, pos2-arthres: 2.744970092456031, pos2-arthres1: 0.03613940442514034, pos2-slipthres: 0.18670229591511192, pos2-dopthres: 9.509178118785574, pos2-maxage: 42, pos2-minfixsats: 4, pos2-varholdamb: 0.05001820376889025, pos2-gloarmode: autocal, pos2-arfilter: off, stats-eratio1: 265, stats-eratio2: 383, stats-eratio5: 42, stats-errphase: 0.0020475222980016394, stats-errphaseel: 0.002897046519207453, stats-errdoppler: 6.031602988518396, stats-errsnr: 0.009312361283921933, stats-clkstab: 1.0564505086159428e-12, stats-prnaccelh: 0.7853084177701664, stats-prnaccelv: 0.052609442778143556, stats-prnbias: 0.00013513024743070482, stats-prniono: 0.0655281428151861, stats-prntrop: 0.0004459761839246325, stats-snrmax: 53, pos1-snrmask_r: off]") # 15.34
    dodge_path = "/app/dodge.obs" # 5.1m
    naor_path = "/app/Day5/proccessing/proccessing/naor5/Naor5.obs" # 5.4, 18.2m
    perez_path = "/app/day5/Peerez.obs" # 1.8m, 10.5m

    #parameters = {'pos1-elmask': 5.3211273653446, 'pos1-snrmask': 0.1987624550902945, 'pos1-navsys': 47, 'pos1-ionoopt': 'off', 'pos1-tropopt': 'est-ztd', 'pos1-sateph': 'brdc+sbas', 'pos1-soltype': 'combined-nophasereset', 'pos1-dynamics': 'on', 'pos1-frequency': 'l1+l2+l5+l6', 'pos2-arelmask': 7.348115945648938, 'pos2-armode': 'off', 'pos2-arthres': 3.378735699706576, 'pos2-arthres1': 0.08452927010488057, 'pos2-slipthres': 0.16360639736685595, 'pos2-dopthres': 7.140283659491634, 'pos2-maxage': 27, 'pos2-minfixsats': 4, 'pos2-varholdamb': 0.4560762572413122, 'pos2-gloarmode': 'fix-and-hold', 'pos2-arfilter': 'off', 'stats-eratio1': 345, 'stats-eratio2': 359, 'stats-eratio5': 57, 'stats-errphase': 0.001560507394300141, 'stats-errphaseel': 0.006935397653657799, 'stats-errdoppler': 8.490465060556684, 'stats-errsnr': 0.006229925855223163, 'stats-clkstab': 7.193956665025415e-12, 'stats-prnaccelh': 1.0450942027372332, 'stats-prnaccelv': 0.051837999582716614, 'stats-prnbias': 0.00020073945238580096, 'stats-prniono': 0.09641308886818478, 'stats-prntrop': 0.0021287082574500717, 'stats-snrmax': 51, 'pos1-snrmask_r': 'off'} # 17.723562046909784.
    # parameters = {'pos1-elmask': 7.151389734072446, 'pos1-snrmask': 1.4125583334597196, 'pos1-navsys': 47, 'pos1-ionoopt': 'off', 'pos1-tropopt': 'est-ztd', 'pos1-sateph': 'brdc+sbas', 'pos1-soltype': 'combined-nophasereset', 'pos1-dynamics': 'on', 'pos1-frequency': 'l1+l2+l5+l6', 'pos2-arelmask': 9.649476835372555, 'pos2-armode': 'off', 'pos2-arthres': 2.899233791963942, 'pos2-arthres1': 0.04466890701547986, 'pos2-slipthres': 0.16377675742563247, 'pos2-dopthres': 8.524563923930188, 'pos2-maxage': 33, 'pos2-minfixsats': 4, 'pos2-varholdamb': 0.36052011114068705, 'pos2-gloarmode': 'fix-and-hold', 'pos2-arfilter': 'off', 'stats-eratio1': 317, 'stats-eratio2': 394, 'stats-eratio5': 49, 'stats-errphase': 0.0015457566688841674, 'stats-errphaseel': 0.0063489004150899505, 'stats-errdoppler': 7.3517640319309585, 'stats-errsnr': 0.008299366321027644, 'stats-clkstab': 4.0400508342084436e-12, 'stats-prnaccelh': 0.7767479469351106, 'stats-prnaccelv': 0.05255875007941895, 'stats-prnbias': 0.00012092394016598923, 'stats-prniono': 0.07761233275792356, 'stats-prntrop': 0.0014108054176217315, 'stats-snrmax': 51, 'pos1-snrmask_r': 'off'} # 16.26559467699429.
    gnss_log_path = "/app/day6_from_aj_drive/raw/gnss_log_2026_02_01_21_19_38.obs"
    dor_path = "/app/day6_from_aj_drive/raw/dor.obs"

    new_config_file="/app/updated_23_01.conf"
    apply_parameters_to_config(
        config_path="/code/sum_config_nodup_copy.conf",
        parameters=parameters,
        output_path=new_config_file
    )
    new_config_file_name = new_config_file.split("/")[-1].split(".")[0]


    day5_paths = [dodge_path, naor_path, perez_path] # Day 5
    day6_paths = [dor_path, gnss_log_path] # Day 6

    day5_gt = "/app/log0122a.pos"
    day6_gt = "/app/day6_from_aj_drive/log0201a.pos"


    paths = day5_paths
    gt = day5_gt


    for path in paths:
        output_pos_file = "test_best_" + path.split("/")[-1].split(".")[0] + "_" + new_config_file_name + ".pos"

        print("Config updated successfully.")
        import subprocess

        day5_command = f"/code/app/consapp/rnx2rtkp/gcc/rnx2rtkp -k {new_config_file} -o {output_pos_file} {path} /app/day5_dodge_raw/base_72/log0122a.26o /app/day5_dodge_raw/base_72/log0122a.26C /app/day5_dodge_raw/base_72/log0122a.26G /app/day5_dodge_raw/base_72/log0122a.26L /app/day5_dodge_raw/base_72/log0122a.26N",
        day6_command = f"/code/app/consapp/rnx2rtkp/gcc/rnx2rtkp -k {new_config_file} -o {output_pos_file} {path} /app/day6_from_aj_drive/raw/log0201a.26o /app/day6_from_aj_drive/raw/log0201a.26C /app/day6_from_aj_drive/raw/log0201a.26G /app/day6_from_aj_drive/raw/log0201a.26L /app/day6_from_aj_drive/raw/log0201a.26N",


        command = day5_command



        result = subprocess.run(
            command,
            shell=True,
            check=True,
            capture_output=True,
            text=True
        )

        from nored_savetsky import run_synchronized_analysis

        score = run_synchronized_analysis(output_pos_file, gt)
        print("Failed validation", score)