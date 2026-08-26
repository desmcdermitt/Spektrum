## 1. Runner — Emit run-started Event

- [x] 1.1 In `runner.py`, after `live_server.start()`, call `self.event_queue.put_nowait({ 'type': 'run-started', 'search_path': search_paths[0], 'module_name': module_name })` (use the first search path; `module_name` may be None)

## 2. Live Server — Handle run-started and Update Snapshot

- [x] 2.1 Add `self._run_context = None` to `LiveServer.__init__`
- [x] 2.2 In `_consume_events`, add a handler for `run-started` that sets `self._run_context = { 'search_path': event['search_path'], 'module_name': event.get('module_name') }`
- [x] 2.3 In `_build_snapshot`, add `'run_context': self._run_context` to the returned dict

## 3. HTML — Display Run Context in Header

- [x] 3.1 Add a `<div id="run-context">` subtitle element to the header in `HTML_PAGE`, styled below the "Spektrum Live" title
- [x] 3.2 In `handleSnapshot`, after processing specs, read `data.run_context` and set the subtitle element text to the search path (append `· <module_name>` if set)

## 4. Tests

- [x] 4.1 Add a test verifying `run-started` is the first event emitted to the queue when running with an event queue
- [x] 4.2 Add a test verifying the live server snapshot includes `run_context` after processing a `run-started` event
