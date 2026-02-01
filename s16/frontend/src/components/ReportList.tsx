import React from 'react';
import {
  List,
  ListItem,
  ListItemText,
  ListItemSecondaryAction,
  IconButton,
  Typography,
  Box,
  Chip,
  Paper,
  Divider
} from '@mui/material';
import DownloadIcon from '@mui/icons-material/Download';
import DeleteIcon from '@mui/icons-material/Delete';
import { ReportListItem } from '../types';
import { formatDate, formatFileSize } from '../utils/formatters';

interface ReportListProps {
  reports: ReportListItem[];
  onDownload: (reportId: string) => void;
  onDelete: (reportId: string) => void;
  loading?: boolean;
}

const ReportList: React.FC<ReportListProps> = ({
  reports,
  onDownload,
  onDelete,
  loading = false
}) => {
  if (loading) {
    return (
      <Paper sx={{ p: 3 }}>
        <Typography variant="h6">Loading reports...</Typography>
      </Paper>
    );
  }

  if (!reports || reports.length === 0) {
    return (
      <Paper sx={{ p: 3 }}>
        <Typography variant="h6">No reports found</Typography>
        <Typography variant="body2" color="text.secondary">
          Generate your first report to get started.
        </Typography>
      </Paper>
    );
  }

  const getFormatColor = (format: string) => {
    switch (format.toLowerCase()) {
      case 'pdf': return 'error';
      case 'html': return 'primary';
      case 'json': return 'secondary';
      default: return 'default';
    }
  };

  return (
    <Paper>
      <Box sx={{ p: 3, pb: 0 }}>
        <Typography variant="h5" gutterBottom>
          Generated Reports
        </Typography>
        <Typography variant="body2" color="text.secondary" gutterBottom>
          {reports.length} reports available
        </Typography>
      </Box>
      <List>
        {reports.map((report, index) => (
          <React.Fragment key={report.report_id}>
            <ListItem>
              <ListItemText
                primary={
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                    <Typography variant="subtitle1">
                      Report {report.report_id.substring(0, 8)}
                    </Typography>
                    <Chip
                      label={report.format.toUpperCase()}
                      color={getFormatColor(report.format)}
                      size="small"
                    />
                  </Box>
                }
                secondary={
                  <Box sx={{ mt: 1 }}>
                    <Typography variant="body2" color="text.secondary">
                      Created: {formatDate(report.created_at)}
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      Size: {formatFileSize(report.size_bytes)}
                    </Typography>
                    {report.data_period_start && report.data_period_end && (
                      <Typography variant="body2" color="text.secondary">
                        Period: {formatDate(report.data_period_start)} - {formatDate(report.data_period_end)}
                      </Typography>
                    )}
                  </Box>
                }
              />
              <ListItemSecondaryAction>
                <IconButton
                  edge="end"
                  onClick={() => onDownload(report.report_id)}
                  title="Download report"
                >
                  <DownloadIcon />
                </IconButton>
                <IconButton
                  edge="end"
                  onClick={() => onDelete(report.report_id)}
                  title="Delete report"
                  color="error"
                >
                  <DeleteIcon />
                </IconButton>
              </ListItemSecondaryAction>
            </ListItem>
            {index < reports.length - 1 && <Divider />}
          </React.Fragment>
        ))}
      </List>
    </Paper>
  );
};

export default ReportList;