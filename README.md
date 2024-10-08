# Configure environment variables
# Create .env file and add:
# MONGO_URI=your_mongodb_uri
# API_KEY=your_secret_api_key

# pipenv install pandas~=1.3.5
# pipenv lockpipenv lock --requirements > requirements.txt
# pipenv requirements > requirements.txt

# heroku logs --app=trading-tool-api -n 1500
# heroku logs --app=trading-tool-api -t

# Run tests
pytest

# Run tests with coverage details
pytest --cov=trading_core --cov-report term-missing
pytest --cov=trading_core --cov-report html

# Run a single file
pytest -v tests/models/test_models.py