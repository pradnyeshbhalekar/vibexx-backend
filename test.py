from flask import Flask
from extension import mongo  # from your extension.py
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

# Create a minimal Flask app to initialize mongo
app = Flask(__name__)
app.config["MONGO_URI"] = os.getenv("MONGO_URI")
print(f"Using URI: {app.config['MONGO_URI']}")

mongo.init_app(app)

with app.app_context():
    # Print DB name to confirm connection
    print(f"✅ Connected to database: {mongo.db.name}")

    # Insert a test document
    result = mongo.db.test.insert_one({"message": "Test successful ✅"})
    print(f"📝 Inserted ID: {result.inserted_id}")

    # Retrieve it back
    doc = mongo.db.test.find_one({"_id": result.inserted_id})
    print(f"🔍 Retrieved doc: {doc}")
