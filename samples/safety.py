"""Guardrails shared by every tool that controls the computer or browser.

- Kill switch: Ctrl+Alt+K sets HALT; every control tool and the brain loop check it.
- Control grant: the first control action each session needs a spoken yes, valid for a few minutes.
- Protected list: banking, payments, crypto and password-manager sites/windows are off-limits to automation.
- Secrets filter: card numbers, SSN/SIN-looking numbers are never typed by Jarvis.
- Audit log: every control action is appended to data/actions.log.
"""
import ctypes
import datetime as dt
import os
import re
import threading
import time
from urllib.parse import urlparse

import config

HALT = threading.Event()
CONFIRM = None  # fallback confirmation channel: callable(question) -> bool
_tl = threading.local()  # per-thread: the confirmation channel and whether this thread is the autopilot
AUTOPILOT_ACTIVE = threading.Event()  # set while an autopilot run owns the browser
_granted_until = 0.0
GRANT_SECONDS = int(float(os.getenv("JARVIS_GRANT_MINUTES", "10")) * 60)
LOG_FILE = config.DATA_DIR / "actions.log"

# Hostnames: tokens containing a dot match the domain or its subdomains; others match as substrings.
DEFAULT_BLOCKED = (
    "paypal,venmo,wise.com,coinbase,binance,kraken,robinhood,schwab,fidelity,vanguard,wealthsimple,questrade,"
    "rbcroyalbank.com,rbc.com,td.com,tdcanadatrust,scotiabank,bmo.com,cibc.com,tangerine.ca,desjardins,"
    "chase.com,wellsfargo,bankofamerica,citi.com,americanexpress,capitalone,"
    "1password,bitwarden,lastpass,dashlane,keepersecurity"
)
BLOCKED = [t.strip().lower() for t in os.getenv("JARVIS_BLOCKED", DEFAULT_BLOCKED).split(",") if t.strip()]
# Window titles that must never be driven or looked at (substring, case-insensitive)
BLOCKED_TITLES = [t for t in BLOCKED if "." not in t] + [
    "password manager", "keepass", "windows security", "user account control", "credential",
]
# Careers portals and job platforms stay usable even on a protected brand (e.g. jobs.td.com, Workday tenants).
DEFAULT_ALLOWED = ("career,jobs,myworkdayjobs,workday,taleo,icims,greenhouse,lever.co,successfactors,"
                   "smartrecruiters,ashbyhq,eightfold,avature,phenompeople,jobvite,brassring,recruiting")
ALLOWED = [t.strip().lower() for t in os.getenv("JARVIS_ALLOW_SITES", DEFAULT_ALLOWED).split(",") if t.strip()]

_SENSITIVE = [
    re.compile(r"\b(?:\d[ -]?){13,19}\b"),          # payment card number
    re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),            # US SSN
    re.compile(r"\b\d{3}[ -]\d{3}[ -]\d{3}\b"),      # Canadian SIN
]


class Halted(Exception):
    pass


ON_HALT = []  # callbacks (e.g. stop the autopilot)


def halt():
    HALT.set()
    log_action("EMERGENCY STOP")
    for cb in ON_HALT:
        try:
            cb()
        except Exception:
            pass


def log_action(text: str):
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(f"{dt.datetime.now().isoformat(timespec='seconds')}  {text}\n")
    except Exception:
        pass


def set_confirm(fn):
    """Called by each Brain on its own thread, so the voice brain and the autopilot don't overwrite each other."""
    _tl.confirm = fn


def mark_autopilot_thread(on=True):
    _tl.autopilot = on


def is_autopilot_thread() -> bool:
    return getattr(_tl, "autopilot", False)


_browser_lock = threading.Lock()
_browser_owner = None   # thread ident of the background worker (autopilot or an agent) using the browser


def claim_browser(timeout=0.0) -> bool:
    """A background worker takes the browser. Returns False if someone else has it after `timeout` seconds."""
    global _browser_owner
    me = threading.get_ident()
    deadline = time.time() + timeout
    while True:
        with _browser_lock:
            if _browser_owner in (None, me):
                _browser_owner = me
                return True
        if time.time() >= deadline:
            return False
        time.sleep(0.5)


def release_browser():
    global _browser_owner
    with _browser_lock:
        if _browser_owner == threading.get_ident():
            _browser_owner = None


def browser_busy_for_me() -> bool:
    """True when a background worker owns the browser and the caller is someone else (e.g. the voice brain)."""
    owner = _browser_owner
    if owner is not None and owner != threading.get_ident():
        return True
    return AUTOPILOT_ACTIVE.is_set() and not is_autopilot_thread()


# ---- unattended agents: what each one may do without asking ----
TRUST_CHOICES = ("submit_forms", "send_messages", "create_calendar_events", "save_email_drafts")
_SEND = re.compile(r"\b(send|reply|post|comment|message|publish)\b", re.I)


def mark_agent_thread(trusted):
    _tl.agent = True
    _tl.trusted = set(trusted or ())
    _tl.declined = []


def declined_actions():
    return list(getattr(_tl, "declined", []))


def is_agent_thread() -> bool:
    return getattr(_tl, "agent", False)


def agent_allows(question: str, trusted) -> bool:
    """Policy for an agent running unattended. Money, deleting, shell commands and code jobs: never."""
    q = (question or "").strip()
    ql = q.lower()
    trusted = set(trusted or ())
    if re.search(r"\b(pay|payment|purchase|buy|checkout|order|donate|transfer|withdraw|delete|remove|close account|"
                 r"deactivate|unsubscribe)\b", ql):
        return False
    if ql.startswith(("i'm about to run", "hand this to the coding agent", "build ", "forget ", "lock the screen")):
        return False
    if ql.startswith("save a draft"):
        return "save_email_drafts" in trusted
    if ql.startswith("add ") and "calendar" in ql:
        return "create_calendar_events" in trusted
    if ql.startswith("upload "):
        return "submit_forms" in trusted
    if ql.startswith(("type ", "press ")):
        return bool(trusted & {"submit_forms", "send_messages"})
    if ql.startswith("click "):
        label = q[6:].rsplit(" on ", 1)[0]
        if _SEND.search(label):
            return "send_messages" in trusted
        return "submit_forms" in trusted and bool(_AP_OK.search(label))
    return False


# Autopilot approves the clicks an application needs and nothing that spends money, deletes, or posts publicly.
_AP_OK = re.compile(r"\b(submit|apply|application|next|continue|review|save|agree|accept|confirm|acknowledge|"
                    r"i understand|upload|attach|finish|done|start|autofill|use my last|yes|send application)\b", re.I)
_AP_NEVER = re.compile(r"\b(pay|payment|purchase|buy|checkout|order|donate|transfer|withdraw|delete|remove|"
                       r"unsubscribe|subscribe|book|reserve|post|publish|tweet|share|invite|connect|follow|message|"
                       r"sign out|log out|close account|deactivate)\b", re.I)


def autopilot_allows(question: str) -> bool:
    q = (question or "").strip()
    ql = q.lower()
    if ql.startswith("upload "):
        return True  # browser_upload already restricts files to JARVIS_DOC_DIRS
    if ql.startswith("type ") or ql.startswith("press "):
        return True  # pressing Enter inside an application form (the typed text itself isn't judged)
    if ql.startswith("click "):
        label = q[6:].rsplit(" on ", 1)[0]  # judge the button label, not the site name
        return bool(_AP_OK.search(label)) and not _AP_NEVER.search(label)
    return False


def confirm(question: str) -> bool:
    """Fails closed: no confirmation channel means no. Autopilot uses its click policy instead of asking."""
    if is_autopilot_thread():
        ok = autopilot_allows(question)
        log_action(f"autopilot {'APPROVED' if ok else 'DECLINED'}: {question}")
        return ok
    if is_agent_thread():
        ok = agent_allows(question, getattr(_tl, "trusted", ()))
        log_action(f"agent {'APPROVED' if ok else 'DECLINED'}: {question}")
        if not ok:
            getattr(_tl, "declined", []).append(question)
        return ok
    fn = getattr(_tl, "confirm", None) or CONFIRM
    return bool(fn and fn(question))


def granted() -> bool:
    return time.time() < _granted_until


def grant(seconds=None):
    global _granted_until
    _granted_until = max(_granted_until, time.time() + (seconds or GRANT_SECONDS))
    log_action(f"control granted for {seconds or GRANT_SECONDS}s")


def revoke():
    global _granted_until
    _granted_until = 0.0


def looks_sensitive(text: str) -> bool:
    return any(p.search(text or "") for p in _SENSITIVE)


def site_blocked(url: str) -> bool:
    parsed = urlparse(url if "://" in url else "https://" + url)
    host = (parsed.hostname or "").lower()
    path = (parsed.path or "").lower()
    if any(tok in host for tok in ALLOWED) or re.search(r"/(careers?|jobs)(/|$)", path):
        return False
    for tok in BLOCKED:
        if "." in tok:
            if host == tok or host.endswith("." + tok):
                return True
        elif tok in host:
            return True
    return False


def window_blocked(title: str) -> bool:
    t = (title or "").lower()
    if any(w in t for w in ("career", "jobs", "job application", "workday", "apply")) and \
            not any(w in t for w in ("password manager", "windows security", "user account control", "credential")):
        return False
    return any(tok in t for tok in BLOCKED_TITLES)


def active_window_title() -> str:
    try:
        user32 = ctypes.windll.user32
        hwnd = user32.GetForegroundWindow()
        buf = ctypes.create_unicode_buffer(512)
        user32.GetWindowTextW(hwnd, buf, 512)
        return buf.value
    except Exception:
        return ""


def check_running():
    if HALT.is_set():
        raise Halted("Stopped by the emergency stop hotkey.")
