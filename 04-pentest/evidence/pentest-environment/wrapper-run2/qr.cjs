'use strict';

// UX-10 QR display host contract. Blueprint 6.3 and 13-platform-ux.md section 2.4:
// display only, paste stays the primary control, and nothing above the version 25 ceiling
// of 997 bytes is rendered. Scan is opt in per request and never the only path.
//
// The encoder itself is not vendored in this round. This module owns the ceiling, the
// version target and the permission flow, and takes an encoder function at the call site:
// encoder(text) returns { version, size, modules } with modules a size x size array of 0 or 1.

const MAX_VERSION = 25;
const SIZE_CEILING_BYTES = 997;

function isEncodable(text) {
  return typeof text === 'string' && text.length > 0 && Buffer.byteLength(text, 'utf8') <= SIZE_CEILING_BYTES;
}

function assertEncodable(text) {
  if (typeof text !== 'string' || text.length === 0) throw new Error('qr: empty payload');
  const bytes = Buffer.byteLength(text, 'utf8');
  if (bytes > SIZE_CEILING_BYTES) {
    throw new Error('qr: payload is ' + bytes + ' bytes, ceiling is ' + SIZE_CEILING_BYTES + ' (version ' + MAX_VERSION + ')');
  }
  return bytes;
}

function renderSpec(text, encoder, options) {
  const bytes = assertEncodable(text);
  if (typeof encoder !== 'function') throw new Error('qr: no encoder installed');
  const matrix = encoder(text);
  if (!matrix || matrix.version > MAX_VERSION || matrix.size !== 21 + 4 * (matrix.version - 1) || !Array.isArray(matrix.modules)) {
    throw new Error('qr: encoder returned a matrix outside the contract');
  }
  if (matrix.modules.length !== matrix.size || matrix.modules.some((row) => !Array.isArray(row) || row.length !== matrix.size)) {
    throw new Error('qr: encoder returned a ragged matrix');
  }
  const modulePx = Math.max(1, Math.floor((options && options.modulePx) || 3));
  return { version: matrix.version, size: matrix.size, modules: matrix.modules, bytes, modulePx, pixelSize: matrix.size * modulePx };
}

// No camera permission is requested before the user asks to scan, and a scan path without
// a visible paste fallback is refused (UX-10 failure modes).
function mayRequestScan(request) {
  return Boolean(request && request.userInitiated === true && request.pasteAvailable === true);
}

module.exports = { MAX_VERSION, SIZE_CEILING_BYTES, isEncodable, assertEncodable, renderSpec, mayRequestScan };
