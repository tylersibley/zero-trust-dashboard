import axios from 'axios';

const isProd = import.meta.env.PROD;
const BASE_URL = isProd
  ? 'https://x3z999sfec.execute-api.us-east-1.amazonaws.com/api/v1'
  : 'http://127.0.0.1:8000/api/v1';

const api = axios.create({
  baseURL: BASE_URL,
  timeout: 60000,
});

export const fetchSummary = () => api.get('/events/summary');
export const fetchAtRiskUsers = () => api.get('/users/at-risk');
export const fetchEvents = (limit = 50) => api.get(`/events?limit=${limit}`);
export const fetchBaseline = (userId) => api.get(`/ml/baseline/${userId}`);
export const simulateRisk = (payload) => api.post('/risk/simulate', payload);

export default api;
