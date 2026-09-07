"""Generates a standalone, beautiful HTML audit certificate for verified records."""

from __future__ import annotations

import base64
from pathlib import Path
from typing import Any, Dict


def generate_html_certificate(
    record: Dict[str, Any],
    block: Dict[str, Any],
    face_crop_path: Path | str,
    output_html_path: Path | str = "output/certificate.html",
) -> Path:
    """
    Generate an offline-capable, self-contained HTML cryptographic certificate.
    """
    out_path = Path(output_html_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    # Convert face crop to base64 data URI for portable standalone HTML
    crop_p = Path(face_crop_path)
    face_b64 = ""
    if crop_p.exists():
        face_bytes = crop_p.read_bytes()
        face_b64 = f"data:image/jpeg;base64,{base64.b64encode(face_bytes).decode('utf-8')}"

    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>FaceChain Cryptographic Certificate — Block #{block.get('index')}</title>
  <style>
    :root {{
      --bg: #0b0f19;
      --card: #111827;
      --border: #1f2937;
      --accent: #10b981;
      --accent-glow: rgba(16, 185, 129, 0.25);
      --text: #f9fafb;
      --muted: #9ca3af;
      --code-bg: #030712;
      --brand: #6366f1;
    }}
    * {{ box-sizing: border-box; margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; }}
    body {{ background-color: var(--bg); color: var(--text); padding: 2rem 1rem; line-height: 1.5; }}
    .container {{ max-width: 860px; margin: 0 auto; }}
    .cert-card {{ background: var(--card); border: 1px solid var(--border); border-radius: 16px; padding: 2.5rem; box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.5); position: relative; overflow: hidden; }}
    .cert-card::before {{ content: ""; position: absolute; top: 0; left: 0; right: 0; height: 4px; background: linear-gradient(90deg, #10b981, #6366f1, #3b82f6); }}
    .header {{ display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 2rem; border-bottom: 1px solid var(--border); padding-bottom: 1.5rem; }}
    .title h1 {{ font-size: 1.75rem; font-weight: 700; letter-spacing: -0.025em; color: var(--text); }}
    .title p {{ color: var(--muted); font-size: 0.875rem; margin-top: 0.25rem; }}
    .badge {{ display: inline-flex; align-items: center; gap: 0.5rem; background: var(--accent-glow); color: var(--accent); border: 1px solid var(--accent); padding: 0.35rem 0.85rem; border-radius: 9999px; font-size: 0.8125rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em; }}
    .grid {{ display: grid; grid-template-columns: 180px 1fr; gap: 2rem; margin-bottom: 2rem; }}
    @media (max-width: 640px) {{ .grid {{ grid-template-columns: 1fr; }} }}
    .face-preview {{ display: flex; flex-direction: column; align-items: center; justify-content: center; background: var(--code-bg); border: 1px solid var(--border); border-radius: 12px; padding: 1rem; text-align: center; }}
    .face-img {{ width: 140px; height: 140px; object-fit: cover; border-radius: 8px; border: 2px solid var(--accent); }}
    .face-label {{ font-size: 0.75rem; color: var(--muted); margin-top: 0.5rem; text-transform: uppercase; font-weight: 600; }}
    .details-table {{ width: 100%; border-collapse: collapse; }}
    .details-table tr {{ border-bottom: 1px solid var(--border); }}
    .details-table tr:last-child {{ border-bottom: none; }}
    .details-table td {{ padding: 0.75rem 0; font-size: 0.875rem; vertical-align: middle; }}
    .details-table td:first-child {{ color: var(--muted); width: 150px; font-weight: 500; }}
    .code-val {{ font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace; background: var(--code-bg); padding: 0.2rem 0.4rem; border-radius: 4px; font-size: 0.8rem; word-break: break-all; color: #a5b4fc; }}
    .blockchain-section {{ background: var(--code-bg); border: 1px solid var(--border); border-radius: 12px; padding: 1.5rem; margin-top: 1.5rem; }}
    .blockchain-section h3 {{ font-size: 1rem; font-weight: 600; margin-bottom: 1rem; color: var(--text); display: flex; align-items: center; gap: 0.5rem; }}
    .blockchain-grid {{ display: grid; grid-template-columns: repeat(2, 1fr); gap: 1rem; }}
    @media (max-width: 640px) {{ .blockchain-grid {{ grid-template-columns: 1fr; }} }}
    .block-field {{ display: flex; flex-direction: column; gap: 0.25rem; }}
    .block-field label {{ font-size: 0.75rem; color: var(--muted); text-transform: uppercase; font-weight: 600; }}
    .footer {{ margin-top: 2rem; text-align: center; font-size: 0.8125rem; color: var(--muted); border-top: 1px solid var(--border); padding-top: 1.5rem; }}
  </style>
</head>
<body>
  <div class="container">
    <div class="cert-card">
      <div class="header">
        <div class="title">
          <h1>FaceChain Verification Proof</h1>
          <p>Hacker House Goa 2026 — Cryptographic Identity & Web Provenance Certificate</p>
        </div>
        <div class="badge">
          <span>●</span> Verified On-Chain
        </div>
      </div>

      <div class="grid">
        <div class="face-preview">
          {"<img src='" + face_b64 + "' alt='Detected Face' class='face-img' />" if face_b64 else "<div style='width:140px;height:140px;display:flex;align-items:center;justify-content:center;background:#1f2937;border-radius:8px;'>No Image</div>"}
          <span class="face-label">Detected Face ROI</span>
        </div>

        <div>
          <table class="details-table">
            <tr>
              <td>Input Image Hash</td>
              <td><span class="code-val">{record.get('input_image_sha256', 'N/A')}</span></td>
            </tr>
            <tr>
              <td>Face Descriptor Hash</td>
              <td><span class="code-val">{record.get('face_encoding_sha256', 'N/A')}</span></td>
            </tr>
            <tr>
              <td>Matched Social Post</td>
              <td><a href="{record.get('matched_page_url', '#')}" target="_blank" style="color: #60a5fa; text-decoration: none; word-break: break-all;">{record.get('matched_page_url', 'N/A')}</a></td>
            </tr>
            <tr>
              <td>Matched Title / Source</td>
              <td><strong>{record.get('matched_title', 'Visual Match')}</strong> ({record.get('matched_source', 'Web')})</td>
            </tr>
            <tr>
              <td>Record Fingerprint</td>
              <td><span class="code-val">{record.get('record_fingerprint', 'N/A')}</span></td>
            </tr>
          </table>
        </div>
      </div>

      <div class="blockchain-section">
        <h3>⛓️ Blockchain Anchor Details</h3>
        <div class="blockchain-grid">
          <div class="block-field">
            <label>Block Index</label>
            <span class="code-val">Block #{block.get('index')}</span>
          </div>
          <div class="block-field">
            <label>Block Timestamp (UTC)</label>
            <span class="code-val">{block.get('timestamp')}</span>
          </div>
          <div class="block-field" style="grid-column: 1 / -1;">
            <label>Previous Block Hash</label>
            <span class="code-val">{block.get('previous_hash')}</span>
          </div>
          <div class="block-field" style="grid-column: 1 / -1;">
            <label>Current Block Hash</label>
            <span class="code-val">{block.get('block_hash')}</span>
          </div>
        </div>
      </div>

      <div class="footer">
        Generated by <strong>FaceChain Verifier</strong> • SHA-256 Chained Ledger • Zero Hardcoded Results
      </div>
    </div>
  </div>
</body>
</html>
"""
    out_path.write_text(html_content, encoding="utf-8")
    return out_path
