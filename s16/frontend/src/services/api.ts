import axios from 'axios';
import {
  TraderOverview,
  PerformanceOverview,
  ReturnMetrics,
  RiskMetrics,
  TradingStatistics,
  PositionAnalysis,
  Trade,
  Position,
  Funding,
  ReportRequest,
  ReportResponse,
  ReportData,
  ReportListItem,
  ApiError
} from '../types';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000/api';

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
});

// Request interceptor for auth if needed
api.interceptors.request.use(
  (config) => {
    // Add auth headers if needed
    return config;
  },
  (error) => Promise.reject(error)
);

// Response interceptor for error handling
api.interceptors.response.use(
  (response) => response,
  (error) => {
    const apiError: ApiError = {
      message: error.response?.data?.message || error.message || 'An error occurred',
      status: error.response?.status || 500,
      details: error.response?.data
    };
    return Promise.reject(apiError);
  }
);

export const traderApi = {
  // Get trader overview
  getTraderOverview: async (address: string): Promise<TraderOverview> => {
    const response = await api.get(`/traders/${address}/overview`);
    return response.data;
  },

  // Get trader trades
  getTraderTrades: async (address: string, limit?: number): Promise<Trade[]> => {
    const response = await api.get(`/traders/${address}/trades`, {
      params: { limit }
    });
    return response.data;
  },

  // Get trader positions
  getTraderPositions: async (address: string): Promise<Position[]> => {
    const response = await api.get(`/traders/${address}/positions`);
    return response.data;
  },

  // Get trader funding history
  getTraderFunding: async (address: string, limit?: number): Promise<Funding[]> => {
    const response = await api.get(`/traders/${address}/funding`, {
      params: { limit }
    });
    return response.data;
  }
};

export const metricsApi = {
  // Get performance overview
  getPerformanceOverview: async (address: string): Promise<PerformanceOverview> => {
    const response = await api.get(`/traders/${address}/performance`);
    return response.data;
  },

  // Get return metrics
  getReturnMetrics: async (address: string): Promise<ReturnMetrics> => {
    const response = await api.get(`/traders/${address}/returns`);
    return response.data;
  },

  // Get risk metrics
  getRiskMetrics: async (address: string): Promise<RiskMetrics> => {
    const response = await api.get(`/traders/${address}/risk`);
    return response.data;
  },

  // Get trading statistics
  getTradingStatistics: async (address: string): Promise<TradingStatistics> => {
    const response = await api.get(`/traders/${address}/statistics`);
    return response.data;
  },

  // Get position analysis
  getPositionAnalysis: async (address: string): Promise<PositionAnalysis> => {
    const response = await api.get(`/traders/${address}/positions/analysis`);
    return response.data;
  }
};

export const reportsApi = {
  // Generate a new report
  generateReport: async (request: ReportRequest): Promise<ReportResponse> => {
    const response = await api.post('/reports/generate', request);
    return response.data;
  },

  // Get report by ID
  getReport: async (reportId: string): Promise<ReportData> => {
    const response = await api.get(`/reports/${reportId}`);
    return response.data;
  },

  // Get list of reports for a trader
  getReportsList: async (address: string): Promise<ReportListItem[]> => {
    const response = await api.get(`/reports`, {
      params: { trader_address: address }
    });
    return response.data;
  },

  // Delete a report
  deleteReport: async (reportId: string): Promise<void> => {
    await api.delete(`/reports/${reportId}`);
  }
};

export default api;