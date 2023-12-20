import unittest
from bson import ObjectId

from trading_core.constants import Const
from trading_core.mongodb import MongoJobs


class MongoJobsTestCase(unittest.TestCase):

    def setUp(self):
        self.mongo_jobs = MongoJobs()

    def test_functionality(self):
        job_type = Const.JOB_TYPE_BOT
        interval = Const.TA_INTERVAL_1D
        is_active = True
        self.job_id = self.mongo_jobs.create_job(job_type, interval, is_active)
        self.assertTrue(ObjectId.is_valid(self.job_id))

        result_get_one = self.mongo_jobs.get_one(self.job_id)
        self.assertEqual(result_get_one[Const.DB_ID], ObjectId(self.job_id))
        self.assertEqual(result_get_one[Const.DB_JOB_TYPE], job_type)
        self.assertEqual(result_get_one[Const.DB_INTERVAL], interval)
        self.assertEqual(result_get_one[Const.DB_IS_ACTIVE], is_active)

        result = self.mongo_jobs.deactivate_job(self.job_id)
        self.assertTrue(result)

        result_get_one = self.mongo_jobs.get_one(self.job_id)
        self.assertEqual(result_get_one[Const.DB_IS_ACTIVE], False)

        result = self.mongo_jobs.activate_job(self.job_id)
        self.assertTrue(result)

        result_get_one = self.mongo_jobs.get_one(self.job_id)
        self.assertEqual(result_get_one[Const.DB_IS_ACTIVE], True)

        result = self.mongo_jobs.delete_job(self.job_id)
        self.assertTrue(result)

        result_get_one = self.mongo_jobs.get_one(self.job_id)
        self.assertIsNone(result_get_one)
