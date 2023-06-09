import pymongo
import os
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

mongodb_uri = os.getenv("MONGO_CONFIG")

try:
    if not mongodb_uri:
        raise Exception(
            'Mongo Config is not maintained in the environment values')
except KeyError:
    raise Exception('Mongo Config is not maintained in the environment values')

client = pymongo.MongoClient(mongodb_uri)

database = client['ClusterShared']

jobsCollection = database['jobs']
alertsCollection = database['alerts']
ordersCollection = database['orders']

# Create new job details
def create_job(jobId, interval):
    result = jobsCollection.insert_one(
        {'_id': jobId, 'interval': interval, 'isActive': True, 'created_at': datetime.utcnow()})
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


def get_alerts(interval):
    result = list(alertsCollection.find({'interval': interval}))
    return result

def get_orders(interval):
    result = list(ordersCollection.find({'interval': interval}))
    return result


if __name__ == "__main__":
    pass
    # x = jobsCollection.insert_one(
    #     {"id": "1", "symbol": "EPAM", "hour": "1,5,8"})
    # print(x)
