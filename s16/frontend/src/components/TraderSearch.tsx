import React, { useState } from 'react';
import { TextField, Button, Box, Alert, Paper } from '@mui/material';
import { isValidTraderAddress } from '../utils/validators';

interface TraderSearchProps {
  onSearch: (address: string) => void;
  loading?: boolean;
}

const TraderSearch: React.FC<TraderSearchProps> = ({ onSearch, loading = false }) => {
  const [address, setAddress] = useState('');
  const [error, setError] = useState('');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!isValidTraderAddress(address)) {
      setError('Please enter a valid trader address (Ethereum or Solana format)');
      return;
    }
    setError('');
    onSearch(address.trim());
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setAddress(e.target.value);
    if (error) setError('');
  };

  return (
    <Paper elevation={2} sx={{ p: 3, mb: 3 }}>
      <Box component="form" onSubmit={handleSubmit} sx={{ display: 'flex', gap: 2, alignItems: 'flex-start' }}>
        <TextField
          fullWidth
          label="Trader Address"
          value={address}
          onChange={handleChange}
          placeholder="Enter Ethereum (0x...) or Solana address"
          error={!!error}
          helperText={error || "Enter a valid blockchain address to search for trader data"}
          disabled={loading}
          sx={{ flexGrow: 1 }}
        />
        <Button
          type="submit"
          variant="contained"
          disabled={loading || !address.trim()}
          sx={{ minWidth: 120, height: 56 }}
        >
          {loading ? 'Searching...' : 'Search'}
        </Button>
      </Box>
      {error && (
        <Alert severity="error" sx={{ mt: 2 }}>
          {error}
        </Alert>
      )}
    </Paper>
  );
};

export default TraderSearch;