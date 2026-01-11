import axios from 'axios';
import dotenv from 'dotenv';

dotenv.config();

const ETHERSCAN_API_KEY = process.env.ETHERSCAN_API_KEY;
const ETHERSCAN_BASE_URL = 'https://api.etherscan.io/api';

export interface ContractInfo {
  address: string;
  sourceCode: string;
  abi: string;
  contractName: string;
  compilerVersion: string;
}

export async function getContractInfo(address: string): Promise<ContractInfo | null> {
  try {
    const response = await axios.get(ETHERSCAN_BASE_URL, {
      params: {
        module: 'contract',
        action: 'getsourcecode',
        address,
        apikey: ETHERSCAN_API_KEY,
      },
    });

    const data = response.data;
    if (data.status === '1' && data.result.length > 0) {
      const result = data.result[0];
      return {
        address,
        sourceCode: result.SourceCode,
        abi: result.ABI,
        contractName: result.ContractName,
        compilerVersion: result.CompilerVersion,
      };
    }
    return null;
  } catch (error) {
    console.error('Error fetching contract info:', error);
    return null;
  }
}

// Placeholder for gathering security datasets (e.g., vulnerabilities)
export async function getSecurityDatasets(): Promise<any[]> {
  // TODO: Integrate with security APIs or databases
  // For now, return mock data
  return [
    {
      id: 'SWC-101',
      title: 'Integer Overflow and Underflow',
      description: 'Integer overflow and underflow vulnerabilities in smart contracts.',
    },
    // Add more...
  ];
}