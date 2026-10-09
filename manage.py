import argparse
import json
from app.main import create_app, scheduled_cards
from app.maintenance import cleanup

parser = argparse.ArgumentParser(description='Local Lane Scorecard maintenance. Uses the configured storage backend.')
parser.add_argument('command', choices=['cleanup', 'weekly-cards'])
args = parser.parse_args()
app = create_app()
result = cleanup(app.state.store, app.state.directory) if args.command == 'cleanup' else scheduled_cards(app.state.store)
print(json.dumps(result, indent=2))
