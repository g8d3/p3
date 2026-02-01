import React from 'react';
import {
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Typography,
  Box,
  Chip
} from '@mui/material';
import { Trade } from '../types';
import { formatCurrency, formatDate, formatNumber } from '../utils/formatters';

interface TradeHistoryProps {
  trades: Trade[];
  loading?: boolean;
}

const TradeHistory: React.FC<TradeHistoryProps> = ({ trades, loading = false }) => {
  if (loading) {
    return (
      <Paper sx={{ p: 3 }}>
        <Typography variant="h6">Loading trade history...</Typography>
      </Paper>
    );
  }

  if (!trades || trades.length === 0) {
    return (
      <Paper sx={{ p: 3 }}>
        <Typography variant="h6">No trades found</Typography>
        <Typography variant="body2" color="text.secondary">
          This trader hasn't executed any trades yet.
        </Typography>
      </Paper>
    );
  }

  return (
    <Paper>
      <Box sx={{ p: 3, pb: 0 }}>
        <Typography variant="h5" gutterBottom>
          Trade History
        </Typography>
        <Typography variant="body2" color="text.secondary" gutterBottom>
          {trades.length} trades found
        </Typography>
      </Box>
      <TableContainer>
        <Table>
          <TableHead>
            <TableRow>
              <TableCell>Timestamp</TableCell>
              <TableCell>Asset</TableCell>
              <TableCell>Side</TableCell>
              <TableCell align="right">Price</TableCell>
              <TableCell align="right">Size</TableCell>
              <TableCell align="right">Leverage</TableCell>
              <TableCell align="right">PnL</TableCell>
              <TableCell align="right">Fees</TableCell>
              <TableCell>Transaction</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {trades.map((trade) => (
              <TableRow key={trade.id} hover>
                <TableCell>
                  {formatDate(trade.timestamp)}
                </TableCell>
                <TableCell>
                  <Typography variant="body2" sx={{ fontFamily: 'monospace' }}>
                    {trade.asset}
                  </Typography>
                </TableCell>
                <TableCell>
                  <Chip
                    label={trade.side}
                    color={trade.side === 'BUY' ? 'success' : 'error'}
                    size="small"
                    variant="outlined"
                  />
                </TableCell>
                <TableCell align="right">
                  {formatCurrency(trade.price)}
                </TableCell>
                <TableCell align="right">
                  {formatNumber(trade.size)}
                </TableCell>
                <TableCell align="right">
                  {formatNumber(trade.leverage, 1)}x
                </TableCell>
                <TableCell align="right">
                  <Typography
                    variant="body2"
                    color={trade.closed_pnl >= 0 ? 'success.main' : 'error.main'}
                  >
                    {formatCurrency(trade.closed_pnl)}
                  </Typography>
                </TableCell>
                <TableCell align="right">
                  {formatCurrency(trade.fees)}
                </TableCell>
                <TableCell>
                  <Typography variant="body2" sx={{ fontFamily: 'monospace', fontSize: '0.75rem' }}>
                    {trade.tx_hash.substring(0, 8)}...{trade.tx_hash.substring(trade.tx_hash.length - 6)}
                  </Typography>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>
    </Paper>
  );
};

export default TradeHistory;