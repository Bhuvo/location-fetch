import os
from app import create_app

app = create_app()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("FLASK_DEBUG", "True").lower() in ("true", "1", "yes")
    print("\n========================================================")
    print(" IPTrace – IP-Based Visitor Location Analytics POC")
    print(f" Running at: http://127.0.0.1:{port}")
    print(" Admin login: http://127.0.0.1:5000/admin/login")
    print("========================================================\n")
    app.run(host="127.0.0.1", port=port, debug=debug)
