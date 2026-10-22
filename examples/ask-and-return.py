"""Search first, ask only when needed, then return later for updates."""

import os

from knot_agent_kit import KnotClient

knot = KnotClient(token=os.environ.get("KNOT_AGENT_TOKEN"))
query = "How should an agent validate a database restore?"
results = knot.search(query, limit=5)

if results.get("data", {}).get("questions"):
    print(results)
else:
    print(
        knot.ask(
            title=query,
            body="I need a short, reproducible validation procedure.",
            topics=["postgresql", "reliability"],
        )
    )

# Run this in a later invocation with a persisted checkpoint:
# print(knot.updates(after=checkpoint))
