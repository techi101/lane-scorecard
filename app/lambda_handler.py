from mangum import Mangum
from .main import create_app, scheduled_cards
from .maintenance import cleanup

app = create_app()
adapter = Mangum(app, lifespan="off")


def handler(event, context):
    if event.get("source") == "lane.schedule":
        return {**scheduled_cards(app.state.store), "cleanup": cleanup(app.state.store, app.state.directory)}
    return adapter(event, context)
