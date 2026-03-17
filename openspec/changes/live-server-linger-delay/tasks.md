## 1. CLI Flags

- [x] 1.1 Add `--live-linger` integer flag (default 5) to `spektrum/__main__.py` `setup_argparse()`
- [x] 1.2 Pass `live_linger` to `SpektrumRunner` instantiation in `spektrum/__main__.py` when `--live` is active
- [x] 1.3 Add `--live-linger` integer flag (default 5) to `paladin/__main__.py` `func_test_args` group
- [x] 1.4 In `paladin/spektrum_runner()`, extend argv with `--live-linger <value>` when `--live` is active

## 2. Runner and Server Wiring

- [x] 2.1 Add `live_linger` parameter to `SpektrumRunner.__init__` (default 5) and store as `self.live_linger`
- [x] 2.2 Pass `live_linger` to `LiveServer.__init__` when constructing the server in `runner.py`
- [x] 2.3 Add `linger` parameter to `LiveServer.__init__` (default 5) and store as `self._linger`

## 3. Linger Behavior in LiveServer

- [x] 3.1 In `LiveServer.shutdown()`, after broadcasting `run-complete` to clients, print a linger notice to stdout if `self._linger > 0`
- [x] 3.2 In `LiveServer.shutdown()`, `await asyncio.sleep(self._linger)` before closing the server (skip sleep when linger is 0)

## 4. Tests

- [x] 4.1 Add unit test: server with linger=0 shuts down without delay (assert elapsed time < 0.5s)
- [x] 4.2 Add unit test: server with linger=2 stays up for ~2 seconds after shutdown is called (assert elapsed ≥ 1.5s)
- [x] 4.3 Add unit test: linger notice is printed to stdout when linger > 0
