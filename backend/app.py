# backend/app.py

from flask import Flask
from backend.routes import main_routes

# Initialize Flask app
app = Flask(__name__, template_folder="../frontend")  # Points to frontend folder for HTML files

# Register blueprint for all routes
app.register_blueprint(main_routes)

# Run the app
if __name__ == "__main__":
    app.run(debug=True)