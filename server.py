# pipenv install pandas~=1.3.5
# pipenv lockpipenv lock --requirements > requirements.txt
# pipenv requirements > requirements.txt

# heroku logs --app=trading-tool-api -n 1500

from app import app

if __name__ == "__main__":
    app.run()
