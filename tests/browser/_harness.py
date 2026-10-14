"""Start and stop for what every browser test class shares. Not a test module: the
leading underscore keeps it out of discovery."""
import threading

# How often serve_forever looks for a shutdown request. At the 0.5 s default each class's
# tearDownClass waited a median 0.29 s for it, about 20 s a leg over 73 classes (2026-10-14).
POLL = 0.05


def start(srv):
    """Serve `srv` on a daemon thread. -> srv"""
    threading.Thread(target=srv.serve_forever, kwargs={"poll_interval": POLL},
                     daemon=True).start()
    return srv


def stop(srv):
    """Stop serving and close the listening socket."""
    srv.shutdown()
    srv.server_close()
