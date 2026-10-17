// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/// @title DisclosureRegistry
/// @notice TokenTruth · 项目披露/研究/风险状态链上存证
/// @dev 单合约；链上仅存摘要哈希与关键元数据，原始文档保留链下
contract DisclosureRegistry {
    enum EvidenceType {
        PROJECT_DISCLOSURE,    // 项目方披露新版本
        RESEARCH_REPORT,       // 投资者研究报告
        RISK_STATUS_CHANGE,    // 风险状态变更
        INVESTOR_QA,           // 投资者问答（可选锚定）
        CONTENT_PUBLISH,       // 项目方内容发布
        EXECUTION_CONSENT      // 用户授权执行
    }

    struct Evidence {
        bytes32 evidenceHash;   // 内容摘要 hash
        string  evidenceId;     // 链下主键
        uint8   evidenceType;   // EvidenceType 枚举
        uint256 timestamp;
        string  projectId;      // 项目脱敏 ID
        string  docVersion;     // 关联资料版本
        bytes32 fromStatus;     // 状态变更前
        bytes32 toStatus;       // 状态变更后
        address recorder;
        uint256 blockNumber;
    }

    /// evidenceHash => 记录
    mapping(bytes32 => Evidence) public records;
    /// evidenceId => evidenceHash（防重复）
    mapping(string => bytes32) public idToHash;
    /// 全量 evidenceHash 列表
    bytes32[] public allHashes;
    /// 项目方地址 => 是否有权上传
    mapping(address => bool) public authorizedRecorders;
    /// owner
    address public owner;

    event EvidenceRecorded(
        bytes32 indexed evidenceHash,
        string  evidenceId,
        uint8   evidenceType,
        uint256 timestamp,
        string  projectId,
        string  docVersion,
        bytes32 fromStatus,
        bytes32 toStatus,
        address recorder,
        uint256 blockNumber
    );

    event RecorderAuthorized(address indexed recorder, bool authorized);
    event OwnershipTransferred(address indexed previous, address indexed current);

    modifier onlyOwner() {
        require(msg.sender == owner, "DisclosureRegistry: not owner");
        _;
    }

    modifier onlyAuthorized() {
        require(authorizedRecorders[msg.sender] || msg.sender == owner, "DisclosureRegistry: not authorized");
        _;
    }

    constructor() {
        owner = msg.sender;
        emit OwnershipTransferred(address(0), msg.sender);
        authorizedRecorders[msg.sender] = true;
        emit RecorderAuthorized(msg.sender, true);
    }

    function setRecorder(address recorder, bool authorized) external onlyOwner {
        authorizedRecorders[recorder] = authorized;
        emit RecorderAuthorized(recorder, authorized);
    }

    function recordEvidence(
        bytes32 evidenceHash,
        string calldata evidenceId,
        uint8 evidenceType,
        uint256 timestamp,
        string calldata projectId,
        string calldata docVersion,
        bytes32 fromStatus,
        bytes32 toStatus
    ) external onlyAuthorized returns (bool) {
        require(evidenceHash != bytes32(0), "DisclosureRegistry: empty hash");
        require(bytes(evidenceId).length > 0, "DisclosureRegistry: empty evidenceId");
        require(idToHash[evidenceId] == bytes32(0), "DisclosureRegistry: duplicate evidenceId");
        require(evidenceType <= uint8(EvidenceType.EXECUTION_CONSENT), "DisclosureRegistry: invalid type");

        Evidence memory rec = Evidence({
            evidenceHash: evidenceHash,
            evidenceId: evidenceId,
            evidenceType: evidenceType,
            timestamp: timestamp,
            projectId: projectId,
            docVersion: docVersion,
            fromStatus: fromStatus,
            toStatus: toStatus,
            recorder: msg.sender,
            blockNumber: block.number
        });
        records[evidenceHash] = rec;
        idToHash[evidenceId] = evidenceHash;
        allHashes.push(evidenceHash);

        emit EvidenceRecorded(
            evidenceHash, evidenceId, evidenceType, timestamp,
            projectId, docVersion, fromStatus, toStatus,
            msg.sender, block.number
        );
        return true;
    }

    function verify(bytes32 evidenceHash) external view returns (bool exists, Evidence memory rec) {
        rec = records[evidenceHash];
        exists = rec.evidenceHash != bytes32(0);
    }

    function getByEvidenceId(string calldata evidenceId) external view returns (bool exists, Evidence memory rec) {
        bytes32 h = idToHash[evidenceId];
        if (h == bytes32(0)) return (false, rec);
        rec = records[h];
        return (true, rec);
    }

    function totalEvidence() external view returns (uint256) {
        return allHashes.length;
    }

    function transferOwnership(address newOwner) external onlyOwner {
        require(newOwner != address(0), "DisclosureRegistry: zero owner");
        emit OwnershipTransferred(owner, newOwner);
        owner = newOwner;
    }
}
