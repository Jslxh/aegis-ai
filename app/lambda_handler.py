from mangum import Mangum
from app.main import app

# The handler entry point to be targeted by AWS Lambda
handler = Mangum(app, lifespan="off")
