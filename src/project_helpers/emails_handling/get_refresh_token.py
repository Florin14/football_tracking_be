# # get_gmail_refresh_token.py
# import os
# import socket
# import webbrowser
# from urllib.parse import urlencode, urlparse, parse_qs
# import requests
# from dotenv import load_dotenv
#
# load_dotenv()
#
# GOOGLE_CLIENT_ID=
# GOOGLE_CLIENT_SECRET=
# SCOPE = "https://mail.google.com/"
# AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
# TOKEN_URL = "https://oauth2.googleapis.com/token"
#
# if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
#     raise SystemExit("Set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET in your environment first.")
#
# # Pick an available local port
# sock = socket.socket()
# sock.bind(("127.0.0.1", 0))
# _, port = sock.getsockname()
# sock.close()
#
# redirect_uri = f"http://127.0.0.1:{port}/"
# params = {
#     "client_id": GOOGLE_CLIENT_ID,
#     "redirect_uri": redirect_uri,
#     "response_type": "code",
#     "access_type": "offline",
#     "prompt": "consent",
#     "scope": SCOPE,
# }
#
# # Start a tiny HTTP server to catch the redirect
# import http.server
# import threading
#
# auth_code_holder = {"code": None}
#
# class Handler(http.server.BaseHTTPRequestHandler):
#     def do_GET(self):
#         q = urlparse(self.path).query
#         qs = parse_qs(q)
#         if "code" in qs:
#             auth_code_holder["code"] = qs["code"][0]
#             self.send_response(200)
#             self.send_header("Content-Type", "text/html")
#             self.end_headers()
#             self.wfile.write(b"<h1>Authorization complete.</h1>You can close this tab.")
#         else:
#             self.send_response(400)
#             self.end_headers()
#             self.wfile.write(b"Missing 'code' parameter.")
#     def log_message(self, *args, **kwargs):
#         pass  # keep console clean
#
# server = http.server.HTTPServer(("127.0.0.1", port), Handler)
# t = threading.Thread(target=server.serve_forever, daemon=True)
# t.start()
#
# # Open consent screen
# auth_link = f"{AUTH_URL}?{urlencode(params)}"
# print("Opening browser for Google consent…")
# webbrowser.open(auth_link)
#
# # Wait for the code
# import time
# for _ in range(300):  # up to ~5 minutes
#     if auth_code_holder["code"]:
#         break
#     time.sleep(0.2)
#
# server.shutdown()
#
# code = auth_code_holder["code"]
# if not code:
#     raise SystemExit("Did not receive an authorization code (timed out).")
#
# # Exchange code for tokens
# resp = requests.post(
#     TOKEN_URL,
#     data={
#         "client_id": GOOGLE_CLIENT_ID,
#         "client_secret": GOOGLE_CLIENT_SECRET,
#         "code": code,
#         "redirect_uri": redirect_uri,
#         "grant_type": "authorization_code",
#     },
#     timeout=15,
# )
# resp.raise_for_status()
# tokens = resp.json()
#
# refresh = tokens.get("refresh_token")
# access = tokens.get("access_token")
#
# if not refresh:
#     raise SystemExit(
#         "No refresh_token returned. Try again and ensure 'prompt=consent' and use the same Desktop client. "
#         "If you previously approved this client, revoke access at https://myaccount.google.com/permissions and retry."
#     )
#
# print("\n=== SUCCESS ===")
# print("GOOGLE_REFRESH_TOKEN=", refresh)
# print("\n(You can also note the current access token if you want to test immediately):")
# print("ACCESS_TOKEN=", access)
#
#
#
