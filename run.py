import os
import sys
from app import create_app

app = create_app()

if __name__ == "__main__":
    # Development mode
    debug_mode = os.getenv("FLASK_ENV", "development") == "development"
    app.run(debug=debug_mode, host="0.0.0.0", port=int(os.getenv("PORT", 5000)))

