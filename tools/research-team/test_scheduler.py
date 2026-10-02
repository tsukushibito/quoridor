"""Scheduler tests: all RPC uses a fake server, never the actual research host."""
import asyncio
from datetime import datetime, timedelta, timezone
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

SOURCE = Path(__file__).resolve().parents[2] / 'scripts/dev/research-scheduler.py'
spec = importlib.util.spec_from_file_location('scheduler', SOURCE)
s = importlib.util.module_from_spec(spec)
spec.loader.exec_module(s)


class FakeServer:
    def __init__(self):
        self.threads = {'target': {'id': 'target', 'status': {'type': 'idle'}}}
        self.turns = []
        self.calls = []
        self.reads = []
        self.lose_response = False
        self.stop_confirms = True

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_):
        pass

    async def read_thread(self, thread):
        self.reads.append(thread)
        return self.threads[thread]

    async def request(self, method, params):
        self.calls.append((method, params))
        if method == 'thread/turns/list':
            return {'data': self.turns, 'nextCursor': None}
        if method == 'thread/resume':
            self.threads[params['threadId']]['status']['type'] = 'idle'
            return {}
        if method == 'turn/start':
            turn = {'id': 'owned', 'status': 'inProgress', 'items': [
                {'type': 'userMessage', 'content': params['input']}]}
            self.turns.insert(0, turn)
            self.threads['target']['status']['type'] = 'active'
            if self.lose_response:
                raise TimeoutError('lost ack')
            return {'turn': turn}
        if method == 'turn/interrupt':
            if self.stop_confirms:
                for turn in self.turns:
                    if turn['id'] == params['turnId']:
                        turn['status'] = 'interrupted'
                self.threads['target']['status']['type'] = 'idle'
            return {}
        raise AssertionError(method)


class FakeBackend:
    def __init__(self, server):
        self.server = server
        self.issues = {'monitor': {'id': 'monitor', 'status': 'in_progress', 'labels': []},
                       'research': {'id': 'research', 'status': 'deferred', 'labels': []}}
        self.unavailable = False

    def issue(self, issue):
        return self.issues[issue]

    async def connect(self, timeout):
        if self.unavailable:
            raise s.SchedulerError('unavailable')
        return self.server


class Fixture:
    def setup(self, directory):
        self.root = Path(directory)
        self.now = datetime(2026, 10, 1, tzinfo=timezone.utc)
        self.role = self.root / '.agents/research-team/roles'
        self.role.mkdir(parents=True)
        (self.role / 'experiment.md').write_text('Test role')
        (self.role.parent / 'common.md').write_text('Test common')
        _, digest = s.team.role_definition('experiment', self.root)
        self.registry = {'schema_version': 1, 'project_root': str(self.root), 'definitions_root': str(self.root),
                         'roles': {'experiment': {'thread_id': 'target', 'definition_sha256': digest}}}
        (self.root / 'registry.json').write_text(json.dumps(self.registry))
        self.contract = {'target': 'experiment', 'dispatch_issue': 'monitor',
                         'end_at': (self.now + timedelta(hours=2)).isoformat(), 'max_active_sessions': 4,
                         'max_turn_seconds': 300, 'observation_only': True}
        (self.root / 'contract.json').write_text(json.dumps(self.contract))
        (self.root / 'prompt.md').write_text('Observe only')
        self.raw = {'enabled': True, 'interval_seconds': 1800, 'end_at': self.contract['end_at'],
                    'run_on_start': True, 'registry': 'registry.json', 'target': 'experiment',
                    'dispatch_issue': 'monitor', 'observed_issue': 'research', 'contract_file': 'contract.json',
                    'prompt_file': 'prompt.md', 'max_active_sessions': 4, 'request_timeout_seconds': 1,
                    'max_turn_seconds': 300, 'log_max_bytes': 5000, 'log_backups': 3}
        self.config_path = self.root / 'config.json'
        self.write_config()
        self.server = FakeServer()
        self.backend = FakeBackend(self.server)
        self.directory = self.root / 'runtime'
        self.directory.mkdir()
        self.engine = s.Engine(s.load_config(self.config_path, self.root), self.directory, self.root,
                               self.backend, now=lambda: self.now)

    def write_config(self):
        self.config_path.write_text(json.dumps(self.raw))

    def finish(self):
        for handler in self.engine.logger.handlers:
            handler.close()


class EngineTests(Fixture, unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.setup(self.temp.name)

    async def asyncTearDown(self):
        self.finish()
        self.temp.cleanup()

    async def test_dispatch_and_skip_active_without_steer(self):
        self.assertTrue(await self.engine.tick())
        self.assertEqual(self.engine.state['owned']['turn_id'], 'owned')
        await self.engine.tick()
        self.assertEqual(sum(m == 'turn/start' for m, _ in self.server.calls), 1)
        self.assertFalse(any(m == 'turn/steer' for m, _ in self.server.calls))

    async def test_external_active_never_owned_or_interrupted(self):
        self.server.threads['target']['status']['type'] = 'active'
        await self.engine.tick()
        await self.engine.tick(interrupt=True)
        self.assertFalse(any(m.startswith('turn/') for m, _ in self.server.calls))

    async def test_not_loaded_resume_preserves_model(self):
        self.server.threads['target']['status']['type'] = 'notLoaded'
        await self.engine.tick()
        resume = next(p for m, p in self.server.calls if m == 'thread/resume')
        self.assertEqual(set(resume), {'threadId', 'excludeTurns'})

    async def test_other_active_sessions_do_not_block_target(self):
        for i in range(4):
            name = f'other{i}'
            self.registry['roles'][name] = {'thread_id': name}
            self.server.threads[name] = {'id': name, 'status': {'type': 'active'}}
        (self.root / 'registry.json').write_text(json.dumps(self.registry))
        await self.engine.tick()
        self.assertEqual(sum(m == 'turn/start' for m, _ in self.server.calls), 1)
        self.assertTrue(all(t == 'target' for t in self.server.reads))
        self.assertEqual(self.engine.state['owned']['turn_id'], 'owned')

    async def test_deadline_interrupts_exact_owned_turn(self):
        await self.engine.tick()
        self.server.turns.insert(0, {'id': 'external', 'status': 'inProgress', 'items': []})
        self.now += timedelta(hours=3)
        self.assertFalse(await self.engine.tick())
        self.assertEqual([p['turnId'] for m, p in self.server.calls if m == 'turn/interrupt'], ['owned'])
        self.assertIsNone(self.engine.state['owned'])

    async def test_paused_issue_no_dispatch(self):
        self.backend.issues['monitor']['labels'] = ['paused-by-user']
        self.assertFalse(await self.engine.tick())
        self.assertEqual(self.server.calls, [])

    async def test_observed_deferred_can_be_read_but_pause_stops(self):
        await self.engine.tick()
        self.backend.issues['research']['labels'] = ['paused-by-user']
        self.assertFalse(await self.engine.tick())
        self.assertIsNone(self.engine.state['owned'])

    async def test_blocked_deferred_closed_dispatch_stops(self):
        for status in ['blocked', 'deferred', 'closed']:
            self.backend.issues['monitor']['status'] = status
            self.assertFalse(await self.engine.tick())
        self.assertEqual(self.server.calls, [])

    async def test_turn_limit_owned_only(self):
        await self.engine.tick()
        self.now += timedelta(seconds=301)
        await self.engine.tick(due=False)
        self.assertIsNone(self.engine.state['owned'])
        self.assertEqual(self.engine.state['last_result']['event'], 'turn_limit')

    async def test_lost_response_resolved_after_restart_no_duplicate(self):
        self.server.lose_response = True
        with self.assertRaises(TimeoutError):
            await self.engine.tick()
        self.assertTrue(self.engine.state['recovery_required'])
        restarted = s.Engine(self.engine.config, self.directory, self.root, self.backend, now=lambda: self.now)
        try:
            await restarted.tick()
            self.assertEqual(restarted.state['owned']['turn_id'], 'owned')
            self.assertEqual(sum(m == 'turn/start' for m, _ in self.server.calls), 1)
        finally:
            for h in restarted.logger.handlers:
                h.close()

    async def test_unknown_outcome_missing_history_blocks_dispatch(self):
        self.server.lose_response = True
        with self.assertRaises(TimeoutError):
            await self.engine.tick()
        self.server.turns = []
        self.server.threads['target']['status']['type'] = 'idle'
        await self.engine.tick()
        self.assertTrue(self.engine.state['recovery_required'])
        self.assertEqual(sum(m == 'turn/start' for m, _ in self.server.calls), 1)

    async def test_backward_wall_clock_does_not_extend_turn_budget(self):
        await self.engine.tick()
        self.now -= timedelta(hours=1)
        self.engine.owned_mono = time.monotonic() - 301
        await self.engine.tick(due=False)
        self.assertIsNone(self.engine.state['owned'])

    async def test_ended_contract_never_contacts_server(self):
        self.now += timedelta(hours=3)
        self.assertFalse(await self.engine.tick())
        self.assertEqual(self.server.calls, [])

    async def test_quoted_run_marker_is_not_ownership_proof(self):
        self.server.lose_response = True
        with self.assertRaises(TimeoutError):
            await self.engine.tick()
        marker = self.server.turns[0]['items'][0]['content'][0]['text']
        self.server.turns = [{'id': 'foreign', 'status': 'inProgress', 'items': [
            {'type': 'userMessage', 'content': [{'type': 'text', 'text': 'Quoted evidence: ' + marker}]}]}]
        self.server.threads['target']['status']['type'] = 'idle'
        await self.engine.tick(interrupt=True)
        self.assertTrue(self.engine.state['recovery_required'])
        self.assertFalse(any(m == 'turn/interrupt' for m, _ in self.server.calls))

    async def test_unavailable_no_dispatch(self):
        self.backend.unavailable = True
        with self.assertRaises(s.SchedulerError):
            await self.engine.tick()
        self.assertNotIn('owned', self.engine.state)

    async def test_disabled_skips_and_reload_reenable(self):
        self.raw['enabled'] = False
        self.write_config()
        self.assertTrue(self.engine.reload())
        await self.engine.tick()
        self.assertEqual(self.server.calls, [])
        self.raw['enabled'] = True
        self.write_config()
        self.assertTrue(self.engine.reload())
        await self.engine.tick()
        self.assertEqual(sum(m == 'turn/start' for m, _ in self.server.calls), 1)

    async def test_start_time_and_definition_drift(self):
        self.engine.config['start'] = self.now + timedelta(hours=1)
        await self.engine.tick()
        self.assertEqual(self.server.calls, [])
        self.engine.config['start'] = None
        (self.role / 'experiment.md').write_text('Changed definition')
        with self.assertRaises(s.team.TeamError):
            await self.engine.tick()

    async def test_interrupt_unconfirmed_retains_ownership(self):
        await self.engine.tick()
        self.server.stop_confirms = False
        await self.engine.tick(interrupt=True)
        self.assertIsNotNone(self.engine.state['owned'])
        self.assertTrue(any(m == 'turn/interrupt' for m, _ in self.server.calls))

    async def test_concurrent_client_lock_skips_without_dispatch(self):
        with s.team.dispatch_lock(self.root):
            with self.assertRaises(s.team.TeamError):
                await self.engine.tick()
        self.assertFalse(any(m == 'turn/start' for m, _ in self.server.calls))


class ClientCapacityTests(Fixture, unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.setup(self.temp.name)

    async def asyncTearDown(self):
        self.finish()
        self.temp.cleanup()

    async def test_existing_client_ignores_legacy_count_limit(self):
        from types import SimpleNamespace
        from unittest.mock import AsyncMock
        for i in range(3):
            key = f'other{i}'
            self.registry['roles'][key] = {'thread_id': key}
            self.server.threads[key] = {'id': key, 'status': {'type': 'active'}}
        (self.root/'registry.json').write_text(json.dumps(self.registry))
        self.server.deliver = AsyncMock(return_value={'accepted': True})
        args = SimpleNamespace(command='send', issue='monitor', registry=str(self.root/'registry.json'),
                               role='experiment', body_file=str(self.root/'prompt.md'), cwd=None,
                               max_active_sessions=3)
        def json_command(command):
            if command[0] == 'codex':
                return {'status': 'running', 'socketPath': 'FAKE'}
            return [{'id': 'monitor', 'status': 'in_progress', 'labels': []}]
        with patch.object(s.team, 'project_root', return_value=self.root), \
             patch.object(s.team, 'command_json', side_effect=json_command), \
             patch.object(s.team, 'AppServer', return_value=self.server):
            self.assertTrue((await s.team.run(args))['accepted'])
            self.server.deliver.assert_awaited_once()
            self.server.deliver.reset_mock()
            # Existing active turn can receive evidence even with all slots occupied.
            self.server.threads['target']['status']['type'] = 'active'
            self.assertTrue((await s.team.run(args))['accepted'])
            self.server.deliver.assert_awaited_once()


class SettingsTests(Fixture, unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.setup(self.temp.name)

    def tearDown(self):
        self.finish()
        self.temp.cleanup()

    def test_config_validation_and_reload_retains_old(self):
        original = self.engine.config['config_sha256']
        for key, value in [('interval_seconds', 0), ('interval_seconds', True), ('end_at', '2027-01-01'),
                           ('end_at', '2027-01-01T00:00:00Z'), ('max_active_sessions', False), ('max_turn_seconds', 301)]:
            old = self.raw[key]
            self.raw[key] = value
            self.write_config()
            self.assertFalse(self.engine.reload(), (key, value))
            self.assertEqual(self.engine.config['config_sha256'], original)
            self.raw[key] = old

    def test_deprecated_session_fields_accept_null_and_ignore_legacy_mismatch(self):
        for value in (None, 99):
            self.raw['max_active_sessions'] = value
            self.write_config()
            self.assertTrue(self.engine.reload())

    def test_rotation(self):
        self.engine.config['log_max_bytes'] = 200
        self.engine.config['log_backups'] = 2
        self.engine.configure_log()
        for i in range(20):
            self.engine.record('test', text='x' * 100)
        self.assertTrue((self.directory / 'events.jsonl.2').exists())
        self.assertFalse((self.directory / 'events.jsonl.3').exists())

    def test_identity_reuse_and_double_lock(self):
        ident = s.process_identity(__import__('os').getpid())
        self.assertTrue(s.alive(ident))
        self.assertFalse(s.alive({**ident, 'start_ticks': 'wrong'}))
        with s.team.dispatch_lock(self.root):
            with self.assertRaises(s.team.TeamError):
                with s.team.dispatch_lock(self.root):
                    pass

    def test_cadence_skips_missed_ticks(self):
        self.assertEqual(s.next_due(100, 30, 100), 130)
        self.assertEqual(s.next_due(100, 30, 199), 220)
        self.assertEqual(s.next_due(100, 30, 500), 520)


class CLITests(unittest.TestCase):
    def test_process_start_reload_stop_without_real_server(self):
        # Child imports a fake AppServer and issue backend. The real codex command is never used.
        with tempfile.TemporaryDirectory() as tmp:
            fixture = Fixture()
            fixture.setup(tmp)
            fixture.finish()
            fixture.raw['enabled'] = False
            fixture.raw['end_at'] = (s.utc_now() + timedelta(minutes=5)).isoformat()
            fixture.contract['end_at'] = fixture.raw['end_at']
            (fixture.root / 'contract.json').write_text(json.dumps(fixture.contract))
            fixture.write_config()
            harness = fixture.root / 'harness.py'
            harness.write_text("""import importlib.util,sys
from pathlib import Path
spec=importlib.util.spec_from_file_location('scheduler', sys.argv.pop(1))
s=importlib.util.module_from_spec(spec);spec.loader.exec_module(s)
root=Path(sys.argv.pop(1))
s.team.project_root=lambda: root
s.AppBackend.issue=lambda self,issue: {'id':issue,'status':'in_progress','labels':[]}
original=s.subprocess.Popen
def spawn(argv,**kwargs):
    # Preserve the real startup handshake while the child also uses the mock backend.
    argv=[argv[0],'-B',str(Path(__file__).resolve()),str(Path(s.__file__).resolve()),str(root),*argv[3:]]
    return original(argv,**kwargs)
s.subprocess.Popen=spawn
s.main()
""")
            # start uses the actual entrypoint in its subprocess. Test run directly through harness
            # to keep backend fake, and exercise control commands against the same runtime.
            runtime = fixture.directory
            child = subprocess.Popen([sys.executable, '-B', str(harness), str(SOURCE), str(fixture.root),
                                      'run', '--config', str(fixture.config_path), '--state-dir', str(runtime)],
                                     stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            def command(name):
                return subprocess.run([sys.executable, '-B', str(harness), str(SOURCE), str(fixture.root),
                                       name, '--state-dir', str(runtime)], capture_output=True, text=True, timeout=15)
            try:
                until = time.monotonic() + 10
                while time.monotonic() < until:
                    state = s.read_json(runtime/'state.json') if (runtime/'state.json').exists() else {}
                    if state.get('phase') == 'running':
                        break
                    if child.poll() is not None:
                        self.fail(child.communicate()[1].decode())
                    time.sleep(.05)
                self.assertTrue(json.loads(command('status').stdout)['running'])
                self.assertEqual(command('reload').returncode, 0)
                until = time.monotonic()+8
                while time.monotonic()<until:
                    events = (runtime/'events.jsonl').read_text()
                    if '"event": "reloaded"' in events:
                        break
                    time.sleep(.05)
                self.assertIn('"event": "reloaded"', events)
                other = subprocess.run([sys.executable,'-B',str(harness),str(SOURCE),str(fixture.root),
                                        'run','--config',str(fixture.config_path),'--state-dir',str(runtime)],
                                       capture_output=True,text=True,timeout=10)
                self.assertNotEqual(other.returncode, 0)
                self.assertIn('already running', other.stderr)
                self.assertEqual(command('stop').returncode, 0)
                child.wait(timeout=10)
                self.assertFalse(json.loads(command('status').stdout)['running'])
                start = subprocess.run([sys.executable,'-B',str(harness),str(SOURCE),str(fixture.root),
                                        'start','--config',str(fixture.config_path),'--state-dir',str(runtime)],
                                       capture_output=True,text=True,timeout=15)
                self.assertEqual(start.returncode, 0, start.stderr)
                self.assertTrue(json.loads(start.stdout)['started'])
                self.assertEqual(command('stop').returncode, 0)
            finally:
                if child.poll() is None:
                    child.terminate()
                    child.wait(timeout=10)
                child.communicate()


if __name__ == '__main__':
    unittest.main()
