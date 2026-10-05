'use strict';
// Compatibility entry for frozen recipe callers. New callers import the shared boundary.
// Remove only after listed recipe references migrate; old results remain tied to their Git version.
module.exports = require('../ai-sigma-common/generation/identity.cjs');
