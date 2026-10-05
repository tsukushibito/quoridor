'use strict';

const { execFile } = require('child_process');

function parseUsage(stdout) {
  return stdout
    .trim()
    .split('\n')
    .filter(Boolean)
    .map((line) => {
      const fields = line.split(',').map((field) => field.trim());
      const pid = Number(fields[0]);
      const match = fields[1]?.match(/^(\d+)\s*MiB$/);
      if (!Number.isSafeInteger(pid) || pid < 1 || !match) throw Error('GPU_USAGE_UNKNOWN');
      return { pid, bytes: Number(match[1]) * 1024 * 1024 };
    });
}

function checkUsage(rows, ownedPids, limitBytes) {
  if (rows.some((row) => !ownedPids.has(row.pid))) throw Error('EXTERNAL_GPU_CURRENT_UNKNOWN');
  if (rows.reduce((sum, row) => sum + row.bytes, 0) >= limitBytes) throw Error('GPU_VRAM_GUARD');
}

async function readUsage(gpuId) {
  return new Promise((resolve, reject) => {
    execFile(
      'nvidia-smi',
      ['--id=' + gpuId, '--query-compute-apps=pid,used_gpu_memory', '--format=csv,noheader'],
      { encoding: 'utf8', timeout: 3000, maxBuffer: 32768 },
      (error, stdout) => {
        if (error) return reject(Error('GPU_READ_UNKNOWN:' + error.message));
        try {
          resolve(parseUsage(stdout));
        } catch (failure) {
          reject(failure);
        }
      },
    );
  });
}

module.exports = { parseUsage, checkUsage, readUsage };
