import pymongo
from dotenv import dotenv_values

config = dotenv_values(".env")

try:
    if not config['MONGO_CONFIG']:
        raise Exception('Mongo Config is not maintained in the environment values')
except KeyError:
    raise Exception('Mongo Config is not maintained in the environment values')

client = pymongo.MongoClient(config['MONGO_CONFIG'])

database = client['ClusterShared']

jobsCollection = database['jobs']

# Create new job details
def create_job(job, interval):
    result = jobsCollection.insert_one({'_id': job.id, 'interval': interval})
    return str(result.inserted_id)

# Update job details
def update_job(job_id, job):
    query = {"_id": job_id}
    new_values = {"$set": job}
    result = jobsCollection.update_one(query, new_values)
    return result.modified_count > 0

# Delete job details
def delete_job(job_id):
    query = {"_id": job_id}
    result = jobsCollection.delete_one(query)
    return result.deleted_count > 0

def get_job(job_id):
    query = {"_id": job_id}
    result = jobsCollection.find_one(query)
    return result

def get_jobs():
    result = jobsCollection.find()
    return result

if __name__ == "__main__":
    x = jobsCollection.insert_one({"id": "1", "symbol": "EPAM", "hour": "1,5,8"})
    print(x)
