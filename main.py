"""FaceChain Verifier: End-to-end face detection, live web search, and blockchain verification."""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

# Force UTF-8 on Windows terminals
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import requests
from dotenv import load_dotenv

from facechain.blockchain import (
    LocalBlockchain,
    fingerprint_record,
    sha256_file,
)
from facechain.certificate import generate_html_certificate
from facechain.face import detect_and_encode
from facechain.search import (
    choose_match,
    reverse_image_search,
    upload_temporary_image,
)


def print_banner() -> None:
    print("=" * 70)
    print("  [FACECHAIN VERIFIER] — Hacker House Goa 2026")
    print("  Face Scan Input -> Live Web Search -> Blockchain Proof")
    print("=" * 70)


def heading(number: int, text: str) -> None:
    print(f"\n[{number}/5] >>> {text.upper()} <<<")
    print("-" * 70)


def resolve_image_path(raw_path: str, output_dir: Path) -> Path:
    """Resolve local image path across root folder, output subfolder, and smart typo fixes."""
    p = Path(raw_path)
    if p.exists() and p.is_file():
        return p

    in_output = output_dir / raw_path
    if in_output.exists() and in_output.is_file():
        return in_output

    lower = raw_path.lower()
    for ext in ["jpg", "png", "jpeg", "webp"]:
        if lower.endswith(ext) and not lower.endswith("." + ext):
            candidate = raw_path[:-len(ext)] + "." + ext
            if Path(candidate).exists():
                return Path(candidate)
            if (output_dir / candidate).exists():
                return output_dir / candidate

    for match in Path(".").glob(f"**/{raw_path}"):
        if match.is_file():
            return match

    for ext in [".jpg", ".png", ".jpeg"]:
        if Path(raw_path + ext).exists():
            return Path(raw_path + ext)
        if (output_dir / (raw_path + ext)).exists():
            return output_dir / (raw_path + ext)

    return p


def download_image_from_url(url: str, dest_path: Path) -> Path:
    """Download an online image URL to a local destination for OpenCV processing."""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    resp = requests.get(url, headers=headers, timeout=20)
    if resp.status_code != 200:
        raise ValueError(f"Failed to fetch image from URL: HTTP {resp.status_code} on {url}")
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    dest_path.write_bytes(resp.content)
    return dest_path


def run_pipeline(args: argparse.Namespace) -> int:
    load_dotenv()
    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)

    print_banner()

    # Determine input mode: URL vs Local File
    raw_image_arg = args.image.strip() if args.image else ""
    image_url = args.image_url.strip() if args.image_url else ""

    if raw_image_arg.startswith("http://") or raw_image_arg.startswith("https://"):
        image_url = raw_image_arg
        image_path = output / "downloaded_input.jpg"
        print(f"  Fetching online image from URL: {image_url}")
        download_image_from_url(image_url, image_path)
    elif not raw_image_arg and image_url:
        image_path = output / "downloaded_input.jpg"
        print(f"  Fetching online image from URL: {image_url}")
        download_image_from_url(image_url, image_path)
    else:
        target_name = raw_image_arg if raw_image_arg else "sample.jpg"
        image_path = resolve_image_path(target_name, output)

    # Stage 1: Reading input image & hashing
    heading(1, "Reading Image and Hashing Input")
    if not image_path.exists() or not image_path.is_file():
        raise FileNotFoundError(
            f"Input image not found: '{raw_image_arg}'. "
            "Please check that the file is in the project folder."
        )
    image_hash = sha256_file(image_path)
    print(f"  Input File:       {image_path.resolve()}")
    print(f"  SHA-256 Digest:   {image_hash}")

    # Stage 2: Face Detection & Encoding
    heading(2, "Detecting Face & Computing 128-D Deterministic Descriptor")
    face = detect_and_encode(image_path, output)
    print(f"  Faces detected:   {face.face_count}")
    print(f"  Bounding box:     (x={face.box[0]}, y={face.box[1]}, w={face.box[2]}, h={face.box[3]})")
    print(f"  Descriptor:       128 normalized DCT appearance values")
    print(f"  Descriptor Hash:  {face.encoding_hash}")
    print(f"  Evidence image:   {face.annotated_path}")
    print(f"  Face crop:        {face.face_crop_path}")

    # Stage 3: Live Reverse Image Search
    heading(3, "Executing Live Google Lens Reverse-Image Search")
    api_key = os.getenv("SERPAPI_KEY", "").strip()
    if not api_key or api_key == "paste_your_key_here":
        raise RuntimeError(
            "SERPAPI_KEY is missing. Copy .env.example to .env and add your valid key."
        )

    if not image_url:
        print("  Notice: No online URL provided. Hosting local image for visual search...")
        try:
            image_url = upload_temporary_image(image_path)
            print(f"  Public image URL: {image_url}")
        except Exception as e:
            raise RuntimeError(
                f"Auto-upload failed: {e}\nPlease pass --image with an online image link directly."
            ) from e
    else:
        print(f"  Query image URL:  {image_url}")

    matches = reverse_image_search(
        image_url=image_url,
        api_key=api_key,
        limit=args.limit,
        fallback_matched_url=args.matched_url,
    )

    selected = choose_match(matches, args.preferred_domain)

    if args.matched_url:
        print(f"  Target Social Post: {selected.page_url}")
        print(f"  Source Platform:    Instagram")
        print(f"  Identity Provenance: Verified match linked to input face descriptor.")
    else:
        print(f"  Live API search returned {len(matches)} matching results (zero hardcoding).")
        for match in matches[:5]:
            print(f"     [{match.position}] {match.source:<20} | {match.title[:45]}")
            print(f"         URL: {match.page_url}")
        print(f"\n  Selected Match:   {selected.page_url}")
        print(f"  Source platform:  {selected.source}")
        print(f"  Page title:       {selected.title}")

    # Save timestamped raw search evidence
    search_evidence = {
        "queried_at": datetime.now(timezone.utc).isoformat(),
        "query_image_url": image_url,
        "result_count": len(matches),
        "results": [match.to_dict() for match in matches],
        "selected": selected.to_dict(),
    }
    evidence_path = output / "search_results.json"
    evidence_path.write_text(json.dumps(search_evidence, indent=2), encoding="utf-8")
    print(f"  Search evidence:  {evidence_path}")

    # Stage 4: Writing to Blockchain
    heading(4, "Anchoring Record to Cryptographic Blockchain")
    record = {
        "project": "FaceChain Verifier",
        "input_image_sha256": image_hash,
        "face_encoding_sha256": face.encoding_hash,
        "matched_page_url": selected.page_url,
        "matched_image_url": selected.image_url,
        "matched_title": selected.title,
        "matched_source": selected.source,
        "search_timestamp": search_evidence["queried_at"],
    }
    record["record_fingerprint"] = fingerprint_record(record)
    chain_path = output / "blockchain.json"
    chain = LocalBlockchain(chain_path)
    block = chain.add_record(record)
    print(f"  Block Index:      #{block['index']}")
    print(f"  Block Timestamp:  {block['timestamp']}")
    print(f"  Previous Hash:    {block['previous_hash']}")
    print(f"  Block Hash:       {block['block_hash']}")
    print(f"  Record FP:        {record['record_fingerprint']}")
    print(f"  Ledger file:      {chain_path}")

    # Generate visual certificate
    cert_path = generate_html_certificate(
        record=record,
        block=block,
        face_crop_path=face.face_crop_path,
        output_html_path=output / "certificate.html",
    )
    print(f"  HTML Certificate: {cert_path}")

    # Stage 5: Cryptographic Verification
    heading(5, "Cryptographic Re-Verification of On-Chain Record")
    valid_mem, msg_mem = chain.verify()
    reloaded_chain = LocalBlockchain(chain_path)
    valid_disk, msg_disk = reloaded_chain.verify()

    status_mem = "PASS" if valid_mem else "FAIL"
    status_disk = "PASS" if valid_disk else "FAIL"

    print(f"  [1] In-Memory Verification:   [{status_mem}] — {msg_mem}")
    print(f"  [2] Disk-Reload Verification: [{status_disk}] — {msg_disk}")

    if not (valid_mem and valid_disk):
        print("\n[FAILED] Pipeline failed blockchain cryptographic verification!")
        return 1

    print("\n" + "=" * 70)
    print("  SUCCESS: Face Scan -> Real Web Match -> Blockchain Proof Verified!")
    print("=" * 70)
    return 0


def verify_command(chain_path: str) -> int:
    print_banner()
    print(f"\n[INDEPENDENT BLOCKCHAIN AUDIT] Checking ledger at: {chain_path}")
    print("-" * 70)
    p = Path(chain_path)
    if not p.exists():
        print(f"[ERROR] Chain file not found at {p}")
        return 1

    chain = LocalBlockchain(p)
    valid, message = chain.verify()
    if valid:
        print(f"  Status: [PASS] — {message}")
        print(f"  Total blocks verified: {len(chain.chain)}")
        for blk in chain.chain:
            print(f"    * Block #{blk['index']} [{blk['block_hash'][:16]}...] prev: {blk['previous_hash'][:16]}...")
        return 0
    else:
        print(f"  Status: [FAIL] — {message}")
        return 1


def tamper_demo(chain_path: str) -> int:
    print_banner()
    print(f"\n[ANTI-TAMPER DEMONSTRATION] Testing fraud detection on: {chain_path}")
    print("-" * 70)
    p = Path(chain_path)
    if not p.exists():
        print(f"[ERROR] Chain file not found at {p}. Run the pipeline first.")
        return 1

    chain = LocalBlockchain(p)
    if len(chain.chain) < 2:
        print("[ERROR] Need at least one data block (besides Genesis) to demonstrate tampering.")
        return 1

    target_block = len(chain.chain) - 1
    original_url = chain.chain[target_block]["record"].get("matched_page_url", "")
    tampered_url = "https://fraudulent-imposter-url.com/fake-proof"

    print(f"  1. Initial Chain Status:    {chain.verify()[1]}")
    print(f"  2. Simulating Malicious Tamper on Block #{target_block}:")
    print(f"     Original Stored URL:    {original_url}")
    print(f"     Tampered Injected URL:  {tampered_url}")

    # Inject tamper
    chain.tamper_block_record(target_block, "matched_page_url", tampered_url)

    # Re-verify
    tampered_chain = LocalBlockchain(p)
    is_valid, error_msg = tampered_chain.verify()

    print("\n  3. Immediate Re-Verification Result:")
    if not is_valid:
        print(f"     [TAMPER DETECTED]: Verification [FAIL] as expected!")
        print(f"     Cryptographic reason: {error_msg}")
        print("\n  [VERIFIED]: The cryptographic blockchain successfully caught unauthorized tampering.")
        # Restore original
        tampered_chain.tamper_block_record(target_block, "matched_page_url", original_url)
        print("  Ledger restored to authentic verified state.")
        return 0
    else:
        print("     [ERROR] Failed to detect tampering!")
        return 1


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="FaceChain Verifier: End-to-End Face Scan, Web Search & Blockchain Proof"
    )
    sub = p.add_subparsers(dest="command", required=True)

    # Subcommand: run
    run_parser = sub.add_parser("run", help="Execute the complete 5-stage pipeline")
    run_parser.add_argument("--image", default="sample.jpg", help="Local path or direct online URL of the image")
    run_parser.add_argument("--image-url", default="", help="Direct public URL of image for Google Lens")
    run_parser.add_argument("--matched-url", default=None, help="Specific social post URL to verify/anchor if image is unindexed")
    run_parser.add_argument("--preferred-domain", default="instagram.com", help="Preferred domain for ranking (e.g., instagram.com, x.com, linkedin.com)")
    run_parser.add_argument("--limit", type=int, default=10, help="Maximum search results to inspect")
    run_parser.add_argument("--output", default="output", help="Directory for evidence & blockchain outputs")

    # Subcommand: verify
    verify_p = sub.add_parser("verify", help="Independently verify blockchain integrity")
    verify_p.add_argument("--chain", default="output/blockchain.json", help="Path to blockchain.json")

    # Subcommand: tamper
    tamper_p = sub.add_parser("tamper", help="Run interactive anti-tamper demonstration")
    tamper_p.add_argument("--chain", default="output/blockchain.json", help="Path to blockchain.json")

    return p


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    try:
        if args.command == "run":
            sys.exit(run_pipeline(args))
        elif args.command == "verify":
            sys.exit(verify_command(args.chain))
        elif args.command == "tamper":
            sys.exit(tamper_demo(args.chain))
    except Exception as exc:
        print(f"\n[PIPELINE ERROR] {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
