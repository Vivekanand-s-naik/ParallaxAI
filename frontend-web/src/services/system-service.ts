import { apiClient } from './api-client';
import type {
  CommandCenterStatsResponse,
  SystemHealthResponse,
} from '@/types/governance';

/**
 * System & Command Center Service aligned with /api/v1/system/* endpoints.
 */
export const systemService = {
  async getCommandCenterStats(): Promise<CommandCenterStatsResponse> {
    const { data } =
      await apiClient.get<CommandCenterStatsResponse>('/system/stats');
    return data;
  },

  async getSystemHealth(): Promise<SystemHealthResponse> {
    const { data } =
      await apiClient.get<SystemHealthResponse>('/system/health');
    return data;
  },
};

