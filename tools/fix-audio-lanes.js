#!/usr/bin/env node
// Greedy interval-colouring for SFX audio lanes in index.html so that no two
// overlapping <audio> clips share a data-track-index. VO stays on 2, BGM on 3.
const fs = require("fs");
const path = "index.html";
let html = fs.readFileSync(path, "utf8");

// collect sfx clips: id, start, end
const re = /<audio\s+id="(sfx-[^"]+)"[^>]*>/g;
const clips = [];
let m;
while ((m = re.exec(html))) {
  const tag = m[0];
  const id = m[1];
  const start = parseFloat(/data-start="([\d.]+)"/.exec(tag)[1]);
  const durM = /data-duration="([\d.]+)"/.exec(tag);
  // fall back to known file durations for clips without data-duration
  const fileDurs = {
    "key-press": 0.44, "whoosh-short": 0.58, "whoosh": 0.58, ping: 1.33,
    pop: 0.73, chime: 2.55, "impact-bass-1": 2.12, "impact-bass-2": 2.6,
    sparkle: 1.81, error: 1.62, "glitch-1": 2.64,
  };
  const srcM = /src="assets\/audio\/sfx\/([^".]+)/.exec(tag);
  const dflt = srcM ? fileDurs[srcM[1]] || 1.5 : 1.5;
  const dur = durM ? parseFloat(durM[1]) : dflt;
  clips.push({ id, start, end: start + dur, tag });
}
clips.sort((a, b) => a.start - b.start || a.end - b.end);

const laneEnd = new Map(); // lane -> last end
for (const c of clips) {
  let lane = 4;
  while (laneEnd.has(lane) && laneEnd.get(lane) > c.start + 1e-6) lane++;
  c.lane = lane;
  laneEnd.set(lane, c.end);
}

for (const c of clips) {
  const newTag = c.tag.replace(/data-track-index="\d+"/, `data-track-index="${c.lane}"`);
  html = html.replace(c.tag, newTag);
}
fs.writeFileSync(path, html);
const lanes = Math.max(...clips.map((c) => c.lane));
console.log(`rewrote ${clips.length} sfx clips; lanes 4..${lanes}`);
for (const c of clips) console.log(`  ${c.id}: ${c.start.toFixed(2)}-${c.end.toFixed(2)} -> lane ${c.lane}`);
