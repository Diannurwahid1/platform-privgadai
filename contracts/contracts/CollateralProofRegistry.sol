// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {AccessControl} from "@openzeppelin/contracts/access/AccessControl.sol";
import {Pausable} from "@openzeppelin/contracts/utils/Pausable.sol";

/// @notice Records custody evidence commitments. Both identifiers are opaque bytes32 values.
/// @dev Never submit names, addresses, photos, KTP numbers, raw file hashes or public UUIDs.
contract CollateralProofRegistry is AccessControl, Pausable {
    bytes32 public constant REGISTRAR_ROLE = keccak256("REGISTRAR_ROLE");

    mapping(bytes32 eventId => bytes32 digest) private _proofs;

    event ProofRegistered(bytes32 indexed eventId, bytes32 digest, address indexed registrar);

    error EmptyProof();
    error ProofConflict(bytes32 eventId);

    constructor(address admin, address registrar) {
        require(admin != address(0) && registrar != address(0), "zero address");
        _grantRole(DEFAULT_ADMIN_ROLE, admin);
        _grantRole(REGISTRAR_ROLE, registrar);
    }

    function registerProof(bytes32 eventId, bytes32 digest) external onlyRole(REGISTRAR_ROLE) whenNotPaused {
        if (eventId == bytes32(0) || digest == bytes32(0)) revert EmptyProof();
        bytes32 current = _proofs[eventId];
        if (current == digest) return;
        if (current != bytes32(0)) revert ProofConflict(eventId);
        _proofs[eventId] = digest;
        emit ProofRegistered(eventId, digest, msg.sender);
    }

    function proofOf(bytes32 eventId) external view returns (bytes32) {
        return _proofs[eventId];
    }

    function pause() external onlyRole(DEFAULT_ADMIN_ROLE) { _pause(); }
    function unpause() external onlyRole(DEFAULT_ADMIN_ROLE) { _unpause(); }
}
