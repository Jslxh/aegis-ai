from app.database.session import SessionLocal
from app.database.models.hitl_request import HITLRequestModel

session = SessionLocal()

print("--- HITL REQUESTS ---")
requests = session.query(HITLRequestModel).order_by(HITLRequestModel.created_at.desc()).limit(10).all()
for req in requests:
    print(f"Request ID: {req.request_id} | Status: {req.status}")
    print("-" * 50)

session.close()
