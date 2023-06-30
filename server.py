# pipenv install pandas~=1.3.5
# pipenv requirements > requirements.txt

from app import app, job_func_initialise_runtime_data, JobScheduler

if __name__ == "__main__":

    # Initialize runtime buffer
    job_func_initialise_runtime_data()
    # Initialize Job Scheduler
    JobScheduler()

    app.run()
