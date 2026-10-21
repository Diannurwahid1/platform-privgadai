// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {AccessControl} from "@openzeppelin/contracts/access/AccessControl.sol";
import {Pausable} from "@openzeppelin/contracts/utils/Pausable.sol";

/// @notice Immutable commitments for successive versions of a pawn agreement.
/// @dev The registrar attests that the platform recorded the documents and consent evidence.
///      This contract does not authenticate a borrower's signature or enforce a loan.
///      IDs and digests must be opaque; never put PII, raw document hashes or UUIDs on-chain.
contract PawnAgreementEvidenceRegistry is AccessControl, Pausable {
    bytes32 public constant REGISTRAR_ROLE = keccak256("REGISTRAR_ROLE");

    struct Commitment {
        bytes32 documentDigest;
        bytes32 consentDigest;
        uint64 recordedAt;
    }

    mapping(bytes32 agreementId => uint32 version) public latestVersion;
    mapping(bytes32 agreementId => mapping(uint32 version => Commitment)) private _commitments;

    event AgreementVersionRecorded(
        bytes32 indexed agreementId,
        uint32 indexed version,
        bytes32 documentDigest,
        bytes32 consentDigest,
        address indexed registrar
    );

    error EmptyCommitment();
    error InvalidVersion(uint32 expected, uint32 received);
    error CommitmentConflict(bytes32 agreementId, uint32 version);

    constructor(address admin, address registrar) {
        require(admin != address(0) && registrar != address(0), "zero address");
        _grantRole(DEFAULT_ADMIN_ROLE, admin);
        _grantRole(REGISTRAR_ROLE, registrar);
    }

    function recordVersion(
        bytes32 agreementId,
        uint32 version,
        bytes32 documentDigest,
        bytes32 consentDigest
    ) external onlyRole(REGISTRAR_ROLE) whenNotPaused {
        if (agreementId == bytes32(0) || documentDigest == bytes32(0) || consentDigest == bytes32(0)) {
            revert EmptyCommitment();
        }
        Commitment storage current = _commitments[agreementId][version];
        if (current.recordedAt != 0) {
            if (current.documentDigest == documentDigest && current.consentDigest == consentDigest) return;
            revert CommitmentConflict(agreementId, version);
        }
        uint32 expected = latestVersion[agreementId] + 1;
        if (version != expected) revert InvalidVersion(expected, version);
        current.documentDigest = documentDigest;
        current.consentDigest = consentDigest;
        current.recordedAt = uint64(block.timestamp);
        latestVersion[agreementId] = version;
        emit AgreementVersionRecorded(agreementId, version, documentDigest, consentDigest, msg.sender);
    }

    function commitmentOf(bytes32 agreementId, uint32 version) external view returns (Commitment memory) {
        return _commitments[agreementId][version];
    }

    function pause() external onlyRole(DEFAULT_ADMIN_ROLE) { _pause(); }
    function unpause() external onlyRole(DEFAULT_ADMIN_ROLE) { _unpause(); }
}
