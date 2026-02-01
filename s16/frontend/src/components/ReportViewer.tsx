import React from 'react';
import {
  Card,
  CardContent,
  Typography,
  Grid,
  Box,
  Divider,
  Chip,
  LinearProgress,
  Accordion,
  AccordionSummary,
  AccordionDetails
} from '@mui/material';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import { ReportData } from '../types';
import { formatCurrency, formatPercentage, formatNumber, formatDate } from '../utils/formatters';

interface ReportViewerProps {
  report: ReportData;
  loading?: boolean;
}

const ReportViewer: React.FC<ReportViewerProps> = ({ report, loading = false }) => {
  if (loading) {
    return (
      <Card>
        <CardContent>
          <Typography variant="h6">Loading report...</Typography>
          <LinearProgress />
        </CardContent>
      </Card>
    );
  }

  if (!report) {
    return (
      <Card>
        <CardContent>
          <Typography variant="h6">No report data available</Typography>
        </CardContent>
      </Card>
    );
  }

  const { metadata, executive_summary, trader_overview, performance_overview } = report;

  return (
    <Box>
      <Card sx={{ mb: 3 }}>
        <CardContent>
          <Typography variant="h4" gutterBottom>
            Trading Performance Report
          </Typography>
          <Grid container spacing={2}>
            <Grid item xs={12} sm={6}>
              <Typography variant="subtitle2" color="text.secondary">
                Trader Address
              </Typography>
              <Typography variant="body1" sx={{ fontFamily: 'monospace' }}>
                {metadata.trader_address}
              </Typography>
            </Grid>
            <Grid item xs={12} sm={6}>
              <Typography variant="subtitle2" color="text.secondary">
                Report Generated
              </Typography>
              <Typography variant="body1">
                {formatDate(metadata.created_at)}
              </Typography>
            </Grid>
            <Grid item xs={12} sm={6}>
              <Typography variant="subtitle2" color="text.secondary">
                Data Period
              </Typography>
              <Typography variant="body1">
                {metadata.data_period_start ? formatDate(metadata.data_period_start) : 'N/A'} - {' '}
                {metadata.data_period_end ? formatDate(metadata.data_period_end) : 'N/A'}
              </Typography>
            </Grid>
            <Grid item xs={12} sm={6}>
              <Typography variant="subtitle2" color="text.secondary">
                Total Trades
              </Typography>
              <Typography variant="body1">
                {formatNumber(metadata.total_trades)}
              </Typography>
            </Grid>
          </Grid>
        </CardContent>
      </Card>

      <Accordion defaultExpanded>
        <AccordionSummary expandIcon={<ExpandMoreIcon />}>
          <Typography variant="h6">Executive Summary</Typography>
        </AccordionSummary>
        <AccordionDetails>
          <Grid container spacing={3}>
            <Grid item xs={12} sm={6} md={3}>
              <Box>
                <Typography variant="subtitle2" color="text.secondary">
                  Total Return
                </Typography>
                <Typography variant="h5" color={executive_summary.total_return_pct >= 0 ? 'success.main' : 'error.main'}>
                  {formatPercentage(executive_summary.total_return_pct)}
                </Typography>
              </Box>
            </Grid>
            <Grid item xs={12} sm={6} md={3}>
              <Box>
                <Typography variant="subtitle2" color="text.secondary">
                  Sharpe Ratio
                </Typography>
                <Typography variant="h5">
                  {formatNumber(executive_summary.sharpe_ratio, 2)}
                </Typography>
              </Box>
            </Grid>
            <Grid item xs={12} sm={6} md={3}>
              <Box>
                <Typography variant="subtitle2" color="text.secondary">
                  Max Drawdown
                </Typography>
                <Typography variant="h5" color="error.main">
                  {formatPercentage(executive_summary.max_drawdown_pct)}
                </Typography>
              </Box>
            </Grid>
            <Grid item xs={12} sm={6} md={3}>
              <Box>
                <Typography variant="subtitle2" color="text.secondary">
                  Win Rate
                </Typography>
                <Typography variant="h5" color="success.main">
                  {formatPercentage(executive_summary.win_rate_pct)}
                </Typography>
              </Box>
            </Grid>
          </Grid>
        </AccordionDetails>
      </Accordion>

      <Accordion>
        <AccordionSummary expandIcon={<ExpandMoreIcon />}>
          <Typography variant="h6">Trader Overview</Typography>
        </AccordionSummary>
        <AccordionDetails>
          <Grid container spacing={3}>
            <Grid item xs={12} sm={6} md={3}>
              <Box>
                <Typography variant="subtitle2" color="text.secondary">
                  Account Value
                </Typography>
                <Typography variant="h6">
                  {formatCurrency(trader_overview.account_value)}
                </Typography>
              </Box>
            </Grid>
            <Grid item xs={12} sm={6} md={3}>
              <Box>
                <Typography variant="subtitle2" color="text.secondary">
                  Margin Usage
                </Typography>
                <Chip
                  label={formatPercentage(trader_overview.margin_usage_pct)}
                  color={trader_overview.margin_usage_pct > 80 ? 'error' : trader_overview.margin_usage_pct > 50 ? 'warning' : 'success'}
                />
              </Box>
            </Grid>
            <Grid item xs={12} sm={6} md={3}>
              <Box>
                <Typography variant="subtitle2" color="text.secondary">
                  Margin Used
                </Typography>
                <Typography variant="h6">
                  {formatCurrency(trader_overview.margin_used)}
                </Typography>
              </Box>
            </Grid>
            <Grid item xs={12} sm={6} md={3}>
              <Box>
                <Typography variant="subtitle2" color="text.secondary">
                  Margin Available
                </Typography>
                <Typography variant="h6">
                  {formatCurrency(trader_overview.margin_available)}
                </Typography>
              </Box>
            </Grid>
          </Grid>
        </AccordionDetails>
      </Accordion>

      <Accordion>
        <AccordionSummary expandIcon={<ExpandMoreIcon />}>
          <Typography variant="h6">Performance Overview</Typography>
        </AccordionSummary>
        <AccordionDetails>
          <Grid container spacing={3}>
            <Grid item xs={12} sm={6} md={3}>
              <Box>
                <Typography variant="subtitle2" color="text.secondary">
                  Annualized Return
                </Typography>
                <Typography variant="h6" color={performance_overview.annualized_return_pct >= 0 ? 'success.main' : 'error.main'}>
                  {formatPercentage(performance_overview.annualized_return_pct)}
                </Typography>
              </Box>
            </Grid>
            <Grid item xs={12} sm={6} md={3}>
              <Box>
                <Typography variant="subtitle2" color="text.secondary">
                  Volatility
                </Typography>
                <Typography variant="h6">
                  {formatPercentage(performance_overview.volatility_pct)}
                </Typography>
              </Box>
            </Grid>
            <Grid item xs={12} sm={6} md={3}>
              <Box>
                <Typography variant="subtitle2" color="text.secondary">
                  Sortino Ratio
                </Typography>
                <Typography variant="h6">
                  {formatNumber(performance_overview.sortino_ratio, 2)}
                </Typography>
              </Box>
            </Grid>
            <Grid item xs={12} sm={6} md={3}>
              <Box>
                <Typography variant="subtitle2" color="text.secondary">
                  Calmar Ratio
                </Typography>
                <Typography variant="h6">
                  {formatNumber(performance_overview.calmar_ratio, 2)}
                </Typography>
              </Box>
            </Grid>
          </Grid>
        </AccordionDetails>
      </Accordion>

      {/* Additional sections can be added for other report data */}
    </Box>
  );
};

export default ReportViewer;