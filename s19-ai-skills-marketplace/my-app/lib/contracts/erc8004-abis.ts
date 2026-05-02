// ERC-8004 Registry Contract ABIs

export const IDENTITY_REGISTRY_ABI = [
  {
    inputs: [
      { internalType: "string", name: "metadataURI", type: "string" },
      { internalType: "address", name: "owner", type: "address" }
    ],
    name: "registerIdentity",
    outputs: [{ internalType: "uint256", name: "tokenId", type: "uint256" }],
    stateMutability: "nonpayable",
    type: "function"
  },
  {
    inputs: [{ internalType: "address", name: "owner", type: "address" }],
    name: "getTokenIdByOwner",
    outputs: [{ internalType: "uint256", name: "", type: "uint256" }],
    stateMutability: "view",
    type: "function"
  },
  {
    inputs: [{ internalType: "uint256", name: "tokenId", type: "uint256" }],
    name: "tokenURI",
    outputs: [{ internalType: "string", name: "", type: "string" }],
    stateMutability: "view",
    type: "function"
  },
  {
    inputs: [{ internalType: "uint256", name: "tokenId", type: "uint256" }],
    name: "ownerOf",
    outputs: [{ internalType: "address", name: "", type: "address" }],
    stateMutability: "view",
    type: "function"
  },
  {
    inputs: [{ internalType: "address", name: "owner", type: "address" }],
    name: "balanceOf",
    outputs: [{ internalType: "uint256", name: "", type: "uint256" }],
    stateMutability: "view",
    type: "function"
  }
] as const;

export const REPUTATION_REGISTRY_ABI = [
  {
    inputs: [
      { internalType: "uint256", name: "agentId", type: "uint256" },
      { internalType: "uint8", name: "rating", type: "uint8" },
      { internalType: "string", name: "feedback", type: "string" }
    ],
    name: "submitFeedback",
    outputs: [],
    stateMutability: "nonpayable",
    type: "function"
  },
  {
    inputs: [{ internalType: "uint256", name: "agentId", type: "uint256" }],
    name: "getReputationScore",
    outputs: [{ internalType: "uint256", name: "score", type: "uint256" }],
    stateMutability: "view",
    type: "function"
  },
  {
    inputs: [{ internalType: "uint256", name: "agentId", type: "uint256" }],
    name: "getTotalFeedbacks",
    outputs: [{ internalType: "uint256", name: "total", type: "uint256" }],
    stateMutability: "view",
    type: "function"
  },
  {
    inputs: [
      { internalType: "uint256", name: "agentId", type: "uint256" },
      { internalType: "uint256", name: "index", type: "uint256" }
    ],
    name: "getFeedback",
    outputs: [
      { internalType: "uint8", name: "rating", type: "uint8" },
      { internalType: "string", name: "feedback", type: "string" },
      { internalType: "uint256", name: "timestamp", type: "uint256" }
    ],
    stateMutability: "view",
    type: "function"
  }
] as const;

export const VALIDATION_REGISTRY_ABI = [
  {
    inputs: [
      { internalType: "uint256", name: "escrowId", type: "uint256" },
      { internalType: "bool", name: "isValid", type: "bool" },
      { internalType: "string", name: "evidence", type: "string" }
    ],
    name: "validateTask",
    outputs: [],
    stateMutability: "nonpayable",
    type: "function"
  },
  {
    inputs: [{ internalType: "uint256", name: "escrowId", type: "uint256" }],
    name: "getValidationStatus",
    outputs: [
      { internalType: "bool", name: "isValid", type: "bool" },
      { internalType: "string", name: "evidence", type: "string" }
    ],
    stateMutability: "view",
    type: "function"
  },
  {
    inputs: [
      { internalType: "uint256", name: "escrowId", type: "uint256" },
      { internalType: "string", name: "reason", type: "string" }
    ],
    name: "raiseDispute",
    outputs: [],
    stateMutability: "nonpayable",
    type: "function"
  },
  {
    inputs: [{ internalType: "uint256", name: "escrowId", type: "uint256" }],
    name: "isDisputed",
    outputs: [{ internalType: "bool", name: "", type: "bool" }],
    stateMutability: "view",
    type: "function"
  }
] as const;

export const ESCROW_CONTRACT_ABI = [
  {
    inputs: [
      { internalType: "address payable", name: "seller", type: "address" },
      { internalType: "uint256", name: "amount", type: "uint256" },
      { internalType: "uint256", name: "deadline", type: "uint256" }
    ],
    name: "createEscrow",
    outputs: [{ internalType: "uint256", name: "escrowId", type: "uint256" }],
    stateMutability: "payable",
    type: "function"
  },
  {
    inputs: [{ internalType: "uint256", name: "escrowId", type: "uint256" }],
    name: "releaseFunds",
    outputs: [],
    stateMutability: "nonpayable",
    type: "function"
  },
  {
    inputs: [{ internalType: "uint256", name: "escrowId", type: "uint256" }],
    name: "refundBuyer",
    outputs: [],
    stateMutability: "nonpayable",
    type: "function"
  },
  {
    inputs: [{ internalType: "uint256", name: "escrowId", type: "uint256" }],
    name: "getEscrowDetails",
    outputs: [
      { internalType: "address payable", name: "buyer", type: "address" },
      { internalType: "address payable", name: "seller", type: "address" },
      { internalType: "uint256", name: "amount", type: "uint256" },
      { internalType: "uint256", name: "deadline", type: "uint256" },
      { internalType: "bool", name: "released", type: "bool" }
    ],
    stateMutability: "view",
    type: "function"
  },
  {
    inputs: [{ internalType: "uint256", name: "escrowId", type: "uint256" }],
    name: "deposit",
    outputs: [],
    stateMutability: "payable",
    type: "function"
  }
] as const;