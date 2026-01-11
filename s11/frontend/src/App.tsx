import React, { useState } from 'react';
import axios from 'axios';
import './App.css';

const API_BASE = 'http://localhost:3001/api';

function App() {
  console.log('App component rendered');
  const [contractAddress, setContractAddress] = useState('');
  const [contractInfo, setContractInfo] = useState<any>(null);
  const [auditResult, setAuditResult] = useState<any>(null);
  const [protectionStatus, setProtectionStatus] = useState<string>('');

  const fetchContractInfo = async () => {
    console.log('Fetching contract info for:', contractAddress);
    try {
      const res = await axios.get(`${API_BASE}/data/contract/${contractAddress}`);
      console.log('Contract info fetched:', res.data);
      setContractInfo(res.data);
    } catch (err) {
      console.error('Error fetching contract info:', err);
      alert('Error fetching contract info');
    }
  };

  const runAudit = async () => {
    if (!contractInfo) return;
    console.log('Running audit for contract:', contractInfo.contractName);
    try {
      const res = await axios.post(`${API_BASE}/audit/run`, {
        sourceCode: contractInfo.sourceCode,
        contractName: contractInfo.contractName,
      });
      console.log('Audit result:', res.data);
      setAuditResult(res.data);
    } catch (err) {
      console.error('Error running audit:', err);
      alert('Error running audit');
    }
  };

  const startProtection = async () => {
    console.log('Starting protection for contract:', contractAddress);
    try {
      await axios.post(`${API_BASE}/protection/start/${contractAddress}`);
      console.log('Protection started for:', contractAddress);
      setProtectionStatus(`Monitoring ${contractAddress}`);
    } catch (err) {
      console.error('Error starting protection:', err);
      alert('Error starting protection');
    }
  };

  return (
    <div className="App">
      <h1>Smart Contract Security Tool</h1>
      <input
        type="text"
        placeholder="Enter contract address"
        value={contractAddress}
        onChange={(e) => setContractAddress(e.target.value)}
      />
      <button onClick={fetchContractInfo}>Fetch Contract Info</button>

      {contractInfo && (
        <div>
          <h2>Contract Info</h2>
          <p>Name: {contractInfo.contractName}</p>
          <p>Compiler: {contractInfo.compilerVersion}</p>
          <button onClick={runAudit}>Run Audit</button>
          <button onClick={startProtection}>Start Protection</button>
        </div>
      )}

      {auditResult && (
        <div>
          <h2>Audit Result</h2>
          <pre>{JSON.stringify(auditResult, null, 2)}</pre>
        </div>
      )}

      {protectionStatus && (
        <div>
          <h2>Protection</h2>
          <p>{protectionStatus}</p>
        </div>
      )}
    </div>
  );
}

export default App;
