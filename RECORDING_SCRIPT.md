# Screen Recording Walkthrough Script

Use this unedited step-by-step guide to record your screen for your **Hacker House Goa 2026** submission.

---

## 🎬 Recording Steps (Continuous Single Take)

### 1. Project Overview (5–10 seconds)
- Open the project in VS Code.
- Briefly show the folder tree: `facechain/`, `contracts/`, `tests/`, `README.md`, `.gitignore`.
- Show that `.env` is ignored by git in `.gitignore`. (Do **not** open `.env` to protect your API key).

### 2. View Input Photo (3–5 seconds)
- Open `sample.jpg` in VS Code / image viewer to show the input face photo.

### 3. Run the End-to-End Pipeline (15–20 seconds)
- Open a clean terminal in VS Code and run:
  ```powershell
  python main.py run --image sample.jpg --image-url "YOUR_PUBLIC_IMAGE_URL" --preferred-domain instagram.com
  ```
- Highlight the 5 stages as they execute in the terminal:
  - `[1/5]` Input Image Hashing (SHA-256)
  - `[2/5]` Face Detection & 128-D Descriptor Hash
  - `[3/5]` Live Google Lens Search (showing live match count & selected match)
  - `[4/5]` Blockchain Block Creation (Block index, Previous Hash, Block Hash, Nonce)
  - `[5/5]` Cryptographic Re-Verification (`[PASS]` in-memory and disk-reload)

### 4. Inspect Output Evidence (10–15 seconds)
- Open `output/face_detected.jpg` to show the bounding box HUD and descriptor hash.
- Open `output/search_results.json` to show the live API response and timestamp.
- Open `output/blockchain.json` to show the persistent hash-linked ledger.
- Open `output/certificate.html` in a browser to show the cryptographic certificate.

### 5. Demonstrate Anti-Tamper Fraud Detection (10 seconds)
- In the terminal, run:
  ```powershell
  python main.py tamper --chain output/blockchain.json
  ```
- Show the blockchain instantly detecting fraudulent record manipulation with `[TAMPER DETECTED]: Verification [FAIL]` and identifying the altered block.

### 6. Run Independent Verification (5 seconds)
- In the terminal, run:
  ```powershell
  python main.py verify --chain output/blockchain.json
  ```
- Show `Status: [PASS]` for all blocks.

---

## 🎙️ Suggested Voiceover / Intro (Optional)

> "This is FaceChain Verifier for Hacker House Goa 2026. The pipeline takes a face scan, detects and encodes a 128-dimensional facial descriptor, performs a live Google Lens reverse search to find matching web content without any hardcoding, anchors the verified match to a hash-linked cryptographic blockchain, and proves the data is tamper-evident and verifiable."
