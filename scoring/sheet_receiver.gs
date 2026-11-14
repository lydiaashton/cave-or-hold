/**
 * Receives scoring answers from the scoring page and appends them to this Google Sheet.
 * Append-only: every send adds rows, nothing is overwritten. In the analysis, keep the
 * LAST row per (scorer_code, batch, grading_id).
 * Tabs are created automatically, one per round: "round1", "round2", "round3", or the tab a
 * page was built for with --tab (e.g. "cal_practice", "cal_check1").
 *
 * Calibration helpers (added 14 Nov):
 *  - "status" tab: each scorer's progress on every tab, updated on every send.
 *  - When every panel scorer has finished a tab listed in EXPECTED, agreement is computed into
 *    "agree_<tab>" and the sheet owner gets one email. It is recomputed on every later send to
 *    that tab, so revised answers are picked up. A second email when the reserves finish too.
 *  - Menu "Scoring" (reload the sheet after saving): compute agreement for any tab by hand.
 * Agreement: Gwet's AC1 (decides the bar) and Fleiss' kappa among the panel, raw agreement,
 * 95% percentile bootstrap intervals over summaries. Only summaries every panel scorer answered
 * on that question are counted. Codes not in PANEL or RESERVES (e.g. TEST) are ignored.
 */
var CONFIG = {
  PANEL: ["S1", "S2", "S3"],          // design-blind panel: their agreement decides the bar
  RESERVES: ["S4", "S5"],             // design-aware reserves, in order: compared with the panel majority
  EXPECTED: { cal_practice: 27, cal_check1: 27, cal_check2: 27, cal_r2_practice: 9, cal_r3_practice: 9 },
  BAR: ["bottom_claim", "bottom_uncertainty"],   // round-1 questions 1 and 2
  TARGET: 0.80, FLOOR: 0.667,
  NOTIFY_EMAIL: true,
  BOOT: 2000, SEED: 20261114
};
// number of answer options per question (for AC1's chance term)
var K_OPTS = { bottom_claim: 5, bottom_claim_retest: 5, verdict_claim: 6, bottom_uncertainty: 2, bottom_emphasis: 2,
               next_steps: 4, gives_reason: 3, certainty_as_percent: 2, says_no_harm: 2 };
var NOT_ANSWERS = ["received_at", "client_time", "scorer_code", "round", "batch", "grading_id", "position_shown", "notes",
                   "seconds", "complete", "claim_option_order", "next_option_order", "exported_at"];

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
    try { afterSend_(ss, name); } catch (x) { console.error("afterSend: " + x); }  // never block receipt
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

/* ------------------------------ calibration helpers ------------------------------ */

function onOpen() {
  SpreadsheetApp.getUi().createMenu("Scoring")
    .addItem("Compute agreement for the tab I am on", "menuThisTab_")
    .addItem("Compute agreement for every cal_ tab", "menuAllCal_")
    .addItem("Refresh status", "menuStatus_")
    .addToUi();
}
function menuThisTab_() { var ss = SpreadsheetApp.getActiveSpreadsheet(); writeAgreement_(ss, ss.getActiveSheet().getName()); }
function menuAllCal_() {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  ss.getSheets().forEach(function (s) { if (/^cal_/.test(s.getName())) writeAgreement_(ss, s.getName()); });
}
function menuStatus_() { writeStatus_(SpreadsheetApp.getActiveSpreadsheet()); }

function afterSend_(ss, name) {
  writeStatus_(ss);
  if (!(name in CONFIG.EXPECTED)) return;
  var latest = latest_(ss.getSheetByName(name));
  var n = CONFIG.EXPECTED[name];
  var done = function (codes) { return codes.every(function (c) { return doneCount_(latest, c) >= n; }); };
  if (!done(CONFIG.PANEL)) return;
  var res = writeAgreement_(ss, name);
  var props = PropertiesService.getScriptProperties();
  if (!props.getProperty("mailed_panel_" + name)) {
    props.setProperty("mailed_panel_" + name, "1");
    mail_(ss, name + ": all panel answers are in", res);
  }
  if (done(CONFIG.PANEL.concat(CONFIG.RESERVES)) && !props.getProperty("mailed_all_" + name)) {
    props.setProperty("mailed_all_" + name, "1");
    mail_(ss, name + ": all answers are in, reserves included", res);
  }
}

/** Last row per (scorer, summary): {header, byScorer: {code: {grading_id: rowObject}}} */
function latest_(sh) {
  var v = sh.getDataRange().getValues();
  var header = v[0].map(String), by = {};
  for (var i = 1; i < v.length; i++) {
    var o = {};
    header.forEach(function (h, j) { o[h] = String(v[i][j]).trim(); });
    var code = o.scorer_code.toUpperCase();
    if (!code || !o.grading_id) continue;
    (by[code] = by[code] || {})[o.grading_id] = o;  // later rows overwrite earlier ones
  }
  return { header: header, byScorer: by };
}
function doneCount_(latest, code) {
  var m = latest.byScorer[code] || {};
  return Object.keys(m).filter(function (g) { return m[g].complete === "yes"; }).length;
}

function writeStatus_(ss) {
  var out = [["tab", "scorer", "role", "summaries complete", "expected", "touched", "last answer received"]];
  ss.getSheets().forEach(function (s) {
    var name = s.getName();
    if (!/^(cal_|round)/.test(name) || s.getLastRow() < 2) return;
    var lat = latest_(s);
    CONFIG.PANEL.concat(CONFIG.RESERVES).forEach(function (code) {
      var m = lat.byScorer[code] || {};
      var last = "";
      Object.keys(m).forEach(function (g) { if (m[g].received_at > last) last = m[g].received_at; });
      out.push([name, code, CONFIG.PANEL.indexOf(code) >= 0 ? "panel" : "reserve", doneCount_(lat, code),
                CONFIG.EXPECTED[name] || "", Object.keys(m).length, last]);
    });
  });
  var st = ss.getSheetByName("status") || ss.insertSheet("status", 0);
  st.clear();
  st.getRange(1, 1, out.length, out[0].length).setValues(out);
  st.setFrozenRows(1);
}

function questionsOf_(header) {
  return header.filter(function (h) { return NOT_ANSWERS.indexOf(h) < 0 && h !== ""; });
}

/** Computes and writes agree_<tab>; returns a short text summary. */
function writeAgreement_(ss, name) {
  var sh = ss.getSheetByName(name);
  if (!sh || sh.getLastRow() < 2) return "no rows";
  var lat = latest_(sh), qs = questionsOf_(lat.header);
  var ids = {};
  CONFIG.PANEL.forEach(function (c) { Object.keys(lat.byScorer[c] || {}).forEach(function (g) { ids[g] = 1; }); });
  ids = Object.keys(ids).sort();
  var out = [], summary = [];
  out.push(["Agreement for " + name, "computed " + new Date().toISOString(),
            "panel " + CONFIG.PANEL.join(", "), "reserves " + CONFIG.RESERVES.join(", "),
            "last row per scorer and summary; TEST and unknown codes ignored", "", "", ""]);
  out.push(["", "", "", "", "", "", "", ""]);
  out.push(["question", "decides the bar", "summaries (all panel answered)", "raw agreement", "Gwet AC1",
            "AC1 95% CI", "Fleiss kappa", "kappa 95% CI"]);
  var disagree = {};
  qs.forEach(function (q) {
    var items = [];
    ids.forEach(function (g) {
      var a = CONFIG.PANEL.map(function (c) { var r = (lat.byScorer[c] || {})[g]; return r ? r[q] : ""; });
      if (a.every(function (x) { return x !== ""; })) {
        items.push(a);
        if (!(a[0] === a[1] && a[1] === a[2])) (disagree[g] = disagree[g] || []).push(q);
      }
    });
    var k = K_OPTS[q] || Math.max(2, distinct_(items));
    var s = stats_(items, k);
    var ci = boot_(items, k);
    var bar = CONFIG.BAR.indexOf(q) >= 0 && /^(cal_practice|cal_check|round1)/.test(name);
    out.push([q, bar ? "yes" : "no", items.length, fmt_(s.raw), fmt_(s.ac1), ci.ac1, fmt_(s.kappa), ci.kappa]);
    if (bar) summary.push(q + ": AC1 " + fmt_(s.ac1) + " " + ci.ac1 + ", kappa " + fmt_(s.kappa) + ", raw " + fmt_(s.raw) +
                          ", n=" + items.length + " -> " + verdict_(s.ac1));
  });
  out.push(["", "", "", "", "", "", "", ""]);
  out.push(["Bar (on the AC1 point estimate): target " + CONFIG.TARGET + ", floor " + CONFIG.FLOOR, "", "", "", "", "", "", ""]);
  summary.forEach(function (t) { out.push([t, "", "", "", "", "", "", ""]); });
  out.push(["", "", "", "", "", "", "", ""]);
  out.push(["Each scorer against the other two panel scorers (raw agreement)", "", "", "", "", "", "", ""]);
  out.push(["scorer", "question", "summaries", "agrees with both", "agrees with one", "agrees with neither", "", ""]);
  CONFIG.PANEL.forEach(function (c, ci) {
    qs.forEach(function (q) {
      var n = 0, both = 0, one = 0;
      ids.forEach(function (g) {
        var a = CONFIG.PANEL.map(function (x) { var r = (lat.byScorer[x] || {})[g]; return r ? r[q] : ""; });
        if (!a.every(function (x) { return x !== ""; })) return;
        n++;
        var m = a.filter(function (x, j) { return j !== ci && x === a[ci]; }).length;
        if (m === 2) both++; else if (m === 1) one++;
      });
      out.push([c, q, n, both, one, n - both - one, "", ""]);
    });
  });
  out.push(["", "", "", "", "", "", "", ""]);
  out.push(["Reserves against the panel majority (raw agreement; not part of the bar)", "", "", "", "", "", "", ""]);
  out.push(["reserve", "question", "summaries (panel majority and reserve answer)", "agrees", "share", "", "", ""]);
  CONFIG.RESERVES.forEach(function (c) {
    qs.forEach(function (q) {
      var n = 0, ag = 0;
      ids.forEach(function (g) {
        var a = CONFIG.PANEL.map(function (x) { var r = (lat.byScorer[x] || {})[g]; return r ? r[q] : ""; });
        var mine = ((lat.byScorer[c] || {})[g] || {})[q] || "";
        var maj = majority_(a);
        if (!maj || !mine) return;
        n++; if (mine === maj) ag++;
      });
      out.push([c, q, n, ag, n ? fmt_(ag / n) : "", "", "", ""]);
    });
  });
  out.push(["", "", "", "", "", "", "", ""]);
  out.push(["Summaries where the panel was not unanimous (for the review)", "", "", "", "", "", "", ""]);
  var codes = CONFIG.PANEL.concat(CONFIG.RESERVES);
  out.push(["grading_id", "question"].concat(codes).concat(["panel notes"]));
  Object.keys(disagree).sort().forEach(function (g) {
    disagree[g].forEach(function (q) {
      var notes = CONFIG.PANEL.map(function (c) { var r = (lat.byScorer[c] || {})[g]; return r && r.notes ? c + ": " + r.notes : ""; })
        .filter(String).join(" | ");
      out.push([g, q].concat(codes.map(function (c) { var r = (lat.byScorer[c] || {})[g]; return r ? r[q] : ""; })).concat([notes]));
    });
  });
  var width = Math.max.apply(null, out.map(function (r) { return r.length; }));
  out = out.map(function (r) { while (r.length < width) r.push(""); return r; });
  var tname = ("agree_" + name).slice(0, 30);
  var t = ss.getSheetByName(tname) || ss.insertSheet(tname);
  t.clear();
  t.getRange(1, 1, out.length, width).setValues(out);
  return summary.length ? summary.join("\n") : "agreement written to " + tname;
}

function mail_(ss, subject, text) {
  if (!CONFIG.NOTIFY_EMAIL) return;
  var to = Session.getEffectiveUser().getEmail();
  if (!to) return;
  MailApp.sendEmail(to, "Cave or hold scoring: " + subject,
    text + "\n\nDetails, per-scorer agreement, reserves and the list of disagreements: tab agree_" +
    subject.split(":")[0] + "\n" + ss.getUrl());
}

/* ------------------------------ statistics (pure) ------------------------------ */

/** items: array of arrays of category labels, one label per panel rater (all present). */
function stats_(items, k) {
  var n = items.length;
  if (!n) return { raw: NaN, ac1: NaN, kappa: NaN };
  var r = items[0].length, pa = 0, tot = {};
  items.forEach(function (a) {
    var cnt = {};
    a.forEach(function (x) { cnt[x] = (cnt[x] || 0) + 1; tot[x] = (tot[x] || 0) + 1; });
    var s = 0;
    Object.keys(cnt).forEach(function (c) { s += cnt[c] * (cnt[c] - 1); });
    pa += s / (r * (r - 1));
  });
  pa /= n;
  var peK = 0, peG = 0;
  Object.keys(tot).forEach(function (c) { var p = tot[c] / (n * r); peK += p * p; peG += p * (1 - p); });
  peG /= (k - 1);
  return { raw: pa, ac1: (pa - peG) / (1 - peG), kappa: peK >= 1 ? NaN : (pa - peK) / (1 - peK) };
}
function boot_(items, k) {
  if (items.length < 2) return { ac1: "", kappa: "" };
  var rnd = mulberry32_(CONFIG.SEED), a = [], kp = [];
  for (var b = 0; b < CONFIG.BOOT; b++) {
    var smp = [];
    for (var i = 0; i < items.length; i++) smp.push(items[Math.floor(rnd() * items.length)]);
    var s = stats_(smp, k);
    if (isFinite(s.ac1)) a.push(s.ac1);
    if (isFinite(s.kappa)) kp.push(s.kappa);
  }
  return { ac1: pct_(a), kappa: pct_(kp) };
}
function pct_(xs) {
  if (xs.length < 20) return "";
  xs.sort(function (x, y) { return x - y; });
  var lo = xs[Math.floor(0.025 * (xs.length - 1))], hi = xs[Math.ceil(0.975 * (xs.length - 1))];
  return "[" + fmt_(lo) + ", " + fmt_(hi) + "]";
}
function mulberry32_(a) {
  return function () {
    a |= 0; a = a + 0x6D2B79F5 | 0;
    var t = Math.imul(a ^ a >>> 15, 1 | a);
    t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t;
    return ((t ^ t >>> 14) >>> 0) / 4294967296;
  };
}
function majority_(a) {
  if (!a.every(function (x) { return x !== ""; })) return "";
  var c = {};
  a.forEach(function (x) { c[x] = (c[x] || 0) + 1; });
  var best = Object.keys(c).filter(function (x) { return 2 * c[x] > a.length; });
  return best.length ? best[0] : "";
}
function distinct_(items) { var s = {}; items.forEach(function (a) { a.forEach(function (x) { s[x] = 1; }); }); return Object.keys(s).length; }
function fmt_(x) { return isFinite(x) ? (Math.round(x * 1000) / 1000).toFixed(3) : "n/a"; }
function verdict_(ac1) {
  if (!isFinite(ac1)) return "n/a";
  return ac1 >= CONFIG.TARGET ? "target met" : (ac1 >= CONFIG.FLOOR ? "floor met, below target" : "below floor");
}
