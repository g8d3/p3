import React from 'react';
import { Card, CardContent, Typography, Grid, Box, Chip } from '@mui/material';
import { TraderOverview as TraderOverviewType } from '../types';
import { formatCurrency, formatPercentage } from '../utils/formatters';

interface TraderOverviewProps {
  data: TraderOverviewType;
  loading?: boolean;
}

const TraderOverview: React.FC<TraderOverviewProps> = ({ data, loading = false }) => {
  if (loading) {
    return (
      <Card>
        <CardContent>
          <Typography variant="h6">Loading trader overview...</Typography>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardContent>
        <Typography variant="h5" gutterBottom>
          Trader Overview
        </Typography>
        <Grid container spacing={3}>
          <Grid item xs={12} sm={6} md={3}>
            <Box>
              <Typography variant="subtitle2" color="text.secondary">
                Account Value
              </Typography>
              <Typography variant="h6">
                {formatCurrency(data.account_value)}
              </Typography>
            </Box>
          </Grid>
          <Grid item xs={12} sm={6} md={3}>
            <Box>
              <Typography variant="subtitle2" color="text.secondary">
                Margin Used
              </Typography>
              <Typography variant="h6">
                {formatCurrency(data.margin_used)}
              </Typography>
            </Box>
          </Grid>
          <Grid item xs={12} sm={6} md={3}>
            <Box>
              <Typography variant="subtitle2" color="text.secondary">
                Margin Available
              </Typography>
              <Typography variant="h6">
                {formatCurrency(data.margin_available)}
              </Typography>
            </Box>
          </Grid>
          <Grid item xs={12} sm={6} md={3}>
            <Box>
              <Typography variant="subtitle2" color="text.secondary">
                Margin Usage
              </Typography>
              <Chip
                label={formatPercentage(data.margin_usage_pct)}
                color={data.margin_usage_pct > 80 ? 'error' : data.margin_usage_pct > 50 ? 'warning' : 'success'}
                size="small"
              />
            </Box>
          </Grid>
          {data.liquidation_price && (
            <Grid item xs={12} sm={6} md={3}>
              <Box>
                <Typography variant="subtitle2" color="text.secondary">
                  Liquidation Price
                </Typography>
                <Typography variant="h6">
                  {formatCurrency(data.liquidation_price)}
                </Typography>
              </Box>
            </Grid>
          )}
          <Grid item xs={12}>
            <Box>
              <Typography variant="subtitle2" color="text.secondary">
                Address
              </Typography>
              <Typography variant="body2" sx={{ fontFamily: 'monospace' }}>
                {data.address}
              </Typography>
            </Box>
          </Grid>
          <Grid item xs={12}>
            <Box>
              <Typography variant="subtitle2" color="text.secondary">
                Last Updated
              </Typography>
              <Typography variant="body2">
                {new Date(data.last_updated).toLocaleString()}
              </Typography>
            </Box>
          </Grid>
        </Grid>
      </CardContent>
    </Card>
  );
};

export default TraderOverview;