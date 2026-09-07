// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @title FaceVerificationRegistry
 * @dev On-Chain Cryptographic Registry for Face Identification and Social Web Provenance Records.
 * Designed for Hacker House Goa 2026 Shortlisting Task 3.
 */
contract FaceVerificationRegistry {
    struct VerificationRecord {
        uint256 blockId;
        uint256 timestamp;
        bytes32 inputImageHash;
        bytes32 faceEncodingHash;
        bytes32 recordFingerprint;
        string matchedPageUrl;
        string matchedSource;
        address registrar;
    }

    address public owner;
    uint256 public totalRecords;

    // Mapping from faceEncodingHash => Record
    mapping(bytes32 => VerificationRecord) public recordsByFaceHash;
    // Array of all anchored records
    VerificationRecord[] public recordHistory;

    event FaceRecordAnchored(
        uint256 indexed blockId,
        bytes32 indexed faceEncodingHash,
        bytes32 recordFingerprint,
        string matchedPageUrl,
        uint256 timestamp,
        address indexed registrar
    );

    constructor() {
        owner = msg.sender;
    }

    /**
     * @notice Anchor a verified face-search match onto the blockchain ledger.
     * @param inputImageHash SHA-256 hash of the input image file.
     * @param faceEncodingHash SHA-256 hash of the 128-d face descriptor vector.
     * @param recordFingerprint Canonical SHA-256 fingerprint of the full match payload.
     * @param matchedPageUrl Real social media/web URL discovered by Google Lens.
     * @param matchedSource Content platform or domain name (e.g. "instagram.com").
     */
    function anchorRecord(
        bytes32 inputImageHash,
        bytes32 faceEncodingHash,
        bytes32 recordFingerprint,
        string calldata matchedPageUrl,
        string calldata matchedSource
    ) external returns (uint256 blockId) {
        require(faceEncodingHash != bytes32(0), "Invalid face encoding hash");
        require(recordFingerprint != bytes32(0), "Invalid record fingerprint");
        require(bytes(matchedPageUrl).length > 0, "Matched URL cannot be empty");

        blockId = totalRecords++;

        VerificationRecord memory newRecord = VerificationRecord({
            blockId: blockId,
            timestamp: block.timestamp,
            inputImageHash: inputImageHash,
            faceEncodingHash: faceEncodingHash,
            recordFingerprint: recordFingerprint,
            matchedPageUrl: matchedPageUrl,
            matchedSource: matchedSource,
            registrar: msg.sender
        });

        recordsByFaceHash[faceEncodingHash] = newRecord;
        recordHistory.push(newRecord);

        emit FaceRecordAnchored(
            blockId,
            faceEncodingHash,
            recordFingerprint,
            matchedPageUrl,
            block.timestamp,
            msg.sender
        );
    }

    /**
     * @notice Re-verify an off-chain record against the on-chain anchor.
     * @param faceEncodingHash SHA-256 hash of the face descriptor.
     * @param expectedFingerprint Expected canonical record fingerprint.
     * @return isValid True if the record exists and matches the stored fingerprint.
     * @return blockId The index of the anchor record.
     * @return timestamp The block timestamp when the anchor was committed.
     */
    function verifyRecord(
        bytes32 faceEncodingHash,
        bytes32 expectedFingerprint
    ) external view returns (bool isValid, uint256 blockId, uint256 timestamp) {
        VerificationRecord memory record = recordsByFaceHash[faceEncodingHash];
        if (record.faceEncodingHash == bytes32(0)) {
            return (false, 0, 0);
        }
        isValid = (record.recordFingerprint == expectedFingerprint);
        return (isValid, record.blockId, record.timestamp);
    }
}
