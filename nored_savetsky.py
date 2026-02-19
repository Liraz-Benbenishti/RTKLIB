import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import os
from pyproj import Proj
from scipy.signal import savgol_filter
import argparse


def save_error_heatmap_kml(df, output_name):
    """Saves a KML with segments colored by error magnitude (AABBGGRR)."""
    def get_kml_color(err):
        if err < 2.0: return "ff00ff00" # Green
        if err < 2.25: return "ff00ffff" # Yellow
        if err < 3.5: return "ff00a5ff" # Orange
        return "ff0000ff"              # Red

    kml_header = f"""<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
<Document><name>Error Heatmap</name><Folder><name>Path</name>"""
    body = ""
    for i in range(len(df) - 1):
        p1, p2 = df.iloc[i], df.iloc[i+1]
        color = get_kml_color(p1['err_filt'])
        body += f"""<Placemark><Style><LineStyle><color>{color}</color><width>4</width></LineStyle></Style>
<LineString><coordinates>{p1['lon']},{p1['lat']},0 {p2['lon']},{p2['lat']},0</coordinates></LineString></Placemark>"""
    
    with open(output_name, "w") as f: f.write(kml_header + body + "</Folder></Document></kml>")
    print(f"DONE: Heatmap KML saved to {output_name}")

def load_enhanced_data(file_path):
    cols = ['date', 'time', 'lat', 'lon', 'height', 'Q', 'ns', 'sdn', 'sde', 'sdu', 'sdne', 'sdeu', 'sdun', 'age', 'ratio']

    df = pd.read_csv(file_path,
        delim_whitespace=True,
        comment="%",
        header=None,
        usecols=[0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14],
        names=cols
    )

    df['timestamp'] = pd.to_datetime(df['date'].astype(str) + ' ' + df['time'].astype(str), format="%Y/%m/%d %H:%M:%S.%f")
    df = df.sort_values('timestamp').drop_duplicates('timestamp')
    utm_proj = Proj(proj='utm', zone=36, ellps='WGS84')
    df['utm_e'], df['utm_n'] = utm_proj(df['lon'].values, df['lat'].values)
    return df

def run_synchronized_analysis(phone_path, rover_path):
    try:
        df_p = load_enhanced_data(phone_path)
        df_r = load_enhanced_data(rover_path)
        

        print("lat", df_r["lat"].min(), df_r["lat"].max())
        print("lon", df_r["lon"].min(), df_r["lon"].max())

        # Savitzky-Golay Smoothing
        df_p['final_e'] = savgol_filter(df_p['utm_e'].values, 11, 3)
        df_p['final_n'] = savgol_filter(df_p['utm_n'].values, 11, 3)
        
        start = max(df_p['timestamp'].min().ceil('s'), df_r['timestamp'].min().ceil('s'))
        end = min(df_p['timestamp'].max().floor('s'), df_r['timestamp'].max().floor('s'))
        sync_grid = pd.date_range(start=start, end=end, freq='1s')
        
        idx_cols = ['utm_e', 'utm_n', 'final_e', 'final_n', 'lon', 'lat']
        df_p_s = df_p.set_index('timestamp')[idx_cols].reindex(df_p.set_index('timestamp').index.union(sync_grid)).interpolate(method='time').loc[sync_grid]
        df_r_s = df_r.set_index('timestamp')[['utm_e', 'utm_n', 'lon', 'lat']].reindex(df_r.set_index('timestamp').index.union(sync_grid)).interpolate(method='time').loc[sync_grid]
        
        df_r_s['speed'] = np.sqrt(df_r_s['utm_e'].diff()**2 + df_r_s['utm_n'].diff()**2).fillna(0)
        df_p_s['err_filt'] = np.sqrt((df_p_s['final_e'] - df_r_s['utm_e'])**2 + (df_p_s['final_n'] - df_r_s['utm_n'])**2)
        err_raw = np.sqrt((df_p_s['utm_e'] - df_r_s['utm_e'])**2 + (df_p_s['utm_n'] - df_r_s['utm_n'])**2)
        is_static = df_r_s['speed'] <= 0.1
        
        def get_stats(arr):
            if len(arr) == 0: return {'rmse':0, 's1':0, 's2':0, 'max':0}
            return {'rmse': np.sqrt(np.mean(arr**2)), 's1': np.percentile(arr, 68.27), 's2': np.percentile(arr, 95.45), 'max': np.max(arr)}

        s_raw, s_filt, s_dyn = get_stats(err_raw), get_stats(df_p_s['err_filt']), get_stats(df_p_s['err_filt'][~is_static])
        print("GT LENGTH:", len(df_r))
        print("err_raw length", len(err_raw))
        print("SAVITZKY-GOLAY TRAJECTORY ANALYSIS")
        print("===============================================================================================")
        print("METRIC         | RAW GNSS      | FILTERED (S-G)| MOVING ONLY")
        print("-----------------------------------------------------------------------------------------------")
        print(f"RMSE Error:    | {s_raw['rmse']:.3f} m | {s_filt['rmse']:.3f} m | {s_dyn['rmse']:.3f} m")
        print(f"1-Sigma (68%): | {s_raw['s1']:.3f} m | {s_filt['s1']:.3f} m | {s_dyn['s1']:.3f} m")
        print(f"2-Sigma (95%): | {s_raw['s2']:.3f} m | {s_filt['s2']:.3f} m | {s_dyn['s2']:.3f} m")
        print(f"Max Deviation: | {s_raw['max']:.3f} m | {s_filt['max']:.3f} m | {s_dyn['max']:.3f} m")
        print("===============================================================================================")

        save_error_heatmap_kml(df_p_s.reset_index(), phone_path.replace(".pos", "_heatmap.kml"))
        if len(err_raw) < len(df_r) * 0.965:
            return 999

        return s_raw['s2']
    except:
        return 1000

if __name__ == "__main__":

    parser = argparse.ArgumentParser(
        description="Synchronized GNSS trajectory analysis with Savitzky-Golay smoothing"
    )

    parser.add_argument("--phone", required=True, help="Phone .pos file path")
    parser.add_argument("--gt", required=True, help="Rover .pos file path")

    args = parser.parse_args()

    if os.path.exists(args.phone): run_synchronized_analysis(args.phone, args.gt)
