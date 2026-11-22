"""JARVIS Universal Multi-User Mailbox Deep Query Engine
Supports:
1. Universal IMAP access (App Passwords) for ANY user.
2. Local OAuth credentials for local master session.
3. Completely clean of hardcoded personal information.
"""

from __future__ import annotations

import email
from email.header import decode_header
import imaplib
import json
import os
import platform
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx
import psutil
from fastapi import FastAPI, Header, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

app = FastAPI(title="JARVIS Hologram HUD")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DASHBOARD_DIR = Path(__file__).parent.resolve()
CONNECTORS_DIR = Path.home() / ".openjarvis" / "connectors"
GMAIL_FILE = CONNECTORS_DIR / "gmail.json"


# In-memory session store for connected users (email -> app_password)
USER_SESSIONS: Dict[str, str] = {}


class ConnectRequest(BaseModel):
    email: str
    app_password: str


def clean_header_text(header_val: Optional[str]) -> str:
    if not header_val:
        return ""
    try:
        decoded_parts = decode_header(header_val)
        out = []
        for text, enc in decoded_parts:
            if isinstance(text, bytes):
                out.append(text.decode(enc or "utf-8", errors="ignore"))
            else:
                out.append(str(text))
        return "".join(out)
    except Exception:
        return str(header_val)


def extract_body_snippet(msg: email.message.Message, max_len: int = 150) -> str:
    snippet = ""
    try:
        if msg.is_multipart():
            for part in msg.walk():
                ctype = part.get_content_type()
                disp = str(part.get("Content-Disposition"))
                if ctype == "text/plain" and "attachment" not in disp:
                    payload = part.get_payload(decode=True)
                    if payload:
                        snippet = payload.decode("utf-8", errors="ignore")
                        break
        else:
            payload = msg.get_payload(decode=True)
            if payload:
                snippet = payload.decode("utf-8", errors="ignore")
    except Exception:
        snippet = ""

    clean = " ".join(snippet.split())
    if len(clean) > max_len:
        return clean[:max_len] + "..."
    return clean or "(No body content preview)"


def fetch_emails_via_imap(user_email: str, app_pwd: str, query: str = "", limit: int = 15) -> List[Dict[str, Any]]:
    """Connects directly to Gmail IMAP using the user's specific App Password."""
    pwd_clean = app_pwd.replace(" ", "")
    try:
        mail = imaplib.IMAP4_SSL("imap.gmail.com", 993, timeout=12.0)
        mail.login(user_email, pwd_clean)
        mail.select("INBOX", readonly=True)

        if query:
            # Search subject, body, or from
            # Gmail IMAP supports standard or X-GM-RAW
            try:
                status, data = mail.search(None, f'(OR (FROM "{query}") (SUBJECT "{query}"))')
            except Exception:
                status, data = mail.search(None, "ALL")
        else:
            status, data = mail.search(None, "ALL")

        if status != "OK" or not data or not data[0]:
            mail.logout()
            return []

        msg_ids = data[0].split()
        total_found = len(msg_ids)
        target_ids = msg_ids[-limit:]

        results = []
        for mid in reversed(target_ids):
            res, msg_data = mail.fetch(mid, "(RFC822.HEADER BODY.PEEK[TEXT])")
            if res != "OK" or not msg_data:
                continue

            raw_bytes = None
            for part in msg_data:
                if isinstance(part, tuple) and part[1]:
                    raw_bytes = part[1]
                    break

            if not raw_bytes:
                continue

            msg = email.message_from_bytes(raw_bytes)
            subject = clean_header_text(msg.get("Subject", "(No Subject)"))
            sender = clean_header_text(msg.get("From", "Unknown"))
            date_str = clean_header_text(msg.get("Date", ""))
            snippet = extract_body_snippet(msg)

            results.append({
                "id": mid.decode("utf-8", errors="ignore"),
                "from": sender,
                "subject": subject,
                "date": date_str,
                "snippet": snippet,
            })

        mail.logout()
        return results
    except Exception as e:
        return [{"error": f"IMAP connection failed: {str(e)}"}]


def get_local_oauth_token() -> str:
    """Fallback only for local dev session if configured."""
    if not GMAIL_FILE.exists():
        return ""
    try:
        data = json.loads(GMAIL_FILE.read_text(encoding="utf-8"))
        return data.get("access_token", "")
    except Exception:
        return ""


def extract_search_terms(raw_query: str) -> str:
    """Clean natural language wrapper words so the exact search query hits mail."""
    q = raw_query.strip()
    stop_phrases = [
        "what are my emails regarding", "what are my emails about", "what are my emails from",
        "find emails regarding", "find emails about", "find emails from", "find emails with",
        "find email from", "find email about", "search emails from", "search emails about",
        "search email from", "search email about", "show me emails from", "show me emails about",
        "show emails from", "get emails from", "tell me about",
        "check emails from", "check emails about", "emails from",
        "email from", "emails about", "summarize emails from", "summarize email from",
        "summarize emails about", "summarize email about", "summarize my email from",
        "summarize my emails from", "can you find emails from", "can you check emails from",
        "fetch emails from", "give me emails from"
    ]
    lower_q = q.lower()
    for phrase in stop_phrases:
        if phrase in lower_q:
            idx = lower_q.find(phrase)
            after = q[idx + len(phrase):].strip()
            if after:
                return after.strip(" ?.!\"'")
    
    cleaned = re.sub(r'^(find|search|show|get|check|tell me about|summarize)\s+', '', q, flags=re.IGNORECASE)
    cleaned = re.sub(r'\s+(emails|email|messages|message|mail|mails)$', '', cleaned, flags=re.IGNORECASE)
    return cleaned.strip(" ?.!\"'")


@app.post("/api/connect")
def connect_user_mailbox(payload: ConnectRequest):
    """Authenticate and test connection for any user's email."""
    email_addr = payload.email.strip().lower()
    app_pwd = payload.app_password.strip().replace(" ", "")

    if not email_addr or not app_pwd:
        raise HTTPException(status_code=400, detail="Email and App Password required")

    try:
        mail = imaplib.IMAP4_SSL("imap.gmail.com", 993, timeout=10.0)
        mail.login(email_addr, app_pwd)
        status, counts = mail.select("INBOX", readonly=True)
        total_msgs = counts[0].decode() if counts and counts[0] else "0"
        mail.logout()

        # Cache session
        USER_SESSIONS[email_addr] = app_pwd

        return {
            "status": "success",
            "email": email_addr,
            "total_messages": total_msgs,
            "message": f"Successfully authenticated {email_addr}."
        }
    except Exception as e:
        raise HTTPException(
            status_code=401,
            detail=f"Authentication failed. Please check your Gmail address and 16-letter App Password. Error: {str(e)}"
        )


@app.get("/api/telemetry")
def get_telemetry(x_user_email: Optional[str] = Header(default=None)) -> Dict[str, Any]:
    cpu = psutil.cpu_percent(interval=None)
    mem = psutil.virtual_memory().percent

    current_user = "Guest"
    if isinstance(x_user_email, str) and x_user_email.strip():
        current_user = x_user_email.strip().lower()

    user_display = current_user.split("@")[0].title() if current_user != "Guest" else "Guest User"
    
    total_messages = "Standby"
    if current_user in USER_SESSIONS:
        total_messages = "Live Ingestion"

    return {
        "host_platform": f"{platform.system()} {platform.machine()}",
        "engine_version": "v1.0.5 Autonomous AI",
        "cpu_utilization": f"{cpu:.1f}%",
        "memory_usage": f"{mem:.1f}%",
        "data_sources": "Universal IMAP / Cloud",
        "total_emails_indexed": total_messages,
        "user_name": user_display,
        "user_email": current_user if current_user != "Guest" else "",
        "timestamp": datetime.now().strftime("%A, %B %d, %Y | %I:%M %p"),
    }


@app.get("/api/emails")
def get_emails(
    q: str = Query(default=""),
    limit: int = Query(default=12),
    x_user_email: Optional[str] = Header(None),
    x_app_password: Optional[str] = Header(None),
) -> List[Dict[str, Any]]:
    # 1. Check if user credentials sent in header or cached
    email_addr = (x_user_email or "").strip().lower()
    app_pwd = (x_app_password or "").strip() or USER_SESSIONS.get(email_addr, "")

    if email_addr and app_pwd:
        return fetch_emails_via_imap(email_addr, app_pwd, query=q, limit=limit)

    return []


@app.post("/api/ask")
async def ask_jarvis(request: Request) -> Dict[str, Any]:
    body = await request.json()
    query = body.get("query", "").strip()
    user_email = body.get("email", "").strip().lower()
    app_pwd = body.get("app_password", "").strip() or USER_SESSIONS.get(user_email, "")

    if not query:
        return {"response": "Please specify a query, Sir."}

    if not user_email or not app_pwd:
        return {
            "response": (
                "Sir, no mailbox credentials detected for this session. "
                "Please click **'Set Up Gmail Access'** above to connect your mailbox with your App Password."
            )
        }

    clean_search = extract_search_terms(query)
    search_target = clean_search if clean_search else query

    # Fetch live emails for THIS user
    matched_emails = fetch_emails_via_imap(user_email, app_pwd, query=search_target, limit=6)
    if not matched_emails or (len(matched_emails) == 1 and "error" in matched_emails[0]):
        # Retry with ALL to perform client-side substring matching across recent 20
        all_recent = fetch_emails_via_imap(user_email, app_pwd, query="", limit=20)
        target_lower = search_target.lower()
        matched_emails = [
            m for m in all_recent
            if target_lower in m.get("subject", "").lower()
            or target_lower in m.get("from", "").lower()
            or target_lower in m.get("snippet", "").lower()
        ]

    if not matched_emails:
        return {
            "response": (
                f"Sir, I searched your mailbox ({user_email}) for '{search_target}', "
                f"but found no corresponding emails. You can try searching by sender name or keyword."
            )
        }

    res_lines = [f"**Archive Search Complete — Records for '{search_target}':**\n"]
    for m in matched_emails[:5]:
        sender = m.get("from", "").split("<")[0].strip()
        res_lines.append(
            f"• **{m.get('subject')}**\n"
            f"  _From: {sender} | Date: {m.get('date')}_\n"
            f"  **Summary:** {m.get('snippet')}\n"
        )
    return {"response": "\n".join(res_lines)}


@app.get("/", response_class=HTMLResponse)
def serve_dashboard():
    html_path = DASHBOARD_DIR / "templates" / "index.html"
    if not html_path.exists():
        html_path = DASHBOARD_DIR / "index.html"
    return html_path.read_text(encoding="utf-8")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8090)
