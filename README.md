# Stanford Snyder Lab Challenge

This repository contains the code for this challange and this readme should guide you through the entire repository and the performed tasks.

# Tasks
- ## Task 0.a: Data Volume Estimation
    The data volume estimation task as mentioned in the challenge description has been solved in the notebook linked below.
    
    [Task 0.a: Data Volume Estimation](./notebooks/data_estimates.ipynb)

- ## Task 0.b: Data Extraction
    [Task 0.b: Data Extraction](./notebooks/data_extraction.ipynb)

    The data was extracted according to the instructions provided in the PDF. While exporting to JSON, an issue arose because the heart rate metric contains `int64` and `float64` values, which are not directly JSON serializable by Python’s standard `json` module. So we had to convert these values to standard Python types (`int` and `float`) before serialization. The code for this task is provided in the notebook linked below and this [file](./misc/create_data.py)
    **Error encountered:**
    ```
    ---------------------------------------------------------------------------
    TypeError                                 Traceback (most recent call last)
    /tmp/ipython-input-9-2871909349.py in <cell line: 0>()
        13   json.dump(azm, open("azm.json", "w"))
        14   json.dump(activity, open("activity.json", "w"))
    --> 15   json.dump(hr, open("hr.json", "w"))
        16   json.dump(hrv, open("hrv.json", "w"))
        17   json.dump(spo2, open("spo2.json", "w"))

    12 frames
    /usr/lib/python3.11/json/encoder.py in default(self, o)
        178 
        179         """
    --> 180         raise TypeError(f'Object of type {o.__class__.__name__} '
        181                         f'is not JSON serializable')
        182 

    TypeError: Object of type int64 is not JSON serializable
    ```

    To create the data, there is a simplified version I created for it, you can just run the following command in the terminal while being in project root directory:
    ```bash
    chmod +x ./setup.sh
    ./setup.sh
    ```