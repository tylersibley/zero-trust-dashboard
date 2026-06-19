import { BrowserRouter, Routes, Route } from 'react-router-dom';
import Layout from './components/Layout';
import Overview from './pages/Overview';
import UserDrilldown from './pages/UserDrilldown';
import LiveFeed from './pages/LiveFeed';
import RiskSimulator from './pages/RiskSimulator';
import AnomalyDetection from './pages/AnomalyDetection';
import Analytics from './pages/Analytics';

export default function App() {
  return (
    <BrowserRouter>
      <Layout>
        <Routes>
          <Route path="/"            element={<Overview />} />
          <Route path="/users"       element={<UserDrilldown />} />
          <Route path="/users/:userId" element={<UserDrilldown />} />
          <Route path="/live-feed"   element={<LiveFeed />} />
          <Route path="/simulate"    element={<RiskSimulator />} />
          <Route path="/anomalies"   element={<AnomalyDetection />} />
          <Route path="/analytics"   element={<Analytics />} />
        </Routes>
      </Layout>
    </BrowserRouter>
  );
}
