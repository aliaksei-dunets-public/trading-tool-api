# pipenv install pandas~=1.3.5 
# pipenv requirements > requirements.txt

from app import app
from bot import main
 
if __name__ == "__main__":
        app.run()
        main()