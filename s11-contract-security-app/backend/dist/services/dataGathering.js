"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.getContractInfo = getContractInfo;
exports.getSecurityDatasets = getSecurityDatasets;
const axios_1 = __importDefault(require("axios"));
const dotenv_1 = __importDefault(require("dotenv"));
dotenv_1.default.config();
const ETHERSCAN_API_KEY = process.env.ETHERSCAN_API_KEY;
const ETHERSCAN_BASE_URL = 'https://api.etherscan.io/api';
async function getContractInfo(address) {
    try {
        const response = await axios_1.default.get(ETHERSCAN_BASE_URL, {
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
    }
    catch (error) {
        console.error('Error fetching contract info:', error);
        return null;
    }
}
// Placeholder for gathering security datasets (e.g., vulnerabilities)
async function getSecurityDatasets() {
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
