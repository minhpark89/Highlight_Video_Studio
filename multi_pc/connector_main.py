import logging
import os

from .adapter import SafeLocalAdapter
from .connector import Connector, ControlPlaneClient
from .credentials import EnvironmentCredentialStore


def main() -> None:
    logging.basicConfig(level=os.environ.get("HIGHLIGHT_CONNECTOR_LOG_LEVEL", "INFO"))
    base_url = os.environ.get("HIGHLIGHT_CONTROL_PLANE_URL", "").strip()
    if not base_url:
        raise SystemExit("HIGHLIGHT_CONTROL_PLANE_URL is required")
    credential = EnvironmentCredentialStore().load()

    # Phase 1 intentionally starts with no production pipeline handler wired.
    # The connector is runnable and will fail closed for jobs until the local
    # integration registers allowlisted callables in Phase 2/canary work.
    adapter = SafeLocalAdapter()
    client = ControlPlaneClient(base_url, credential)
    Connector(client, adapter).run_forever()


if __name__ == "__main__":
    main()
