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
  Chip,
  Tooltip
} from '@mui/material';
import { Position } from '../types';
import { formatCurrency, formatDate, formatNumber, formatPercentage } from '../utils/formatters';

interface PositionListProps {
  positions: Position[];
  loading?: boolean;
}

const PositionList: React.FC<PositionListProps> = ({ positions, loading = false }) => {
  if (loading) {
    return (
      <Paper sx={{ p: 3 }}>
        <Typography variant="h6">Loading positions...</Typography>
      </Paper>
    );
  }

  if (!positions || positions.length === 0) {
    return (
      <Paper sx={{ p: 3 }}>
        <Typography variant="h6">No open positions</Typography>
        <Typography variant="body2" color="text.secondary">
          This trader currently has no open positions.
        </Typography>
      </Paper>
    );
  }

  return (
    <Paper>
      <Box sx={{ p: 3, pb: 0 }}>
        <Typography variant="h5" gutterBottom>
          Open Positions
        </Typography>
        <Typography variant="body2" color="text.secondary" gutterBottom>
          {positions.length} positions found
        </Typography>
      </Box>
      <TableContainer>
        <Table>
          <TableHead>
            <TableRow>
              <TableCell>Asset</TableCell>
              <TableCell align="right">Size</TableCell>
              <TableCell align="right">Entry Price</TableCell>
              <TableCell align="right">Mark Price</TableCell>
              <TableCell align="right">Leverage</TableCell>
              <TableCell align="right">Unrealized PnL</TableCell>
              <TableCell align="right">ROE</TableCell>
              <TableCell align="right">Margin Used</TableCell>
              <TableCell>Liquidation Price</TableCell>
              <TableCell>Last Updated</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {positions.map((position) => (
              <TableRow key={position.asset} hover>
                <TableCell>
                  <Typography variant="body2" sx={{ fontFamily: 'monospace' }}>
                    {position.asset}
                  </Typography>
                </TableCell>
                <TableCell align="right">
                  {formatNumber(position.size)}
                </TableCell>
                <TableCell align="right">
                  {formatCurrency(position.entry_price)}
                </TableCell>
                <TableCell align="right">
                  {formatCurrency(position.mark_price)}
                </TableCell>
                <TableCell align="right">
                  {formatNumber(position.leverage, 1)}x
                </TableCell>
                <TableCell align="right">
                  <Typography
                    variant="body2"
                    color={position.unrealized_pnl >= 0 ? 'success.main' : 'error.main'}
                  >
                    {formatCurrency(position.unrealized_pnl)}
                  </Typography>
                </TableCell>
                <TableCell align="right">
                  <Tooltip title={`Return on Equity: ${formatPercentage(position.roe)}`}>
                    <Chip
                      label={formatPercentage(position.roe)}
                      color={position.roe >= 0 ? 'success' : 'error'}
                      size="small"
                      variant="outlined"
                    />
                  </Tooltip>
                </TableCell>
                <TableCell align="right">
                  {formatCurrency(position.margin_used)}
                </TableCell>
                <TableCell>
                  <Typography variant="body2" color="error.main">
                    {formatCurrency(position.liquidation_price)}
                  </Typography>
                </TableCell>
                <TableCell>
                  {formatDate(position.timestamp)}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>
    </Paper>
  );
};

export default PositionList;