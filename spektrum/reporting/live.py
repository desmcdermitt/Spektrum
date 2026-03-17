import asyncio
import json
import sys


HTML_PAGE = '''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Spektrum Live</title>
  <style>
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body { font-family: 'Segoe UI', system-ui, sans-serif; background: #0f1117; color: #e1e4e8; line-height: 1.5; }
    header { background: #161b22; border-bottom: 1px solid #30363d; padding: 16px 24px; display: flex; align-items: center; justify-content: space-between; }
    h1 { font-size: 1.25rem; font-weight: 600; color: #58a6ff; }
    #run-context { font-size: 0.78rem; color: #8b949e; margin-top: 2px; font-family: 'Courier New', monospace; }
    #connection-status { font-size: 0.85rem; color: #8b949e; display: flex; align-items: center; gap: 6px; }
    #status-dot { width: 10px; height: 10px; border-radius: 50%; background: #d29922; flex-shrink: 0; }
    #banner { display: none; margin: 16px 24px 0; padding: 12px 16px; border-radius: 6px; font-weight: 600; font-size: 0.95rem; }
    #banner.run-passed { background: #0d4a23; border: 1px solid #3fb950; color: #3fb950; }
    #banner.run-failed { background: #4a0d0d; border: 1px solid #f85149; color: #f85149; }
    main { padding: 16px 24px; }
    .spec-section { margin-bottom: 16px; background: #161b22; border: 1px solid #30363d; border-radius: 8px; overflow: hidden; }
    .spec-header { padding: 10px 16px; font-weight: 600; font-size: 0.95rem; background: #21262d; border-bottom: 1px solid #30363d; color: #c9d1d9; }
    .case-row { border-bottom: 1px solid #21262d; }
    .case-row:last-child { border-bottom: none; }
    .case-header { display: flex; align-items: center; padding: 9px 16px; cursor: pointer; user-select: none; gap: 10px; }
    .case-header:hover { background: #1c2128; }
    .case-name { flex: 1; font-size: 0.875rem; font-family: 'Courier New', monospace; color: #c9d1d9; }
    .case-duration { font-size: 0.75rem; color: #8b949e; min-width: 56px; text-align: right; }
    .toggle-icon { font-size: 0.65rem; color: #8b949e; min-width: 10px; }
    .badge { display: inline-block; padding: 1px 8px; border-radius: 12px; font-size: 0.7rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.04em; min-width: 60px; text-align: center; }
    .badge-pending { background: #21262d; color: #8b949e; border: 1px solid #30363d; }
    .badge-running { background: #1a3a5c; color: #58a6ff; border: 1px solid #388bfd; animation: pulse 1.4s ease-in-out infinite; }
    .badge-passed { background: #0d4a23; color: #3fb950; border: 1px solid #2ea043; }
    .badge-failed { background: #4a0d0d; color: #f85149; border: 1px solid #da3633; }
    .badge-skipped { background: #2a2010; color: #d29922; border: 1px solid #9e6a03; }
    @keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.55; } }
    .case-details { display: none; padding: 10px 16px; background: #0d1117; border-top: 1px solid #21262d; font-size: 0.82rem; }
    .case-details.open { display: block; }
    .detail-label { font-weight: 600; color: #6e7681; margin-bottom: 4px; font-size: 0.72rem; text-transform: uppercase; letter-spacing: 0.06em; }
    .error-block { color: #f85149; font-family: 'Courier New', monospace; white-space: pre-wrap; word-break: break-word; font-size: 0.8rem; }
    .skip-reason { color: #d29922; }
    .expect-item { padding: 1px 0; font-family: 'Courier New', monospace; font-size: 0.8rem; }
    .expect-item.pass { color: #3fb950; }
    .expect-item.fail { color: #f85149; }
    .no-details { color: #6e7681; font-style: italic; }
  </style>
</head>
<body>
  <header>
    <div><h1>&#9889; Spektrum Live</h1><div id="run-context"></div></div>
    <div id="connection-status"><span id="status-dot"></span>Connecting...</div>
  </header>
  <div id="banner"></div>
  <main id="specs"></main>
  <script>
    var state = { specs: {} };

    function connect() {
      var es = new EventSource('/events');
      es.onopen = function() { setStatus('Connected', '#3fb950'); };
      es.onerror = function() { setStatus('Reconnecting\u2026', '#d29922'); };
      es.addEventListener('snapshot', function(e) { handleSnapshot(JSON.parse(e.data)); });
      es.addEventListener('case-update', function(e) { handleCaseUpdate(JSON.parse(e.data)); });
      es.addEventListener('run-complete', function(e) { handleRunComplete(JSON.parse(e.data)); });
    }

    function setStatus(text, color) {
      var dot = document.getElementById('status-dot');
      dot.style.background = color;
      var cs = document.getElementById('connection-status');
      cs.childNodes[1] ? (cs.childNodes[1].textContent = text) : cs.appendChild(document.createTextNode(text));
    }

    function handleSnapshot(data) {
      state.specs = {};
      var container = document.getElementById('specs');
      container.innerHTML = '';
      (data.specs || []).forEach(function(spec) {
        state.specs[spec.id] = spec;
        container.appendChild(renderSpec(spec));
      });
      if (data.run_context) {
        var rc = data.run_context;
        var text = rc.search_path || '';
        if (rc.module_name) { text += ' \u00b7 ' + rc.module_name; }
        document.getElementById('run-context').textContent = text;
      }
      if (data.run_complete) { handleRunComplete(data.run_complete); }
    }

    function renderSpec(spec) {
      var section = document.createElement('div');
      section.className = 'spec-section';
      section.id = 'spec-' + spec.id;
      var header = document.createElement('div');
      header.className = 'spec-header';
      header.textContent = spec.display_name || spec.name;
      section.appendChild(header);
      (spec.cases || []).forEach(function(c) { section.appendChild(renderCase(spec.id, c)); });
      return section;
    }

    function renderCase(specId, c) {
      var row = document.createElement('div');
      row.className = 'case-row';
      row.id = 'case-' + specId + '-' + c.name;
      var status = c.status || 'pending';
      var durHtml = (c.duration != null) ? '<span class="case-duration">' + Math.round(c.duration * 1000) + 'ms</span>' : '<span class="case-duration"></span>';
      row.innerHTML =
        '<div class="case-header" onclick="toggleDetails(this)">' +
          '<span class="case-name">' + esc(c.display_name || c.name) + '</span>' +
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
          html += '<div class="error-block">' + esc(lines.join('\\n')) + '</div>';
        });
      }
      if (d.skip_reason) {
        html += '<div class="detail-label">Skip Reason</div><div class="skip-reason">' + esc(d.skip_reason) + '</div>';
      }
      if (d.expects && d.expects.length) {
        html += '<div class="detail-label" style="margin-top:6px">Assertions</div>';
        d.expects.forEach(function(e) {
          html += '<div class="expect-item ' + (e.success ? 'pass' : 'fail') + '">' + (e.success ? '&#10003; ' : '&#10007; ') + esc(e.evaluation) + '</div>';
        });
      }
      if (!html) { html = '<span class="no-details">No details available.</span>'; }
      return html;
    }

    function handleCaseUpdate(data) {
      var row = document.getElementById('case-' + data.spec_id + '-' + data.case_name);
      if (!row) { return; }
      var badge = row.querySelector('.badge');
      badge.className = 'badge badge-' + data.status;
      badge.textContent = data.status;
      var dur = row.querySelector('.case-duration');
      if (data.duration != null) { dur.textContent = Math.round(data.duration * 1000) + 'ms'; }
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
      var icon = failed > 0 ? '\u2717' : '\u2713';
      banner.className = 'banner ' + cls;
      banner.style.display = 'block';
      banner.textContent = icon + ' ' + passed + ' passed, ' + failed + ' failed, ' + skipped + ' skipped';
      document.title = failed > 0 ? '\u2717 ' + failed + ' failed \u2014 Spektrum' : '\u2713 All passed \u2014 Spektrum';
      setStatus('Run complete', failed > 0 ? '#f85149' : '#3fb950');
    }

    function toggleDetails(header) {
      var details = header.nextElementSibling;
      var icon = header.querySelector('.toggle-icon');
      details.classList.toggle('open');
      icon.innerHTML = details.classList.contains('open') ? '&#9660;' : '&#9654;';
    }

    function esc(s) {
      if (!s) { return ''; }
      return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
    }

    connect();
  </script>
</body>
</html>'''


def _default_json(obj):
    """Fallback serializer: stringify objects that aren't natively JSON-serializable."""
    return str(obj)


def _format_sse(event_type, data):
    return (
        'event: ' + event_type + '\ndata: ' + json.dumps(data, default=_default_json) + '\n\n'
    ).encode('utf-8')


class LiveServer:
    def __init__(self, port, event_queue, linger=5):
        self.port = port
        self._queue = event_queue
        self._linger = linger
        self._clients = []
        self._state = {}
        self._state_order = []
        self._run_complete = None
        self._run_context = None
        self._server = None
        self._shutdown_event = asyncio.Event()
        self._consumer_task = None

    async def start(self):
        try:
            self._server = await asyncio.start_server(
                self._handle_connection,
                '127.0.0.1',
                self.port,
            )
        except OSError as exc:
            if 'Address already in use' in str(exc) or exc.errno == 98:
                print(
                    f'Error: Port {self.port} is already in use. '
                    f'Use --live-port to specify a different port.',
                    file=sys.stderr,
                )
                sys.exit(1)
            raise
        self._consumer_task = asyncio.ensure_future(self._consume_events())

    async def shutdown(self):
        # Wait for the run-complete signal or timeout
        try:
            await asyncio.wait_for(self._shutdown_event.wait(), timeout=5.0)
        except asyncio.TimeoutError:
            pass

        # Hold the server open so developers have time to load the results page
        if self._linger > 0:
            print(f'Live view available for {self._linger} more seconds...', flush=True)
            await asyncio.sleep(self._linger)

        # Close remaining SSE client connections
        for writer in list(self._clients):
            try:
                writer.close()
                await writer.wait_closed()
            except Exception:
                pass
        self._clients.clear()

        # Cancel the consumer task
        if self._consumer_task and not self._consumer_task.done():
            self._consumer_task.cancel()
            try:
                await self._consumer_task
            except asyncio.CancelledError:
                pass

        # Close the TCP server
        if self._server:
            self._server.close()
            await self._server.wait_closed()

    async def _handle_connection(self, reader, writer):
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

    async def _handle_root(self, writer):
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
        except Exception:
            pass
        finally:
            writer.close()

    async def _handle_events(self, writer):
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
        except Exception:
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
        except Exception:
            pass
        finally:
            if writer in self._clients:
                self._clients.remove(writer)

    async def _handle_404(self, writer):
        try:
            writer.write(b'HTTP/1.1 404 Not Found\r\nContent-Length: 0\r\nConnection: close\r\n\r\n')
            await writer.drain()
        except Exception:
            pass
        finally:
            writer.close()

    async def _send_snapshot(self, writer):
        snapshot = self._build_snapshot()
        try:
            writer.write(_format_sse('snapshot', snapshot))
            await writer.drain()
        except Exception:
            pass

    def _build_snapshot(self):
        specs = []
        for spec_id in self._state_order:
            info = self._state.get(spec_id)
            if info:
                specs.append({
                    'id': spec_id,
                    'name': info['name'],
                    'display_name': info['display_name'],
                    'cases': list(info['cases'].values()),
                })
        return {
            'specs': specs,
            'run_complete': self._run_complete,
            'run_context': self._run_context,
        }

    async def _broadcast(self, event_type, data):
        if not self._clients:
            return
        msg = _format_sse(event_type, data)
        for writer in list(self._clients):
            try:
                if not writer.is_closing():
                    writer.write(msg)
                    await writer.drain()
            except Exception:
                if writer in self._clients:
                    self._clients.remove(writer)

    async def _consume_events(self):
        while True:
            try:
                event = await self._queue.get()
            except asyncio.CancelledError:
                break

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

            elif event_type == 'case-started':
                spec_id = event['spec_id']
                case_name = event['case_name']
                if spec_id in self._state and case_name in self._state[spec_id]['cases']:
                    self._state[spec_id]['cases'][case_name]['status'] = 'running'
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
                assertion = event.get('assertion', {})
                if spec_id in self._state and case_name in self._state[spec_id]['cases']:
                    case = self._state[spec_id]['cases'][case_name]
                    if case['details'] is None:
                        case['details'] = {'expects': [], 'errors': [], 'skip_reason': None}
                    case['details']['expects'].append(assertion)
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
                if spec_id in self._state and case_name in self._state[spec_id]['cases']:
                    self._state[spec_id]['cases'][case_name].update({
                        'status': status,
                        'duration': duration,
                        'details': details,
                    })
                await self._broadcast('case-update', {
                    'spec_id': spec_id,
                    'case_name': case_name,
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
                await self._broadcast('run-complete', self._run_complete)
                self._shutdown_event.set()
                break
