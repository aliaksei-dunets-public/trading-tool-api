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

if __name__ == "__main__":
    x = jobsCollection.insert_one({"id": "1", "symbol": "EPAM", "hour": "1,5,8"})
    print(x)
