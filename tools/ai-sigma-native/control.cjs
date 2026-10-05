'use strict';
const now = () => Number(process.hrtime.bigint()) / 1e6;
const controlDrain = () => new Promise((resolve) => setImmediate(resolve));
module.exports = { now, controlDrain };
