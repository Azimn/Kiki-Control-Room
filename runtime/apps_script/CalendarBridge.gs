/** Outbound-only local client bridge. Never polls Telegram or exposes the PC. */
function bridgeJson_(body) {
  return ContentService.createTextOutput(JSON.stringify(body)).setMimeType(ContentService.MimeType.JSON);
}

function bridgeAuth_(envelope, secret, now) {
  if (!secret || secret.length < 32 || !envelope || typeof envelope.payload !== 'string' ||
      envelope.payload.length > 4096 || typeof envelope.signature !== 'string') return null;
  const expected = Utilities.computeHmacSha256Signature(envelope.payload, secret)
    .map(b => ('0' + ((b + 256) % 256).toString(16)).slice(-2)).join('');
  if (envelope.signature.length !== expected.length) return null;
  let mismatch = 0;
  for (let i = 0; i < expected.length; i++) mismatch |= expected.charCodeAt(i) ^ envelope.signature.charCodeAt(i);
  if (mismatch) return null;
  const request = JSON.parse(envelope.payload);
  if (!Number.isInteger(request.timestamp) || Math.abs(now / 1000 - request.timestamp) > 300) return null;
  return request;
}

function bridgeApi_(method, path, body) {
  const response = UrlFetchApp.fetch('https://www.googleapis.com/calendar/v3/' + path, {
    method: method, contentType: 'application/json',
    headers: {Authorization: 'Bearer ' + ScriptApp.getOAuthToken()},
    payload: body ? JSON.stringify(body) : undefined, muteHttpExceptions: true
  });
  const code = response.getResponseCode();
  let data = {};
  try { data = JSON.parse(response.getContentText()); } catch (_) {}
  return {code: code, data: data};
}

function bridgeMatchesBooking_(event, b) {
  const start = Date.parse(b.start), end = start + b.duration * 60000;
  return !!event && event.status !== 'cancelled' &&
    event.summary === b.title.trim() &&
    event.start && Date.parse(event.start.dateTime) === start &&
    event.end && Date.parse(event.end.dateTime) === end &&
    event.extendedProperties && event.extendedProperties.private &&
    event.extendedProperties.private.kiki_request_id === b.id;
}

function bridgeBook_(request, cfg, now, api) {
  if (!cfg.writeId || !cfg.ids.length) return {code: 'unavailable'};
  const path = 'calendars/' + encodeURIComponent(cfg.writeId) + '/events';
  if (request.action === 'health') {
    const target = api('get', 'calendars/' + encodeURIComponent(cfg.writeId));
    if (target.code !== 200) return {code: 'unavailable'};
    const start = new Date(now).toISOString(), end = new Date(now + 86400000).toISOString();
    for (const id of Array.from(new Set(cfg.ids.concat([cfg.writeId])))) {
      const read = api('get', 'calendars/' + encodeURIComponent(id) + '/events?timeMin=' + encodeURIComponent(start) + '&timeMax=' + encodeURIComponent(end) + '&maxResults=1');
      if (read.code !== 200) return {code: 'unavailable'};
    }
    return {code: 'ready'};
  }
  const b = request.booking;
  if (request.action !== 'book' || !b || !/^[a-f0-9]{32}$/.test(b.id) || typeof b.title !== 'string' ||
      !b.title.trim() || b.title.length > 120 || !Number.isInteger(b.duration) ||
      b.duration < 5 || b.duration > 240 || typeof b.start !== 'string' || !Number.isFinite(b.offered)) return {code: 'invalid'};
  const start = new Date(b.start), end = new Date(start.getTime() + b.duration * 60000);
  if (!Number.isFinite(start.getTime())) return {code: 'invalid'};
  // Client-generated Calendar event IDs make repeated/lost-response requests idempotent.
  const eventId = 'kiki' + b.id;
  const existing = api('get', path + '/' + eventId);
  if (existing.code === 200) {
    return bridgeMatchesBooking_(existing.data, b) ? {code: 'booked', event_id: eventId} : {code: 'invalid'};
  }
  if (existing.code !== 404) return {code: 'unavailable'};
  if (start.getTime() <= now || now - b.offered * 1000 > 1800000 || b.offered * 1000 > now + 300000) return {code: 'invalid'};
  for (const id of Array.from(new Set(cfg.ids.concat([cfg.writeId])))) {
    let page = '';
    do {
      const read = api('get', 'calendars/' + encodeURIComponent(id) + '/events?singleEvents=true&maxResults=2500&timeMin=' +
        encodeURIComponent(start.toISOString()) + '&timeMax=' + encodeURIComponent(end.toISOString()) +
        (page ? '&pageToken=' + encodeURIComponent(page) : ''));
      if (read.code !== 200 || (read.data.items !== undefined && !Array.isArray(read.data.items))) return {code: 'unavailable'};
      if ((read.data.items || []).some(event => event.status !== 'cancelled' && event.transparency !== 'transparent')) return {code: 'conflict'};
      page = read.data.nextPageToken || '';
    } while (page);
  }
  const write = api('post', path + '?sendUpdates=none', {
    id: eventId, summary: b.title.trim(),
    start: {dateTime: start.toISOString()}, end: {dateTime: end.toISOString()},
    description: 'Scheduled by an explicit command to Kiki Control Room.',
    extendedProperties: {private: {kiki_request_id: b.id}}
  });
  if (write.code === 200 || write.code === 201) return {code: 'booked', event_id: eventId};
  if (write.code === 409) {
    const retry = api('get', path + '/' + eventId);
    if (retry.code === 200) return bridgeMatchesBooking_(retry.data, b) ? {code: 'booked', event_id: eventId} : {code: 'invalid'};
  }
  return {code: 'unavailable'};
}

function doPost(e) {
  const lock = LockService.getScriptLock();
  try {
    if (!e || !e.postData || e.postData.contents.length > 8192) return bridgeJson_({code: 'unauthorized'});
    const props = PropertiesService.getScriptProperties();
    const request = bridgeAuth_(JSON.parse(e.postData.contents), props.getProperty('CALENDAR_BRIDGE_KEY'), Date.now());
    if (!request) return bridgeJson_({code: 'unauthorized'});
    if (!lock.tryLock(20000)) return bridgeJson_({code: 'unavailable'});
    const cfg = {writeId: props.getProperty('WRITE_CALENDAR_ID'),
      ids: (props.getProperty('READ_CALENDAR_IDS') || '').split(',').map(x => x.trim()).filter(Boolean)};
    return bridgeJson_(bridgeBook_(request, cfg, Date.now(), bridgeApi_));
  } catch (_) {
    // Do not log request bodies, credentials, Calendar API errors, or event data.
    return bridgeJson_({code: 'unavailable'});
  } finally { lock.releaseLock(); }
}

function verifyCalendarBridgeAccess() {
  const props = PropertiesService.getScriptProperties();
  const result = bridgeBook_({action: 'health'}, {writeId: props.getProperty('WRITE_CALENDAR_ID'),
    ids: (props.getProperty('READ_CALENDAR_IDS') || '').split(',').map(x => x.trim()).filter(Boolean)}, Date.now(), bridgeApi_);
  console.log('Calendar bridge read access: ' + result.code + '. Write permission is verified on the first explicit booking.');
}

function authorizeCalendarBooking() {
  ScriptApp.requireAllScopes(ScriptApp.AuthMode.FULL);
  console.log('Calendar booking permissions granted.');
}

function diagnoseCalendarSetupTest() {
  const props = PropertiesService.getScriptProperties();
  const target = props.getProperty('WRITE_CALENDAR_ID');
  const ids = (props.getProperty('READ_CALENDAR_IDS') || '').split(',').filter(Boolean);
  const queries = ['calendars/' + encodeURIComponent(target) + '/events/kikiffffffffffffffffffffffffffffffff'];
  ids.forEach(id => queries.push('calendars/' + encodeURIComponent(id) + '/events?singleEvents=true&timeMin=2026-10-15T00%3A00%3A00Z&timeMax=2026-10-15T00%3A05%3A00Z'));
  queries.forEach((path, i) => {
    const result = bridgeApi_('get', path);
    const reason = result.data.error && result.data.error.errors && result.data.error.errors[0] && result.data.error.errors[0].reason;
    console.log('Diagnostic check ' + i + ': HTTP ' + result.code + ', reason ' + (reason || 'none'));
  });
}
