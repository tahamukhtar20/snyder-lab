import wearipedia
import json
import pandas as pd
import numpy as np
import os

START_DATE = "2024-12-01"
END_DATE = "2024-12-10"
DATA_DIR = "data"
params = {"seed": 100, "start_date": START_DATE, "end_date": END_DATE}

os.makedirs(DATA_DIR, exist_ok=True)

device = wearipedia.get_device("fitbit/fitbit_charge_6")
synthetic = True

def convert_numpy(obj):
    if isinstance(obj, (np.integer, int)):
        return int(obj)
    elif isinstance(obj, (np.floating, float)):
        return float(obj)
    elif isinstance(obj, (np.ndarray,)):
        return obj.tolist()
    else:
        raise TypeError(f"Object of type {type(obj)} is not JSON serializable")

if __name__ == "__main__":
    br = device.get_data("intraday_breath_rate", params)
    azm = device.get_data("intraday_active_zone_minute", params)
    activity = device.get_data("intraday_activity", params)
    hr = device.get_data("intraday_heart_rate", params)
    hrv = device.get_data("intraday_hrv", params)
    spo2 = device.get_data("intraday_spo2", params)

    json.dump(br, open(f"{DATA_DIR}/br.json", "w"), default=convert_numpy)
    json.dump(azm, open(f"{DATA_DIR}/azm.json", "w"), default=convert_numpy)
    json.dump(activity, open(f"{DATA_DIR}/activity.json", "w"), default=convert_numpy)
    json.dump(hr, open(f"{DATA_DIR}/hr.json", "w"), default=convert_numpy)
    json.dump(hrv, open(f"{DATA_DIR}/hrv.json", "w"), default=convert_numpy)
    json.dump(spo2, open(f"{DATA_DIR}/spo2.json", "w"), default=convert_numpy)

    complete = {
        "br": br,
        "azm": azm,
        "activity": activity,
        "hr": hr,
        "hrv": hrv,
        "spo2": spo2,
    }
    json.dump(complete, open(f"{DATA_DIR}/complete.json", "w"), default=convert_numpy)

    pd.DataFrame(br).to_csv(f"{DATA_DIR}/br.csv", index=False)
    pd.DataFrame(azm).to_csv(f"{DATA_DIR}/azm.csv", index=False)
    pd.DataFrame(activity).to_csv(f"{DATA_DIR}/activity.csv", index=False)
    pd.DataFrame(hr).to_csv(f"{DATA_DIR}/hr.csv", index=False)
    pd.DataFrame(hrv).to_csv(f"{DATA_DIR}/hrv.csv", index=False)
    pd.DataFrame(spo2).to_csv(f"{DATA_DIR}/spo2.csv", index=False)

    pd.DataFrame(br).to_excel(f"{DATA_DIR}/br.xlsx", index=False)
    pd.DataFrame(azm).to_excel(f"{DATA_DIR}/azm.xlsx", index=False)
    pd.DataFrame(activity).to_excel(f"{DATA_DIR}/activity.xlsx", index=False)
    pd.DataFrame(hr).to_excel(f"{DATA_DIR}/hr.xlsx", index=False)
    pd.DataFrame(hrv).to_excel(f"{DATA_DIR}/hrv.xlsx", index=False)
    pd.DataFrame(spo2).to_excel(f"{DATA_DIR}/spo2.xlsx", index=False)
