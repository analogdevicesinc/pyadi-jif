import axios from 'axios'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api'

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Converter API
export const converterApi = {
  getSupportedConverters: () => apiClient.get<string[]>('/converters/supported'),

  getConverterInfo: (part: string) => apiClient.get(`/converters/${part}/info`),

  getQuickModes: (part: string) => apiClient.get(`/converters/${part}/quick-modes`),

  getJESDControls: (part: string) => apiClient.post(`/converters/${part}/jesd-controls`),

  getValidModes: (part: string, config: any) =>
    apiClient.post(`/converters/${part}/valid-modes`, config),

  getDiagram: (part: string) => apiClient.get(`/converters/${part}/diagram`, {
    responseType: 'blob',
  }),
}

// Clock API
export const clockApi = {
  getSupportedClocks: () => apiClient.get<string[]>('/clocks/supported'),

  getConfigurableProperties: (part: string) =>
    apiClient.get(`/clocks/${part}/configurable-properties`),

  solveConfig: (part: string, config: any) =>
    apiClient.post(`/clocks/${part}/solve`, config),

  getDiagram: (part: string, config: any) =>
    apiClient.post(`/clocks/${part}/diagram`, config, {
      responseType: 'blob',
    }),
}

// System API
export const systemApi = {
  getFPGADevKits: () => apiClient.get<string[]>('/systems/fpga-dev-kits'),

  getFPGAConstraints: () => apiClient.get('/systems/fpga-constraints'),

  solveConfig: (config: any) => apiClient.post('/systems/solve', config),

  getDiagram: (config: any) =>
    apiClient.post('/systems/diagram', config, {
      responseType: 'blob',
    }),
}
