// SPDX-License-Identifier: MIT
pragma solidity ^0.8.28;

/// @title YieldOptimizer — AI-powered DeFi yield aggregation
/// @notice Automatically routes funds to best-yielding protocols
/// @dev Uses on-chain data + off-chain AI signals for optimal allocation
contract YieldOptimizer {
    error InsufficientBalance(uint256 requested, uint256 available);
    error InvalidProtocol(address protocol);
    error StrategyExpired(uint256 deadline);
    error NotOwner(address caller);
    error NotKeeper(address caller);
    error RebalanceFailed(string reason);

    event Deposited(address indexed user, uint256 amount, uint256 shares);
    event Withdrawn(address indexed user, uint256 amount, uint256 shares);
    event Rebalanced(address indexed protocol, uint256 amount, bytes signal);
    event StrategyUpdated(bytes32 indexed strategyId, string description);
    event YieldClaimed(uint256 amount, uint256 timestamp);

    struct Strategy {
        address protocol;
        uint256 allocationBps;      // Basis points (100 = 1%)
        uint256 minApy;             // Minimum APY in basis points
        uint256 deadline;           // Timestamp when strategy expires
        bool active;
    }

    struct UserVault {
        uint256 shares;
        uint256 depositedAt;
        uint256 lastClaim;
    }

    address public immutable owner;
    address public keeper;           // AI agent / bot address
    uint256 public totalShares;
    uint256 public totalAssets;
    uint256 public constant MAX_BPS = 10_000;
    uint256 public performanceFee = 500;    // 5% default
    uint256 public lastRebalance;
    uint256 public minRebalanceInterval = 1 hours;

    mapping(bytes32 => Strategy) public strategies;
    mapping(address => UserVault) public vaults;
    mapping(address => bool) public approvedProtocols;
    bytes32[] public activeStrategies;

    modifier onlyOwner() {
        if (msg.sender != owner) revert NotOwner(msg.sender);
        _;
    }

    modifier onlyKeeper() {
        if (msg.sender != keeper && msg.sender != owner) revert NotKeeper(msg.sender);
        _;
    }

    constructor(address _keeper) {
        owner = msg.sender;
        keeper = _keeper;
    }

    function setKeeper(address _keeper) external onlyOwner {
        keeper = _keeper;
    }

    function approveProtocol(address protocol, bool status) external onlyOwner {
        approvedProtocols[protocol] = status;
    }

    function addStrategy(
        bytes32 strategyId,
        address protocol,
        uint256 allocationBps,
        uint256 minApy,
        uint256 duration
    ) external onlyOwner {
        if (!approvedProtocols[protocol]) revert InvalidProtocol(protocol);
        if (allocationBps > MAX_BPS) revert InvalidProtocol(protocol);

        strategies[strategyId] = Strategy({
            protocol: protocol,
            allocationBps: allocationBps,
            minApy: minApy,
            deadline: block.timestamp + duration,
            active: true
        });
        activeStrategies.push(strategyId);
        emit StrategyUpdated(strategyId, "Strategy added");
    }

    function deposit() external payable returns (uint256 shares) {
        if (msg.value == 0) revert InsufficientBalance(0, 0);

        shares = totalShares == 0
            ? msg.value
            : (msg.value * totalShares) / totalAssets;

        vaults[msg.sender] = UserVault({
            shares: vaults[msg.sender].shares + shares,
            depositedAt: block.timestamp,
            lastClaim: block.timestamp
        });

        totalShares += shares;
        totalAssets += msg.value;

        emit Deposited(msg.sender, msg.value, shares);
    }

    function withdraw(uint256 shares) external returns (uint256 amount) {
        UserVault storage vault = vaults[msg.sender];
        if (shares > vault.shares) revert InsufficientBalance(shares, vault.shares);

        amount = (shares * totalAssets) / totalShares;

        vault.shares -= shares;
        totalShares -= shares;
        totalAssets -= amount;

        (bool sent,) = payable(msg.sender).call{value: amount}("");
        require(sent, "Transfer failed");

        emit Withdrawn(msg.sender, amount, shares);
    }

    /// @notice AI agent calls this to rebalance based on market conditions
    /// @param strategyId Target strategy
    /// @param amount Amount to rebalance
    /// @param signal AI signal data (off-chain verified)
    function rebalance(
        bytes32 strategyId,
        uint256 amount,
        bytes calldata signal
    ) external onlyKeeper {
        if (block.timestamp < lastRebalance + minRebalanceInterval) {
            revert RebalanceFailed("Rebalance cooldown active");
        }

        Strategy storage strategy = strategies[strategyId];
        if (!strategy.active) revert InvalidProtocol(strategy.protocol);
        if (block.timestamp > strategy.deadline) revert StrategyExpired(strategy.deadline);

        lastRebalance = block.timestamp;

        (bool sent,) = payable(strategy.protocol).call{value: amount}("");
        require(sent, "Transfer failed");

        emit Rebalanced(strategy.protocol, amount, signal);
    }

    /// @notice Claim accumulated yield
    function claimYield() external returns (uint256) {
        UserVault storage vault = vaults[msg.sender];
        uint256 timePassed = block.timestamp - vault.lastClaim;
        uint256 estimatedYield = (vault.shares * timePassed * 1e12) / 365 days; // simplified

        vault.lastClaim = block.timestamp;
        totalAssets -= estimatedYield;

        (bool sent,) = payable(msg.sender).call{value: estimatedYield}("");
        require(sent, "Transfer failed");

        emit YieldClaimed(estimatedYield, block.timestamp);
        return estimatedYield;
    }

    function getVaultInfo(address user) external view returns (
        uint256 shares,
        uint256 value,
        uint256 depositedAt,
        uint256 lastClaim
    ) {
        UserVault memory vault = vaults[user];
        shares = vault.shares;
        value = totalShares > 0 ? (vault.shares * totalAssets) / totalShares : 0;
        depositedAt = vault.depositedAt;
        lastClaim = vault.lastClaim;
    }

    function getActiveStrategies() external view returns (Strategy[] memory) {
        Strategy[] memory result = new Strategy[](activeStrategies.length);
        for (uint256 i = 0; i < activeStrategies.length; i++) {
            result[i] = strategies[activeStrategies[i]];
        }
        return result;
    }

    receive() external payable {
        totalAssets += msg.value;
    }
}
