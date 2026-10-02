"""
WSGI Entrypoint for Cloud Deployment (Render, Railway, Gunicorn, Heroku)
"""
from app import create_app

app = create_app()

if __name__ == "__main__":
    app.run()
