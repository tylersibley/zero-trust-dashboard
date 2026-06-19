import axios from 'axios';

const api = axios.create({
  baseURL: 'http://127.0.0.1:8000/api/v1',
  timeout: 10000,
});

export const fetchSummary = () => api.get('/events/summary');
export const fetchAtRiskUsers = () => api.get('/users/at-risk');
export const fetchEvents = (limit = 50) => api.get(`/events?limit=${limit}`);
export const fetchBaseline = (userId) => api.get(`/ml/baseline/${userId}`);
export const simulateRisk = (payload) => api.post('/risk/simulate', payload);

export default api;
