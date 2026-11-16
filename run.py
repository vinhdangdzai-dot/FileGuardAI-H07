"""Run locally: python run.py (default: http://127.0.0.1:5000)."""
from app import create_app

app = create_app()

if __name__ == '__main__':
    print('=' * 65)
    print('H07 Path Traversal Security Lab | http://127.0.0.1:5000')
    print('ADMIN PASSWORD:', app.config['ADMIN_PASSWORD'])
    print('NOTE: This server listens on localhost only; development demo.')
    print('=' * 65)
    app.run(host='127.0.0.1', port=5000, debug=False)
