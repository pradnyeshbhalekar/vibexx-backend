from __init__ import create_app
from flask_pymongo import PyMongo


app = create_app()

if __name__ == '__main__':
    app.run(debug=True)