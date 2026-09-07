"""Automated test suite for FaceChain Verifier."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from facechain.blockchain import (
    LocalBlockchain,
    compute_block_hash,
    fingerprint_record,
    sha256_file,
)
from facechain.certificate import generate_html_certificate
from facechain.face import detect_and_encode, hash_descriptor
from facechain.search import SearchResult, choose_match


def test_face_detection_and_encoding(tmp_path: Path):
    """Test face detection, 128-d descriptor extraction, and evidence generation."""
    sample_path = Path("sample.jpg")
    assert sample_path.exists(), "sample.jpg must exist in workspace for tests"

    res = detect_and_encode(sample_path, tmp_path)
    assert len(res.box) == 4
    assert res.box[2] > 0 and res.box[3] > 0
    assert len(res.encoding) == 128
    assert len(res.encoding_hash) == 64
    assert res.annotated_path.exists()
    assert res.face_crop_path.exists()


def test_face_descriptor_determinism(tmp_path: Path):
    """Test that the 128-d descriptor is deterministic for identical input."""
    sample_path = Path("sample.jpg")
    res1 = detect_and_encode(sample_path, tmp_path / "run1")
    res2 = detect_and_encode(sample_path, tmp_path / "run2")

    assert res1.encoding == res2.encoding
    assert res1.encoding_hash == res2.encoding_hash


def test_blockchain_genesis_and_chaining(tmp_path: Path):
    """Test blockchain initialization, block linking, and verification."""
    chain_file = tmp_path / "blockchain.json"
    chain = LocalBlockchain(chain_file)

    assert len(chain.chain) == 1
    assert chain.chain[0]["index"] == 0
    assert chain.chain[0]["previous_hash"] == "0" * 64

    # Add block 1
    rec1 = {
        "input_image_sha256": "1111" * 16,
        "face_encoding_sha256": "aaaa" * 16,
        "matched_page_url": "https://instagram.com/p/test1",
    }
    b1 = chain.add_record(rec1)
    assert b1["index"] == 1
    assert b1["previous_hash"] == chain.chain[0]["block_hash"]

    # Add block 2
    rec2 = {
        "input_image_sha256": "2222" * 16,
        "face_encoding_sha256": "bbbb" * 16,
        "matched_page_url": "https://x.com/user/status/2",
    }
    b2 = chain.add_record(rec2)
    assert b2["index"] == 2
    assert b2["previous_hash"] == b1["block_hash"]

    # Verify complete chain
    is_valid, msg = chain.verify()
    assert is_valid is True
    assert "verified" in msg.lower()


def test_blockchain_tamper_detection(tmp_path: Path):
    """Test that altering any record payload or block hash is caught by verify()."""
    chain_file = tmp_path / "tamper_chain.json"
    chain = LocalBlockchain(chain_file)

    rec = {
        "face_encoding_sha256": "cafe" * 16,
        "matched_page_url": "https://instagram.com/p/authentic",
    }
    chain.add_record(rec)

    # 1. Verify before tamper
    assert chain.verify()[0] is True

    # 2. Tamper payload record
    chain.tamper_block_record(1, "matched_page_url", "https://evil.com/fake")
    is_valid, msg = chain.verify()
    assert is_valid is False
    assert "tampered" in msg.lower() or "mismatch" in msg.lower()

    # 3. Reload from disk to prove persistence of tamper detection
    reloaded = LocalBlockchain(chain_file)
    assert reloaded.verify()[0] is False


def test_search_match_ranking():
    """Test domain prioritization and genuine fallback in search ranking."""
    matches = [
        SearchResult(1, "Blog Post", "https://example.com/blog/1", "Example", "https://img.com/1.jpg"),
        SearchResult(2, "Reddit Discussion", "https://reddit.com/r/pics/1", "Reddit", "https://img.com/2.jpg"),
        SearchResult(3, "Instagram Photo", "https://www.instagram.com/p/abc12345/", "Instagram", "https://img.com/3.jpg"),
    ]

    # Preference for instagram.com
    selected_ig = choose_match(matches, preferred_domain="instagram.com")
    assert selected_ig.position == 3
    assert "instagram.com" in selected_ig.page_url

    # Preference for non-matching domain falls back to top visual match
    selected_fallback = choose_match(matches, preferred_domain="tiktok.com")
    assert selected_fallback.position == 1


def test_html_certificate_generation(tmp_path: Path):
    """Test generation of standalone HTML audit certificate."""
    cert_path = tmp_path / "certificate.html"
    dummy_crop = tmp_path / "face_crop.jpg"
    dummy_crop.write_bytes(b"\xff\xd8\xff\xe0" + b"\x00" * 100)  # Minimal JPEG header

    record = {
        "input_image_sha256": "abc",
        "face_encoding_sha256": "def",
        "matched_page_url": "https://instagram.com/p/xyz",
        "matched_title": "Test Title",
        "matched_source": "Instagram",
        "record_fingerprint": "123456",
    }
    block = {
        "index": 1,
        "timestamp": "2026-09-07T00:00:00Z",
        "previous_hash": "0000",
        "block_hash": "ffff",
    }

    out = generate_html_certificate(record, block, dummy_crop, cert_path)
    assert out.exists()
    content = out.read_text(encoding="utf-8")
    assert "FaceChain Cryptographic Certificate" in content
    assert "https://instagram.com/p/xyz" in content
