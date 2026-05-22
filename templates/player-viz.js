(function (global) {
  "use strict";

  function midiHz(p) {
    return 440 * Math.pow(2, (p - 69) / 12);
  }

  function velAmp(v, bassCutoff, B, pitch) {
    const base = Math.pow(v / 127, 1.35);
    const low = pitch < bassCutoff ? B : 1;
    return base * low;
  }

  function beatToSec(beat, tempoMap) {
    let sec = 0;
    for (let i = 0; i < tempoMap.length; i++) {
      const b0 = tempoMap[i].beat;
      const bpm = tempoMap[i].bpm;
      const b1 = i + 1 < tempoMap.length ? tempoMap[i + 1].beat : beat;
      if (beat <= b0) break;
      const hi = Math.min(beat, b1);
      sec += ((hi - b0) / bpm) * 60;
      if (beat <= b1) return sec;
    }
    if (tempoMap.length) {
      const last = tempoMap[tempoMap.length - 1];
      if (beat > last.beat) sec += ((beat - last.beat) / last.bpm) * 60;
    }
    return sec;
  }

  function activeAt(notes, T) {
    const out = [];
    for (let i = 0; i < notes.length; i++) {
      const n = notes[i];
      if (n.s <= T && T < n.e) out.push(n);
    }
    return out;
  }

  function DmidiViz(canvas, opts) {
    this.canvas = canvas;
    this.ctx = canvas.getContext("2d");
    this.notes = opts.notes || [];
    this.pitchMin = opts.pitchMin ?? 21;
    this.pitchMax = opts.pitchMax ?? 108;
    this.durationBeats = opts.durationBeats || 1;
    this.tempoMap = opts.tempoMap || [{ beat: 0, bpm: 120 }];
    this.bassCutoff = opts.bassCutoff || 280;
    this.mode = "fit";
    this.T = 0;
    this.B = 1;
    this.scrollBeats = 6;
    this.playheadFrac = 0.14;
    this.pcmHistory = new Float32Array(100);
    this.pcmIdx = 0;
    this.pcmVisible = 100;
    this._playing = false;
    this._drawQueued = false;
    this._onResize = this.resize.bind(this);
    window.addEventListener("resize", this._onResize);
  }

  DmidiViz.prototype.destroy = function () {
    window.removeEventListener("resize", this._onResize);
  };

  DmidiViz.prototype.setPlaying = function (on) {
    this._playing = !!on;
    if (!this._playing) this.draw();
  };

  DmidiViz.prototype.requestDraw = function () {
    if (!this._playing) {
      this.draw();
      return;
    }
    if (this._drawQueued) return;
    this._drawQueued = true;
    const self = this;
    requestAnimationFrame(function () {
      self._drawQueued = false;
      self.draw();
    });
  };

  DmidiViz.prototype.setMode = function (m) {
    this.mode = m;
    this.draw();
  };

  DmidiViz.prototype.setT = function (t, opts) {
    opts = opts || {};
    this.T = t;
    if (this.mode === "pcm") this._pushPcmSample();
    if (opts.playing) this.requestDraw();
    else this.draw();
  };

  DmidiViz.prototype.setB = function (b) {
    this.B = b;
    if (this.mode === "pcm") this._pushPcmSample();
    this.draw();
  };

  DmidiViz.prototype.resize = function () {
    const parent = this.canvas.parentElement;
    if (!parent) return;
    const r = parent.getBoundingClientRect();
    const dpr = window.devicePixelRatio || 1;
    this.canvas.width = Math.max(1, Math.floor(r.width * dpr));
    this.canvas.height = Math.max(1, Math.floor(r.height * dpr));
    this.canvas.style.width = r.width + "px";
    this.canvas.style.height = r.height + "px";
    this.ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    this.draw();
  };

  DmidiViz.prototype._padPitch = function () {
    const pad = 2;
    return {
      lo: Math.max(0, this.pitchMin - pad),
      hi: Math.min(127, this.pitchMax + pad),
    };
  };

  DmidiViz.prototype._notesInWindow = function (t0, t1) {
    const out = [];
    for (let i = 0; i < this.notes.length; i++) {
      const n = this.notes[i];
      if (n.e < t0 || n.s > t1) continue;
      out.push(n);
    }
    return out;
  };

  DmidiViz.prototype._drawKeyrollRects = function (notes, mapX, mapY, clip) {
    const ctx = this.ctx;
    const h = this.canvas.height / (window.devicePixelRatio || 1);
    const rowH = Math.max(2, (mapY(this.pitchMin) - mapY(this.pitchMin + 1)) * 0.82);
    ctx.fillStyle = "rgba(100, 180, 255, 0.85)";
    ctx.strokeStyle = "rgba(200, 230, 255, 0.35)";
    ctx.lineWidth = 1;
    for (let i = 0; i < notes.length; i++) {
      const n = notes[i];
      const x0 = mapX(n.s);
      const x1 = mapX(n.e);
      const y = mapY(n.p) - rowH * 0.5;
      const w = Math.max(1, x1 - x0);
      if (clip) {
        if (x1 < clip.left || x0 > clip.right) continue;
      }
      const bright = this.T >= n.s && this.T < n.e;
      if (bright) ctx.fillStyle = "rgba(255, 220, 120, 0.95)";
      else ctx.fillStyle = "rgba(100, 180, 255, 0.75)";
      ctx.fillRect(x0, y, w, rowH);
      ctx.strokeRect(x0, y, w, rowH);
    }
  };

  DmidiViz.prototype._drawFit = function () {
    const ctx = this.ctx;
    const w = this.canvas.width / (window.devicePixelRatio || 1);
    const h = this.canvas.height / (window.devicePixelRatio || 1);
    const pr = this._padPitch();
    const mapX = function (b) {
      return (b / this.durationBeats) * w;
    }.bind(this);
    const mapY = function (p) {
      return h - ((p - pr.lo) / (pr.hi - pr.lo)) * h;
    };
    ctx.fillStyle = "#0d1117";
    ctx.fillRect(0, 0, w, h);
    this._drawGridFit(w, h, pr, mapX, mapY);
    const notes = this._notesInWindow(0, this.durationBeats);
    this._drawKeyrollRects(notes, mapX, mapY, null);
    this._drawPlayLineFit(mapX);
  };

  DmidiViz.prototype._drawGridFit = function (w, h, pr, mapX, mapY) {
    const ctx = this.ctx;
    ctx.strokeStyle = "rgba(255,255,255,0.06)";
    ctx.lineWidth = 1;
    for (let p = pr.lo; p <= pr.hi; p++) {
      if (p % 12 === 0) {
        ctx.strokeStyle = "rgba(255,255,255,0.12)";
        const y = mapY(p);
        ctx.beginPath();
        ctx.moveTo(0, y);
        ctx.lineTo(w, y);
        ctx.stroke();
      }
    }
    const beats = Math.min(32, Math.ceil(this.durationBeats));
    const step = this.durationBeats / beats;
    ctx.strokeStyle = "rgba(255,255,255,0.05)";
    for (let b = 0; b <= this.durationBeats; b += step) {
      const x = mapX(b);
      ctx.beginPath();
      ctx.moveTo(x, 0);
      ctx.lineTo(x, h);
      ctx.stroke();
    }
  };

  DmidiViz.prototype._drawPlayLineFit = function (mapX) {
    const ctx = this.ctx;
    const w = this.canvas.width / (window.devicePixelRatio || 1);
    const h = this.canvas.height / (window.devicePixelRatio || 1);
    const x = mapX(this.T);
    ctx.strokeStyle = "rgba(255, 90, 90, 0.9)";
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.moveTo(x, 0);
    ctx.lineTo(x, h);
    ctx.stroke();
  };

  DmidiViz.prototype._drawScroll = function () {
    const ctx = this.ctx;
    const w = this.canvas.width / (window.devicePixelRatio || 1);
    const h = this.canvas.height / (window.devicePixelRatio || 1);
    const pr = this._padPitch();
    const playX = w * this.playheadFrac;
    const span = this.scrollBeats;
    const ppb = (w - playX) / span;
    const mapX = function (beat) {
      return playX - (this.T - beat) * ppb;
    }.bind(this);
    const mapY = function (p) {
      return h - ((p - pr.lo) / (pr.hi - pr.lo)) * h;
    };
    ctx.fillStyle = "#0d1117";
    ctx.fillRect(0, 0, w, h);
    ctx.strokeStyle = "rgba(255, 90, 90, 0.95)";
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.moveTo(playX, 0);
    ctx.lineTo(playX, h);
    ctx.stroke();
    ctx.fillStyle = "rgba(255, 90, 90, 0.08)";
    ctx.fillRect(playX - 1, 0, 3, h);
    const t0 = this.T - this.scrollBeats - 1;
    const t1 = this.T + 3;
    const notes = this._notesInWindow(t0, t1);
    this._drawKeyrollRects(notes, mapX, mapY, { left: -20, right: w + 20 });
  };

  DmidiViz.prototype._pushPcmSample = function () {
    const act = activeAt(this.notes, this.T);
    const tSec = beatToSec(this.T, this.tempoMap);
    let s = 0;
    for (let i = 0; i < act.length; i++) {
      const n = act[i];
      const f = midiHz(n.p);
      const a = velAmp(n.v, this.bassCutoff, this.B, n.p);
      s += a * Math.sin(2 * Math.PI * f * tSec);
    }
    const peak = Math.max(1, act.length * 0.35);
    s = Math.max(-1, Math.min(1, s / peak));
    this.pcmHistory[this.pcmIdx % this.pcmHistory.length] = s;
    this.pcmIdx++;
  };

  DmidiViz.prototype._drawPcm = function () {
    const ctx = this.ctx;
    const w = this.canvas.width / (window.devicePixelRatio || 1);
    const h = this.canvas.height / (window.devicePixelRatio || 1);
    const mid = h * 0.5;
    const waveH = h * 0.42;
    const nVis = this.pcmVisible;
    const slotW = w / nVis;
    ctx.fillStyle = "#0d1117";
    ctx.fillRect(0, 0, w, h);

    ctx.strokeStyle = "rgba(120, 220, 255, 0.95)";
    ctx.lineWidth = 2;
    ctx.beginPath();
    const len = this.pcmHistory.length;
    for (let i = 0; i < nVis; i++) {
      const idx = (this.pcmIdx - nVis + i + len) % len;
      const v = this.pcmHistory[idx];
      const x = i * slotW + slotW * 0.5;
      const y = mid - v * waveH;
      if (i === 0) ctx.moveTo(x, y);
      else ctx.lineTo(x, y);
    }
    ctx.stroke();

    ctx.strokeStyle = "rgba(255,255,255,0.12)";
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.moveTo(0, mid);
    ctx.lineTo(w, mid);
    ctx.stroke();

    const act = activeAt(this.notes, this.T);
    ctx.fillStyle = "rgba(255,255,255,0.5)";
    ctx.font = "11px system-ui, sans-serif";
    ctx.fillText(
      act.length + " partials · " + nVis + " samples · T=" + this.T.toFixed(2),
      8,
      h - 10
    );
  };

  DmidiViz.prototype.draw = function () {
    if (!this.ctx) return;
    if (this.mode === "fit") this._drawFit();
    else if (this.mode === "scroll") this._drawScroll();
    else this._drawPcm();
  };

  global.DmidiViz = DmidiViz;
  global.DmidiVizMidiHz = midiHz;
  global.DmidiVizBeatToSec = beatToSec;
})(typeof window !== "undefined" ? window : globalThis);
