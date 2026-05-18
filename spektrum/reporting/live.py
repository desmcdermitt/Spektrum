import asyncio
import json
import os
import queue as stdlib_queue
import select
import socket
import sys
import threading
import time
from typing import (
    Any,
    Optional,
)

from spektrum import logger

log = logger.get(__name__)


HTML_PAGE = '''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Spektrum Live</title>
  <style>
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body { font-family: 'Segoe UI', system-ui, sans-serif; background: #0f1117; color: #e1e4e8;
           line-height: 1.5; }
    header { background: #161b22; border-bottom: 1px solid #30363d; padding: 16px 24px;
             display: flex; align-items: center; justify-content: space-between; }
    h1 { font-size: 1.25rem; font-weight: 600; color: #58a6ff; }
    #run-context { font-size: 0.78rem; color: #8b949e; margin-top: 2px;
                   font-family: 'Courier New', monospace; }
    #connection-status { font-size: 0.85rem; color: #8b949e; display: flex;
                         align-items: center; gap: 6px; }
    #status-dot { width: 10px; height: 10px; border-radius: 50%; background: #d29922;
                  flex-shrink: 0; }
    #banner { display: none; margin: 16px 24px 0; padding: 12px 16px; border-radius: 6px;
              font-weight: 600; font-size: 0.95rem; }
    #banner.run-passed { background: #0d4a23; border: 1px solid #3fb950; color: #3fb950; }
    #banner.run-failed { background: #4a0d0d; border: 1px solid #f85149; color: #f85149; }
    main { padding: 16px 24px; }

    /* Root spec card */
    .spec-section { margin-bottom: 16px; background: #161b22; border: 1px solid #30363d;
                    border-radius: 8px; overflow: hidden; }
    .spec-header { padding: 12px 16px; font-weight: 700; font-size: 1rem; background: #21262d;
                   border-bottom: 1px solid #30363d; color: #58a6ff;
                   border-left: 4px solid #388bfd; }

    /* Nested child specs */
    .spec-children { padding: 8px; background: #0d1117; border-top: 1px solid #21262d;
                     display: flex; flex-direction: column; gap: 6px; }
    .spec-nested { background: #161b22; border: 1px solid #21262d; border-radius: 6px;
                   overflow: hidden; }
    .spec-header-1 { padding: 9px 14px; font-weight: 600; font-size: 0.9rem; background: #1c2128;
                     border-bottom: 1px solid #21262d; color: #c9d1d9;
                     border-left: 3px solid #6e7681; }
    .spec-header-2 { padding: 8px 12px; font-weight: 500; font-size: 0.85rem; background: #161b22;
                     border-bottom: 1px solid #21262d; color: #8b949e;
                     border-left: 2px solid #30363d; }

    /* Cases */
    .case-row { border-bottom: 1px solid #21262d; }
    .case-row:last-child { border-bottom: none; }
    .case-header { display: flex; align-items: center; padding: 9px 16px; cursor: pointer;
                   user-select: none; gap: 10px; }
    .case-header:hover { background: #1c2128; }
    .spec-nested .case-header { padding: 7px 14px; }
    .case-name { flex: 1; font-size: 0.875rem; font-family: 'Courier New', monospace;
                 color: #c9d1d9; }
    .case-duration { font-size: 0.75rem; color: #8b949e; min-width: 56px; text-align: right; }
    .toggle-icon { font-size: 0.65rem; color: #8b949e; min-width: 10px; }
    .badge { display: inline-block; padding: 1px 8px; border-radius: 12px; font-size: 0.7rem;
             font-weight: 600; text-transform: uppercase; letter-spacing: 0.04em;
             min-width: 60px; text-align: center; }
    .badge-pending { background: #21262d; color: #8b949e; border: 1px solid #30363d; }
    .badge-running { background: #1a3a5c; color: #58a6ff; border: 1px solid #388bfd;
                     animation: pulse 1.4s ease-in-out infinite; }
    .badge-passed { background: #0d4a23; color: #3fb950; border: 1px solid #2ea043; }
    .badge-failed { background: #4a0d0d; color: #f85149; border: 1px solid #da3633; }
    .badge-skipped { background: #2a2010; color: #d29922; border: 1px solid #9e6a03; }
    @keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.55; } }
    .case-details { display: none; padding: 10px 16px; background: #0d1117;
                    border-top: 1px solid #21262d; font-size: 0.82rem; }
    .case-details.open { display: block; }
    .detail-label { font-weight: 600; color: #6e7681; margin-bottom: 4px; font-size: 0.72rem;
                    text-transform: uppercase; letter-spacing: 0.06em; }
    .error-block { color: #f85149; font-family: 'Courier New', monospace; white-space: pre-wrap;
                   word-break: break-word; font-size: 0.8rem; }
    .skip-reason { color: #d29922; }
    .expect-item { padding: 1px 0; font-family: 'Courier New', monospace; font-size: 0.8rem; }
    .expect-item.pass { color: #3fb950; }
    .expect-item.fail { color: #f85149; }
    .expect-values { margin: 2px 0 4px 18px; font-family: 'Courier New', monospace;
                     font-size: 0.78rem; display: flex; flex-direction: column; gap: 1px; }
    .expect-values .val-line { white-space: pre-wrap; word-break: break-all; }
    .expect-values .val-label { color: #6e7681; }
    .expect-values .val-actual { color: #f85149; }
    .expect-values .val-expected { color: #3fb950; }
    .no-details { color: #6e7681; font-style: italic; }
    .hdr-btn { padding: 6px 14px; border-radius: 6px; border: 1px solid #30363d;
               background: #21262d; color: #c9d1d9; font-size: 0.82rem; cursor: pointer; }
    .hdr-btn:hover { background: #2d333b; border-color: #58a6ff; color: #58a6ff; }

    @media print {
      * { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
      body { background: #fff; color: #1f2328; }
      header { background: #f6f8fa; border-bottom: 1px solid #d0d7de; break-after: avoid; }
      h1 { color: #0969da; }
      #run-context { color: #57606a; }
      #connection-status, .hdr-btn { display: none; }
      #banner { display: block !important; break-after: avoid; }
      #banner.run-passed { background: #dafbe1; border-color: #2da44e; color: #1a7f37; }
      #banner.run-failed { background: #ffebe9; border-color: #cf222e; color: #cf222e; }
      main { padding: 12px 16px; break-before: avoid; }
      .spec-section { background: #fff; border-color: #d0d7de; }
      .spec-header { background: #f6f8fa; color: #0969da; border-color: #d0d7de; }
      .spec-children { background: #f6f8fa; border-color: #d0d7de; }
      .spec-nested { background: #fff; border-color: #d0d7de; }
      .spec-header-1 { background: #f6f8fa; color: #1f2328; border-color: #d0d7de; }
      .spec-header-2 { background: #fff; color: #57606a; border-color: #d0d7de; }
      .case-row { border-color: #d0d7de; }
      .case-header { cursor: default; break-inside: avoid; }
      .case-header:hover { background: transparent; }
      .case-name { color: #1f2328; }
      .case-duration { color: #57606a; }
      .toggle-icon { display: none; }
      .badge-pending { background: #f6f8fa; color: #57606a; border-color: #d0d7de; }
      .badge-running { background: #ddf4ff; color: #0550ae; border-color: #54aeff;
                        animation: none; }
      .badge-passed { background: #dafbe1; color: #1a7f37; border-color: #2da44e; }
      .badge-failed { background: #ffebe9; color: #cf222e; border-color: #cf222e; }
      .badge-skipped { background: #fff8c5; color: #9a6700; border-color: #d4a72c; }
      .case-details { display: block !important; background: #f6f8fa; border-color: #d0d7de; }
      .detail-label { color: #57606a; }
      .error-block { color: #cf222e; }
      .skip-reason { color: #9a6700; }
      .expect-item.pass { color: #1a7f37; }
      .expect-item.fail { color: #cf222e; }
      .expect-values .val-label { color: #57606a; }
      .expect-values .val-actual { color: #cf222e; }
      .expect-values .val-expected { color: #1a7f37; }
      .no-details { color: #57606a; }
    }
  </style>
</head>
<body>
  <header>
    <div><h1>&#9889; Spektrum Live</h1><div id="run-context"></div></div>
    <div style="display:flex;align-items:center;gap:8px;">
      <button class="hdr-btn" onclick="expandAll()">&#9660; Expand All</button>
      <button class="hdr-btn" onclick="collapseAll()">&#9654; Collapse All</button>
      <button class="hdr-btn" onclick="window.print()">&#128438; Save PDF</button>
      <div id="connection-status"><span id="status-dot"></span>Connecting...</div>
    </div>
  </header>
  <div id="banner"></div>
  <main id="specs"></main>
  <script>
    var state = { specs: {}, rootOrder: [] };

    function setDetailOpen(detailEl, open) {
      detailEl.classList.toggle('open', open);
      var icon = detailEl.previousElementSibling &&
        detailEl.previousElementSibling.querySelector('.toggle-icon');
      if (icon) { icon.innerHTML = open ? '&#9660;' : '&#9654;'; }
    }

    function expandAll() {
      document.querySelectorAll('.case-details').forEach(function(d) { setDetailOpen(d, true); });
    }

    function collapseAll() {
      document.querySelectorAll('.case-details').forEach(function(d) { setDetailOpen(d, false); });
    }

    var _printState = null;
    window.onbeforeprint = function() {
      _printState = [];
      document.querySelectorAll('.case-details').forEach(function(d) {
        _printState.push(d.classList.contains('open'));
        setDetailOpen(d, true);
      });
    };
    window.onafterprint = function() {
      if (!_printState) { return; }
      document.querySelectorAll('.case-details').forEach(function(d, i) {
        setDetailOpen(d, !!_printState[i]);
      });
      _printState = null;
    };

    function connect() {
      var es = new EventSource('/events');
      es.onopen = function() { setStatus('Connected', '#3fb950'); };
      es.onerror = function() { setStatus('Reconnecting…', '#d29922'); };
      es.addEventListener('snapshot', function(e) { handleSnapshot(JSON.parse(e.data)); });
      es.addEventListener('case-update', function(e) { handleCaseUpdate(JSON.parse(e.data)); });
      es.addEventListener('spec-cases-updated', function(e) {
        handleSpecCasesUpdated(JSON.parse(e.data)); });
      es.addEventListener('run-complete', function(e) { handleRunComplete(JSON.parse(e.data)); });
    }

    function setStatus(text, color) {
      var dot = document.getElementById('status-dot');
      dot.style.background = color;
      var cs = document.getElementById('connection-status');
      cs.childNodes[1] ? (cs.childNodes[1].textContent = text)
        : cs.appendChild(document.createTextNode(text));
    }

    function buildTree(specs) {
      var byId = {};
      state.rootOrder = [];
      specs.forEach(function(s) { byId[s.id] = Object.assign({}, s, { _children: [] }); });
      specs.forEach(function(s) {
        if (s.parent_id && byId[s.parent_id]) {
          byId[s.parent_id]._children.push(s.id);
        } else {
          state.rootOrder.push(s.id);
        }
      });
      state.specs = byId;
    }

    function handleSnapshot(data) {
      buildTree(data.specs || []);
      var container = document.getElementById('specs');
      container.innerHTML = '';
      state.rootOrder.forEach(function(id) {
        container.appendChild(renderSpec(state.specs[id], 0));
      });
      if (data.run_context && data.run_context.module_name) {
        document.getElementById('run-context').textContent = data.run_context.module_name;
      }
      if (data.run_complete) { handleRunComplete(data.run_complete); }
    }

    function renderSpec(spec, depth) {
      var isRoot = depth === 0;
      var section = document.createElement('div');
      section.className = isRoot ? 'spec-section' : 'spec-nested';
      section.id = 'spec-' + spec.id;

      var header = document.createElement('div');
      header.className = isRoot ? 'spec-header' : ('spec-header-' + Math.min(depth, 2));
      header.textContent = spec.display_name || spec.name;
      section.appendChild(header);

      (spec.cases || []).forEach(function(c) { section.appendChild(renderCase(spec.id, c)); });

      if (spec._children && spec._children.length) {
        var children = document.createElement('div');
        children.className = 'spec-children';
        spec._children.forEach(function(childId) {
          var child = state.specs[childId];
          if (child) { children.appendChild(renderSpec(child, depth + 1)); }
        });
        section.appendChild(children);
      }

      return section;
    }

    function renderCase(specId, c) {
      var row = document.createElement('div');
      row.className = 'case-row';
      row.id = 'case-' + specId + '-' + c.name;
      var status = c.status || 'pending';
      var durHtml = (c.duration != null)
        ? '<span class="case-duration">' + formatDuration(c.duration * 1000) + '</span>'
        : '<span class="case-duration"></span>';
      row.innerHTML =
        '<div class="case-header" onclick="toggleDetails(this)">' +
          '<span class="case-name">' + esc(decodeUnicode(c.display_name || c.name)) + '</span>' +
          durHtml +
          '<span class="badge badge-' + status + '">' + status + '</span>' +
          '<span class="toggle-icon">&#9654;</span>' +
        '</div>' +
        '<div class="case-details">' + renderDetails(c) + '</div>';
      return row;
    }

    function renderDetails(c) {
      var d = c.details;
      if (!d) { return '<span class="no-details">No details yet.</span>'; }
      var html = '';
      if (d.errors && d.errors.length) {
        html += '<div class="detail-label">Error</div>';
        d.errors.forEach(function(lines) {
          html += '<div class="error-block">' + esc(decodeUnicode(lines.join('\\n'))) + '</div>';
        });
      }
      if (d.skip_reason) {
        html += '<div class="detail-label">Skip Reason</div>'
          + '<div class="skip-reason">' + esc(d.skip_reason) + '</div>';
      }
      if (d.expects && d.expects.length) {
        html += '<div class="detail-label" style="margin-top:6px">Assertions</div>';
        d.expects.forEach(function(e) {
          html += '<div class="expect-item ' + (e.success ? 'pass' : 'fail') + '">'
            + (e.success ? '&#10003; ' : '&#10007; ')
            + esc(decodeUnicode(e.evaluation)) + '</div>';
          if (!e.success && e.target !== undefined && e.expected !== undefined) {
            html += '<div class="expect-values">' +
              '<div class="val-line"><span class="val-label">actual:   </span>'
              + '<span class="val-actual">' + esc(String(e.target)) + '</span></div>' +
              '<div class="val-line"><span class="val-label">expected: </span>'
              + '<span class="val-expected">' + esc(String(e.expected)) + '</span></div>' +
            '</div>';
          }
        });
      }
      if (!html) { html = '<span class="no-details">No details available.</span>'; }
      return html;
    }

    var LIFECYCLE_BEFORE = { 'before_all': true, 'before_each': true };
    var LIFECYCLE_AFTER = { 'after_all': true, 'after_each': true };

    function handleSpecCasesUpdated(data) {
      var spec = state.specs[data.spec_id];
      if (!spec) { return; }
      var specEl = document.getElementById('spec-' + data.spec_id);
      if (!specEl) { return; }
      var newNames = {};
      data.cases.forEach(function(c) { newNames[c.name] = c; });
      (spec.cases || []).forEach(function(c) {
        if (!newNames[c.name]) {
          var old = document.getElementById('case-' + data.spec_id + '-' + c.name);
          if (old) { old.parentNode.removeChild(old); }
        }
      });
      var existingByName = {};
      (spec.cases || []).forEach(function(c) { existingByName[c.name] = c; });
      spec.cases = data.cases.map(function(c) {
        return existingByName[c.name] || {
          name: c.name, display_name: c.display_name,
          status: 'pending', duration: null, details: null
        };
      });
      var childrenEl = specEl.querySelector('.spec-children');
      spec.cases.forEach(function(c) {
        if (!document.getElementById('case-' + data.spec_id + '-' + c.name)) {
          specEl.insertBefore(renderCase(data.spec_id, c), childrenEl || null);
        }
      });
    }

    function handleCaseUpdate(data) {
      var row = document.getElementById('case-' + data.spec_id + '-' + data.case_name);
      if (!row) {
        var specEl = document.getElementById('spec-' + data.spec_id);
        if (!specEl) { return; }
        var c = {
          name: data.case_name,
          display_name: data.case_name.replace(/_/g, ' '),
          status: data.status, duration: data.duration, details: data.details
        };
        row = renderCase(data.spec_id, c);
        var childrenEl = specEl.querySelector('.spec-children');
        if (LIFECYCLE_BEFORE[data.case_name]) {
          var firstCase = specEl.querySelector('.case-row');
          specEl.insertBefore(row, firstCase || childrenEl || null);
        } else {
          specEl.insertBefore(row, childrenEl || null);
        }
        var spec = state.specs[data.spec_id];
        if (spec) {
          if (LIFECYCLE_BEFORE[data.case_name]) { (spec.cases = spec.cases || []).unshift(c); }
          else { (spec.cases = spec.cases || []).push(c); }
        }
      }
      var badge = row.querySelector('.badge');
      badge.className = 'badge badge-' + data.status;
      badge.textContent = data.status;
      var dur = row.querySelector('.case-duration');
      if (data.duration != null) { dur.textContent = formatDuration(data.duration * 1000); }
      var details = row.querySelector('.case-details');
      details.innerHTML = renderDetails({ details: data.details });
      var spec = state.specs[data.spec_id];
      if (spec) {
        var c = (spec.cases || []).find(function(x) { return x.name === data.case_name; });
        if (c) { c.status = data.status; c.details = data.details; c.duration = data.duration; }
      }
    }

    function handleRunComplete(data) {
      var banner = document.getElementById('banner');
      var failed = data.failed || 0;
      var passed = data.passed || 0;
      var skipped = data.skipped || 0;
      var cls = failed > 0 ? 'run-failed' : 'run-passed';
      var icon = failed > 0 ? '✗' : '✓';
      banner.className = 'banner ' + cls;
      banner.style.display = 'block';
      banner.textContent = icon + ' ' + passed + ' passed, '
        + failed + ' failed, ' + skipped + ' skipped';
      document.title = failed > 0
        ? '✗ ' + failed + ' failed — Spektrum'
        : '✓ All passed — Spektrum';
      setStatus('Run complete', failed > 0 ? '#f85149' : '#3fb950');
    }

    function toggleDetails(header) {
      var details = header.nextElementSibling;
      var icon = header.querySelector('.toggle-icon');
      details.classList.toggle('open');
      icon.innerHTML = details.classList.contains('open') ? '&#9660;' : '&#9654;';
    }

    function decodeUnicode(s) {
      if (!s) { return s; }
      return String(s).replace(/\\+u([0-9a-fA-F]{4})/g, function(_, hex) {
        return String.fromCharCode(parseInt(hex, 16));
      });
    }

    function esc(s) {
      if (!s) { return ''; }
      return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;')
        .replace(/>/g, '&gt;').replace(/"/g, '&quot;');
    }

    function formatDuration(ms) {
      if (ms < 1000) { return Math.round(ms) + 'ms'; }
      if (ms < 60000) { return (ms / 1000).toFixed(1) + 's'; }
      var m = Math.floor(ms / 60000);
      var s = Math.round((ms % 60000) / 1000);
      return m + 'm ' + s + 's';
    }

    connect();
  </script>
</body>
</html>'''


def _default_json(obj: object) -> str:
    '''Fallback serializer: stringify objects that aren't natively JSON-serializable.'''
    return str(obj)


def _format_sse(event_type: str, data: dict) -> bytes:
    payload = json.dumps(data, default=_default_json, ensure_ascii=False)
    return ('event: ' + event_type + '\ndata: ' + payload + '\n\n').encode('utf-8')


class LiveServer:
    def __init__(self, port: int, event_queue: Any, linger: int = 5) -> None:
        self.port = port
        self._queue = event_queue
        self._linger = linger
        self._clients = []
        self._state = {}
        self._state_order = []
        self._run_complete = None
        self._run_context = None
        self._server = None
        self._shutdown_event = None
        self._consumer_task = None
        self._thread = None
        self._thread_ready = threading.Event()

    # ------------------------------------------------------------------
    # Thread-based entry points (used by SpektrumRunner with --live)
    # ------------------------------------------------------------------

    def start_in_thread(self) -> None:
        '''Start the live server in a daemon background thread.

        Returns after the TCP server is accepting connections.  The background
        thread uses a plain synchronous socket + select loop — no asyncio — so
        it is completely immune to any event-loop state in the calling thread.
        '''
        self._thread_ready.clear()
        self._thread = threading.Thread(target=self._serve_sync, daemon=True)
        self._thread.start()
        self._thread_ready.wait(timeout=10.0)

    # ------------------------------------------------------------------
    # Synchronous socket-based server (used by start_in_thread)
    # No asyncio — immune to event-loop patching in host environments.
    # ------------------------------------------------------------------

    def _serve_sync(self) -> None:
        '''Blocking socket/select server loop. Runs for the lifetime of the run.'''
        server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            server_sock.bind(('127.0.0.1', self.port))
        except OSError as exc:
            if 'Address already in use' in str(exc) or exc.errno == 98:
                log.error(
                    f'Error: Port {self.port} is already in use. '
                    f'Use --live-port to specify a different port.',
                )
                self._thread_ready.set()
                os._exit(1)
            raise

        server_sock.listen(10)
        server_sock.setblocking(False)
        self._thread_ready.set()

        sse_sockets = []     # non-blocking sockets with open SSE connections
        last_ping = time.monotonic()

        while True:
            all_readable = [server_sock] + sse_sockets
            try:
                readable, _, _ = select.select(all_readable, [], [], 0.05)
            except OSError:
                break

            dead = []
            for sock in readable:
                if sock is server_sock:
                    conn, _ = server_sock.accept()
                    sse_conn = self._handle_sync_connection(conn)
                    if sse_conn is not None:
                        sse_sockets.append(sse_conn)
                else:
                    # Client sent data — most likely a disconnect
                    try:
                        data = sock.recv(1024)
                        if not data:
                            dead.append(sock)
                    except BlockingIOError:
                        pass
                    except (OSError, BrokenPipeError):
                        dead.append(sock)

            for sock in dead:
                if sock in sse_sockets:
                    sse_sockets.remove(sock)
                try:
                    sock.close()
                except OSError:
                    pass

            # Drain the event queue
            done = False
            while True:
                try:
                    event = self._queue.get_nowait()
                except stdlib_queue.Empty:
                    break
                if self._process_event_sync(event, sse_sockets):
                    done = True
                    break

            if done:
                break

            # SSE keep-alive pings every 15 s
            now = time.monotonic()
            if now - last_ping > 15:
                last_ping = now
                ping_dead = []
                for sock in list(sse_sockets):
                    try:
                        sock.setblocking(True)
                        sock.sendall(b': ping\n\n')
                        sock.setblocking(False)
                    except OSError:
                        ping_dead.append(sock)
                for sock in ping_dead:
                    if sock in sse_sockets:
                        sse_sockets.remove(sock)
                    try:
                        sock.close()
                    except OSError:
                        pass

        # Linger: keep server open so the developer can read results
        if self._linger > 0:
            print(f'Live view available for {self._linger} more seconds...', flush=True)
            time.sleep(self._linger)

        for sock in sse_sockets:
            try:
                sock.close()
            except OSError:
                pass
        try:
            server_sock.close()
        except OSError:
            pass

    def _handle_sync_connection(self, conn: socket.socket) -> Optional[socket.socket]:
        '''Parse an incoming HTTP request and respond.  Returns the socket if
        it becomes an SSE connection, otherwise None.'''
        conn.settimeout(5.0)
        try:
            buf = b''
            while b'\r\n\r\n' not in buf:
                chunk = conn.recv(4096)
                if not chunk:
                    conn.close()
                    return None
                buf += chunk
                if len(buf) > 65536:
                    conn.close()
                    return None

            first_line = buf.split(b'\r\n', 1)[0].decode('utf-8', errors='replace')
            parts = first_line.strip().split()
            if len(parts) < 2:
                conn.close()
                return None

            path = parts[1].split('?', 1)[0]

            if path == '/':
                body = HTML_PAGE.encode('utf-8')
                response = (
                    b'HTTP/1.1 200 OK\r\n'
                    b'Content-Type: text/html; charset=utf-8\r\n'
                    b'Connection: close\r\n'
                    + ('Content-Length: ' + str(len(body)) + '\r\n').encode()
                    + b'\r\n'
                    + body
                )
                try:
                    conn.sendall(response)
                except OSError:
                    pass
                conn.close()
                return None

            elif path == '/events':
                try:
                    conn.sendall(
                        b'HTTP/1.1 200 OK\r\n'
                        b'Content-Type: text/event-stream\r\n'
                        b'Cache-Control: no-cache\r\n'
                        b'Connection: keep-alive\r\n'
                        b'X-Accel-Buffering: no\r\n'
                        b'\r\n'
                    )
                    conn.sendall(_format_sse('snapshot', self._build_snapshot()))
                except OSError:
                    conn.close()
                    return None
                conn.setblocking(False)
                return conn

            else:
                try:
                    conn.sendall(
                        b'HTTP/1.1 404 Not Found\r\n'
                        b'Content-Length: 0\r\n'
                        b'Connection: close\r\n\r\n'
                    )
                except OSError:
                    pass
                conn.close()
                return None

        except OSError:
            try:
                conn.close()
            except OSError:
                pass
            return None

    def _broadcast_sync(self, sse_sockets: list, event_type: str, data: dict) -> None:
        '''Send an SSE event to all connected clients, pruning dead sockets.'''
        msg = _format_sse(event_type, data)
        dead = []
        for sock in list(sse_sockets):
            try:
                sock.setblocking(True)
                sock.sendall(msg)
                sock.setblocking(False)
            except OSError:
                dead.append(sock)
        for sock in dead:
            if sock in sse_sockets:
                sse_sockets.remove(sock)
            try:
                sock.close()
            except OSError:
                pass

    def _apply_event(self, event: dict) -> bool:
        '''Apply state mutations for one event. Returns True when the run is complete.'''
        event_type = event.get('type')

        if event_type == 'run-started':
            self._run_context = {
                'search_path': event['search_path'],
                'module_name': event.get('module_name'),
            }

        elif event_type == 'spec-discovered':
            spec_id = event['spec_id']
            if spec_id not in self._state:
                self._state_order.append(spec_id)
            self._state[spec_id] = {
                'name': event['spec_name'],
                'display_name': event['spec_display_name'],
                'parent_id': event.get('parent_id'),
                'cases': {
                    c['name']: {
                        'name': c['name'],
                        'display_name': c['display_name'],
                        'status': 'pending',
                        'duration': None,
                        'details': None,
                    }
                    for c in event['cases']
                },
            }

        elif event_type == 'spec-cases-updated':
            spec_id = event['spec_id']
            if spec_id in self._state:
                existing = self._state[spec_id]['cases']
                self._state[spec_id]['cases'] = {
                    c['name']: existing.get(c['name'], {
                        'name': c['name'],
                        'display_name': c['display_name'],
                        'status': 'pending',
                        'duration': None,
                        'details': None,
                    })
                    for c in event['cases']
                }

        elif event_type == 'case-started':
            spec_id = event['spec_id']
            case_name = event['case_name']
            if spec_id in self._state and case_name in self._state[spec_id]['cases']:
                self._state[spec_id]['cases'][case_name]['status'] = 'running'

        elif event_type == 'assertion-added':
            spec_id = event['spec_id']
            case_name = event['case_name']
            assertion = event.get('assertion', {})
            if spec_id in self._state and case_name in self._state[spec_id]['cases']:
                case = self._state[spec_id]['cases'][case_name]
                if case['details'] is None:
                    case['details'] = {'expects': [], 'errors': [], 'skip_reason': None}
                case['details']['expects'].append(assertion)

        elif event_type == 'case-finished':
            spec_id = event['spec_id']
            case_name = event['case_name']
            status = event['status']
            duration = event.get('duration')
            details = event.get('details')
            if spec_id in self._state and case_name in self._state[spec_id]['cases']:
                self._state[spec_id]['cases'][case_name].update({
                    'status': status,
                    'duration': duration,
                    'details': details,
                })

        elif event_type == 'run-complete':
            self._run_complete = {
                'passed': event.get('passed', 0),
                'failed': event.get('failed', 0),
                'skipped': event.get('skipped', 0),
                'duration': event.get('duration', 0),
            }
            return True

        return False

    def _process_event_sync(self, event: dict, sse_sockets: list) -> bool:
        '''Handle one event from the queue.  Returns True when the run is done.'''
        if event is None:
            return True

        event_type = event.get('type')
        done = self._apply_event(event)

        if event_type == 'spec-cases-updated':
            spec_id = event['spec_id']
            self._broadcast_sync(sse_sockets, 'spec-cases-updated', {
                'spec_id': spec_id,
                'cases': event['cases'],
            })

        elif event_type == 'case-started':
            spec_id = event['spec_id']
            case_name = event['case_name']
            self._broadcast_sync(sse_sockets, 'case-update', {
                'spec_id': spec_id,
                'case_name': case_name,
                'status': 'running',
                'duration': None,
                'details': None,
            })

        elif event_type == 'assertion-added':
            spec_id = event['spec_id']
            case_name = event['case_name']
            if spec_id in self._state and case_name in self._state[spec_id]['cases']:
                case = self._state[spec_id]['cases'][case_name]
                self._broadcast_sync(sse_sockets, 'case-update', {
                    'spec_id': spec_id,
                    'case_name': case_name,
                    'status': 'running',
                    'duration': None,
                    'details': case['details'],
                })

        elif event_type == 'case-finished':
            spec_id = event['spec_id']
            case_name = event['case_name']
            status = event['status']
            duration = event.get('duration')
            details = event.get('details')
            self._broadcast_sync(sse_sockets, 'case-update', {
                'spec_id': spec_id,
                'case_name': case_name,
                'status': status,
                'duration': duration,
                'details': details,
            })

        elif event_type == 'run-complete':
            self._broadcast_sync(sse_sockets, 'run-complete', self._run_complete)

        return done

    def shutdown(self) -> None:
        '''Join the background thread started by start_in_thread().'''
        if self._thread:
            self._thread.join(timeout=self._linger + 15)

    # ------------------------------------------------------------------
    # Async entry points (used by tests that run the server in-loop)
    # ------------------------------------------------------------------

    async def start(self) -> None:
        '''Start the server inside the current event loop (for async test usage).'''
        self._shutdown_event = asyncio.Event()
        try:
            self._server = await asyncio.start_server(
                self._handle_connection,
                '127.0.0.1',
                self.port,
            )
        except OSError as exc:
            if 'Address already in use' in str(exc) or exc.errno == 98:
                log.error(
                    f'Error: Port {self.port} is already in use. '
                    f'Use --live-port to specify a different port.',
                )
                sys.exit(1)
            raise
        self._consumer_task = asyncio.ensure_future(self._consume_events())

    async def _async_cleanup(self) -> None:
        '''Async cleanup after a run-complete signal (paired with async start()).'''
        try:
            await asyncio.wait_for(self._shutdown_event.wait(), timeout=5.0)
        except asyncio.TimeoutError:
            pass

        if self._linger > 0:
            print(f'Live view available for {self._linger} more seconds...', flush=True)
            await asyncio.sleep(self._linger)

        for writer in list(self._clients):
            try:
                writer.close()
                await writer.wait_closed()
            except OSError:
                pass
        self._clients.clear()

        if self._consumer_task and not self._consumer_task.done():
            self._consumer_task.cancel()
            try:
                await self._consumer_task
            except asyncio.CancelledError:
                pass

        if self._server:
            self._server.close()
            await self._server.wait_closed()

    async def _handle_connection(
        self,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
    ) -> None:
        try:
            request_line = await asyncio.wait_for(reader.readline(), timeout=10.0)
        except asyncio.TimeoutError:
            writer.close()
            return

        parts = request_line.decode('utf-8', errors='replace').strip().split()
        if len(parts) < 2:
            writer.close()
            return

        path = parts[1]

        # Drain headers
        while True:
            try:
                line = await asyncio.wait_for(reader.readline(), timeout=5.0)
            except asyncio.TimeoutError:
                break
            if line in (b'\r\n', b'\n', b''):
                break

        if path == '/':
            await self._handle_root(writer)
        elif path == '/events':
            await self._handle_events(writer)
        else:
            await self._handle_404(writer)

    async def _handle_root(self, writer: asyncio.StreamWriter) -> None:
        body = HTML_PAGE.encode('utf-8')
        response = (
            b'HTTP/1.1 200 OK\r\n'
            b'Content-Type: text/html; charset=utf-8\r\n'
            b'Connection: close\r\n'
            + ('Content-Length: ' + str(len(body)) + '\r\n').encode()
            + b'\r\n'
            + body
        )
        try:
            writer.write(response)
            await writer.drain()
        except OSError:
            pass
        finally:
            writer.close()

    async def _handle_events(self, writer: asyncio.StreamWriter) -> None:
        headers = (
            b'HTTP/1.1 200 OK\r\n'
            b'Content-Type: text/event-stream\r\n'
            b'Cache-Control: no-cache\r\n'
            b'Connection: keep-alive\r\n'
            b'X-Accel-Buffering: no\r\n'
            b'\r\n'
        )
        try:
            writer.write(headers)
            await writer.drain()
        except OSError:
            writer.close()
            return

        # Send current state snapshot BEFORE registering for broadcasts,
        # so the client always receives snapshot as the first event.
        await self._send_snapshot(writer)

        self._clients.append(writer)

        # Keep connection alive until the client disconnects or server shuts down
        try:
            while not writer.is_closing():
                await asyncio.sleep(15)
                if writer.is_closing():
                    break
                writer.write(b': ping\n\n')
                await writer.drain()
        except OSError:
            pass
        finally:
            if writer in self._clients:
                self._clients.remove(writer)

    async def _handle_404(self, writer: asyncio.StreamWriter) -> None:
        try:
            writer.write(
                b'HTTP/1.1 404 Not Found\r\nContent-Length: 0\r\nConnection: close\r\n\r\n'
            )
            await writer.drain()
        except OSError:
            pass
        finally:
            writer.close()

    async def _send_snapshot(self, writer: asyncio.StreamWriter) -> None:
        snapshot = self._build_snapshot()
        try:
            writer.write(_format_sse('snapshot', snapshot))
            await writer.drain()
        except OSError:
            pass

    def _build_snapshot(self) -> dict:
        specs = []
        for spec_id in self._state_order:
            info = self._state.get(spec_id)
            if info:
                specs.append({
                    'id': spec_id,
                    'name': info['name'],
                    'display_name': info['display_name'],
                    'parent_id': info.get('parent_id'),
                    'cases': list(info['cases'].values()),
                })
        return {
            'specs': specs,
            'run_complete': self._run_complete,
            'run_context': self._run_context,
        }

    async def _broadcast(self, event_type: str, data: dict) -> None:
        if not self._clients:
            return
        msg = _format_sse(event_type, data)
        for writer in list(self._clients):
            try:
                if not writer.is_closing():
                    writer.write(msg)
                    await writer.drain()
            except OSError:
                if writer in self._clients:
                    self._clients.remove(writer)

    async def _consume_events(self) -> None:
        loop = asyncio.get_running_loop()
        _is_sync_queue = isinstance(self._queue, stdlib_queue.Queue)
        while True:
            try:
                if _is_sync_queue:
                    event = await loop.run_in_executor(
                        None, lambda: self._queue.get(timeout=1.0),
                    )
                else:
                    event = await self._queue.get()
            except asyncio.CancelledError:
                break
            except (RuntimeError, ValueError):
                # stdlib_queue.Empty from timeout — retry
                continue

            if event is None:
                # Sentinel value signals consumer to stop
                break

            event_type = event.get('type')
            self._apply_event(event)

            if event_type == 'spec-cases-updated':
                spec_id = event['spec_id']
                await self._broadcast('spec-cases-updated', {
                    'spec_id': spec_id,
                    'cases': event['cases'],
                })

            elif event_type == 'case-started':
                spec_id = event['spec_id']
                case_name = event['case_name']
                await self._broadcast('case-update', {
                    'spec_id': spec_id,
                    'case_name': case_name,
                    'status': 'running',
                    'duration': None,
                    'details': None,
                })

            elif event_type == 'assertion-added':
                spec_id = event['spec_id']
                case_name = event['case_name']
                if spec_id in self._state and case_name in self._state[spec_id]['cases']:
                    case = self._state[spec_id]['cases'][case_name]
                    await self._broadcast('case-update', {
                        'spec_id': spec_id,
                        'case_name': case_name,
                        'status': 'running',
                        'duration': None,
                        'details': case['details'],
                    })

            elif event_type == 'case-finished':
                spec_id = event['spec_id']
                case_name = event['case_name']
                status = event['status']
                duration = event.get('duration')
                details = event.get('details')
                await self._broadcast('case-update', {
                    'spec_id': spec_id,
                    'case_name': case_name,
                    'status': status,
                    'duration': duration,
                    'details': details,
                })

            elif event_type == 'run-complete':
                await self._broadcast('run-complete', self._run_complete)
                self._shutdown_event.set()
                break
