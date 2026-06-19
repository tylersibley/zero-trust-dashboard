import { BrowserRouter, Routes, Route } from 'react-router-dom';
import Layout from './components/Layout';
import Overview from './pages/Overview';
import UserDrilldown from './pages/UserDrilldown';
import LiveFeed from './pages/LiveFeed';

export default function App() {
  return (
    <BrowserRouter>
      <Layout>
        <Routes>
          <Route path="/"              element={<Overview />} />
          <Route path="/users"         element={<UserDrilldown />} />
          <Route path="/users/:userId" element={<UserDrilldown />} />
          <Route path="/live-feed"     element={<LiveFeed />} />
        </Routes>
      </Layout>
    </BrowserRouter>
  );
}
