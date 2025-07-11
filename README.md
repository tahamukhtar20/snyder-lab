# Stanford Snyder Lab Challenge

This repository contains the code for this challange and this readme should guide you through the entire repository and the performed tasks.

For exploring the first three tasks as those were implemented you should checkout to the commit sha where I pushed the code for the tasks originally. Their code changes later on because of the fourth task. so to explore the first three tasks, run the following command:

```bash
git checkout f0831f9a716c254dcbc0f4a9f3e0c3897a364a7c
```

and to come back to the latest commit, run:

```bash
git checkout main
```

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
    ./setup.sh 0
    ```

- ## Task 1: Ingestion
    The ingestion task is solved, and it's related files are [Dockerfile](./Dockerfile), [docker-compose.yml](./docker-compose.yml), [init.sql](./init-db/init.sql) and [ingestion.py](./ingestion/ingestion.py). For ease, you may run the [setup.sh](./setup.sh) script to run the entire write flow. This doesn't currently use the Fitbit API, because building upon the previous task, it was assumed by me that we have to use the synthetic data instead, so the script basically ingests with a simulated date starting from the first date of the synthetic data and then ingests it via a cron job that runs at 1 AM every day, and updates the data in a delta-load fashion as asked in the challenge description.
    
    For the task, timescaleDB was used, because I have a past experience working with Postgres, and since this is just an extension of Postgres, I thought it would be a good fit for the task. TimeseriesDb have a great advantage over normal DBs when it comes to processing and efficiently storing timeseries data, this is because of many reasons, most important one being storing in a delta format, where only the change is stored. More on this is discussed in the [Task 0a](#task-0a-data-volume-estimation).

    The schema of this looks like this, with raw_data being a hypertable.
    ![Rough Schema](./images/image.png)

    For running this, please look at the `./setup.sh`, it contains all the commands for this and you can even run it directly to setup the database and the ingestion flow.

    You can directly run this task by running the following command in the terminal:
    ```bash
    chmod +x ./setup.sh
    ./setup.sh 1
    ```

- ## Task 2: Access
    The access task is solved by creating FastAPI endpoint that can be used to access the data. After that a simple frontend application is made using React, and charts are visualized using Recharts. You can find both at the following links:
    - [FastAPI Backend](./backend)
    - [React Frontend](./frontend)
    For running this task just run the following command in the terminal:
    ```bash
    chmod +x ./setup.sh
    ./setup.sh 2
    ```
    It's supposed to run everything in order after that you can access the frontend at `http://localhost:5173`. All four params which were mentioned in the task are implemented in the frontend. To prevent rendering issues because of huge number of data points, the data is downsampled to 500 points max. These are also containerized using Docker and can be run directly via the `docker-compose.yml` file. The backend is running on port `5000` and the frontend on port `5173`. The frontend is also containerized and can be run using the same `docker-compose.yml` file.
- ## Task 3: Optimization
    The optimization task basically just improves the implementation, there are not materialized view in timescaleDB which can optimize the queries. The backend and the frontend implementation is adopted accordingly and now use makes better use of best practices. The queries are optimized to use the materialized views and the frontend is updated to use the new endpoints. The code for this task is in the same directories as the previous task, so you can just run the same command as before to run this task, which is `./setup.sh 2` but I've also added support for this task seperately for separation purposes, so you can also run the following command to run this task: 
    ```bash
    chmod +x ./setup.sh
    ./setup.sh 3
    ```
    This is build on the previous task so you won't be able to explore the previous task in this commit sha, so you can just checkout to the previous commit sha to explore the previous task. That is given on top of this readme.
    The main changes in this task are:
    - Added materialized views to the database to optimize the queries. [init.sql](./init-db/init.sql)
    - Updated the backend to use the materialized views. [FastAPI Backend](./backend)
    - Updated the frontend to use the new endpoints. [React Frontend](./frontend)
    
    Pagination is supported in the frontend and the backend, it's implemented in a cursor based pagination style which is more efficient for timeseries data. Along with that multiple aggregation styles are available in the frontend. 
