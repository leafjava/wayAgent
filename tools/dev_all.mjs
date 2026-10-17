import { spawn } from 'node:child_process';
import process from 'node:process';

const isWindows = process.platform === 'win32';
const python = isWindows ? 'python' : 'python3';
const backend = spawn(python, ['tools/dev_server.py'], {
  env: { ...process.env, PORT: '5000', PYTHONUTF8: '1' },
  stdio: 'inherit',
});
const frontend = spawn('npm', ['--prefix', 'frontend', 'run', 'dev'], {
  shell: isWindows,
  stdio: 'inherit',
});

function stop() {
  backend.kill();
  frontend.kill();
}
process.on('SIGINT', stop);
process.on('SIGTERM', stop);
backend.on('exit', code => { if (code && code !== 0) frontend.kill(); });
frontend.on('exit', code => { if (code && code !== 0) backend.kill(); });
