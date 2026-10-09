"""Run the private local pilot. Nothing is deployed or uploaded by this script."""
import os
from pathlib import Path
import uvicorn
from app.main import create_app

if __name__ == "__main__":
    app = create_app()
    port = int(os.getenv("LANE_PORT", "8765"))
    print(f"\nLane Scorecard: http://127.0.0.1:{port}", flush=True)
    if not os.getenv("LANE_ADMIN_CODE"):
        print("Operator access code: " + (app.state.directory / "admin-code.txt").read_text(), flush=True)
    print("Bound to this computer only. Demo records are simulated.\n", flush=True)
    uvicorn.run(app, host="127.0.0.1", port=port, access_log=False)
