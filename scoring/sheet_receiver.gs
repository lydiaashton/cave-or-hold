/**
 * Receives scoring answers from the scoring page and appends them to this Google Sheet.
 * Append-only: every send adds rows, nothing is overwritten. In the analysis, keep the
 * LAST row per (scorer_code, batch, grading_id).
 * Tabs are created automatically, one per round: "round1", "round2", "round3".
 */
function doGet() {
  return out_({ ok: true, message: "Scoring receiver is live." });
}

function doPost(e) {
  var lock = LockService.getScriptLock();
  try {
    lock.waitLock(20000);
    var body = JSON.parse(e.postData.contents);
    var cols = body.cols, rows = body.rows;
    if (!Array.isArray(cols) || !Array.isArray(rows) || rows.length === 0 || rows.length > 500 || cols.length > 40) {
      return out_({ ok: false, error: "bad request" });
    }
    var name = String(body.page || "round1").replace(/[^A-Za-z0-9_]/g, "").slice(0, 30) || "round1";
    var ss = SpreadsheetApp.getActiveSpreadsheet();
    var sh = ss.getSheetByName(name) || ss.insertSheet(name);
    var header = ["received_at", "client_time"].concat(cols.map(clean_));
    if (sh.getLastRow() === 0) { sh.appendRow(header); sh.setFrozenRows(1); }
    var now = new Date();
    var values = rows.map(function (r) {
      return [now, clean_(body.client_time)].concat(cols.map(function (c) { return clean_(r[c]); }));
    });
    sh.getRange(sh.getLastRow() + 1, 1, values.length, header.length).setValues(values);
    return out_({ ok: true, n: values.length });
  } catch (err) {
    return out_({ ok: false, error: String(err) });
  } finally {
    try { lock.releaseLock(); } catch (x) {}
  }
}

/** Text only, capped in length, and never read by Sheets as a formula. */
function clean_(v) {
  v = (v === null || v === undefined) ? "" : String(v).slice(0, 5000);
  return /^[=+\-@]/.test(v) ? "'" + v : v;
}

function out_(o) {
  return ContentService.createTextOutput(JSON.stringify(o)).setMimeType(ContentService.MimeType.JSON);
}
