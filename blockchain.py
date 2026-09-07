"""Cryptographic hash-linked blockchain ledger for tamper-evident verification."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


def sha256_file(file_path: Path | str) -> str:
    """Compute SHA-256 hash of a file on disk."""
    p = Path(file_path)
    if not p.exists():
        raise FileNotFoundError(f"File not found: {p}")
    hasher = hashlib.sha256()
    with open(p, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()


def fingerprint_record(record: Dict[str, Any]) -> str:
    """
    Generate a deterministic SHA-256 fingerprint for a match record.
    
    Excludes any existing 'record_fingerprint' key to allow self-referential hashing.
    """
    filtered = {k: v for k, v in record.items() if k != "record_fingerprint"}
    canonical_json = json.dumps(filtered, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()


def compute_block_hash(
    index: int,
    previous_hash: str,
    timestamp: str,
    record_fingerprint: str,
    nonce: int = 0,
) -> str:
    """Compute SHA-256 hash for a block header."""
    header = f"{index}:{previous_hash}:{timestamp}:{record_fingerprint}:{nonce}"
    return hashlib.sha256(header.encode("utf-8")).hexdigest()


class LocalBlockchain:
    """
    Persistent, tamper-evident hash-linked blockchain ledger.
    
    Each block links to the preceding block's SHA-256 hash and includes a canonical
    fingerprint of the discovered face and social media match record.
    """

    def __init__(self, chain_path: Path | str = "output/blockchain.json") -> None:
        self.chain_path = Path(chain_path)
        self.chain: List[Dict[str, Any]] = []
        if self.chain_path.exists():
            self._load()
        else:
            self._create_genesis_block()

    def _create_genesis_block(self) -> None:
        """Create and commit the initial genesis block."""
        genesis_timestamp = "2026-01-01T00:00:00+00:00"
        genesis_record = {
            "project": "FaceChain Verifier",
            "event": "Genesis Block",
            "protocol_version": "1.0.0",
            "author": "Hacker House Goa 2026 Candidate",
            "description": "Root anchor for face identification and visual provenance chain.",
        }
        rec_fp = fingerprint_record(genesis_record)
        genesis_record["record_fingerprint"] = rec_fp

        block_hash = compute_block_hash(
            index=0,
            previous_hash="0" * 64,
            timestamp=genesis_timestamp,
            record_fingerprint=rec_fp,
            nonce=0,
        )

        genesis_block = {
            "index": 0,
            "timestamp": genesis_timestamp,
            "previous_hash": "0" * 64,
            "record": genesis_record,
            "nonce": 0,
            "block_hash": block_hash,
        }
        self.chain = [genesis_block]
        self._save()

    def _load(self) -> None:
        """Load blockchain ledger from disk."""
        try:
            content = self.chain_path.read_text(encoding="utf-8")
            data = json.loads(content)
            self.chain = data if isinstance(data, list) else data.get("blocks", [])
        except Exception as exc:
            raise ValueError(f"Failed to load blockchain at {self.chain_path}: {exc}") from exc

    def _save(self) -> None:
        """Persist blockchain ledger to disk with formatting."""
        self.chain_path.parent.mkdir(parents=True, exist_ok=True)
        self.chain_path.write_text(json.dumps(self.chain, indent=2), encoding="utf-8")

    @property
    def last_block(self) -> Dict[str, Any]:
        """Return the most recent block."""
        return self.chain[-1]

    def add_record(self, record: Dict[str, Any], proof_of_work_difficulty: int = 1) -> Dict[str, Any]:
        """
        Add a new verified face-match record to the blockchain.

        Args:
            record: Data payload containing face hash, image hash, post URL, etc.
            proof_of_work_difficulty: Optional leading-zero difficulty for block hash.

        Returns:
            The newly created and committed block.
        """
        prev_block = self.last_block
        index = len(self.chain)
        timestamp = datetime.now(timezone.utc).isoformat()

        # Generate canonical fingerprint
        rec = dict(record)
        rec_fp = fingerprint_record(rec)
        rec["record_fingerprint"] = rec_fp

        # Compute hash with optional lightweight proof-of-work
        nonce = 0
        target = "0" * proof_of_work_difficulty
        while True:
            b_hash = compute_block_hash(
                index=index,
                previous_hash=prev_block["block_hash"],
                timestamp=timestamp,
                record_fingerprint=rec_fp,
                nonce=nonce,
            )
            if b_hash.startswith(target):
                break
            nonce += 1

        new_block = {
            "index": index,
            "timestamp": timestamp,
            "previous_hash": prev_block["block_hash"],
            "record": rec,
            "nonce": nonce,
            "block_hash": b_hash,
        }

        self.chain.append(new_block)
        self._save()
        return new_block

    def verify(self) -> Tuple[bool, str]:
        """
        Verify the complete cryptographic integrity of the blockchain.

        Checks:
        1. Genesis block validity.
        2. Previous block hash chaining for all consecutive blocks.
        3. Match record SHA-256 fingerprint recomputation.
        4. Block header SHA-256 recomputation.

        Returns:
            Tuple of (is_valid, status_message).
        """
        if not self.chain:
            return False, "Blockchain is empty."

        # Verify Genesis Block (Block 0)
        genesis = self.chain[0]
        if genesis.get("index") != 0:
            return False, "Genesis block index is not 0."
        if genesis.get("previous_hash") != "0" * 64:
            return False, "Genesis block previous hash is invalid."

        genesis_rec = genesis.get("record", {})
        expected_gen_fp = fingerprint_record(genesis_rec)
        if genesis_rec.get("record_fingerprint") != expected_gen_fp:
            return False, "Genesis block record fingerprint mismatch."

        expected_gen_hash = compute_block_hash(
            index=0,
            previous_hash="0" * 64,
            timestamp=genesis.get("timestamp", ""),
            record_fingerprint=expected_gen_fp,
            nonce=genesis.get("nonce", 0),
        )
        if genesis.get("block_hash") != expected_gen_hash:
            return False, "Genesis block hash is corrupted."

        # Verify subsequent blocks
        for i in range(1, len(self.chain)):
            current = self.chain[i]
            prev = self.chain[i - 1]

            # 1. Index check
            if current.get("index") != i:
                return False, f"Block #{i} has corrupted index: {current.get('index')} != {i}"

            # 2. Hash chaining check
            if current.get("previous_hash") != prev.get("block_hash"):
                return False, (
                    f"Block #{i} previous_hash mismatch! "
                    f"Stored: {current.get('previous_hash')[:16]}... vs "
                    f"Actual Block #{i-1} hash: {prev.get('block_hash')[:16]}..."
                )

            # 3. Payload integrity check
            record = current.get("record", {})
            computed_fp = fingerprint_record(record)
            if record.get("record_fingerprint") != computed_fp:
                return False, (
                    f"Block #{i} record data was tampered with! "
                    f"Fingerprint changed from {record.get('record_fingerprint')[:16]}... to {computed_fp[:16]}..."
                )

            # 4. Block header hash check
            computed_block_hash = compute_block_hash(
                index=current.get("index", i),
                previous_hash=current.get("previous_hash", ""),
                timestamp=current.get("timestamp", ""),
                record_fingerprint=computed_fp,
                nonce=current.get("nonce", 0),
            )
            if current.get("block_hash") != computed_block_hash:
                return False, (
                    f"Block #{i} block_hash is invalid! "
                    f"Stored: {current.get('block_hash')[:16]}... vs "
                    f"Recalculated: {computed_block_hash[:16]}..."
                )

        return True, f"All {len(self.chain)} blocks cryptographically verified and immutable."

    def tamper_block_record(self, block_index: int, key: str, new_value: Any) -> None:
        """
        Deliberately tamper with a record field to demonstrate tamper detection in live demos.
        """
        if block_index < 0 or block_index >= len(self.chain):
            raise IndexError(f"Block index {block_index} out of range.")
        self.chain[block_index]["record"][key] = new_value
        self._save()
